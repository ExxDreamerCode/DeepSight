from __future__ import annotations

import os
from typing import Optional, Dict
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
from .engine_registry import get_data_path


class SoundManager:
    _SOUND_FILES = {
        "move": "move.wav",
        "capture": "capture.wav",
        "check": "check.wav",
        "checkmate": "checkmate.wav",
        "castle": "castle.wav",
        "click": "move.wav",
    }

    def __init__(self) -> None:
        self._enabled: bool = True
        self._volume: float = 0.5
        self._effects: Dict[str, QSoundEffect] = {}
        self._load_sounds()

    def _load_sounds(self) -> None:
        sounds_dir = os.path.join(get_data_path(""), "sounds")
        for name, filename in self._SOUND_FILES.items():
            path = os.path.join(sounds_dir, filename)
            effect = QSoundEffect()
            if os.path.isfile(path):
                effect.setSource(QUrl.fromLocalFile(path))
            effect.setVolume(self._volume)
            self._effects[name] = effect

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        for effect in self._effects.values():
            effect.setVolume(self._volume)

    def play(self, sound_name: str) -> None:
        if not self._enabled:
            return
        effect = self._effects.get(sound_name)
        if effect is None:
            return
        effect.stop()
        effect.play()

    def play_move(self, *, capture: bool = False, check: bool = False,
                  checkmate: bool = False, castle: bool = False) -> None:
        if checkmate:
            self.play("checkmate")
        elif check:
            self.play("check")
        elif capture:
            self.play("capture")
        elif castle:
            self.play("castle")
        else:
            self.play("move")

    def play_ui_click(self) -> None:
        self.play("click")
