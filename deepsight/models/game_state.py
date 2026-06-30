import sys
if sys.getrecursionlimit() < 100000:
    sys.setrecursionlimit(100000)

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import chess
import chess.pgn
import io

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


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
            if self.mate == 0:
                return None
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
        self._initial_fen: str = STARTING_FEN

    def clear(self):
        self._initial_fen = STARTING_FEN
        self.board = chess.Board()
        self.moves.clear()
        self.headers.clear()
        self.current_move_index = -1
        self.pgn_string = ""

    def load_pgn(self, pgn_text: str) -> bool:
        try:
            self.clear()
            
            lines = []
            for line in pgn_text.strip().split('\n'):
                line = line.strip()
                if line:
                    lines.append(line)
            clean_text = '\n'.join(lines)
            
            pgn_io = io.StringIO(clean_text)
            game = chess.pgn.read_game(pgn_io)
            
            if game is None:
                pgn_io.seek(0)
                games = []
                while True:
                    g = chess.pgn.read_game(pgn_io)
                    if g is None:
                        break
                    games.append(g)
                
                if not games:
                    return False
                game = games[0]
            
            self.pgn_string = pgn_text
            self.headers = dict(game.headers.items())

            initial_fen = game.headers.get("FEN", STARTING_FEN)
            self._initial_fen = initial_fen

            self.board = chess.Board()
            if initial_fen != STARTING_FEN:
                self.board.set_fen(initial_fen)
            node = game
            move_number = 1
            
            while node.variations:
                node = node.variations[0]
                move = node.move
                player = self.board.turn
                
                try:
                    san = self.board.san(move)
                except:
                    san = move.uci()

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
            
        except Exception as e:
            print(f"PGN parsing error: {e}")
            return False

    def load_fen(self, fen: str) -> bool:
        self.clear()
        try:
            self.board.set_fen(fen)
            self._initial_fen = fen
            self.current_move_index = -1
            return True
        except Exception as e:
            print(f"FEN parsing error: {e}")
            return False

    def get_position_at(self, move_index: int) -> chess.Board:
        board = chess.Board()
        board.set_fen(self._initial_fen)
        if move_index < 0 or not self.moves:
            return board
        
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
        if self.current_move_index < len(self.moves) - 1:
            self.go_to_move(self.current_move_index + 1)

    def go_back(self):
        if self.current_move_index > -1:
            self.go_to_move(self.current_move_index - 1)
        else:
            self.go_to_move(-1)

    def go_to_start(self):
        self.go_to_move(-1)

    def go_to_end(self):
        if self.moves:
            self.go_to_move(len(self.moves) - 1)
        else:
            self.go_to_move(-1)

    def can_go_forward(self) -> bool:
        return self.current_move_index < len(self.moves) - 1

    def can_go_back(self) -> bool:
        return self.current_move_index > -1

    @property
    def current_move(self) -> Optional[AnalyzedMove]:
        if 0 <= self.current_move_index < len(self.moves):
            return self.moves[self.current_move_index]
        return None
