import chess

from deepsight.move_classifier import BookChecker

START = chess.STARTING_FEN


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_polyglot_reader_is_owned_by_the_checker(tmp_path):
    checker = BookChecker(str(tmp_path))
    assert checker.load_books() == 0
    assert not checker.is_book_move(chess.Board(), chess.Move.from_uci("g1f3"))


def test_text_book_hit_and_miss(tmp_path):
    write(tmp_path / "book.txt",
          "# a comment\n"
          "// another comment\n"
          f"{START}|g1f3\n"
          "\n")

    checker = BookChecker(str(tmp_path))
    assert checker.load_books() == 1
    assert checker.is_book_move(chess.Board(), chess.Move.from_uci("g1f3"))
    assert not checker.is_book_move(chess.Board(), chess.Move.from_uci("e2e4"))


def test_book_is_position_specific(tmp_path):
    board = chess.Board()
    board.push_uci("g1f3")
    fen_after = board.fen()

    write(tmp_path / "book.txt", f"{fen_after}|g8f6\n")

    checker = BookChecker(str(tmp_path))
    checker.load_books()
    assert checker.is_book_move(board, chess.Move.from_uci("g8f6"))
    assert not checker.is_book_move(chess.Board(), chess.Move.from_uci("g8f6"))


def test_pgn_book_is_loaded(tmp_path):
    pgn = ("[Event \"Test\"]\n"
           "[Result \"*\"]\n"
           "\n"
           "1. e4 e5 2. Nf3 Nc6 *\n")
    write(tmp_path / "book.pgn", pgn)

    checker = BookChecker(str(tmp_path))
    loaded = checker.load_books()
    assert loaded == 4
    assert checker.is_book_move(chess.Board(), chess.Move.from_uci("e2e4"))

    board = chess.Board()
    board.push_uci("e2e4")
    assert checker.is_book_move(board, chess.Move.from_uci("e7e5"))
    assert not checker.is_book_move(board, chess.Move.from_uci("d2d4"))


def test_missing_directory_is_not_an_error(tmp_path):
    checker = BookChecker(str(tmp_path / "nope"))
    assert checker.load_books() == 0
    assert not checker.is_book_move(chess.Board(), chess.Move.from_uci("e2e4"))


def test_broken_book_file_is_ignored(tmp_path):
    write(tmp_path / "broken.pgn", "this is not a pgn at all\n")
    write(tmp_path / "good.txt", f"{START}|d2d4\n")

    checker = BookChecker(str(tmp_path))
    checker.load_books()
    assert checker.is_book_move(chess.Board(), chess.Move.from_uci("d2d4"))
