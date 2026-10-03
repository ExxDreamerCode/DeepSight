from __future__ import annotations
import glob
import os
from typing import List, Optional, Sequence, Set
import chess
import chess.pgn
import chess.polyglot
from .classification_types import (
    AlternativeLine,
    ClassificationConfig,
    ClassificationResult,
    MoveClassification,
    is_endgame_position,
)
from .expected_points import Score, expected_points_loss
from .see import static_exchange_evaluation

class BookChecker:
    def __init__(self, books_dir: str = "Books"):
        self.books_dir = books_dir
        self.book_moves: Set[str] = set()
        self._polyglot_readers: List[chess.polyglot.MemoryMappedReader] = []
        self._loaded = False

    def load_books(self) -> int:
        from .engine_registry import get_data_path

        self.book_moves.clear()
        self._polyglot_readers.clear()
        count = 0

        search_dirs = [self.books_dir]
        data_path = get_data_path(self.books_dir)
        if data_path != self.books_dir:
            search_dirs.append(data_path)

        for search_dir in search_dirs:
            if os.path.isdir(search_dir):
                self.books_dir = search_dir
                break
        else:
            self._loaded = True
            return 0

        for filepath in glob.glob(os.path.join(self.books_dir, "*")):
            ext = os.path.splitext(filepath)[1].lower()
            try:
                if ext == ".pgn":
                    count += self._load_pgn_book(filepath)
                elif ext == ".txt" or ext == ".bk":
                    count += self._load_text_book(filepath)
                elif ext == ".bin":
                    count += self._load_polyglot_book(filepath)
            except Exception as e:
                print(f"Failed to load book {filepath}: {e}")

        self._loaded = True
        return count

    def _load_polyglot_book(self, filepath: str) -> int:
        try:
            reader = chess.polyglot.MemoryMappedReader(filepath)
            self._polyglot_readers.append(reader)
            size = os.path.getsize(filepath)
            count = size // 16
            print(f"Loaded PolyGlot book: {filepath} ({count} entries)")
            return count
        except Exception as e:
            print(f"Error loading PolyGlot book {filepath}: {e}")
            return 0

    def _load_pgn_book(self, filepath: str) -> int:
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as handle:
                while True:
                    try:
                        game = chess.pgn.read_game(handle)
                    except Exception:
                        break
                    if game is None:
                        break

                    board = game.board()
                    node = game
                    while node.variations:
                        node = node.variations[0]
                        move = node.move
                        if move is None:
                            break
                        self.book_moves.add(f"{board.fen()}|{move.uci()}")
                        count += 1
                        board.push(move)
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

        if self._polyglot_readers:
            for reader in self._polyglot_readers:
                try:
                    for entry in reader.find_all(board):
                        if entry.move == move:
                            return True
                except Exception:
                    continue

        if not self.book_moves:
            return False

        return f"{board.fen()}|{move.uci()}" in self.book_moves


class MoveClassifier:
    def __init__(self, book_checker: Optional[BookChecker] = None,
                 config: Optional[ClassificationConfig] = None):
        self.book_checker = book_checker if book_checker is not None else BookChecker()
        self.config = config or ClassificationConfig()

    def classify(self, board_before: chess.Board,
                 played_move: chess.Move,
                 best_move: Optional[chess.Move] = None,
                 eval_before=None,
                 eval_after=None,
                 alternatives: Optional[Sequence] = None,
                 prev_player_ep: Optional[float] = None,
                 depth: int = 0) -> ClassificationResult:
        config = self.config
        score_before = Score.coerce(eval_before)
        score_after = Score.coerce(eval_after)

        ep_before = (score_before.expected_points(config.rating)
                     if score_before is not None else None)
        ep_after = (score_after.expected_points_for_other_side(config.rating)
                    if score_after is not None else None)
        ep_loss = expected_points_loss(ep_before, ep_after)

        is_best = (best_move is not None
                   and played_move.uci() == best_move.uci())

        lines = self._prepare_alternatives(board_before, alternatives, ep_before)
        only_good_move = self._is_only_good_move(lines)

        see_value: Optional[int] = None
        is_sacrifice = False
        if played_move in board_before.legal_moves:
            see_value = static_exchange_evaluation(board_before, played_move)
            is_sacrifice = see_value <= -config.sacrifice_threshold()

        result = ClassificationResult(
            label=MoveClassification.GOOD.value,
            ep_before=ep_before,
            ep_after=ep_after,
            ep_loss=ep_loss,
            see=see_value,
            is_sacrifice=is_sacrifice,
            is_best=is_best,
            only_good_move=only_good_move,
            alternatives=tuple(lines),
        )

        if self._delivers_mate(board_before, played_move):
            return self._finish(result, MoveClassification.BEST, "checkmate")

        if config.mark_forced_moves and self._legal_move_count(board_before) == 1:
            return self._finish(result, MoveClassification.FORCED, "only legal move")

        if config.use_book and self._is_book(board_before, played_move):
            return self._finish(result, MoveClassification.BOOK, "opening book")

        if ep_loss is None:
            if is_best:
                return self._finish(result, MoveClassification.BEST, "engine's top move")
            if best_move is None:
                return self._finish(result, MoveClassification.EXCELLENT,
                                    "no engine evaluation available")
            return self._finish(result, MoveClassification.GOOD,
                                "no engine evaluation available")

        if self._is_brilliant(board_before, result, lines):
            return self._finish(result, MoveClassification.BRILLIANT,
                                self._brilliant_reason(board_before, lines))

        if self._is_great(result, lines, prev_player_ep):
            return self._finish(result, MoveClassification.GREAT,
                                self._great_reason(result, only_good_move,
                                                   prev_player_ep))

        if self._is_miss(score_before, score_after, result):
            reason = ("missed a forced mate" if score_before.is_winning_mate
                      else "missed a winning continuation")
            return self._finish(result, MoveClassification.MISS, reason)

        return self._finish(result, MoveClassification(self._band(ep_loss)),
                            f"lost {ep_loss:.3f} expected points")

    def _is_brilliant(self, board_before: chess.Board,
                      result: ClassificationResult,
                      lines: Sequence[AlternativeLine]) -> bool:
        config = self.config

        if not result.is_sacrifice or result.ep_loss is None:
            return False
        if result.ep_loss > config.brilliant_max_loss:
            return False
        if result.ep_after is None or result.ep_after < config.brilliant_not_bad_ep:
            return False
        if not lines:
            return False

        safe_alternatives = [line for line in lines
                             if not line.is_sacrifice
                             and line.ep_loss is not None
                             and line.ep_loss <= config.safe_alternative_max_loss]

        if is_endgame_position(board_before, config.endgame_material_points):
            if safe_alternatives:
                return False
            if not all(line.ep_loss is not None
                       and line.ep_loss >= config.only_good_move_min_loss
                       for line in lines):
                return False
        else:
            if not safe_alternatives:
                return False

        candidates = safe_alternatives or list(lines)
        eps = [line.ep for line in candidates if line.ep is not None]
        if eps and min(eps) > config.brilliant_not_winning_ep:
            return False

        return True

    def _brilliant_reason(self, board_before: chess.Board,
                          lines: Sequence[AlternativeLine]) -> str:
        if is_endgame_position(board_before, self.config.endgame_material_points):
            return "sound sacrifice and the only good move"
        return "sound sacrifice with a safe alternative on the board"

    def _is_great(self, result: ClassificationResult,
                  lines: Sequence[AlternativeLine],
                  prev_player_ep: Optional[float]) -> bool:
        config = self.config

        if result.ep_loss is None or result.ep_loss > config.great_max_loss:
            return False

        if (result.only_good_move
                and result.ep_before is not None
                and result.ep_before >= config.great_min_ep):
            return True

        if prev_player_ep is None or result.ep_after is None:
            return False

        if (prev_player_ep <= config.great_losing_max_ep
                and result.ep_after >= config.great_equal_after_ep):
            return True

        low, high = config.great_equal_band
        if (low <= prev_player_ep <= high
                and result.ep_after >= config.great_winning_after_ep):
            return True

        return False

    def _great_reason(self, result: ClassificationResult, only_good_move: bool,
                      prev_player_ep: Optional[float]) -> str:
        config = self.config
        if (only_good_move and result.ep_before is not None
                and result.ep_before >= config.great_min_ep):
            return "only good move in the position"
        if prev_player_ep is not None and prev_player_ep <= config.great_losing_max_ep:
            return "turned a losing position into an equal one"
        return "turned an equal position into a winning one"

    def _is_miss(self, score_before: Optional[Score],
                 score_after: Optional[Score],
                 result: ClassificationResult) -> bool:
        config = self.config
        if result.ep_loss is None:
            return False

        if (score_before is not None and score_before.is_winning_mate
                and score_after is not None):
            still_mating = score_after.is_mate and score_after.mate <= 0
            if not still_mating:
                return True

        if (result.ep_before is not None and result.ep_after is not None
                and result.ep_before >= config.miss_winning_ep
                and result.ep_after <= config.miss_result_ep
                and result.ep_loss >= config.miss_min_loss):
            return True

        return False

    def _band(self, ep_loss: float) -> str:
        config = self.config
        if ep_loss <= config.best_max_loss:
            return MoveClassification.BEST.value
        if ep_loss <= config.excellent_max_loss:
            return MoveClassification.EXCELLENT.value
        if ep_loss <= config.good_max_loss:
            return MoveClassification.GOOD.value
        if ep_loss <= config.inaccuracy_max_loss:
            return MoveClassification.INACCURACY.value
        if ep_loss <= config.mistake_max_loss:
            return MoveClassification.MISTAKE.value
        return MoveClassification.BLUNDER.value

    def _prepare_alternatives(self, board_before: chess.Board,
                              alternatives: Optional[Sequence],
                              ep_before: Optional[float]) -> List[AlternativeLine]:
        lines: List[AlternativeLine] = []
        for raw in alternatives or ():
            line = self._coerce_alternative(board_before, raw)
            if line is None:
                continue
            line.ep = line.score.expected_points(self.config.rating)
            line.ep_loss = expected_points_loss(ep_before, line.ep)
            lines.append(line)
        return lines

    def _coerce_alternative(self, board_before: chess.Board,
                            raw) -> Optional[AlternativeLine]:
        if raw is None:
            return None

        if isinstance(raw, AlternativeLine):
            line = AlternativeLine(move=raw.move, score=raw.score)
        elif isinstance(raw, (tuple, list)) and len(raw) == 2:
            move, score = raw
            line = AlternativeLine(move=move, score=Score.coerce(score))
        else:
            move = getattr(raw, "move", None)
            score = Score.from_move_eval(raw)
            if move is None or score is None:
                return None
            line = AlternativeLine(move=move, score=score)

        if line.move is None or line.score is None:
            return None
        if line.move == chess.Move.null():
            return None
        if line.move in board_before.legal_moves:
            line.see = static_exchange_evaluation(board_before, line.move)
        return line

    def _is_only_good_move(self, lines: Sequence[AlternativeLine]) -> bool:
        if not lines:
            return False
        return all(line.ep_loss is not None
                   and line.ep_loss >= self.config.only_good_move_min_loss
                   for line in lines)

    def _is_book(self, board_before: chess.Board, played_move: chess.Move) -> bool:
        if self.book_checker is None:
            return False
        try:
            return self.book_checker.is_book_move(board_before, played_move)
        except Exception:
            return False

    @staticmethod
    def _legal_move_count(board_before: chess.Board) -> int:
        try:
            return board_before.legal_moves.count()
        except Exception:
            return 0

    @staticmethod
    def _delivers_mate(board_before: chess.Board, played_move: chess.Move) -> bool:
        if played_move not in board_before.legal_moves:
            return False
        board = board_before.copy(stack=False)
        board.push(played_move)
        return board.is_checkmate()

    @staticmethod
    def _finish(result: ClassificationResult, label: MoveClassification,
                reason: str) -> ClassificationResult:
        result.label = label.value if isinstance(label, MoveClassification) else str(label)
        result.reason = reason
        return result
