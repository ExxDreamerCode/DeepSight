# Third-party notices

DeepSight's own code is distributed under the MIT license (see [LICENSE](LICENSE)). The builds
published from this repository additionally contain the third-party components below - two chess
engines and two Python libraries - each of which keeps its own license. One part of DeepSight is
modelled on someone else's published system rather than built from third-party code: the move
classification, covered in the last section.

## Stockfish

- **Version:** Stockfish 18 (`sf_18`)
- **Where the binaries come from:** the official release
  https://github.com/official-stockfish/Stockfish/releases/tag/sf_18, which publishes builds for
  Windows and macOS and for Linux on x86-64
- **Where the Linux on Arm binary comes from:** Stockfish publishes no build for that platform, so
  DeepSight compiles the upstream source at commit `cb3d4ee9b47d0c5aae855b12379378ea1439675c`
  (tag `sf_18`) with `ARCH=armv8`, without patches of its own
- **What pins them:** `engines.json` records, for every platform DeepSight ships, which asset or
  which commit each engine comes from and the SHA-256 of the archive or the binary. The downloader,
  the CI and the release workflow all read that one file
- **License:** GNU General Public License, version 3 or later - full text in
  [licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)
- **Copyright:** the Stockfish developers, see the source above
- **Corresponding source:** the repository and the release linked above, unmodified

Stockfish runs as a separate process and speaks UCI over stdin/stdout. DeepSight does not link
against it, modify it or merge it with its own code; the two are separate programs distributed
together.

## Ember

- **Version:** 1.3.1 (revision `9e015493`), the same on every platform
- **Where the binaries come from:** the release
  https://github.com/ExxDreamerCode/Ember/releases/tag/V1.3.1, which publishes
  `ember-1.3.1-9e015493-linux-amd64`, `-linux-arm64`, `-macos-amd64`, `-macos-arm64`,
  `-windows-amd64` and `-windows-arm64`; `engines.json` records which one each platform takes and
  its SHA-256
- **Installed as:** `Engines/ember-1.3.1.exe` on Windows, `Engines/ember-1.3.1` on Linux and macOS
- **Source:** https://github.com/ExxDreamerCode/Ember
- **License:** MIT - full text in [LICENSE](LICENSE)
- **Copyright:** D.r.e.A.m.e.R and the Ember contributors

## python-chess

- **Package:** `python-chess` in `requirements.txt`; the same library is published on PyPI as
  `chess` (1.11.x) and as `python-chess` (1.999), both by the same author
- **Source:** https://github.com/niklasf/python-chess
- **License:** GPL-3.0-or-later - full text in [licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)
- **Copyright:** Niklas Fiekas and the python-chess contributors
- **Used for:** PGN and FEN handling, move generation and the board model

## PyQt6

- **Version:** PyQt6 6.11, with the Qt 6.11 libraries it bundles as `PyQt6-Qt6`
- **Source:** https://www.riverbankcomputing.com/software/pyqt/
- **License:** dual-licensed under the GNU GPL version 3 and the Riverbank Commercial License -
  Riverbank states that PyQt, unlike Qt, is not available under the LGPL. The `PyQt6` wheel
  declares `GPL-3.0-only`, and the Qt libraries in the `PyQt6-Qt6` wheel declare LGPL-3.0. The
  GPL text is in [licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)
- **Copyright:** Riverbank Computing Limited for PyQt6, the Qt Company for the Qt libraries
- **Used for:** the interface - windows, panels, dialogs and painting

Unlike the engines, the two Python libraries are imported rather than run as separate processes, so
they are part of the application itself and their licenses travel with any build that bundles them.

## Chess.com move classification

- **What is borrowed:** the label set from Chess.com's Game Review - Brilliant, Great, Best,
  Excellent, Good, Book, Inaccuracy, Miss, Mistake, Blunder - together with the expected-points
  scale those labels are measured against (1.00 always winning, 0.50 equal, 0.00 always losing)
- **Where it is described:** https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc
- **What is *not* borrowed:** no Chess.com code, data or service is used. DeepSight bundles no
  Chess.com software and never contacts Chess.com. The classifier in
  `deepsight/move_classifier.py` is an independent implementation written for this project: it
  reuses the published label names and the published expected-points bands, and computes everything
  else - evaluations, expected points, sacrifices, alternative lines - from our own engine runs.
- **Trademarks:** Chess.com and Game Review are trademarks of Chess.com, LLC. DeepSight is not
  affiliated with, endorsed by or sponsored by Chess.com.

Chess.com does not publish its exact centipawn-to-expected-points conversion, its Brilliant and
Great detection rules, or its "only move" logic. DeepSight approximates those with the logistic
curve used by Lichess and with its own static-exchange and MultiPV rules.

## Notes for distributors

If you redistribute a DeepSight build, keep this file and `licenses/GPL-3.0.txt` together with the
binaries: Stockfish's license has to travel with the Stockfish binary, and its complete
corresponding source is the release or the repository linked above. Every archive published from
this repository already carries both files next to the engines, and `--self-check` reports whether
they are still there.
