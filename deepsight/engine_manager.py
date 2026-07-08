from __future__ import annotations
import subprocess
import threading
import time
import re
import os
from typing import Optional, List, Dict
from enum import Enum

import chess

class EngineProtocol(Enum):
    UCI = "uci"
    XBOARD = "xboard"

class EngineManager:

    def __init__(self, engine_path: str, protocol: EngineProtocol = EngineProtocol.UCI):
        self.engine_path = engine_path
        self.protocol = protocol
        self.process: Optional[subprocess.Popen] = None
        self.stdout_buffer: List[str] = []
        self._lock = threading.Lock()
        self._running = False
        self._name = ""
        self._ready = False
        self._reader_thread: Optional[threading.Thread] = None
        self._use_nnue: Optional[bool] = None
        self._uci_options: Dict[str, str] = {}

    @property
    def name(self) -> str:
        return self._name or os.path.basename(self.engine_path)

    def start(self) -> bool:
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                [self.engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                startupinfo=startupinfo
            )

            self._running = True
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()

            if self.protocol == EngineProtocol.UCI:
                self._send("uci")
                self._wait_for("uciok", timeout=5.0)
                self._parse_uci_options()

                self._send_option_if_supported("book", "")
                self._apply_nnue_option()

                self._send("isready")
                self._wait_for("readyok", timeout=5.0)
                time.sleep(0.1)

            elif self.protocol == EngineProtocol.XBOARD:
                self._send("xboard")
                self._send("protover 2")
                time.sleep(0.5)

            self._ready = True
            return True

        except Exception as e:
            print(f"Failed to start engine: {e}")
            return False

    def stop(self):
        self._running = False
        if self.process:
            try:
                if self.protocol == EngineProtocol.UCI:
                    self._send("stop")
                time.sleep(0.05)
                self._send("quit")
                self.process.wait(timeout=2.0)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
        self._ready = False

    def set_position(self, board: chess.Board):
        if self.protocol == EngineProtocol.UCI:
            self._send("position fen " + board.fen())
        else:
            self._send("setboard " + board.fen())

    def set_position_from_moves(self, moves: List[chess.Move], starting_fen: Optional[str] = None):
        if self.protocol == EngineProtocol.UCI:
            if starting_fen and starting_fen != chess.STARTING_FEN:
                self._send("position fen " + starting_fen + " moves " + " ".join(m.uci() for m in moves))
            else:
                self._send("position startpos moves " + " ".join(m.uci() for m in moves))
        else:
            board = chess.Board()
            if starting_fen:
                board.set_fen(starting_fen)
            for m in moves:
                board.push(m)
            self.set_position(board)

    def start_analysis(self, movetime: Optional[int] = None, depth: Optional[int] = None,
                       infinite: bool = False) -> bool:
        if not self._ready or not self.process:
            return False

        if self.protocol == EngineProtocol.UCI:
            if infinite:
                self._send("go infinite")
            elif depth:
                self._send("go depth " + str(depth))
            else:
                self._send("go movetime " + str(movetime if movetime else 1000))
        else:
            if infinite:
                self._send("go")
            elif depth:
                self._send("sd " + str(depth))
                self._send("go")
            else:
                self._send("st " + str((movetime if movetime else 1000) // 1000))
                self._send("go")
        return True

    def stop_analysis(self):
        if self.protocol == EngineProtocol.UCI:
            self._send("stop")
        else:
            self._send("?")
            self._send("result *")

    def set_option(self, name: str, value: str):
        if self.protocol == EngineProtocol.UCI:
            self._send("setoption name " + name + " value " + value)

    def set_nnue(self, enabled: Optional[bool]):

        self._use_nnue = enabled
        if self.protocol == EngineProtocol.UCI and self._ready:
            self._apply_nnue_option()

    def _parse_uci_options(self):
        with self._lock:
            lines = list(self.stdout_buffer)

        self._uci_options.clear()
        for line in lines:
            m = re.match(r'^option\s+name\s+(.+?)\s+type\s+\S+', line, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                self._uci_options[name.lower()] = name

    def _send_option_if_supported(self, name: str, value: str) -> bool:
        option_name = self._uci_options.get(name.lower())
        if option_name is None:
            return False

        self._send("setoption name " + option_name + " value " + value)
        return True

    def _apply_nnue_option(self):
        if self._use_nnue is None:
            return

        enabled = "true" if self._use_nnue else "false"
        sent_use_nnue = self._send_option_if_supported("Use NNUE", enabled)

        if self._use_nnue:
            self._send_option_if_supported("NNUE", "<embedded>")
        elif not sent_use_nnue and not self._send_option_if_supported("NNUE", ""):
            self._send_option_if_supported("EvalFile", "")

    def _send(self, command: str):
        if self.process and self.process.stdin:
            with self._lock:
                try:
                    self.process.stdin.write((command + "\n").encode('utf-8'))
                    self.process.stdin.flush()
                except:
                    pass

    def _read_output(self):
        while self._running and self.process and self.process.stdout:
            try:
                raw = self.process.stdout.readline()
                if not raw:
                    break
                line = raw.decode('utf-8', errors='replace').strip()
                if line:
                    with self._lock:
                        self.stdout_buffer.append(line)
            except:
                break

    def _wait_for(self, keyword: str, timeout: float = 5.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                for line in self.stdout_buffer:
                    if keyword in line.lower():
                        return True
            time.sleep(0.05)
        return False

    def get_output(self) -> List[str]:
        with self._lock:
            out = self.stdout_buffer.copy()
            self.stdout_buffer.clear()
        return out

    def parse_uci_info(self, line: str) -> Optional[dict]:
        if not line.startswith("info"):
            return None
        data = {}
        m = re.search(r'depth\s+(\d+)', line)
        if m: data['depth'] = int(m.group(1))
        m = re.search(r'score\s+cp\s+(-?\d+)', line)
        if m: data['score_cp'] = int(m.group(1))
        m = re.search(r'score\s+mate\s+(-?\d+)', line)
        if m: data['mate'] = int(m.group(1))
        m = re.search(r'\bpv\s+(.*)', line)
        if m:
            data['pv'] = m.group(1).strip()
        m = re.search(r'nodes\s+(\d+)', line)
        if m: data['nodes'] = int(m.group(1))
        if 'pv' not in data and 'score_cp' not in data and 'mate' not in data:
            return None
        return data

    def parse_xboard_info(self, line: str) -> Optional[dict]:
        data = {}
        m = re.search(r'(\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)', line)
        if m:
            data['depth'] = int(m.group(1))
            data['score_cp'] = int(m.group(2))
            data['time'] = int(m.group(3))
            data['nodes'] = int(m.group(4))
            return data
        m = re.match(r'^move\s+(\w+)', line)
        if m:
            data['bestmove'] = m.group(1)
            return data
        return None
