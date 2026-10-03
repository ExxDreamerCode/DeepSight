import base64
import hashlib
import io
import os
import platform
import re
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from deepsight.engine_registry import BUILTIN_ENGINES, BUILTIN_ENGINE_VERSIONS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Engines"))

import fetch_engines


@pytest.fixture(scope="module")
def pins():
    return fetch_engines.load_pins(ROOT / "engines.json")


def test_the_pins_cover_six_platforms(pins):
    identifiers = [target["id"] for target in pins["targets"]]

    assert identifiers == [
        "linux-x86_64",
        "linux-arm64",
        "macos-x86_64",
        "macos-arm64",
        "windows-x86_64",
        "windows-arm64",
    ]
    assert all(target["runner"] for target in pins["targets"])


def test_every_engine_is_either_downloaded_or_built(pins):
    for target in pins["targets"]:
        assert set(target["engines"]) == {"ember", "stockfish"}
        for name, entry in target["engines"].items():
            if "build" in entry:
                build = entry["build"]
                assert build["repo"].startswith("https://")
                assert build["tag"] and build["commit"] and build["arch"]
                assert len(build["commit"]) == 40
                continue
            assert entry["url"].endswith(entry["asset"]), (target["id"], name)
            assert len(entry["sha256"]) == 64
            int(entry["sha256"], 16)
            assert entry["member"]


def test_the_pins_install_engines_where_the_registry_looks(pins):
    for target in pins["targets"]:
        for name, entry in target["engines"].items():
            installed = entry.get("build", entry)["install_as"]
            assert installed in BUILTIN_ENGINES[name.capitalize()], (target["id"], installed)


def test_the_pinned_engine_versions_match_the_registry(pins):
    for name, engine in pins["engines"].items():
        assert engine["version"] == BUILTIN_ENGINE_VERSIONS[name]


def test_a_machine_maps_onto_one_of_the_targets():
    expected = fetch_engines.target_id_for(platform.system(), platform.machine())

    assert expected in {target["id"] for target in fetch_engines.load_pins()["targets"]}


@pytest.mark.parametrize(
    "system, machine, wanted",
    [
        ("Windows", "AMD64", "windows-x86_64"),
        ("Windows", "ARM64", "windows-arm64"),
        ("Linux", "x86_64", "linux-x86_64"),
        ("Linux", "aarch64", "linux-arm64"),
        ("Darwin", "arm64", "macos-arm64"),
        ("Darwin", "x86_64", "macos-x86_64"),
    ],
)
def test_the_platform_names_are_translated(system, machine, wanted):
    assert fetch_engines.target_id_for(system, machine) == wanted


def test_an_unknown_platform_is_refused():
    with pytest.raises(SystemExit):
        fetch_engines.target_id_for("Plan9", "mips")

    with pytest.raises(SystemExit):
        fetch_engines.target_id_for("Linux", "sparc")

    with pytest.raises(SystemExit):
        fetch_engines.find_target({"targets": []}, "linux-x86_64")


def _tarball(path, member, content):
    with tarfile.open(path, "w:gz") as bundle:
        info = tarfile.TarInfo(member)
        info.size = len(content)
        bundle.addfile(info, io.BytesIO(content))


def _zip(path, member, content):
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(member, content)


def test_a_member_is_taken_out_of_a_tarball(tmp_path):
    archive = tmp_path / "engine.tar.gz"
    _tarball(archive, "ember-1.3.1-9e015493-linux-amd64/ember", b"linux engine")
    installed = tmp_path / "out" / "ember-1.3.1"

    fetch_engines.extract_member(archive, "ember-1.3.1-9e015493-linux-amd64/ember", installed)

    assert installed.read_bytes() == b"linux engine"
    if os.name != "nt":
        assert os.access(installed, os.X_OK)


def test_a_member_is_found_by_its_name_inside_a_folder(tmp_path):
    archive = tmp_path / "engine.zip"
    _zip(archive, "ember-1.3.1-9e015493-windows-arm64/ember.exe", b"arm64 engine")
    installed = tmp_path / "out" / "ember-1.3.1.exe"

    fetch_engines.extract_member(archive, "ember.exe", installed)

    assert installed.read_bytes() == b"arm64 engine"


def test_a_member_that_is_not_there_is_refused(tmp_path):
    archive = tmp_path / "engine.zip"
    _zip(archive, "ember.exe", b"engine")

    with pytest.raises(SystemExit):
        fetch_engines.extract_member(archive, "stockfish.exe", tmp_path / "out")

    other = tmp_path / "notes.txt"
    other.write_text("not an archive", encoding="utf-8")
    with pytest.raises(SystemExit):
        fetch_engines.extract_member(other, "ember.exe", tmp_path / "out2")


def test_a_hash_that_does_not_match_installs_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_engines, "ROOT", tmp_path)
    entry = {
        "asset": "engine.tar.gz",
        "url": "https://example.invalid/engine.tar.gz",
        "member": "ember",
        "sha256": hashlib.sha256(b"something else").hexdigest(),
        "install_as": "Engines/ember-1.3.1",
    }

    def fake_download(url, destination):
        _tarball(destination, "ember", b"not what was pinned")

    monkeypatch.setattr(fetch_engines, "download", fake_download)

    with pytest.raises(SystemExit) as error:
        fetch_engines.fetch_engine("ember", entry, tmp_path, jobs=1)

    assert "engines.json pins" in str(error.value)
    assert not (tmp_path / "Engines").exists()


def test_an_engine_that_is_already_installed_is_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_engines, "ROOT", tmp_path)
    installed = tmp_path / "Engines" / "stockfish"
    installed.parent.mkdir(parents=True)
    installed.write_bytes(b"already here")

    def refuse(*arguments, **keywords):
        raise AssertionError("an installed engine must not be downloaded or built again")

    monkeypatch.setattr(fetch_engines, "download", refuse)
    monkeypatch.setattr(fetch_engines, "build_engine", refuse)

    target = {"id": "test", "engines": {"stockfish": {"install_as": "Engines/stockfish"}}}

    assert fetch_engines.fetch_target(target, jobs=1) == [installed]
    assert installed.read_bytes() == b"already here"


def test_the_build_is_pinned_to_a_tag_and_a_commit(pins):
    build = fetch_engines.find_target(pins, "linux-arm64")["engines"]["stockfish"]["build"]

    assert build["tag"] == "sf_18"
    assert build["make"] == "profile-build"
    assert build["arch"] == "armv8"
    assert build["install_as"] == "Engines/stockfish"


def test_an_engine_is_downloaded_checked_and_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_engines, "ROOT", tmp_path)
    archive = tmp_path / "engine.tar.gz"
    _tarball(archive, "engine/ember", b"a real engine")
    workdir = tmp_path / "work"
    workdir.mkdir()
    pin = {
        "url": archive.as_uri(),
        "asset": "engine.tar.gz",
        "member": "engine/ember",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "install_as": "Engines/ember-1.3.1",
    }

    installed = fetch_engines.fetch_engine("ember", pin, workdir, jobs=1)

    assert installed == tmp_path / "Engines" / "ember-1.3.1"
    assert installed.read_bytes() == b"a real engine"


def test_the_command_line_lists_the_targets(capsys):
    assert fetch_engines.main(["--list"]) == 0

    listed = capsys.readouterr().out

    assert "linux-arm64" in listed
    assert "windows-arm64" in listed
    assert "ubuntu-24.04-arm" in listed


def _flake_value(text, name):
    match = re.search(rf'{name}\s*=\s*"([^"]+)"', text)
    assert match, f"flake.nix declares no {name}"
    return match.group(1)


def test_the_nix_flake_pins_the_same_linux_engines(pins):
    text = (ROOT / "flake.nix").read_text(encoding="utf-8")
    linux = fetch_engines.find_target(pins, "linux-x86_64")["engines"]
    ember = linux["ember"]
    stockfish = linux["stockfish"]

    assert _flake_value(text, "emberVersion") == pins["engines"]["ember"]["version"]
    assert _flake_value(text, "emberRev") == ember["asset"].split("-")[2]
    assert _flake_value(text, "stockfishRelease") == stockfish["url"].rstrip("/").split("/")[-2]
    assert "linux-amd64" in text
    assert stockfish["asset"] in text

    for name, entry in linux.items():
        digest = base64.b64encode(bytes.fromhex(entry["sha256"])).decode()
        assert f"sha256-{digest}" in text, f"flake.nix pins a different {name} digest"
