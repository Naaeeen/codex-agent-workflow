"""Build only proxy_tools 0.1.0 from verified public inputs, without setup.py."""

import argparse
import base64
import csv
from hashlib import sha256
import io
from pathlib import Path
import sys
import tarfile
from urllib.request import ProxyHandler, build_opener
import zipfile


SDIST_URL = "https://files.pythonhosted.org/packages/f2/cf/77d3e19b7fabd03895caca7857ef51e4c409e0ca6b37ee6e9f7daa50b642/proxy_tools-0.1.0.tar.gz"
SDIST_SHA256 = "ccb3751f529c047e2d8a58440d86b205303cf0fe8146f784d1cbcd94f0a28010"
LICENSE_URL = "https://raw.githubusercontent.com/jtushman/proxy_tools/77369e4d321ed7b10d7b6e4885d7fe7a7ec2dfb7/LICENSE.txt"
LICENSE_SHA256 = "a428fb8a2e762af3eb0a6edbbb88e9b42ccfee80fd9b423958bcacf9b9abbfe4"
MODULE = "proxy_tools/__init__.py"
MODULE_SHA256 = "d1539d95e1a713c068ca81d42e047b2c76568964cf277596d4e19efb22f476be"
WHEEL_FILENAME = "proxy_tools-0.1.0-py3-none-any.whl"
DIST = "proxy_tools-0.1.0.dist-info"


def verify(data, expected, label):
    if sha256(data).hexdigest() != expected:
        raise ValueError(f"{label} checksum mismatch")
    return data


def build(sdist, license_text):
    verify(sdist, SDIST_SHA256, "source distribution")
    verify(license_text, LICENSE_SHA256, "upstream license")
    with tarfile.open(fileobj=io.BytesIO(sdist), mode="r:gz") as source:
        members = [member for member in source if member.name == f"proxy_tools-0.1.0/{MODULE}"]
        if len(members) != 1 or not members[0].isfile():
            raise ValueError("expected one regular module file in the source archive")
        with source.extractfile(members[0]) as stream:
            module = verify(stream.read(), MODULE_SHA256, "runtime module")

    # The release metadata says MIT. The identical runtime source and upstream
    # repository instead identify its redistribution notice as BSD.
    files = {
        MODULE: module,
        f"{DIST}/METADATA": (
            b"Metadata-Version: 2.4\nName: proxy_tools\nVersion: 0.1.0\n"
            b"Summary: Proxy Implementation\nLicense: BSD\nLicense-File: LICENSE.txt\n\n"
        ),
        f"{DIST}/WHEEL": b"Wheel-Version: 1.0\nGenerator: build_proxy_tools_wheel.py\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{DIST}/licenses/LICENSE.txt": license_text,
    }
    record_name = f"{DIST}/RECORD"
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, data in sorted(files.items()):
        digest = base64.urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode("ascii")
        writer.writerow([name, f"sha256={digest}", len(data)])
    writer.writerow([record_name, "", ""])
    files[record_name] = record.getvalue().encode("utf-8")

    wheel = io.BytesIO()
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    return wheel.getvalue()


def fetch(url):
    opener = build_opener(ProxyHandler({}))
    with opener.open(url, timeout=30) as response:
        return response.read(32 * 1024 + 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help=f"new path named {WHEEL_FILENAME}")
    parser.add_argument("--fetch", action="store_true", help="fetch the two pinned public inputs")
    parser.add_argument("--sdist", type=Path, help="local copy of the pinned PyPI source archive")
    parser.add_argument("--license", type=Path, help="local copy of the pinned upstream license")
    options = parser.parse_args()
    if options.output.name != WHEEL_FILENAME:
        parser.error(f"output filename must be {WHEEL_FILENAME}")
    if options.fetch and (options.sdist or options.license):
        parser.error("choose --fetch or both local inputs")
    if not options.fetch and not (options.sdist and options.license):
        parser.error("supply both local inputs or use --fetch")
    try:
        sdist = fetch(SDIST_URL) if options.fetch else options.sdist.read_bytes()
        license_text = fetch(LICENSE_URL) if options.fetch else options.license.read_bytes()
        wheel = build(sdist, license_text)
        with options.output.open("xb") as target:
            target.write(wheel)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    print(sha256(wheel).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
