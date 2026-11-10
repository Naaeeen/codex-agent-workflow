"""Explicitly install pinned runtime groups into a reproduced Codex environment."""

from __future__ import annotations

import sys

if __name__ == "__main__":
    sys.dont_write_bytecode = True

import argparse
import base64
import csv
from graphlib import CycleError, TopologicalSorter
import hashlib
import io
from itertools import groupby
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import zipfile
import zlib

import reproduce
from reproduce import ReproduceError


RECEIPT = ".dependency-receipt.json"
ID = re.compile(r"[a-z][a-z0-9-]{0,79}")
SHA = re.compile(r"[a-f0-9]{64}")
PIN = r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9][A-Za-z0-9_.+!-]*"
NPM_VERSION = re.compile(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.+-]+)?")
MAX_ASSET = 2 * 1024**3
MAX_UNPACKED = 4 * 1024**3
SETUP_PYTHONS = {"3.13.7": "--python313", "3.14.3": "--python314"}
MODEL_WEIGHTS = {"qmd-models", "docling-models"}


def relative(path, root=None, *, archive=False):
    # Upstream assets have verified digests and may use names like Serena's
    # memories module or npm's .npmrc for source code and release metadata.
    parts = reproduce.safe_parts(path, exclude_private=not archive)
    if root and (len(parts) < 2 or parts[0] != root):
        raise ReproduceError(f"expected a path under {root}/: {path!r}")
    if RECEIPT in (part.casefold() for part in parts):
        raise ReproduceError("dependency receipt path is reserved")
    return parts


def https_url(value, host=None):
    if not isinstance(value, str):
        raise ReproduceError("artifact URL must be a string")
    url = urlsplit(value)
    if (
        url.scheme != "https" or not url.hostname or url.username or url.password
        or url.fragment or (host and url.netloc != host)
    ):
        raise ReproduceError("expected a public HTTPS artifact URL")
    return value


def manifest(package):
    data = reproduce.read_regular(package / "dependencies.json")
    doc = json.loads(data, object_pairs_hook=reproduce.json_object)
    if (
        not isinstance(doc, dict) or doc.keys() != {"schema_version", "platform", "groups"}
        or type(doc["schema_version"]) is not int or doc["schema_version"] != 1
        or doc["platform"] != "windows-x64" or not isinstance(doc["groups"], list)
        or not doc["groups"]
    ):
        raise ReproduceError("expected nonempty windows-x64 dependency manifest v1")
    groups = {}
    targets = []
    required = {
        "download": {"target", "assets"},
        "npm": {"target", "requires", "recipe", "node", "npm"},
        "pip": {"target", "python_version"},
        "wheel": {"target", "recipe"},
        "manual": {"instructions"},
    }
    optional = {
        "download": {"requires"},
        "npm": {"omit_optional", "layout", "verified_copies"},
        "pip": {"recipe", "bootstrap_recipe", "integrity", "wheels", "wheel_inputs", "requires"},
        "wheel": set(),
        "manual": set(),
    }
    for group in doc["groups"]:
        if not isinstance(group, dict):
            raise ReproduceError("each dependency group must be an object")
        name, kind = group.get("id"), group.get("kind")
        if not isinstance(name, str) or not ID.fullmatch(name) or name in groups or not isinstance(kind, str) or kind not in required:
            raise ReproduceError("invalid or duplicate dependency group")
        keys = required[kind] | {"id", "kind"}
        if not keys <= group.keys() <= keys | optional[kind]:
            raise ReproduceError(f"invalid fields for {name}")
        if kind == "manual":
            if not isinstance(group["instructions"], str) or not group["instructions"].strip():
                raise ReproduceError(f"missing manual steps for {name}")
        else:
            target = relative(group["target"], "codex-home")
            harness_runtime = kind == "pip" and target == ("codex-home", "harness", "runtime")
            if not harness_runtime and (len(target) < 3 or target[1] != "tools"):
                raise ReproduceError(f"group target must be under codex-home/tools/: {name}")
            folded = tuple(x.casefold() for x in target)
            if any(folded[:len(t)] == t or t[:len(folded)] == folded for t in targets):
                raise ReproduceError(f"overlapping dependency targets: {name}")
            targets.append(folded)
        deps = group.get("requires", [])
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
            raise ReproduceError(f"requires must list group ids: {name}")
        if kind == "download":
            validate_assets(group["assets"])
        elif kind == "npm":
            layout = group.get("layout", "recipe")
            if layout not in ("recipe", "node_modules"):
                raise ReproduceError(f"invalid npm layout: {name}")
            if layout == "node_modules":
                if target[-1] != "node_modules":
                    raise ReproduceError(f"npm target must end in node_modules: {name}")
                if group["recipe"] != "/".join(target[:-1]):
                    relative(group["recipe"], "tooling")
            else:
                relative(group["recipe"], "tooling")
            relative(group["node"], "codex-home")
            relative(group["npm"], "codex-home")
            if not isinstance(group.get("omit_optional", False), bool):
                raise ReproduceError(f"invalid omit_optional: {name}")
            validate_npm_copies(group.get("verified_copies", []))
        elif kind == "pip":
            if not isinstance(group["python_version"], str) or not re.fullmatch(r"3\.\d+\.\d+", group["python_version"]):
                raise ReproduceError(f"invalid pinned base Python: {name}")
            if "recipe" in group:
                relative(group["recipe"], "tooling")
            if "bootstrap_recipe" in group:
                relative(group["bootstrap_recipe"], "tooling")
            if group.get("integrity", "hashes") not in ("hashes", "pins"):
                raise ReproduceError(f"invalid pip integrity mode: {name}")
            wheels = group.get("wheels", [])
            if not isinstance(wheels, list):
                raise ReproduceError(f"wheels must be an array: {name}")
            for wheel in wheels:
                if not relative(wheel, "tooling")[-1].endswith(".whl"):
                    raise ReproduceError(f"expected a managed wheel file: {name}")
            inputs = group.get("wheel_inputs", [])
            if not isinstance(inputs, list):
                raise ReproduceError(f"wheel_inputs must be an array: {name}")
            for wheel in inputs:
                if (
                    not isinstance(wheel, dict) or wheel.keys() != {"path", "sha256"}
                    or not relative(wheel["path"], "codex-home")[-1].endswith(".whl")
                    or not isinstance(wheel["sha256"], str) or not SHA.fullmatch(wheel["sha256"])
                ):
                    raise ReproduceError(f"invalid wheel input: {name}")
        elif kind == "wheel":
            relative(group["recipe"], "tooling")
        groups[name] = group
    for name, group in groups.items():
        deps = group.get("requires", [])
        if len(set(deps)) != len(deps) or any(dep == name or dep not in groups or groups[dep]["kind"] == "manual" for dep in deps):
            raise ReproduceError(f"invalid prerequisite ids for {name}")
        if group["kind"] == "npm":
            roots = tuple(groups[dep]["target"] + "/" for dep in deps if groups[dep]["kind"] == "download")
            if any(not group[key].startswith(roots) for key in ("node", "npm")):
                raise ReproduceError(f"npm runtime files must belong to a required download group: {name}")
        if group["kind"] == "pip":
            roots = tuple(groups[dep]["target"] + "/" for dep in deps if groups[dep]["kind"] == "wheel")
            if any(not wheel["path"].startswith(roots) for wheel in group.get("wheel_inputs", [])):
                raise ReproduceError(f"pip built-wheel inputs must belong to a required wheel group: {name}")
    try:
        TopologicalSorter({name: group.get("requires", []) for name, group in groups.items()}).prepare()
    except CycleError as error:
        raise ReproduceError("dependency prerequisites contain a cycle") from error
    return groups


def validate_assets(assets):
    if not isinstance(assets, list) or not assets:
        raise ReproduceError("download group requires one or more assets")
    for asset in assets:
        fields = {"url", "sha256", "format", "output"}
        if not isinstance(asset, dict) or not fields <= asset.keys() <= fields | {"strip_prefix", "member"}:
            raise ReproduceError("invalid download asset")
        https_url(asset["url"])
        if not isinstance(asset["sha256"], str) or not SHA.fullmatch(asset["sha256"]):
            raise ReproduceError("asset requires a lowercase SHA-256")
        if asset["format"] not in ("file", "zip", "tar.gz"):
            raise ReproduceError("unsupported artifact format")
        if asset["output"] != "." or asset["format"] == "file" or "member" in asset:
            relative(asset["output"])
        if "strip_prefix" in asset:
            relative(asset["strip_prefix"])
        if "member" in asset:
            relative(asset["member"])
        if asset["format"] == "file" and ("strip_prefix" in asset or "member" in asset):
            raise ReproduceError("a raw file asset does not have archive members")


def validate_npm_copies(copies):
    if not isinstance(copies, list):
        raise ReproduceError("npm verified_copies must be an array")
    targets = set()
    for entry in copies:
        if (
            not isinstance(entry, dict) or entry.keys() != {"sources", "target", "sha256"}
            or not isinstance(entry["sources"], list) or not entry["sources"]
            or not isinstance(entry["sha256"], str) or not SHA.fullmatch(entry["sha256"])
        ):
            raise ReproduceError("invalid npm verified copy")
        target = relative(entry["target"], "node_modules")
        key = "/".join(target).casefold()
        if key in targets or not target[-1].lower().endswith(".node"):
            raise ReproduceError("expected a unique native .node copy target")
        targets.add(key)
        for source in entry["sources"]:
            path = relative(source, "node_modules")
            if "/".join(path).casefold() == key or not path[-1].lower().endswith(".node"):
                raise ReproduceError("expected a distinct native .node copy source")


def apply_npm_copies(copies, recipe_root):
    for entry in copies:
        for source in entry["sources"]:
            source_path = recipe_root.joinpath(*relative(source, "node_modules"))
            try:
                data = reproduce.read_regular(source_path)
            except FileNotFoundError:
                continue
            if reproduce.sha256(data) == entry["sha256"]:
                break
        else:
            raise ReproduceError("npm native copy has no source matching the expected checksum")
        target = recipe_root.joinpath(*relative(entry["target"], "node_modules"))
        reproduce.directory(target.parent)
        if os.path.lexists(target):
            if reproduce.read_regular(target) != data:
                raise ReproduceError("npm native copy refuses to replace a different target")
        else:
            with target.open("xb") as stream:
                stream.write(data)


class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(asset, path):
    opener = build_opener(ProxyHandler({}), HTTPSRedirect())
    request = Request(https_url(asset["url"]), headers={"User-Agent": "Mozilla/5.0 codex-workflow-reproduce/1"})
    digest = hashlib.sha256()
    total = 0
    with opener.open(request, timeout=60) as response, path.open("xb") as stream:
        https_url(response.geturl())
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_ASSET:
                raise ReproduceError("artifact exceeds maximum download size")
            digest.update(chunk)
            stream.write(chunk)
    if digest.hexdigest() != asset["sha256"]:
        raise ReproduceError("download checksum mismatch")


def archive_paths(members, asset, output):
    """Validate all members and select regular files before copying any archive bytes."""
    prefix = relative(asset["strip_prefix"]) if "strip_prefix" in asset else ()
    selected = relative(asset["member"]) if "member" in asset else None
    base = () if asset["output"] == "." else relative(asset["output"])
    entries = []
    targets = set()
    total = 0
    for record, raw_name, is_dir, is_regular, size in members:
        if not is_dir and not is_regular:
            raise ReproduceError("archive contains a link or special file")
        parts = relative(raw_name.rstrip("/") if is_dir else raw_name, archive=True)
        if is_dir or parts[:len(prefix)] != prefix:
            continue
        parts = parts[len(prefix):]
        if selected is not None and parts != selected:
            continue
        target = base if selected is not None else base + parts
        normalized = "/".join(target).casefold()
        if not target or normalized in targets:
            raise ReproduceError("archive has duplicate or empty output names")
        targets.add(normalized)
        total += size
        if total > MAX_UNPACKED:
            raise ReproduceError("archive exceeds maximum unpacked size")
        entries.append((record, output.joinpath(*target)))
    if not entries:
        raise ReproduceError("archive selection produced no files")
    return entries


def zip_records(archive):
    for info in archive.infolist():
        kind = stat.S_IFMT(info.external_attr >> 16)
        if info.external_attr & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ReproduceError("archive contains a reparse point")
        is_dir = info.is_dir() and kind in (0, stat.S_IFDIR)
        is_regular = not info.is_dir() and kind in (0, stat.S_IFREG)
        yield info, info.orig_filename, is_dir, is_regular, info.file_size


def extract(asset, path, output):
    if asset["format"] == "file":
        target = output.joinpath(*relative(asset["output"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open("rb") as stream, target.open("xb") as handle:
            shutil.copyfileobj(stream, handle)
        return
    if asset["format"] == "zip":
        with zipfile.ZipFile(path) as archive:
            for info, target in archive_paths(zip_records(archive), asset, output):
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as stream, target.open("xb") as handle:
                    shutil.copyfileobj(stream, handle)
    else:
        with tarfile.open(path, "r:gz") as archive:
            members = [(info, info.name, info.isdir(), info.isfile(), info.size) for info in archive]
            for info, target in archive_paths(members, asset, output):
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(info) as stream, target.open("xb") as handle:
                    shutil.copyfileobj(stream, handle)


def managed_bytes(managed, name):
    if name not in managed:
        raise ReproduceError(f"recipe file is outside the verified managed package: {name}")
    return managed[name]


def npm_inputs(group, managed):
    root = group["recipe"]
    package = managed_bytes(managed, f"{root}/package.json")
    lock = managed_bytes(managed, f"{root}/package-lock.json")
    if group.get("layout") == "node_modules":
        tool_root = group["target"].rsplit("/", 1)[0]
        if package != managed_bytes(managed, f"{tool_root}/package.json") or lock != managed_bytes(managed, f"{tool_root}/package-lock.json"):
            raise ReproduceError("npm recipe differs from the tool's installed package files")
    project = json.loads(package, object_pairs_hook=reproduce.json_object)
    dependency_fields = {"dependencies", "devDependencies", "optionalDependencies", "peerDependencies", "overrides"}
    metadata = {"name", "version", "private", "description", "type"}
    if (
        not isinstance(project, dict) or project.keys() - (dependency_fields | metadata)
        or ("description" in project and not isinstance(project["description"], str))
        or ("type" in project and project["type"] not in ("module", "commonjs"))
    ):
        raise ReproduceError("npm recipe root has unsupported package.json fields")
    for field in project.keys() & dependency_fields:
        deps = project[field]
        if not isinstance(deps, dict) or any(not isinstance(v, str) or not NPM_VERSION.fullmatch(v) for v in deps.values()):
            raise ReproduceError(f"npm root {field} requires exact registry versions")
    doc = json.loads(lock, object_pairs_hook=reproduce.json_object)
    if not isinstance(doc, dict) or doc.get("lockfileVersion") != 3 or not isinstance(doc.get("packages"), dict) or "" not in doc["packages"]:
        raise ReproduceError("npm requires a v3 lockfile with a root package")
    for name, package_lock in doc["packages"].items():
        if not name:
            continue
        relative(name, "node_modules")
        if not isinstance(package_lock, dict) or package_lock.get("link"):
            raise ReproduceError("linked npm packages are not allowed")
        https_url(package_lock.get("resolved"), "registry.npmjs.org")
        integrity = package_lock.get("integrity", "")
        match = re.fullmatch(r"sha(256|384|512)-([A-Za-z0-9+/]+={0,2})", integrity) if isinstance(integrity, str) else None
        if not match or len(base64.b64decode(match.group(2), validate=True)) != int(match.group(1)) // 8:
            raise ReproduceError(f"npm package has no valid lockfile integrity: {name}")
    return {"package.json": package, "package-lock.json": lock}


def requirements_lines(requirements, hashed):
    pattern = re.compile(PIN + (r"(?:\s+--hash=sha256:[a-f0-9]{64})+" if hashed else ""))
    lines = []
    for raw in requirements.decode("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not pattern.fullmatch(line):
            raise ReproduceError(f"expected an exact {'hash-locked' if hashed else 'version-locked'} wheel requirement")
        lines.append(line)
    return lines


def requirement_key(name, version):
    return re.sub(r"[-_.]+", "-", name.casefold()), version.casefold()


def pip_bootstrap(group, managed):
    if "bootstrap_recipe" not in group:
        return b""
    requirements = managed_bytes(managed, group["bootstrap_recipe"])
    lines = requirements_lines(requirements, hashed=True)
    if len(lines) != 1 or not lines[0].lower().startswith("pip=="):
        raise ReproduceError("pip bootstrap requires exactly one SHA-256-locked pip wheel")
    return requirements


def pip_inputs(group, managed):
    recipe = group.get("recipe")
    requirements = managed_bytes(managed, recipe) if recipe else b""
    hashed = group.get("integrity", "hashes") == "hashes"
    requirements_lines(requirements, hashed)
    wheels = {}
    for path in group.get("wheels", []):
        name = relative(path)[-1]
        if name.casefold() in (x.casefold() for x in wheels):
            raise ReproduceError("duplicate managed wheel name")
        wheels[name] = managed_bytes(managed, path)
    return requirements, hashed, wheels


def wheel_recipe(group, managed):
    raw = managed_bytes(managed, group["recipe"])
    recipe = json.loads(raw, object_pairs_hook=reproduce.json_object)
    fields = {
        "schema_version", "url", "sha256", "filename", "output_sha256", "python_version",
        "zlib_runtime_version", "old_dist_info", "new_dist_info", "record_order",
        "normalize_metadata_newlines", "timestamps", "metadata_replacements",
    }
    if not isinstance(recipe, dict) or recipe.keys() != fields or type(recipe["schema_version"]) is not int or recipe["schema_version"] != 1:
        raise ReproduceError("invalid wheel reconstruction recipe fields")
    https_url(recipe["url"], "files.pythonhosted.org")
    for key in ("sha256", "output_sha256"):
        if not isinstance(recipe[key], str) or not SHA.fullmatch(recipe[key]):
            raise ReproduceError("wheel recipe requires exact upstream and output SHA-256")
    if len(relative(recipe["filename"])) != 1 or not recipe["filename"].endswith(".whl"):
        raise ReproduceError("expected a single output wheel filename")
    for key in ("old_dist_info", "new_dist_info"):
        if len(relative(recipe[key])) != 1 or not recipe[key].endswith(".dist-info"):
            raise ReproduceError("invalid wheel dist-info directory")
    if (
        recipe["old_dist_info"] == recipe["new_dist_info"]
        or not isinstance(recipe["python_version"], str) or not re.fullmatch(r"3\.\d+\.\d+", recipe["python_version"])
        or not isinstance(recipe["zlib_runtime_version"], str)
        or recipe["record_order"] not in ("sorted", "archive")
        or not isinstance(recipe["normalize_metadata_newlines"], bool)
    ):
        raise ReproduceError("invalid wheel reconstruction options")
    timestamps = recipe["timestamps"]
    if not isinstance(timestamps, list) or not timestamps:
        raise ReproduceError("wheel recipe requires at least one timestamp")
    last_index = -1
    for stamp in timestamps:
        if (
            not isinstance(stamp, dict) or stamp.keys() != {"from_index", "value"}
            or type(stamp["from_index"]) is not int or stamp["from_index"] <= last_index
            or not isinstance(stamp["value"], list) or len(stamp["value"]) != 6
            or any(type(x) is not int for x in stamp["value"])
        ):
            raise ReproduceError("invalid wheel member timestamp")
        zipfile.ZipInfo("probe", tuple(stamp["value"]))
        last_index = stamp["from_index"]
    if timestamps[0]["from_index"] != 0:
        raise ReproduceError("wheel timestamp sequence must start at member zero")
    replacements = recipe["metadata_replacements"]
    if not isinstance(replacements, list) or not replacements:
        raise ReproduceError("wheel recipe requires exact metadata substitutions")
    for item in replacements:
        if (
            not isinstance(item, dict) or item.keys() != {"old", "new"}
            or any(not isinstance(value, str) or not value or "\n" in value or "\r" in value for value in item.values())
        ):
            raise ReproduceError("invalid wheel metadata substitution")
    return recipe


def rebuild_wheel(source, destination, recipe):
    old_dist = recipe["old_dist_info"] + "/"
    new_dist = recipe["new_dist_info"] + "/"
    removed = {old_dist + name for name in ("RECORD", "RECORD.jws", "RECORD.p7s")}
    rows = []
    written = set()
    metadata_found = False

    def info_for(name, index):
        stamp = next(s for s in reversed(recipe["timestamps"]) if s["from_index"] <= index)
        info = zipfile.ZipInfo(name, tuple(stamp["value"]))
        info.create_system = 0
        info.compress_type = zipfile.ZIP_DEFLATED
        return info

    with zipfile.ZipFile(source) as upstream, zipfile.ZipFile(destination, "x") as patched:
        # Validate the complete pinned input before writing any payload members.
        archive_paths(zip_records(upstream), {"output": "."}, destination.parent)
        for item in upstream.infolist():
            name = item.filename
            if item.is_dir() or name in removed:
                continue
            data = upstream.read(item)
            target = new_dist + name[len(old_dist):] if name.startswith(old_dist) else name
            if target.casefold() in written:
                raise ReproduceError("duplicate reconstructed wheel member")
            written.add(target.casefold())
            if name == old_dist + "METADATA":
                metadata_found = True
                if recipe["normalize_metadata_newlines"]:
                    data = data.replace(b"\r\n", b"\n")
                for change in recipe["metadata_replacements"]:
                    old, new = change["old"].encode("utf-8"), change["new"].encode("utf-8")
                    if data.count(old) != 1:
                        raise ReproduceError("wheel metadata substitution did not match exactly once")
                    data = data.replace(old, new, 1)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
            patched.writestr(info_for(target, len(rows)), data)
            rows.append((target, "sha256=" + digest, str(len(data))))
        if not metadata_found:
            raise ReproduceError("wheel METADATA missing")
        if recipe["record_order"] == "sorted":
            rows.sort(key=lambda row: row[0])
        record = new_dist + "RECORD"
        if record.casefold() in written:
            raise ReproduceError("unexpected rebuilt wheel RECORD collision")
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerows([*rows, (record, "", "")])
        patched.writestr(info_for(record, len(rows)), stream.getvalue().encode("utf-8"))


def expected_wheel_inputs(group, destination):
    wheels = {}
    for item in group.get("wheel_inputs", []):
        path = destination.joinpath(*relative(item["path"], "codex-home"))
        data = reproduce.read_regular(path)
        if reproduce.sha256(data) != item["sha256"]:
            raise ReproduceError("reconstructed wheel checksum mismatch")
        if path.name.casefold() in (name.casefold() for name in wheels):
            raise ReproduceError("duplicate reconstructed wheel filename")
        wheels[path.name] = data
    return wheels


def child_environment(state, node=None):
    allowed = {"SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    paths = [str(node.parent)] if node else []
    paths.append(str(Path(env.get("SYSTEMROOT", r"C:\Windows")) / "System32") if os.name == "nt" else os.defpath)
    env["PATH"] = os.pathsep.join(paths)
    if os.name == "nt":
        env["PATHEXT"] = ".COM;.EXE;.BAT;.CMD"
    for key, suffix in {
        "HOME": "home", "USERPROFILE": "home", "APPDATA": "appdata", "LOCALAPPDATA": "localappdata",
        "TEMP": "temp", "TMP": "temp", "TMPDIR": "temp", "XDG_CACHE_HOME": "cache",
    }.items():
        path = state / suffix
        path.mkdir(exist_ok=True)
        env[key] = str(path)
    for name in ("user", "global"):
        path = state / f"{name}.npmrc"
        path.write_text("", encoding="utf-8")
        env[f"NPM_CONFIG_{name.upper()}CONFIG"] = str(path)
    env["NPM_CONFIG_CACHE"] = str(state / "npm-cache")
    env["NPM_CONFIG_UPDATE_NOTIFIER"] = "false"
    env["PIP_CONFIG_FILE"] = os.devnull
    return env


def run(command, cwd, env):
    subprocess.run([str(x) for x in command], cwd=cwd, env=env, check=True)


def verify_binary(path, *, check_parent=True):
    if check_parent:
        reproduce.directory(path.parent)
    info = path.lstat()
    if reproduce.is_link(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ReproduceError(f"expected a regular pinned runtime file: {path}")


def populate(group, output, state, destination, managed):
    kind = group["kind"]
    if kind == "download":
        for index, asset in enumerate(group["assets"]):
            file = state / f"asset-{index}"
            download(asset, file)
            extract(asset, file, output)
            file.unlink()
    elif kind == "npm":
        node = destination.joinpath(*relative(group["node"], "codex-home"))
        npm = destination.joinpath(*relative(group["npm"], "codex-home"))
        verify_binary(node)
        verify_binary(npm)
        modules_only = group.get("layout") == "node_modules"
        recipe_root = state / "npm-project" if modules_only else output
        recipe_root.mkdir(exist_ok=True)
        for name, data in npm_inputs(group, managed).items():
            (recipe_root / name).write_bytes(data)
        command = [node, npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund",
                   "--registry=https://registry.npmjs.org/", "--prefix", recipe_root]
        if group.get("omit_optional"):
            command.append("--omit=optional")
        run(command, recipe_root, child_environment(state, node))
        apply_npm_copies(group.get("verified_copies", []), recipe_root)
        if modules_only:
            modules = recipe_root / "node_modules"
            reproduce.directory(modules)
            output.rmdir()
            reproduce.rename_new(modules, output)
    elif kind == "wheel":
        recipe = wheel_recipe(group, managed)
        actual = platform.python_version(), zlib.ZLIB_RUNTIME_VERSION
        expected = recipe["python_version"], recipe["zlib_runtime_version"]
        if actual != expected:
            raise ReproduceError(f"Wheel byte reproduction requires Python/zlib {expected}. Running {actual}.")
        upstream = state / "upstream.whl"
        download(recipe, upstream)
        target = output / recipe["filename"]
        rebuild_wheel(upstream, target, recipe)
        if reproduce.sha256(reproduce.read_regular(target)) != recipe["output_sha256"]:
            raise ReproduceError("patched wheel output checksum mismatch")
    else:
        actual = platform.python_version()
        if actual != group["python_version"]:
            raise ReproduceError(f"{group['id']} requires base Python {group['python_version']}. Running {actual}.")
        requirements, hashed, wheels = pip_inputs(group, managed)
        bootstrap = pip_bootstrap(group, managed)
        for name, data in expected_wheel_inputs(group, destination).items():
            if name.casefold() in (known.casefold() for known in wheels):
                raise ReproduceError("wheel provided by both the managed package and a reconstruction group")
            wheels[name] = data
        env = child_environment(state)
        run([sys.executable, "-I", "-B", "-m", "venv", output], state, env)
        python = output / "Scripts" / "python.exe"
        verify_binary(python)
        command = [python, "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check",
                   "--no-cache-dir", "--require-virtualenv", "install", "--index-url",
                   "https://pypi.org/simple", "--only-binary=:all:", "--no-deps", "--no-compile"]
        if bootstrap:
            lock = state / "bootstrap.lock"
            lock.write_bytes(bootstrap)
            run([*command, "--force-reinstall", "--require-hashes", "-r", lock], state, env)
        wheelhouse = state / "wheelhouse"
        if wheels:
            wheelhouse.mkdir()
            for name, data in wheels.items():
                (wheelhouse / name).write_bytes(data)
        locked = {
            requirement_key(*line.split(maxsplit=1)[0].split("==", 1))
            for line in requirements_lines(requirements, hashed)
        }
        if requirements:
            lock = state / "requirements.lock"
            lock.write_bytes(requirements)
            local = ["--find-links", wheelhouse] if wheels else []
            run([*command, *local, *(["--require-hashes"] if hashed else []), "-r", lock], state, env)
        for name in wheels:
            parts = name.split("-", 2)
            if len(parts) != 3:
                raise ReproduceError("expected a wheel filename with its distribution and version")
            if requirement_key(*parts[:2]) not in locked:
                run([*command, "--no-index", wheelhouse / name], state, env)


def raise_walk_error(error):
    raise error


def tree_files(target):
    reproduce.directory(target)
    paths = {}
    for root, dirs, files in os.walk(target, followlinks=False, onerror=raise_walk_error):
        root = Path(root)
        for name in dirs:
            path = root / name
            info = path.lstat()
            if reproduce.is_link(info) or not stat.S_ISDIR(info.st_mode):
                raise ReproduceError(f"dependency tree contains a redirected directory: {path}")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        for name in files:
            path = root / name
            if path == target / RECEIPT:
                continue
            verify_binary(path, check_parent=False)
            paths[path.relative_to(target).as_posix()] = path
    return paths


def tree_digests(paths):
    digests = {}
    for relative_path, path in paths.items():
        with path.open("rb") as stream:
            digests[relative_path] = hashlib.file_digest(stream, "sha256").hexdigest()
    return digests


def group_receipt(group, paths, managed):
    spec = json.dumps(group, ensure_ascii=False, sort_keys=True).encode("utf-8")
    inputs = {}
    if group["kind"] == "npm":
        inputs = npm_inputs(group, managed)
    elif group["kind"] == "pip":
        requirements, _, wheels = pip_inputs(group, managed)
        inputs = {"requirements.lock": requirements, **wheels}
        bootstrap = pip_bootstrap(group, managed)
        if bootstrap:
            inputs["bootstrap.lock"] = bootstrap
    elif group["kind"] == "wheel":
        inputs = {"wheel-recipe.json": managed_bytes(managed, group["recipe"])}
    return {
        "group_sha256": reproduce.sha256(spec),
        "input_sha256": {key: reproduce.sha256(data) for key, data in inputs.items()},
        "files": tree_digests(paths),
    }


def check_installed(group, target, managed):
    if not os.path.lexists(target):
        raise ReproduceError(f"Install prerequisite {group['id']} first. Missing {target}")
    try:
        installed = json.loads(reproduce.read_regular(target / RECEIPT))
    except FileNotFoundError as error:
        raise ReproduceError(f"{group['id']} destination exists without a completion receipt: {target}") from error
    paths = tree_files(target)
    if (
        not isinstance(installed, dict) or not isinstance(installed.get("files"), dict)
        or installed["files"].keys() != paths.keys()
        or installed != group_receipt(group, paths, managed)
    ):
        raise ReproduceError(f"{group['id']} installation drift: {target}")


def create_parents(destination, parts):
    parent = destination
    for part in parts:
        parent = parent / part
        parent.mkdir(exist_ok=True)
        reproduce.directory(parent)


def install(group, destination, managed):
    parts = relative(group["target"], "codex-home")
    target = destination.joinpath(*parts)
    create_parents(destination, parts[:-1])
    with tempfile.TemporaryDirectory(prefix=".dependency-stage-", dir=target.parent) as name:
        stage = Path(name)
        state = stage / "state"
        state.mkdir()
        # Windows venv launchers embed their absolute path. Build only this kind at its final path.
        permanent = group["kind"] == "pip"
        output = target if permanent else stage / "payload"
        output.mkdir()
        try:
            populate(group, output, state, destination, managed)
            receipt = group_receipt(group, tree_files(output), managed)
            if not receipt["files"]:
                raise ReproduceError(f"empty dependency group: {group['id']}")
            receipt_data = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
            if permanent:
                staged_receipt = stage / RECEIPT
                staged_receipt.write_bytes(receipt_data)
                reproduce.rename_new(staged_receipt, output / RECEIPT)
            else:
                (output / RECEIPT).write_bytes(receipt_data)
                reproduce.rename_new(output, target)
        except BaseException:
            if permanent:
                reproduce.directory(output)
                if output.resolve().is_relative_to(destination.resolve()):
                    shutil.rmtree(output)
            raise


def operate(destination, names, apply=False, package=reproduce.PACKAGE):
    destination = Path(os.path.abspath(destination))
    groups = manifest(package)
    if any(name not in groups for name in names):
        raise ReproduceError("Unknown dependency group. Preview to see available IDs.")
    if apply and not names:
        raise ReproduceError("--apply requires at least one explicit --group")
    if apply:
        for name in names:
            if groups[name]["kind"] == "manual":
                raise ReproduceError(f"{name} has manual steps: {groups[name]['instructions']}")
    if apply and (os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}):
        raise ReproduceError("the provided runtime dependency manifest targets Windows x64")
    payload = reproduce.operate(destination, "verify", package)
    managed = {"/".join(item.target): item.data for item in payload}
    checked = set()

    def verify_group(name):
        if name in checked:
            return
        group = groups[name]
        if apply:
            for required in group.get("requires", []):
                verify_group(required)
        target = destination.joinpath(*relative(group["target"], "codex-home"))
        check_installed(group, target, managed)
        checked.add(name)

    for name in names or groups:
        group = groups[name]
        if group["kind"] == "manual":
            print(f"{name} [manual] {group['instructions']}")
            continue
        target = destination.joinpath(*relative(group["target"], "codex-home"))
        if os.path.lexists(target):
            verify_group(name)
            print(f"{name} [verified] {group['target']}")
            continue
        if group["kind"] == "npm":
            npm_inputs(group, managed)
        elif group["kind"] == "pip":
            pip_inputs(group, managed)
            pip_bootstrap(group, managed)
        elif group["kind"] == "wheel":
            wheel_recipe(group, managed)
        if not apply:
            print(f"{name} [plan {group['kind']}] {group['target']}")
            continue
        for dependency in group.get("requires", []):
            verify_group(dependency)
        install(group, destination, managed)
        checked.add(name)
        print(f"{name} [installed] {group['target']}")


def setup_order(groups, names, skip_model_weights):
    selected = []
    seen = set()

    def include(name):
        if name in seen:
            return
        if name not in groups:
            raise ReproduceError(f"Unknown setup group {name!r}. Preview to see available IDs.")
        group = groups[name]
        if group["kind"] == "manual":
            raise ReproduceError(f"Setup group {name} requires manual steps. {group['instructions']}")
        if skip_model_weights and name in MODEL_WEIGHTS:
            raise ReproduceError(f"Setup group {name} is required or selected while model weights are skipped.")
        for required in group.get("requires", []):
            include(required)
        selected.append(name)
        seen.add(name)

    if names:
        for name in names:
            include(name)
    else:
        for name, group in groups.items():
            if group["kind"] != "manual" and not (skip_model_weights and name in MODEL_WEIGHTS):
                include(name)
    return selected


def setup_python_requirements(groups, order, managed):
    required = {}
    for name in order:
        group = groups[name]
        kind = group["kind"]
        if kind == "npm":
            npm_inputs(group, managed)
        elif kind == "pip":
            pip_inputs(group, managed)
            pip_bootstrap(group, managed)
            required.setdefault(group["python_version"], set())
        elif kind == "wheel":
            recipe = wheel_recipe(group, managed)
            required.setdefault(recipe["python_version"], set()).add(recipe["zlib_runtime_version"])
    return required


def setup_probe_pythons(runtimes, required):
    for version in required:
        if not runtimes.get(version):
            flag = SETUP_PYTHONS.get(version, version)
            raise ReproduceError(f"Setup requires Python {version}. Supply its executable via {flag}.")
    probe = (
        "import json, platform, struct, zlib\n"
        "print(json.dumps([platform.python_version(), platform.machine().lower(),"
        "struct.calcsize('P'), zlib.ZLIB_RUNTIME_VERSION]))"
    )
    resolved = {}
    for expected, raw in runtimes.items():
        if not raw:
            continue
        executable = raw.resolve(strict=True)
        if not executable.is_file() or executable.suffix.lower() != ".exe":
            raise ReproduceError(f"Select the native Python {expected} executable.")
        result = subprocess.run(
            [str(executable), "-I", "-B", "-c", probe],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        version, machine, word_size, zlib_version = json.loads(result.stdout)
        if version != expected or machine not in {"amd64", "x86_64"} or word_size != 8:
            raise ReproduceError(f"Setup needs x64 Python {expected}. Selected {version} ({machine}, {word_size * 8}-bit).")
        supported = required.get(expected, set())
        if supported and supported != {zlib_version}:
            raise ReproduceError(f"Python {expected} must have zlib {', '.join(sorted(supported))}. Selected {zlib_version}.")
        resolved[expected] = executable
    return resolved


def setup(destination, names, runtimes, apply=False, skip_model_weights=False, package=reproduce.PACKAGE):
    destination = reproduce.destination_path(destination, package)
    groups = manifest(package)
    order = setup_order(groups, names, skip_model_weights)
    if not order:
        raise ReproduceError("No automatic dependency groups selected.")
    existing = os.path.lexists(destination)
    payload = reproduce.operate(destination, "verify" if existing else "plan", package)
    managed = {"/".join(item.target): item.data for item in payload}
    required = setup_python_requirements(groups, order, managed)
    for name in order:
        group = groups[name]
        target = destination.joinpath(*relative(group["target"], "codex-home"))
        if os.path.lexists(target):
            check_installed(group, target, managed)
    print(f"Configuration [{'verified' if existing else 'plan'}] {len(payload)} managed files at {destination}")
    for name in order:
        group = groups[name]
        prerequisites = ", ".join(group.get("requires", [])) or "-"
        print(f"{name} [{group['kind']}] {group['target']} (requires {prerequisites})")
    if not apply:
        return order
    sys.stdout.flush()
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ReproduceError("the provided runtime dependency manifest targets Windows x64")
    executables = setup_probe_pythons(runtimes, required)
    if not existing:
        reproduce.operate(destination, "apply", package)
    def interpreter(name):
        group = groups[name]
        version = group.get("python_version")
        if group["kind"] == "wheel":
            version = wheel_recipe(group, managed)["python_version"]
        return executables[version] if version else Path(sys.executable)

    backend = Path(__file__).resolve()
    for executable, consecutive in groupby(order, key=interpreter):
        arguments = [flag for name in consecutive for flag in ("--group", name)]
        subprocess.run(
            [str(executable), "-E", "-s", "-B", str(backend), str(destination), "--apply", *arguments],
            check=True,
        )
    quoted_python = sys.executable.replace("'", "''")
    quoted_launcher = str(destination / "launch.py").replace("'", "''")
    command = f"& '{quoted_python}' '{quoted_launcher}'"
    print("Verify the CLI version")
    print(f"{command} -- --version")
    print("Launch the installed workflow")
    print(command)
    return order


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="existing destination from reproduce.py --apply")
    parser.add_argument("--group", action="append", default=[], help="group id, repeat for ordered installs")
    parser.add_argument("--apply", action="store_true", help="enable the selected downloads and installs")
    parser.add_argument("--setup", action="store_true", help="plan or apply a complete environment and its dependencies")
    parser.add_argument("--python313", type=Path, help="exact x64 Python 3.13.7 executable for setup")
    parser.add_argument("--python314", type=Path, help="exact x64 Python 3.14.3 executable for setup")
    parser.add_argument("--skip-model-weights", action="store_true", help="skip the model weight groups during setup")
    args = parser.parse_args()
    if not args.setup and (args.python313 or args.python314 or args.skip_model_weights):
        parser.error("runtime and model weight options require --setup")
    try:
        if args.setup:
            runtimes = {"3.13.7": args.python313, "3.14.3": args.python314}
            setup(args.destination, args.group, runtimes, args.apply, args.skip_model_weights)
        else:
            operate(args.destination, args.group, args.apply)
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
