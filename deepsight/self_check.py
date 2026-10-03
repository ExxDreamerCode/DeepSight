from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from typing import Any, Dict, Optional

from . import __version__
from .engine_registry import BUILTIN_ENGINE_VERSIONS, get_data_path, get_engine_path

HANDSHAKE_TIMEOUT = 30

_DATA_FILES = {
    "book": "Books/book.bin",
    "notices": "THIRD_PARTY_NOTICES.md",
    "stockfish_license": "licenses/GPL-3.0.txt",
}

_DATA_DIRS = {
    "pieces": "Images/Pieces",
    "move_icons": "Images/Moves",
}


def _count_data_files(relative_path: str) -> int:
    path = get_data_path(relative_path)
    if not os.path.isdir(path):
        return 0
    return sum(1 for name in os.listdir(path) if os.path.isfile(os.path.join(path, name)))


def _qt_version() -> Optional[str]:
    try:
        from PyQt6.QtCore import QT_VERSION_STR
    except Exception:
        return None
    return QT_VERSION_STR


def _handshake(path: str):
    try:
        finished = subprocess.run(
            [path],
            input="uci\nquit\n",
            capture_output=True,
            text=True,
            timeout=HANDSHAKE_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)[:200]

    if "uciok" not in finished.stdout:
        return False, (finished.stderr or finished.stdout).strip()[:200]

    for line in finished.stdout.splitlines():
        if line.startswith("id name"):
            return True, line[len("id name"):].strip()
    return True, ""


def engine_report(engine_type: str, handshake: bool = True) -> Dict[str, Any]:
    path = get_engine_path(engine_type)
    report: Dict[str, Any] = {
        "version": BUILTIN_ENGINE_VERSIONS.get(engine_type),
        "path": path,
        "present": bool(path),
    }
    if path and handshake:
        answered, detail = _handshake(path)
        report["uci_ok"] = answered
        report["name"] = detail
    return report


def build_report(handshake: bool = True) -> Dict[str, Any]:
    engines = {name: engine_report(name, handshake) for name in sorted(BUILTIN_ENGINE_VERSIONS)}

    data: Dict[str, Any] = {}
    for key, relative_path in _DATA_FILES.items():
        data[key] = os.path.isfile(get_data_path(relative_path))
    for key, relative_path in _DATA_DIRS.items():
        data[key] = _count_data_files(relative_path)

    report: Dict[str, Any] = {
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "platform": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "qt": _qt_version(),
        "engines": engines,
        "data": data,
    }

    engines_ok = all(
        engine["present"] and engine.get("uci_ok", True) for engine in engines.values()
    )
    data_ok = all(
        bool(value) if isinstance(value, bool) else value > 0 for value in data.values()
    )
    report["ok"] = engines_ok and data_ok
    return report


def render_report(report: Dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def write_report(report: Dict[str, Any], target: str) -> None:
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(render_report(report) + "\n")


def summarize(report: Dict[str, Any]) -> str:
    engines = ", ".join(
        f"{name} {engine['version']}"
        f"{'' if engine.get('uci_ok', engine['present']) else ' (no answer)'}"
        for name, engine in report["engines"].items()
    )
    state = "ok" if report["ok"] else "incomplete"
    return (
        f"DeepSight {report['version']} on {report['platform']} {report['machine']} — {state}\n"
        f"Engines: {engines}"
    )
