import re
from pathlib import Path

from deepsight import __version__

ROOT = Path(__file__).resolve().parent.parent


def test_the_version_looks_like_a_release():
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?", __version__)


def test_the_nix_flake_pins_the_same_version():
    text = (ROOT / "flake.nix").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', text)
    assert match, "flake.nix declares no version"
    assert match.group(1) == __version__


def test_the_packaging_spec_does_not_hardcode_a_version():
    text = (ROOT / "deepsight.spec").read_text(encoding="utf-8")
    assert not re.search(r'"\d+\.\d+\.\d+"', text), "the spec must read the version from deepsight"
    assert "__version__" in text
