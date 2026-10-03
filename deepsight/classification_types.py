from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence, Tuple
import chess
from .expected_points import Score
from .see import sacrifice_threshold_for_rating

class MoveClassification(str, Enum):
    BRILLIANT = "Brilliant"
    GREAT = "Great"
    BEST = "Best"
    EXCELLENT = "Excellent"
    GOOD = "Good"
    BOOK = "Book"
    INACCURACY = "Inaccuracy"
    MISTAKE = "Mistake"
    MISS = "Miss"
    BLUNDER = "Blunder"
    FORCED = "Forced"

    def __str__(self) -> str:
        return self.value

POSITIVE_LABELS = (
    MoveClassification.BRILLIANT.value,
    MoveClassification.GREAT.value,
    MoveClassification.BEST.value,
    MoveClassification.EXCELLENT.value,
    MoveClassification.GOOD.value,
    MoveClassification.BOOK.value,
    MoveClassification.FORCED.value,
)

NEGATIVE_LABELS = (
    MoveClassification.INACCURACY.value,
    MoveClassification.MISTAKE.value,
    MoveClassification.MISS.value,
    MoveClassification.BLUNDER.value,
)


@dataclass
class ClassificationConfig:
    rating: Optional[int] = None

    best_max_loss: float = 0.0005
    excellent_max_loss: float = 0.02
    good_max_loss: float = 0.05
    inaccuracy_max_loss: float = 0.10
    mistake_max_loss: float = 0.20

    great_max_loss: float = 0.02
    only_good_move_min_loss: float = 0.10
    great_min_ep: float = 0.10
    great_losing_max_ep: float = 0.25
    great_equal_after_ep: float = 0.45
    great_equal_band: Tuple[float, float] = (0.35, 0.65)
    great_winning_after_ep: float = 0.80

    brilliant_max_loss: float = 0.02
    safe_alternative_max_loss: float = 0.05
    brilliant_not_winning_ep: float = 0.90
    brilliant_not_bad_ep: float = 0.35

    sacrifice_cp: Optional[int] = None

    endgame_material_points: int = 13

    miss_winning_ep: float = 0.80
    miss_result_ep: float = 0.55
    miss_min_loss: float = 0.20

    mark_forced_moves: bool = True
    use_book: bool = True

    def sacrifice_threshold(self) -> int:
        if self.sacrifice_cp is not None:
            return int(self.sacrifice_cp)
        return sacrifice_threshold_for_rating(self.rating)


@dataclass
class AlternativeLine:
    move: chess.Move
    score: Score
    ep: Optional[float] = None
    ep_loss: Optional[float] = None
    see: int = 0

    @property
    def is_sacrifice(self) -> bool:
        return self.see < 0


@dataclass
class ClassificationResult:
    label: str
    reason: str = ""
    ep_before: Optional[float] = None
    ep_after: Optional[float] = None
    ep_loss: Optional[float] = None
    see: Optional[int] = None
    is_sacrifice: bool = False
    is_best: bool = False
    only_good_move: bool = False
    alternatives: Sequence[AlternativeLine] = field(default_factory=tuple)

    def __str__(self) -> str:
        return self.label

    @property
    def is_positive(self) -> bool:
        return self.label in POSITIVE_LABELS

    @property
    def is_negative(self) -> bool:
        return self.label in NEGATIVE_LABELS


def is_endgame_position(board: chess.Board, material_points: int = 13) -> bool:
    total = 0
    for piece_type, points in ((chess.QUEEN, 9), (chess.ROOK, 5),
                               (chess.KNIGHT, 3), (chess.BISHOP, 3)):
        total += points * (len(board.pieces(piece_type, chess.WHITE))
                           + len(board.pieces(piece_type, chess.BLACK)))
    return total <= material_points
