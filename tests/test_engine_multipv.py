import chess
import pytest

from deepsight.engine_manager import EngineManager, EngineProtocol
from deepsight.expected_points import Score
from deepsight.models.game_state import MoveEval


class FakeStdin:
    def __init__(self):
        self.written = []

    def write(self, data):
        self.written.append(data.decode("utf-8"))
        return len(data)

    def flush(self):
        pass


class FakeProcess:
    def __init__(self):
        self.stdin = FakeStdin()


def manager_with_options(options=None):
    manager = EngineManager("dummy-engine")
    manager.process = FakeProcess()
    manager._uci_options = dict(options or {})
    return manager


def test_parse_uci_info_extracts_multipv_rank():
    info = manager_with_options().parse_uci_info(
        "info depth 18 seldepth 24 multipv 2 score cp -34 nodes 100 pv e2e4 e7e5"
    )
    assert info["multipv"] == 2
    assert info["score_cp"] == -34
    assert info["pv"] == "e2e4 e7e5"


def test_parse_uci_info_defaults_to_no_rank():
    info = manager_with_options().parse_uci_info("info depth 12 score cp 15 pv d2d4")
    assert "multipv" not in info


def test_parse_uci_info_reads_mate_scores():
    info = manager_with_options().parse_uci_info(
        "info depth 20 multipv 1 score mate -3 pv h7h8q"
    )
    assert info["mate"] == -3


def test_set_multipv_sends_the_option():
    manager = manager_with_options({"multipv": "MultiPV"})
    assert manager.supports_multipv()
    manager.set_multipv(3)
    assert manager.process.stdin.written == ["setoption name MultiPV value 3\n"]


def test_set_multipv_is_a_no_op_without_engine_support():
    manager = manager_with_options({})
    assert not manager.supports_multipv()
    manager.set_multipv(3)
    assert manager.process.stdin.written == []


def test_set_multipv_clamps_to_at_least_one():
    manager = manager_with_options({"multipv": "MultiPV"})
    manager.set_multipv(0)
    assert manager.process.stdin.written == ["setoption name MultiPV value 1\n"]


def test_set_multipv_ignored_for_xboard():
    manager = EngineManager("dummy", EngineProtocol.XBOARD)
    manager.process = FakeProcess()
    manager._uci_options = {"multipv": "MultiPV"}
    manager.set_multipv(3)
    assert manager.process.stdin.written == []


def test_alternatives_only_use_ranks_above_one():
    rank_evals = {}
    lines = [
        "info depth 10 multipv 1 score cp 30 pv e2e4",
        "info depth 10 multipv 2 score cp 10 pv d2d4",
        "info depth 10 multipv 3 score cp -40 pv g1f3",
        "info depth 12 multipv 1 score cp 25 pv e2e4 e7e5",
        "info depth 12 multipv 2 score cp 5 pv d2d4 d7d5",
    ]
    manager = manager_with_options()

    for line in lines:
        info = manager.parse_uci_info(line)
        move = chess.Move.from_uci(info["pv"].split()[0])
        entry = MoveEval(
            move=move,
            score_cp=float(info["score_cp"]),
            depth=info["depth"],
            multipv=info.get("multipv", 1),
        )
        rank = max(1, entry.multipv)
        previous = rank_evals.get(rank)
        if previous is None or entry.depth >= (previous.depth or 0):
            rank_evals[rank] = entry

    principal = rank_evals[1]
    alternatives = [rank_evals[r] for r in sorted(rank_evals) if r > 1]

    assert principal.depth == 12 and principal.score_cp == 25.0
    assert [ev.move.uci() for ev in alternatives] == ["d2d4", "g1f3"]
    assert Score.from_move_eval(alternatives[0]).cp == 5


def test_move_eval_carries_the_multipv_rank():
    eval_data = MoveEval(move=chess.Move.from_uci("e2e4"), score_cp=10.0, multipv=2)
    assert eval_data.multipv == 2
    assert MoveEval(move=chess.Move.from_uci("e2e4")).multipv == 1


@pytest.mark.parametrize("line", [
    "info depth 5",
    "bestmove e2e4",
    "",
    "uciok",
])
def test_non_score_lines_are_ignored(line):
    assert manager_with_options().parse_uci_info(line) is None
