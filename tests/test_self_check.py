import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from deepsight import __version__
from deepsight import self_check

ROOT = Path(__file__).resolve().parent.parent
MISSING = str(Path(ROOT) / "no-such-directory")


def test_the_report_describes_this_build():
    report = self_check.build_report(handshake=False)

    assert report["version"] == __version__
    assert report["python"] == ".".join(str(part) for part in sys.version_info[:3])
    assert report["frozen"] is False
    assert report["platform"]
    assert report["machine"]


def test_both_engines_are_reported_without_starting_them():
    report = self_check.build_report(handshake=False)

    assert set(report["engines"]) == {"ember", "stockfish"}
    for engine in report["engines"].values():
        assert engine["version"]
        assert isinstance(engine["present"], bool)
        assert "uci_ok" not in engine, "handshake=False must not launch the engines"


def test_the_report_checks_every_file_the_app_loads():
    report = self_check.build_report(handshake=False)

    assert set(report["data"]) == {"book", "notices", "stockfish_license", "pieces", "move_icons"}
    assert report["data"]["pieces"] > 0
    assert report["data"]["move_icons"] > 0
    assert report["data"]["book"] is True


def test_a_build_without_engines_or_data_is_not_ok(monkeypatch):
    monkeypatch.setattr(self_check, "get_engine_path", lambda name: None)
    monkeypatch.setattr(self_check, "get_data_path", lambda relative: f"{MISSING}/{relative}")

    report = self_check.build_report(handshake=False)

    assert report["ok"] is False


def test_an_engine_that_does_not_answer_is_not_ok(monkeypatch):
    monkeypatch.setattr(self_check, "get_engine_path", lambda name: MISSING)

    report = self_check.build_report(handshake=True)

    assert report["engines"]["ember"]["present"] is True
    assert report["engines"]["ember"]["uci_ok"] is False
    assert report["ok"] is False


def test_the_summary_names_the_version_and_the_engines():
    report = self_check.build_report(handshake=False)

    summary = self_check.summarize(report)

    assert f"DeepSight {__version__}" in summary
    assert "ember 1.3.1" in summary
    assert "stockfish 18" in summary


def test_a_written_report_is_readable_json(tmp_path):
    report = self_check.build_report(handshake=False)
    target = tmp_path / "report.json"

    self_check.write_report(report, str(target))

    assert json.loads(target.read_text(encoding="utf-8"))["version"] == __version__


def test_the_command_line_reports_the_version_without_loading_qt():
    finished = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--version"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(ROOT),
    )

    assert finished.returncode == 0
    assert finished.stdout.strip() == f"DeepSight {__version__}"


def test_the_self_check_command_reports_what_is_missing(monkeypatch, tmp_path):
    import main

    monkeypatch.setattr(self_check, "get_engine_path", lambda name: None)
    monkeypatch.setattr(self_check, "get_data_path", lambda relative: f"{MISSING}/{relative}")
    target = tmp_path / "self-check.json"

    code = main.run_self_check(["main.py", "--self-check", str(target)])

    report = json.loads(target.read_text(encoding="utf-8"))
    assert code == 1
    assert report["ok"] is False
    assert report["engines"]["ember"]["present"] is False


@pytest.mark.skipif(
    os.environ.get("DEEPSIGHT_RUN_ENGINE_TESTS") != "1",
    reason="set DEEPSIGHT_RUN_ENGINE_TESTS=1 and provide an engine binary",
)
def test_the_packaged_self_check_starts_the_engines(tmp_path):
    target = tmp_path / "self-check.json"

    finished = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--self-check", str(target)],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(ROOT),
    )

    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["ok"] is True, report
    assert report["engines"]["ember"]["uci_ok"] is True
    assert finished.returncode == 0
