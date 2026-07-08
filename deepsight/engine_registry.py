from __future__ import annotations

import os
import sys
import shutil
import tempfile
import atexit
from typing import Optional, Dict, Tuple
from pathlib import Path

from .engine_manager import EngineProtocol


BUILTIN_ENGINES: Dict[str, Tuple[str, ...]] = {
    "Ember": (
        "Engines/ember.exe",
        "Engines/Ember.exe",
        "Engines/ember",
    ),
    "Stockfish": (
        "Engines/stockfish-windows-x86-64.exe",
        "Engines/stockfish.exe",
        "Engines/stockfish",
    ),
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
    candidates = []

    env_base = os.environ.get("DEEPSIGHT_DATA_DIR")
    if env_base:
        candidates.append(Path(env_base))

    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys._MEIPASS))
        candidates.append(Path(sys.executable).resolve().parent)
    else:
        candidates.append(Path(__file__).resolve().parent.parent)
        candidates.append(Path.cwd())

    for base in candidates:
        path = base / relative_path
        if path.exists():
            return str(path)

    return str(candidates[0] / relative_path)


def _resolve_existing_data_path(relative_paths: Tuple[str, ...]) -> Optional[str]:
    for rel_path in relative_paths:
        path = get_data_path(rel_path)
        if os.path.isfile(path):
            return path
    return None


def extract_builtin_engine(name: str) -> Optional[str]:
    global _temp_dir

    if name in _extracted:
        return _extracted[name]

    if name not in BUILTIN_ENGINES:
        return None

    src_path = _resolve_existing_data_path(BUILTIN_ENGINES[name])
    if src_path is None:
        return None

    if _temp_dir is None:
        _temp_dir = tempfile.mkdtemp(prefix="deepsight_engines_")

    dst_name = os.path.basename(src_path)
    if os.name == "nt" and not dst_name.lower().endswith(".exe"):
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
