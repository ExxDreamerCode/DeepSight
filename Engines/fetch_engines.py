from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
PINS_FILE = Path(os.environ.get("DEEPSIGHT_PINS", ROOT / "engines.json"))
USER_AGENT = "DeepSight build"

_SYSTEM_NAMES = {"windows": "windows", "darwin": "macos", "linux": "linux"}
_ARCH_NAMES = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "x64": "x86_64",
    "arm64": "arm64",
    "aarch64": "arm64",
}


def load_pins(path: Optional[Path] = None) -> Dict[str, Any]:
    with open(path or PINS_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def find_target(pins: Dict[str, Any], target_id: str) -> Dict[str, Any]:
    for target in pins["targets"]:
        if target["id"] == target_id:
            return target
    known = ", ".join(target["id"] for target in pins["targets"])
    raise SystemExit(f"unknown target {target_id!r}, engines.json has: {known}")


def target_id_for(system: str, machine: str) -> str:
    name = _SYSTEM_NAMES.get(system.lower())
    if name is None:
        raise SystemExit(f"unsupported system: {system}")
    arch = _ARCH_NAMES.get(machine.lower())
    if arch is None:
        raise SystemExit(f"unsupported architecture: {machine}")
    return f"{name}-{arch}"


def current_target(pins: Dict[str, Any]) -> Dict[str, Any]:
    return find_target(pins, target_id_for(platform.system(), platform.machine()))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response, open(destination, "wb") as handle:
        shutil.copyfileobj(response, handle)


def _archive_member(names: List[str], wanted: str) -> str:
    if wanted in names:
        return wanted
    basename = Path(wanted).name
    for name in names:
        if Path(name).name == basename:
            return name
    raise SystemExit(f"{wanted!r} is not in the archive, it has: {', '.join(names[:6])}")


def extract_member(archive: Path, member: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            name = _archive_member(bundle.namelist(), member)
            with bundle.open(name) as source, open(destination, "wb") as target:
                shutil.copyfileobj(source, target)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as bundle:
            name = _archive_member(bundle.getnames(), member)
            source = bundle.extractfile(name)
            if source is None:
                raise SystemExit(f"{name!r} is not a regular file")
            with source, open(destination, "wb") as target:
                shutil.copyfileobj(source, target)
    else:
        raise SystemExit(f"{archive} is neither a zip nor a tar archive")

    destination.chmod(0o755)


def clone_source(entry: Dict[str, Any], workdir: Path) -> Path:
    source = workdir / "source"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", entry["tag"], entry["repo"], str(source)],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != entry["commit"]:
        raise SystemExit(f"{entry['tag']} points at {head}, expected {entry['commit']}")
    return source


def build_engine(engine: str, entry: Dict[str, Any], workdir: Path, jobs: int) -> Path:
    source = clone_source(entry, workdir)
    subprocess.run(
        ["make", f"-j{jobs}", entry.get("make", "build"), f"ARCH={entry['arch']}"],
        cwd=source / "src",
        check=True,
    )
    built = source / "src" / "stockfish"
    if not built.is_file():
        raise SystemExit(f"the build produced no {built}")
    installed = ROOT / entry["install_as"]
    installed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, installed)
    installed.chmod(0o755)
    return installed


def fetch_engine(engine: str, entry: Dict[str, Any], workdir: Path, jobs: int) -> Path:
    installed = ROOT / entry["install_as"]

    if "build" in entry:
        build = entry["build"]
        print(f"{engine}: building from {build['repo']} at {build['tag']} ({build['arch']})")
        return build_engine(engine, build, workdir, jobs)

    archive = workdir / entry["asset"]
    print(f"{engine}: downloading {entry['asset']}")
    download(entry["url"], archive)

    actual = sha256_of(archive)
    if actual != entry["sha256"]:
        raise SystemExit(
            f"{entry['asset']}: sha256 is {actual}, engines.json pins {entry['sha256']}"
        )

    extract_member(archive, entry["member"], installed)
    print(f"{engine}: installed {installed.relative_to(ROOT)}")
    return installed


def fetch_target(target: Dict[str, Any], jobs: int, force: bool = False) -> List[Path]:
    installed: List[Path] = []

    with tempfile.TemporaryDirectory(prefix="deepsight-engines-") as temporary:
        workdir = Path(temporary)
        for engine, entry in target["engines"].items():
            if not force and (ROOT / entry["install_as"]).is_file():
                print(f"{engine}: {entry['install_as']} is already there, skipping")
                installed.append(ROOT / entry["install_as"])
                continue
            installed.append(fetch_engine(engine, entry, workdir, jobs))

    return installed


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", help="target to install, for example linux-arm64")
    parser.add_argument("--list", action="store_true", help="list the targets and exit")
    parser.add_argument("--force", action="store_true", help="install again over existing files")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    arguments = parser.parse_args(argv)

    pins = load_pins()

    if arguments.list:
        for target in pins["targets"]:
            engines = ", ".join(target["engines"])
            print(f"{target['id']:<16} {target.get('runner', ''):<18} {engines}")
        return 0

    target = (
        find_target(pins, arguments.target) if arguments.target else current_target(pins)
    )
    print(f"target: {target['id']}")

    try:
        own = target_id_for(platform.system(), platform.machine())
    except SystemExit:
        own = None
    if own is not None and own != target["id"]:
        print(
            f"note: these are {target['id']} engines and this machine is {own}, "
            f"so they will not run here"
        )

    for path in fetch_target(target, arguments.jobs, arguments.force):
        print(f"ready: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
