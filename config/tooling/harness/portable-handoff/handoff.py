"""Portable, offline data-movement contract. Never executes bundle commands."""
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

from safe_io import LedgerError, regular_read, require, secure_path

MAX_FILE = 1024 * 1024
MAX_TOTAL = 8 * MAX_FILE
MAX_PACKAGE = 12 * MAX_FILE
MAX_FILES = 64
HASH = re.compile(r"[0-9a-f]{64}\Z")
RESERVED = {"con", "prn", "aux", "nul", "conin$", "conout$",
            *(f"com{i}" for i in "123456789\u00b9\u00b2\u00b3"),
            *(f"lpt{i}" for i in "123456789\u00b9\u00b2\u00b3")}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(value):
    require(isinstance(value, str) and 0 < len(value) <= 240, "Invalid relative path")
    require(not any(ord(c) < 32 for c in value), "Control character in path")
    require(not any(c in value for c in '\\:*?"<>|'), "Non-portable path")
    parts = value.split("/")
    require(all(p and p not in (".", "..") and not p.endswith((" ", "."))
                and p.split(".")[0].rstrip(" ").casefold() not in RESERVED for p in parts), "Unsafe path")
    require(not PurePosixPath(value).is_absolute(), "Absolute path forbidden")
    for part in parts:
        low = part.casefold()
        require(low not in {".git", ".codex", ".ssh", ".aws", ".azure", ".gcloud", "credentials",
                            "credentials.json", "auth.json", "token.json", "tokens.json", "secrets.json",
                            "id_rsa", "id_ed25519", ".npmrc", ".pypirc", ".netrc"}
                and not low.startswith(".env") and not low.endswith((".pem", ".key", ".p12", ".pfx")),
                "Common secret or private-state path forbidden")
    return value


def paths_unique(paths):
    folded = [p.casefold() for p in paths]
    require(len(folded) == len(set(folded)), "Duplicate or case-colliding paths")
    for a in folded:
        require(not any(b.startswith(a + "/") for b in folded), "File/directory collision")
    spellings = {}
    for path in paths:
        parts = path.split("/")
        for end in range(1, len(parts) + 1):
            prefix = "/".join(parts[:end])
            require(spellings.setdefault(prefix.casefold(), prefix) == prefix,
                    "Inconsistent path component case")


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), "Invalid object schema")


def strings(value, label):
    require(isinstance(value, list) and 0 < len(value) <= 64, f"Invalid {label}")
    require(all(isinstance(x, str) and 0 < len(x) <= 4096 and "\x00" not in x for x in value),
            f"Invalid {label} text")


def contract(value):
    keys(value, {"runtime", "command", "outputs", "acceptance"})
    keys(value["runtime"], {"name", "version", "recipe"})
    strings([value["runtime"]["name"], value["runtime"]["version"]], "runtime")
    strings(value["runtime"]["recipe"], "recipe")
    cmd = value["command"]
    keys(cmd, {"argv", "cwd", "timeout_seconds"})
    strings(cmd["argv"], "argv")
    for arg in cmd["argv"]:
        require(not arg.startswith(("/", "\\")) and not re.match(r"^[A-Za-z]:", arg)
                and ".." not in arg.replace("\\", "/").split("/"), "Non-portable argv")
    require(cmd["cwd"] == "." or relative(cmd["cwd"]), "Invalid cwd")
    require(type(cmd["timeout_seconds"]) is int and 1 <= cmd["timeout_seconds"] <= 60,
            "Timeout must be 1..60 seconds")
    strings(value["acceptance"], "acceptance")
    outputs = value["outputs"]
    require(isinstance(outputs, list) and 0 < len(outputs) <= MAX_FILES, "Invalid output count")
    for entry in outputs:
        keys(entry, {"path", "max_bytes", "sha256"})
        relative(entry["path"])
        require(type(entry["max_bytes"]) is int and 0 <= entry["max_bytes"] <= MAX_FILE, "Invalid output limit")
        require(isinstance(entry["sha256"], str) and HASH.fullmatch(entry["sha256"]), "Invalid expected output hash")
    paths_unique([x["path"] for x in outputs])
    return value


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "Duplicate JSON key")
        obj[key] = value
    return obj


def load(path):
    try:
        return json.loads(regular_read(Path(path).absolute(), MAX_PACKAGE).decode("utf-8"),
                          object_pairs_hook=unique_object)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise LedgerError("Invalid JSON") from exc


def encoded_file(path, data):
    return {"path": path, "size": len(data), "sha256": digest(data),
            "base64": base64.b64encode(data).decode("ascii")}


def validate_files(files):
    require(isinstance(files, list) and 0 < len(files) <= MAX_FILES, "Invalid file count")
    decoded = {}
    total = 0
    for item in files:
        keys(item, {"path", "size", "sha256", "base64"})
        relative(item["path"])
        require(type(item["size"]) is int and 0 <= item["size"] <= MAX_FILE, "Invalid file size")
        require(isinstance(item["base64"], str) and len(item["base64"]) <= 4 * ((MAX_FILE + 2) // 3),
                "Oversized encoded file")
        try:
            data = base64.b64decode(item["base64"], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise LedgerError("Invalid base64") from exc
        require(len(data) == item["size"] and digest(data) == item["sha256"], "File integrity mismatch")
        total += len(data)
        require(total <= MAX_TOTAL, "Total payload exceeds limit")
        require(item["path"] not in decoded, "Duplicate file")
        decoded[item["path"]] = data
    paths_unique(list(decoded))
    return decoded


def validate_bundle(bundle):
    keys(bundle, {"format", "contract", "files"})
    require(bundle["format"] == "portable-handoff-v1", "Unknown bundle format")
    contract(bundle["contract"])
    data = validate_files(bundle["files"])
    paths_unique(list(data) + [x["path"] for x in bundle["contract"]["outputs"]])
    cwd = bundle["contract"]["command"]["cwd"]
    require(cwd == "." or any(p.startswith(cwd + "/") for p in data), "Command cwd missing from inputs")
    return data


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def save_new(path, data):
    target = secure_path(Path(path).absolute(), must_exist=False)
    require(target.parent.is_dir(), "Output parent must exist")
    require(len(data) <= MAX_PACKAGE, "Package exceeds limit")
    with target.open("xb") as stream:
        stream.write(data)


def prepare(source, spec):
    keys(spec, {"inputs", "contract"})
    contract(spec["contract"])
    require(isinstance(spec["inputs"], list) and 0 < len(spec["inputs"]) <= MAX_FILES, "Invalid input count")
    paths_unique([relative(p) for p in spec["inputs"]])
    root = secure_path(Path(source).absolute(), kind="dir")
    bundle = {"format": "portable-handoff-v1", "contract": spec["contract"], "files": [
        encoded_file(p, regular_read(root / p, MAX_FILE)) for p in spec["inputs"]]}
    validate_bundle(bundle)
    return bundle


def extract_data(data, destination):
    # All content validated before the first directory/file write. A fresh exclusive
    # destination prevents overwrites; filesystem errors may leave partial output.
    root = secure_path(Path(destination).absolute(), must_exist=False)
    require(root.parent.is_dir(), "Destination parent must exist")
    require(not root.exists(), "Destination must not already exist")
    root.mkdir()
    for name, content in data.items():
        target = root / name
        secure_path(target, must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        secure_path(target, must_exist=False)
        with target.open("xb") as stream:
            stream.write(content)


def collect(bundle, workspace):
    inputs = validate_bundle(bundle)
    root = secure_path(Path(workspace).absolute(), kind="dir")
    outputs = bundle["contract"]["outputs"]
    allowed = set(inputs) | {x["path"] for x in outputs}
    actual = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = secure_path(Path(directory) / name)
            if path.is_file():
                actual.add(path.relative_to(root).as_posix())
            else:
                rel = path.relative_to(root).as_posix()
                require(any(p.startswith(rel + "/") for p in allowed), "Unknown output directory")
    require(actual == allowed, "Missing or unknown workspace file")
    for name, expected in inputs.items():
        require(regular_read(root / name, MAX_FILE) == expected, "Input changed during execution")
    files = []
    for output in outputs:
        data = regular_read(root / output["path"], output["max_bytes"])
        require(digest(data) == output["sha256"], "Output acceptance hash mismatch")
        files.append(encoded_file(output["path"], data))
    result = {"format": "portable-handoff-result-v1", "bundle_sha256": digest(canonical(bundle)), "files": files}
    validate_result(bundle, result)
    return result


def validate_result(bundle, result):
    validate_bundle(bundle)
    keys(result, {"format", "bundle_sha256", "files"})
    require(result["format"] == "portable-handoff-result-v1", "Invalid result format")
    require(result["bundle_sha256"] == digest(canonical(bundle)), "Result belongs to a different bundle")
    data = validate_files(result["files"])
    outputs = bundle["contract"]["outputs"]
    require(set(data) == {x["path"] for x in outputs}, "Missing or unknown result output")
    for output in outputs:
        content = data[output["path"]]
        require(len(content) <= output["max_bytes"] and digest(content) == output["sha256"],
                "Result acceptance mismatch")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("source"); p.add_argument("spec"); p.add_argument("bundle")
    for action in ("verify", "extract", "collect", "verify-result", "extract-result"):
        p = sub.add_parser(action); p.add_argument("bundle")
        if action == "extract": p.add_argument("destination")
        if action == "collect": p.add_argument("workspace"); p.add_argument("result")
        if action in ("verify-result", "extract-result"): p.add_argument("result")
        if action == "extract-result": p.add_argument("destination")
    args = parser.parse_args()
    if args.action == "prepare":
        bundle = prepare(args.source, load(args.spec)); save_new(args.bundle, canonical(bundle))
    else:
        bundle = load(args.bundle); data = validate_bundle(bundle)
        if args.action == "extract": extract_data(data, args.destination)
        if args.action == "collect": save_new(args.result, canonical(collect(bundle, args.workspace)))
        if args.action in ("verify-result", "extract-result"):
            data = validate_result(bundle, load(args.result))
            if args.action == "extract-result": extract_data(data, args.destination)
    print(json.dumps({"status": "ok", "action": args.action}))


if __name__ == "__main__":
    try:
        main()
    except (LedgerError, OSError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        sys.exit(2)
