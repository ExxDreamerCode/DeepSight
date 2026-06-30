from __future__ import annotations

import os
import sys
import shutil
import tempfile
import atexit
from typing import Optional, Dict, Tuple
from pathlib import Path

from .engine_manager import EngineProtocol


BUILTIN_ENGINES: Dict[str, str] = {
    "Ember": "Engines/Ember.exe",
    "Stockfish": "Engines/stockfish-windows-x86-64.exe",
}

_temp_dir: Optional[str] = None
_extracted: Dict[str, str] = {}


def _cleanup():
    global _temp_dir
    if _temp_dir and os.path.isdir(_temp_dir):
        try:
            shutil.rmtree(_temp_dir, ignore_errors=True)
        except:
            pass
    _temp_dir = None
    _extracted.clear()


atexit.register(_cleanup)


def get_data_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def extract_builtin_engine(name: str) -> Optional[str]:
    global _temp_dir

    if name in _extracted:
        return _extracted[name]

    if name not in BUILTIN_ENGINES:
        return None

    rel_path = BUILTIN_ENGINES[name]
    src_path = get_data_path(rel_path)

    if not os.path.isfile(src_path):
        return None

    if _temp_dir is None:
        _temp_dir = tempfile.mkdtemp(prefix="deepsight_engines_")

    dst_name = f"{name}.exe"
    dst_path = os.path.join(_temp_dir, dst_name)

    try:
        shutil.copy2(src_path, dst_path)
        os.chmod(dst_path, 0o755)
        _extracted[name] = dst_path
        return dst_path
    except Exception as e:
        print(f"Failed to extract engine {name}: {e}")
        return None


def get_builtin_engine_path(name: str) -> Optional[str]:
    return extract_builtin_engine(name)


def get_engine_path(engine_type: str,
                    custom_path: Optional[str] = None) -> Optional[str]:
    engine_type = engine_type.lower()

    if engine_type == "ember":
        return get_builtin_engine_path("Ember")
    elif engine_type == "stockfish":
        return get_builtin_engine_path("Stockfish")
    elif engine_type == "external":
        if custom_path and os.path.isfile(custom_path):
            return custom_path
        return None
    else:
        return None


def get_engine_protocol(engine_type: str,
                        external_protocol: EngineProtocol = EngineProtocol.UCI) -> EngineProtocol:
    return EngineProtocol.UCI


def list_engine_types() -> list:
    engines = ["ember", "stockfish", "external"]
    return engines


def get_engine_display_name(engine_type: str) -> str:
    names = {
        "ember": "Ember (built-in)",
        "stockfish": "Stockfish (built-in)",
        "external": "External engine...",
    }
    return names.get(engine_type, engine_type)