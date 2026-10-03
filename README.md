# DeepSight — Chess Analyzer

**DeepSight** is a desktop application for deep analysis of chess games, with a graphical interface. It loads games in PGN format, accepts any position as FEN, connects to UCI-compatible chess engines and returns a detailed score for every move.

Russian version: [docs/README.ru.md](docs/README.ru.md).

![Python](https://img.shields.io/badge/python-3.11-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
[![CI](https://github.com/ExxDreamerCode/DeepSight/actions/workflows/ci.yml/badge.svg)](https://github.com/ExxDreamerCode/DeepSight/actions/workflows/ci.yml)

<img alt="DeepSight window: chessboard, evaluation bar and side panels" src="Images/screenshot.png" width="860">

---

## Features

- **Game loading** — import PGN files or paste PGN text
- **Arbitrary positions** — set any position through FEN
- **Built-in engines** — Ember and Stockfish come from the Nix build, but are not stored in the repository
- **External engines** — connect any UCI-compatible engine
- **Full game analysis** — every move analysed automatically and scored in centipawns or mate
- **Incremental re-analysis** — moves that already have a result are kept, so after editing the end of a game only the affected moves are evaluated again
- **Live evaluation** — a fast score for the current position, without running a full analysis
- **Move classification** — Game Review labels (Brilliant, Great, Best, Excellent, Good, Book, Inaccuracy, Mistake, Miss, Blunder, Forced) driven by an expected-points model that accounts for how lost or won the position already is.
- **Game navigation** — arrow keys step through the moves, Home/End jump to either end
- **Evaluation bar** — a visual read on who is ahead
- **Best-move arrow** — the engine's suggested move drawn on the board
- **Dark theme** — the whole interface is dark
- **NNUE support** — uses the engine's neural network weights where the engine supports them

---

## Installation

### Requirements

- Python 3.11+
- Linux x86_64 for the Nix build of the current system

### Dependencies

```
PyQt6>=6.5
python-chess>=1.999
pytest>=7.0
```

### Installing from source

```bash
git clone https://github.com/ExxDreamerCode/DeepSight.git
cd DeepSight
pip install -r requirements.txt
Engines/download-engines.bat
python main.py
```

Engines are not kept in the source tree. To run the built-in engines from source, put compatible UCI executables into `Engines/`, or use the Nix build below. Otherwise run `download-engines.bat`, which fetches both required engines automatically.

### Building with Nix for the current system

```bash
nix build .#
./result/bin/deepsight
```

This build produces a Nix derivation of the application and adds the engines to it:

- Ember is downloaded from the pinned `ExxDreamerCode/Ember` release
- Stockfish is downloaded from the pinned `official-stockfish/Stockfish` release

### Building the Windows exe by hand

The Nix build is Linux-only. On Windows, use PyInstaller directly — the configuration lives in `deepsight.spec`.

```bash
pip install pyinstaller
pyinstaller deepsight.spec --clean --noconfirm
```

The finished `.exe` appears in `dist/`. The PyInstaller spec embeds the engines, so put compatible Windows UCI engines next to the application in `Engines/`, or run `Engines/download-engines.bat`. If the engines are missing, a PyInstaller build downloads them automatically.

---

## Usage

1. **Start the application:**
   ```bash
   python main.py
   ```

2. **Load a game:**
   - Click `File → Load PGN...` and choose a PGN file
   - Or paste PGN text into the field on the left panel and press "Load PGN"

3. **Set an arbitrary position:**
   - Enter a FEN into the matching field and press "Set FEN"

4. **Analysis:**
   - Choose an engine (Ember, Stockfish or an external one)
   - Set the time per move and the analysis depth
   - Press "Start Analysis"
   - Progress is shown in the status bar
   - "Skip analyzed moves" (on by default) keeps the result already stored for every move, so
     running the analysis again only evaluates what has no result yet, or what changed. Turn it
     off to score the whole game from scratch. Results live in memory for the current session and
     are dropped when a game is loaded again; changing the engine, the depth, the time per move or
     the number of MultiPV lines also invalidates them.

5. **Navigation:**
   - ← / → — step through the moves
   - Home / End — jump to the start or the end of the game
   - Click a move in the list to jump to it

6. **Quick evaluation:**
   - Runs automatically when a game is loaded or a move is selected
   - Shown on the evaluation bar and in the status bar

---

## Built-in engines

| Engine | Linux Nix build | Windows, by hand | Protocol | License |
|--------|-------------------|----------------|----------|---------|
| **Ember** | `Engines/ember-1.3.1` | `Engines/ember-1.3.1.exe` | UCI | MIT (ours) |
| **Stockfish** | `Engines/stockfish` | `Engines/stockfish-windows-x86-64.exe` | UCI | GPL-3.0-or-later - see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

Engines are not committed to the repository. The Linux Nix build downloads or builds them as part of the derivation. On Windows, put compatible `.exe` engines into `Engines/` next to the application, or run `Engines/download-engines.bat`. Both engines are named after the version they come from, so the folder says which one you have; a plain `ember.exe` or `ember` is accepted as well.

---

## Keyboard shortcuts

| Key | Action |
|---------|----------|
| ← | Previous move |
| → | Next move |
| Home | Start of the game |
| End | End of the game |

---

## Development

### Running in debug mode

The `Debug` menu offers:

- **Show Engine Output** — a window with the engine's raw output
- **Test Engine Direct** — a direct check of the engine connection

### Adding a new engine

1. Add the engine source to `flake.nix`
2. Install the executable into `Engines/` inside the Linux Nix build
3. Add an entry to `BUILTIN_ENGINES` in `engine_registry.py`
4. Set the protocol in `get_engine_protocol()` if needed

### Tests

```bash
pip install -r requirements.txt
python -m pytest
```

The fast suite covers the expected-points model, static exchange evaluation, the
move classifier, the opening book, the engine's MultiPV plumbing and the
incremental re-analysis. It needs no engine binary.

The end-to-end suite runs a whole game through a real UCI engine and is opt-in,
because it requires one of the engines in `Engines/`:

```bash
DEEPSIGHT_RUN_ENGINE_TESTS=1 python -m pytest
```

[CI](.github/workflows/ci.yml) runs on every push and pull request, on Linux, Windows and macOS:
the fast suite on Python 3.13, and the end-to-end suite against each engine the builds ship,
downloaded from the release pinned in `flake.nix`.

---

## Contributors

- [ExxDreamerCode](https://github.com/ExxDreamerCode)
- [Boris Nagaev (@starius)](https://github.com/starius)

---

## License

DeepSight's own code is distributed under the MIT license. See [LICENSE](LICENSE) for details.

That license covers this application and not the engines shipped with it. Ember is ours and MIT as well; Stockfish 18 is GPL-3.0-or-later. Both are separate programs, started as their own processes and spoken to over UCI, so each keeps its own license - see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The Python dependencies are third-party too and keep their own licenses: [python-chess](https://github.com/niklasf/python-chess) is GPL-3.0-or-later and PyQt6 is GPL-3.0-only (Riverbank also sells a commercial license for it).
