#!/usr/bin/env python3
"""Fetch approved files or stage the static dots.oag.sh deployment."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
BASE = "https://dots.oag.sh/"
LIMIT = 25 * 1024 * 1024


def digest(path):
    with path.open("rb") as source:
        value = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
        return value.hexdigest()


def catalog():
    data = json.loads((ROOT / "artifacts.json").read_text())
    paths = set()
    for entry in data["files"].values():
        path = Path(entry["path"])
        if (path.is_absolute() or ".." in path.parts or not entry["path"].startswith("assets/")
                or entry["path"] in paths):
            raise ValueError(f"invalid or duplicate asset path: {path}")
        paths.add(entry["path"])
        if len(entry["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in entry["sha256"]):
            raise ValueError(f"invalid SHA-256: {path}")
        if not entry["source"].startswith("https://"):
            raise ValueError(f"source must use HTTPS: {path}")
        if entry.get("source_type", "direct") not in ("direct", "ocs"):
            raise ValueError(f"unsupported source type: {path}")
    for key in data["current"].values():
        if key not in data["files"]:
            raise ValueError(f"unknown current artifact: {key}")
    return data


def source_url(entry):
    if entry.get("source_type") != "ocs":
        return entry["source"]
    # KDE Store download links expire. Resolve them only for upstream staging;
    # clients still use the immutable mirror path and the pinned SHA-256.
    metadata = subprocess.check_output([
        "curl", "--proto", "=https", "--proto-redir", "=https", "-fsSL",
        "--connect-timeout", "15", "--max-time", "30", "--max-filesize", "1048576",
        entry["source"],
    ])
    root = ET.fromstring(metadata)
    url = root.findtext("./data/content/downloadlink1", "")
    if root.findtext("./meta/statuscode") != "100" or not url.startswith("https://"):
        raise ValueError(f"OCS source did not return an HTTPS download: {entry['source']}")
    return url


def fetch(entry, destination, *, upstream=False, force=False):
    destination = Path(destination)
    if not force and destination.is_file() and digest(destination) == entry["sha256"]:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        url = source_url(entry) if upstream else BASE + entry["path"]
        subprocess.run(["curl", "--proto", "=https", "--proto-redir", "=https",
                        "--tlsv1.2", "-fsSL", "--connect-timeout", "15", "--max-time", "180",
                        "--max-filesize", str(LIMIT), "-o", str(temporary), url], check=True)
        if temporary.stat().st_size > LIMIT or digest(temporary) != entry["sha256"]:
            raise ValueError(f"size or SHA-256 mismatch: {url}")
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def starship_target():
    arch = platform.machine().lower()
    arch = {"amd64": "x86_64", "arm64": "aarch64", "riscv64": "riscv64gc",
            "i386": "i686", "i586": "i686"}.get(arch, arch)
    if arch.startswith("armv"):
        arch = "arm"
    if sys.maxsize <= 2**32:
        arch = {"x86_64": "i686", "aarch64": "arm"}.get(arch, arch)
    system = platform.system()
    if system == "Linux":
        return f"{arch}-unknown-linux-musl" + ("eabihf" if arch == "arm" else "")
    if system == "Darwin":
        return f"{arch}-apple-darwin"
    if system == "FreeBSD":
        return f"{arch}-unknown-freebsd"
    raise ValueError(f"unsupported Starship platform: {system}/{arch}")


def install_starship(data, destination):
    key = "starship-" + starship_target()
    if key not in data["current"]:
        raise ValueError(f"no approved archive for {key}")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        archive = Path(temporary) / "starship.tar.gz"
        fetch(data["files"][data["current"][key]], archive)
        binary = Path(temporary) / "starship"
        with tarfile.open(archive) as tar:
            member = tar.getmember("starship")
            if not member.isfile():
                raise ValueError("Starship archive does not contain a regular binary")
            with tar.extractfile(member) as source, binary.open("wb") as output:
                shutil.copyfileobj(source, output)
        binary.chmod(0o755)
        os.replace(binary, destination)


def stage(data, upstream=False):
    public = ROOT / "public"
    expected = {entry["path"] for entry in data["files"].values()} | {"init.sh", "_headers", "_redirects"}
    actual = {str(path.relative_to(public)) for path in public.rglob("*") if path.is_file()}
    # Check before writing too: a symlink must not redirect staging into local files.
    if (actual - expected or public.is_symlink()
            or any(path.is_symlink() for path in public.rglob("*"))):
        raise ValueError("public/ contains unexpected files or symlinks; inspect before publishing")
    for entry in data["files"].values():
        fetch(entry, public / entry["path"], upstream=upstream)
    shutil.copyfile(ROOT.parent / "init.sh", public / "init.sh")
    for name in ("_headers", "_redirects"):
        shutil.copyfile(ROOT / name, public / name)
    # Refuse to publish stray files, including local config or stale partials.
    actual = {str(path.relative_to(public)) for path in public.rglob("*") if path.is_file()}
    if actual != expected or any(path.is_symlink() for path in public.rglob("*")):
        raise ValueError("public/ contains unexpected files or symlinks; inspect before publishing")
    print(f"Staged {len(data['files'])} approved files and init.sh")


def verify(data):
    with tempfile.TemporaryDirectory() as temporary:
        for entry in data["files"].values():
            fetch(entry, Path(temporary) / "asset", force=True)
        entry = {"path": "", "sha256": digest(ROOT.parent / "init.sh")}
        fetch(entry, Path(temporary) / "init.sh", force=True)
    print(f"Verified live bootstrap and {len(data['files'])} asset hashes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    get = commands.add_parser("fetch", help="fetch a current artifact from dots.oag.sh")
    get.add_argument("name")
    get.add_argument("destination", type=Path)
    starship = commands.add_parser("starship", help="install the approved platform binary")
    starship.add_argument("destination", type=Path)
    build = commands.add_parser("stage", help="stage all retained versions for deployment")
    build.add_argument("--upstream", action="store_true", help="fetch missing files from recorded upstreams")
    commands.add_parser("verify", help="verify every live file against this checkout")
    args = parser.parse_args()
    try:
        data = catalog()
        if args.command == "fetch":
            fetch(data["files"][data["current"][args.name]], args.destination)
        elif args.command == "starship":
            install_starship(data, args.destination)
        elif args.command == "stage":
            stage(data, args.upstream)
        else:
            verify(data)
    except (OSError, ValueError, KeyError, ET.ParseError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f"artifacts: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
