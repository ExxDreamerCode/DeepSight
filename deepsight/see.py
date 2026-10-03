from __future__ import annotations
from typing import Optional
import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

SACRIFICE_THRESHOLD_DEFAULT = 200
SACRIFICE_THRESHOLD_BEGINNER = 100
SACRIFICE_THRESHOLD_ADVANCED = 300

def piece_value(piece_type: int) -> int:
    return PIECE_VALUES.get(piece_type, 0)


def sacrifice_threshold_for_rating(rating: Optional[int]) -> int:
    if rating is None:
        return SACRIFICE_THRESHOLD_DEFAULT
    if rating < 1200:
        return SACRIFICE_THRESHOLD_BEGINNER
    if rating < 2000:
        return SACRIFICE_THRESHOLD_DEFAULT
    return SACRIFICE_THRESHOLD_ADVANCED


def _capture_move(board: chess.Board, from_square: chess.Square,
                  to_square: chess.Square) -> chess.Move:
    piece = board.piece_at(from_square)
    if (piece is not None and piece.piece_type == chess.PAWN
            and chess.square_rank(to_square) in (0, 7)):
        return chess.Move(from_square, to_square, promotion=chess.QUEEN)
    return chess.Move(from_square, to_square)


def _least_valuable_attacker(board: chess.Board, color: chess.Color,
                             square: chess.Square) -> Optional[chess.Move]:
    candidates = []
    for attacker_square in board.attackers(color, square):
        piece = board.piece_at(attacker_square)
        if piece is None:
            continue
        candidates.append((piece_value(piece.piece_type), attacker_square))
    candidates.sort()

    for _, attacker_square in candidates:
        capture = _capture_move(board, attacker_square, square)
        if board.is_legal(capture):
            return capture
    return None


def _swap_gain(board: chess.Board, square: chess.Square, color: chess.Color) -> int:
    victim = board.piece_at(square)
    if victim is None or victim.color == color:
        return 0

    capture = _least_valuable_attacker(board, color, square)
    if capture is None:
        return 0

    gain = piece_value(victim.piece_type)
    if capture.promotion is not None:
        gain += piece_value(capture.promotion) - piece_value(chess.PAWN)

    board.push(capture)
    try:
        gain -= _swap_gain(board, square, not color)
    finally:
        board.pop()

    return max(0, gain)


def static_exchange_evaluation(board: chess.Board, move: chess.Move) -> int:
    if move not in board.legal_moves:
        return 0

    if board.is_en_passant(move):
        initial = piece_value(chess.PAWN)
    else:
        victim = board.piece_at(move.to_square)
        initial = piece_value(victim.piece_type) if victim is not None else 0

    if move.promotion is not None:
        initial += piece_value(move.promotion) - piece_value(chess.PAWN)

    working = board.copy(stack=False)
    working.push(move)
    return initial - _swap_gain(working, move.to_square, working.turn)


def material_given_up(board: chess.Board, move: chess.Move) -> int:
    return max(0, -static_exchange_evaluation(board, move))


def is_sacrifice(board: chess.Board, move: chess.Move,
                 threshold: int = SACRIFICE_THRESHOLD_DEFAULT) -> bool:
    return material_given_up(board, move) >= threshold
