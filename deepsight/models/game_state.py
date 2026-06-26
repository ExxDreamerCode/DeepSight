from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import chess
import chess.pgn

@dataclass
class MoveEval:

    move: chess.Move
    score_cp: Optional[float] = None
    mate: Optional[int] = None
    depth: Optional[int] = None
    best_line: List[chess.Move] = field(default_factory=list)

    @property
    def score(self) -> Optional[str]:
        if self.mate is not None:
            return f"#{self.mate}"
        if self.score_cp is not None:
            return f"{self.score_cp / 100.0:+.2f}"
        return None

    @property
    def score_num(self) -> Optional[float]:
        if self.mate is not None:

            sign = 1 if self.mate > 0 else -1
            return sign * 10000.0 / abs(self.mate)
        return self.score_cp / 100.0 if self.score_cp is not None else None

@dataclass
class AnalyzedMove:

    move_number: int
    move: chess.Move
    san: str
    player: chess.Color

    eval_before: Optional[MoveEval] = None

    eval_after: Optional[MoveEval] = None

    best_move: Optional[chess.Move] = None

    classification: str = ""

    depth: int = 0

    is_book: bool = False

class GameState:

    def __init__(self):
        self.board = chess.Board()
        self.moves: List[AnalyzedMove] = []
        self.headers: Dict[str, str] = {}
        self.current_move_index: int = -1
        self.pgn_string: str = ""

    def clear(self):
        self.board = chess.Board()
        self.moves.clear()
        self.headers.clear()
        self.current_move_index = -1
        self.pgn_string = ""

    def load_pgn(self, pgn_text: str) -> bool:

        try:
            game = chess.pgn.read_game(chess.io.StringIO(pgn_text))
            if game is None:
                return False

            self.clear()
            self.pgn_string = pgn_text
            self.headers = dict(game.headers.items())

            node = game
            move_number = 1
            while node.variations:
                node = node.variations[0]
                move = node.move
                player = self.board.turn
                san = self.board.san(move)

                analyzed = AnalyzedMove(
                    move_number=move_number,
                    move=move,
                    san=san,
                    player=player
                )
                self.moves.append(analyzed)
                self.board.push(move)

                if player == chess.BLACK:
                    move_number += 1

            self.board = chess.Board()
            self.current_move_index = -1
            return True
        except Exception:
            return False

    def load_fen(self, fen: str) -> bool:

        try:
            self.clear()
            self.board.set_fen(fen)
            return True
        except Exception:
            return False

    def get_position_at(self, move_index: int) -> chess.Board:

        board = chess.Board()
        for i in range(move_index + 1):
            if i < len(self.moves):
                board.push(self.moves[i].move)
        return board

    def go_to_move(self, move_index: int):

        if move_index < -1 or move_index >= len(self.moves):
            return
        self.current_move_index = move_index
        self.board = self.get_position_at(move_index)

    def go_forward(self):

        self.go_to_move(self.current_move_index + 1)

    def go_back(self):

        self.go_to_move(self.current_move_index - 1)

    @property
    def current_move(self) -> Optional[AnalyzedMove]:
        if 0 <= self.current_move_index < len(self.moves):
            return self.moves[self.current_move_index]
        return None
