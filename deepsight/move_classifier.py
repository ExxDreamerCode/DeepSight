from __future__ import annotations
import os
import glob
from typing import Set, Optional, List
import chess
import chess.pgn


class BookChecker:
    def __init__(self, books_dir: str = "Books"):
        self.books_dir = books_dir
        self.book_moves: Set[str] = set()
        self._loaded = False

    def load_books(self) -> int:
        self.book_moves.clear()
        count = 0

        if not os.path.isdir(self.books_dir):
            self._loaded = True
            return 0

        for filepath in glob.glob(os.path.join(self.books_dir, "*")):
            ext = os.path.splitext(filepath)[1].lower()
            try:
                if ext == ".pgn":
                    n = self._load_pgn_book(filepath)
                    count += n
                elif ext == ".txt" or ext == ".bk":
                    n = self._load_text_book(filepath)
                    count += n
            except Exception as e:
                print(f"Failed to load book {filepath}: {e}")

        self._loaded = True
        return count

    def _load_pgn_book(self, filepath: str) -> int:
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            games_text = []
            current_game = []
            in_game = False
            for line in content.split('\n'):
                if line.strip().startswith('[') and not in_game:
                    in_game = True
                    current_game = [line]
                elif line.strip().startswith('[') and in_game:
                    current_game.append(line)
                elif line.strip() and in_game:
                    current_game.append(line)
                elif not line.strip() and in_game:
                    if current_game:
                        games_text.append('\n'.join(current_game))
                    current_game = []
                    in_game = False

            if current_game:
                games_text.append('\n'.join(current_game))

            for game_text in games_text:
                try:
                    game = chess.pgn.read_game(chess.io.StringIO(game_text))
                    if game is None:
                        continue

                    board = chess.Board()
                    node = game
                    while node.variations:
                        node = node.variations[0]
                        move = node.move
                        fen = board.fen()
                        self.book_moves.add(f"{fen}|{move.uci()}")
                        count += 1
                        board.push(move)
                except:
                    continue
        except Exception as e:
            print(f"Error loading PGN book {filepath}: {e}")

        return count

    def _load_text_book(self, filepath: str) -> int:
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue

                    if "|" in line:
                        self.book_moves.add(line)
                        count += 1
        except Exception as e:
            print(f"Error loading text book {filepath}: {e}")
        return count

    def is_book_move(self, board: chess.Board, move: chess.Move) -> bool:
        if not self._loaded:
            self.load_books()

        if not self.book_moves:
            return False

        fen = board.fen()
        move_uci = move.uci()

        return f"{fen}|{move_uci}" in self.book_moves


class MoveClassifier:
    def __init__(self, book_checker: Optional[BookChecker] = None):
        self.book_checker = book_checker or BookChecker()

    def classify(self, board_before: chess.Board, played_move: chess.Move,
                best_move: Optional[chess.Move], eval_before: Optional[float],
                eval_after: Optional[float] = None, depth: int = 0) -> str:

        if self.book_checker.is_book_move(board_before, played_move):
            return "Book"

        is_best = (played_move == best_move or
                (best_move is not None and played_move.uci() == best_move.uci()))

        if eval_before is None or eval_after is None:
            if is_best:
                return "Best"
            if best_move is None:
                return "Excellent"
            return "Good"

        MATE_THRESHOLD = 10.0

        after_is_mate = abs(eval_after) > MATE_THRESHOLD
        before_is_mate = abs(eval_before) > MATE_THRESHOLD

        def _mate_for_player_after() -> bool:
            return after_is_mate and (
                (board_before.turn == chess.WHITE and eval_after > 0) or
                (board_before.turn == chess.BLACK and eval_after < 0)
            )

        def _mate_for_opponent_after() -> bool:
            return after_is_mate and (
                (board_before.turn == chess.WHITE and eval_after < 0) or
                (board_before.turn == chess.BLACK and eval_after > 0)
            )

        def _mate_for_player_before() -> bool:
            return before_is_mate and (
                (board_before.turn == chess.WHITE and eval_before > 0) or
                (board_before.turn == chess.BLACK and eval_before < 0)
            )

        def _mate_for_opponent_before() -> bool:
            return before_is_mate and (
                (board_before.turn == chess.WHITE and eval_before < 0) or
                (board_before.turn == chess.BLACK and eval_before > 0)
            )

        if _mate_for_player_before():
            if _mate_for_opponent_after():
                return "Inaccuracy"
            if _mate_for_player_after():
                return "Best"
            return "Best"

        if _mate_for_opponent_before():
            return "Best"

        if _mate_for_player_after():
            if is_best:
                return "Best"
            was_winning = (
                (board_before.turn == chess.WHITE and eval_before > 1.5) or
                (board_before.turn == chess.BLACK and eval_before < -1.5)
            )
            if was_winning:
                return "Brilliant"
            return "Best"

        if _mate_for_opponent_after():
            return "Inaccuracy"

        if board_before.turn == chess.WHITE:
            eval_after_fixed = -eval_after
            loss = eval_before - eval_after_fixed
        else:
            black_before = eval_before
            black_after = -eval_after
            loss = black_before - black_after
        if loss < 0:
            loss = 0

        if loss < 0.01:
            classification = "Best"
        elif loss < 0.3:
            classification = "Excellent"
        elif loss < 0.9:
            classification = "Good"
        elif loss < 1.2:
            classification = "Inaccuracy"
        elif loss < 2.5:
            classification = "Mistake"
        else:
            classification = "Blunder"

        if board_before.turn == chess.WHITE:
            position_advantage = eval_before
        else:
            position_advantage = -eval_before

        if position_advantage < -6.0:
            if classification == "Blunder":
                classification = "Good"
            elif classification == "Mistake":
                classification = "Good"
            elif classification == "Inaccuracy":
                classification = "Good"
        elif position_advantage < -2.0:
            if classification == "Blunder":
                classification = "Mistake"

        if not is_best and classification == "Best":
            classification = "Excellent"

        if is_best:
            classification = "Best"

        return classification