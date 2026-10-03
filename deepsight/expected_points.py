from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

BASE_SLOPE = 0.00368208
RATING_MIN = 600.0
RATING_MAX = 2400.0
RATING_SCALE_MIN = 0.65
RATING_SCALE_MAX = 1.10
MATE_WIN_EP = 1.0
MATE_LOSS_EP = 0.0
_EXP_LIMIT = 60.0

def rating_slope_scale(rating: Optional[float]) -> float:
    if rating is None:
        return 1.0

    r = min(max(float(rating), RATING_MIN), RATING_MAX)
    t = (r - RATING_MIN) / (RATING_MAX - RATING_MIN)
    return RATING_SCALE_MIN + t * (RATING_SCALE_MAX - RATING_SCALE_MIN)


def slope(rating: Optional[float] = None) -> float:
    return BASE_SLOPE * rating_slope_scale(rating)


def cp_to_expected_points(cp: float, rating: Optional[float] = None) -> float:
    x = slope(rating) * float(cp)
    if x >= _EXP_LIMIT:
        return MATE_WIN_EP
    if x <= -_EXP_LIMIT:
        return MATE_LOSS_EP
    return 1.0 / (1.0 + math.exp(-x))


def mate_to_expected_points(mate: int) -> float:
    return MATE_WIN_EP if mate > 0 else MATE_LOSS_EP


@dataclass(frozen=True)
class Score:
    cp: Optional[int] = None
    mate: Optional[int] = None

    def __post_init__(self):
        if self.mate is not None:
            object.__setattr__(self, "cp", None)

    @property
    def is_mate(self) -> bool:
        return self.mate is not None

    @property
    def is_winning_mate(self) -> bool:
        return self.mate is not None and self.mate > 0

    @property
    def is_losing_mate(self) -> bool:
        return self.mate is not None and self.mate <= 0

    def negated(self) -> "Score":
        if self.mate is not None:
            return Score(mate=-self.mate)
        if self.cp is not None:
            return Score(cp=-self.cp)
        return Score()

    def expected_points(self, rating: Optional[float] = None) -> Optional[float]:
        if self.mate is not None:
            return mate_to_expected_points(self.mate)
        if self.cp is not None:
            return cp_to_expected_points(self.cp, rating)
        return None

    def expected_points_for_other_side(self, rating: Optional[float] = None) -> Optional[float]:
        ep = self.expected_points(rating)
        return None if ep is None else 1.0 - ep

    @classmethod
    def from_cp(cls, cp: Optional[float]) -> Optional["Score"]:
        if cp is None:
            return None
        return cls(cp=int(round(cp)))

    @classmethod
    def from_pawns(cls, pawns: Optional[float]) -> Optional["Score"]:
        if pawns is None:
            return None
        return cls(cp=int(round(pawns * 100.0)))

    @classmethod
    def from_move_eval(cls, eval_data) -> Optional["Score"]:
        if eval_data is None:
            return None
        return cls(cp=getattr(eval_data, "score_cp", None),
                   mate=getattr(eval_data, "mate", None))

    @classmethod
    def coerce(cls, value) -> Optional["Score"]:
        if value is None or isinstance(value, Score):
            return value
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return cls.from_pawns(float(value))
        if hasattr(value, "score_cp") or hasattr(value, "mate"):
            return cls.from_move_eval(value)
        return None


def expected_points_loss(ep_before: Optional[float],
                         ep_after: Optional[float]) -> Optional[float]:
    if ep_before is None or ep_after is None:
        return None
    return max(0.0, float(ep_before) - float(ep_after))
