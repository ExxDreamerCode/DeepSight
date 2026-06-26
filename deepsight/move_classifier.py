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
            return 0

        for filepath in glob.glob(os.path.join(self.books_dir, "*")):
            ext = os.path.splitext(filepath)[1].lower()
            try:
                if ext in (".pgn", ".txt"):
                    n = self._load_pgn_book(filepath)
                    count += n
                elif ext == ".bin":

                    n = self._load_polyglot_book(filepath)
                    count += n
                elif ext == ".bk":

                    n = self._load_text_book(filepath)
                    count += n
            except Exception as e:
                print(f"Failed to load book {filepath}: {e}")

        self._loaded = True
        return count

    def _load_pgn_book(self, filepath: str) -> int:

        count = 0
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        while content:
            game = chess.pgn.read_game(chess.io.StringIO(content))
            if game is None:
                break

            board = chess.Board()
            node = game
            while node.variations:
                node = node.variations[0]
                move = node.move
                fen = board.fen()

                self.book_moves.add(f"{fen}|{move.uci()}")
                count += 1
                board.push(move)

            idx = content.find("\n\n", content.find("]"))
            if idx == -1:
                break
            content = content[idx:].strip()

        return count

    def _load_polyglot_book(self, filepath: str) -> int:

        count = 0
        try:

            with open(filepath, "rb") as f:
                data = f.read()

            entry_size = 16
            for i in range(0, len(data), entry_size):
                if i + entry_size > len(data):
                    break

                entry = data[i:i + entry_size]

                key = int.from_bytes(entry[:8], 'big')

                move_data = int.from_bytes(entry[8:10], 'big')

                weight = int.from_bytes(entry[10:12], 'big')

                if weight == 0:
                    continue

                from_sq = (move_data >> 6) & 0x3F
                to_sq = move_data & 0x3F
                promotion = (move_data >> 12) & 0x7

                if not (0 <= from_sq < 64 and 0 <= to_sq < 64):
                    continue

                promo_piece = None
                if promotion:
                    promo_map = {1: chess.KNIGHT, 2: chess.BISHOP,
                                 3: chess.ROOK, 4: chess.QUEEN}
                    promo_piece = promo_map.get(promotion)

                try:
                    move = chess.Move(from_sq, to_sq, promotion=promo_piece)

                    self.book_moves.add(f"any|{move.uci()}")
                    count += 1
                except:
                    continue
        except:
            pass

        return count

    def _load_text_book(self, filepath: str) -> int:

        count = 0
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("//"):

                    if "|" in line:
                        self.book_moves.add(line)
                    else:
                        self.book_moves.add(f"any|{line}")
                    count += 1
        return count

    def is_book_move(self, board: chess.Board, move: chess.Move) -> bool:

        if not self._loaded:
            self.load_books()

        fen = board.fen()
        move_uci = move.uci()

        if f"{fen}|{move_uci}" in self.book_moves:
            return True

        if f"any|{move_uci}" in self.book_moves:
            return True

        return False

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

        if is_best:
            return "Best"

        if eval_before is None:
            if best_move is None:
                return "Excellent"
            return "Good"

        if eval_after is not None:

            loss_before = eval_before
            loss_after = -eval_after
            loss = loss_before - loss_after
        else:

            loss = 0.5

        if loss < 0:
            loss = 0

        if loss < 0.01:
            return "Best"

        if loss < 0.3:
            return "Excellent"

        if loss < 0.7:
            return "Good"

        if loss < 1.2:
            return "Inaccuracy"

        if loss < 2.5:
            return "Mistake"

        return "Blunder"
