# DeepSight — Chess Analyzer

**DeepSight** is a desktop application for deep analysis of chess games, with a graphical interface. It loads games in PGN format, accepts any position as FEN, connects to UCI-compatible chess engines and returns a detailed score for every move.

Russian version: [docs/README.ru.md](docs/README.ru.md).

![Python](https://img.shields.io/badge/python-3.13-blue)
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
python Engines/fetch_engines.py
python main.py
```

Engines are not kept in the source tree. `Engines/fetch_engines.py` installs the two the builds ship for the machine it runs on: it downloads each one from its pinned release, checks the SHA-256 recorded in `engines.json` and only then puts it into `Engines/`. `--target linux-arm64` fetches for another platform instead, `--list` shows what is available, and on Windows `Engines/download-engines.bat` is the same script with a Python interpreter looked up for you. The Nix build below does the same thing inside the derivation.

### Building with Nix for the current system

```bash
nix build .#
./result/bin/deepsight
```

This build produces a Nix derivation of the application and adds the engines to it:

- Ember is downloaded from the pinned `ExxDreamerCode/Ember` release
- Stockfish is downloaded from the pinned `official-stockfish/Stockfish` release

### Building the application by hand

The Nix build is Linux-only. PyInstaller covers the other systems, and its configuration lives in `deepsight.spec`:

```bash
pip install pyinstaller
pyinstaller deepsight.spec --clean --noconfirm
```

The finished single-file build appears in `dist/`. The spec embeds the engines, so run `Engines/fetch_engines.py` first — or `Engines/download-engines.bat` on Windows, which also downloads them automatically when a build finds none.

The releases come from the same spec with three switches set:

```bash
DEEPSIGHT_ONEDIR=1 DEEPSIGHT_REQUIRE_ENGINES=1 DEEPSIGHT_UPX=0 pyinstaller deepsight.spec --noconfirm --clean
```

- `DEEPSIGHT_ONEDIR` produces a folder instead of a single file. With two engines and Qt inside, a one-file build would unpack hundreds of megabytes on every launch.
- `DEEPSIGHT_REQUIRE_ENGINES` fails the build when an engine is missing, so a release cannot go out without them.
- `DEEPSIGHT_UPX=0` keeps UPX away from the executables, which some antivirus products flag.

On macOS the same build also produces `dist/DeepSight.app` with the version in its `Info.plist`, and on Windows the `.exe` carries the version, the product name and the copyright as file properties. Place `Images/DeepSight.ico` or `Images/DeepSight.icns` next to the other images to give the builds an icon; without it they get the PyInstaller default.

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

7. **Checking a build:**
   ```bash
   python main.py --version
   python main.py --self-check report.json
   ```
   `--self-check` writes a JSON report of what the application actually found — its version, whether it is a packaged build, the Qt and Python versions, where each engine is, whether each one answers UCI, and whether the book, the images and the license notices are in place. It exits non-zero when something is missing, which is how the release workflow refuses to publish a broken artifact. The same summary appears under `Help → About DeepSight`.

---

## Releases

Releases are built by [.github/workflows/release.yml](.github/workflows/release.yml) from a `v` tag, and only once the whole test suite has passed — the fast one on three systems, then the end-to-end games against both engines. Every build runs its own packaged application with `--self-check`, so an artifact whose engines do not answer, or that is missing the book or the license notices, never reaches the release page.

| Artifact | System |
|----------|--------|
| `DeepSight-<version>-windows-x86_64.zip` | Windows, Intel and AMD |
| `DeepSight-<version>-windows-arm64.zip` | Windows on Arm |
| `DeepSight-<version>-macos-arm64.zip` | macOS, Apple silicon |
| `DeepSight-<version>-macos-x86_64.zip` | macOS, Intel |
| `DeepSight-<version>-linux-x86_64.tar.gz` | Linux, Intel and AMD |
| `DeepSight-<version>-linux-arm64.tar.gz` | Linux on Arm |

Both engines travel inside each archive, so nothing has to be downloaded on first launch. `SHA256SUMS.txt` carries the digests, and every artifact gets a build provenance attestation. The Linux and Windows x86_64 builds ship the official engine releases; for Linux on Arm, where Stockfish publishes nothing, the release workflow builds it from the pinned source commit instead.

The builds are not code signed, because there is no paid certificate behind them.

- **macOS** refuses an unsigned download with "the developer cannot be verified". Open it once with a right click and then "Open", or clear the flag: `xattr -dr com.apple.quarantine DeepSight.app`.
- **Windows** may show a SmartScreen warning. Choose "More info", then "Run anyway".

---

## Built-in engines

| Engine | Version | Unix builds | Windows builds | Protocol | License |
|--------|---------|-------------|----------------|----------|---------|
| **Ember** | 1.3.1 | `Engines/ember-1.3.1` | `Engines/ember-1.3.1.exe` | UCI | MIT (ours) |
| **Stockfish** | 18 | `Engines/stockfish` | `Engines/stockfish-windows-x86-64.exe`, or `Engines/stockfish.exe` on Arm | UCI | GPL-3.0-or-later - see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

Engines are not committed to the repository. The releases and the Nix build ship them, and from source `Engines/fetch_engines.py` installs the ones matching the current machine. Which binary comes from which release, under which name and with which digest, is recorded once in `engines.json`, which the downloader, the CI and the release workflow all read — so a release cannot ship an engine that a developer never tested. Both engines are named after the version they come from, so the folder says which one you have; a plain `ember.exe` or `ember` is accepted as well.

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
the fast suite on Python 3.13, and the end-to-end suite with both engines, fetched through
`Engines/fetch_engines.py` from the pins in `engines.json`. The release workflow calls the same
file, so a tag is checked exactly like a branch.

### Versioning

The version lives in `deepsight/__init__.py` and nowhere else. `flake.nix`, the packaging spec, the
About dialog and the release workflow all read it from there, and a test fails when the flake
drifts. Releases are tagged `v<version>`, and the release workflow refuses to publish when the tag
and the code disagree. A version carrying a suffix, such as `0.2.0-rc.1`, is published as a
pre-release.

---

## Contributors

- [ExxDreamerCode](https://github.com/ExxDreamerCode)
- [Boris Nagaev (@starius)](https://github.com/starius)

---

## License

DeepSight's own code is distributed under the MIT license. See [LICENSE](LICENSE) for details.

That license covers this application and not the engines shipped with it. Ember is ours and MIT as well; Stockfish 18 is GPL-3.0-or-later. Both are separate programs, started as their own processes and spoken to over UCI, so each keeps its own license - see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The Python dependencies are third-party too and keep their own licenses: [python-chess](https://github.com/niklasf/python-chess) is GPL-3.0-or-later and PyQt6 is GPL-3.0-only (Riverbank also sells a commercial license for it).
