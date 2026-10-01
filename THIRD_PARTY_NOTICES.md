# Third-party notices

DeepSight's own code is distributed under the MIT license (see [LICENSE](LICENSE)). The builds
published from this repository additionally contain the two chess engines below, each of which
keeps its own license.

## Stockfish

- **Version:** Stockfish 18 (`sf_18`)
- **Where the binary comes from:** the official release
  https://github.com/official-stockfish/Stockfish/releases/tag/sf_18 - the Windows build
  (`stockfish-windows-x86-64.zip`) is fetched by `Engines/download-engines.bat`, the Linux build
  (`stockfish-ubuntu-x86-64.tar`) by `flake.nix`, where it is pinned by its sha256 as well
- **License:** GNU General Public License, version 3 or later - full text in
  [licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)
- **Copyright:** the Stockfish developers, see the source above

Stockfish runs as a separate process and speaks UCI over stdin/stdout. DeepSight does not link
against it, modify it or merge it with its own code; the two are separate programs distributed
together.

## Ember

- **Version:** 1.3.1 (revision `9e015493`), the same on both platforms: Windows takes
  `ember-1.3.1-9e015493-windows-amd64.zip` in `Engines/download-engines.bat`, Linux takes
  `ember-1.3.1-9e015493-linux-amd64.tar.gz` in `flake.nix`
- **Installed as:** `Engines/ember-1.3.1.exe` on Windows, `Engines/ember-1.3.1` on Linux
- **Release the binaries come from:** https://github.com/ExxDreamerCode/Ember/releases/tag/V1.3.1
- **Source:** https://github.com/ExxDreamerCode/Ember
- **License:** MIT - full text in [LICENSE](LICENSE)
- **Copyright:** D.r.e.A.m.e.R and the Ember contributors

## Notes for distributors

If you redistribute a DeepSight build, keep this file and `licenses/GPL-3.0.txt` together with the
binaries: Stockfish's license has to travel with the Stockfish binary, and its complete
corresponding source is the release linked above.
