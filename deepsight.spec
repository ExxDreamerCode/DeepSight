# -*- mode: python ; coding: utf-8 -*-

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

block_cipher = None

ROOT_DIR = os.getcwd()
NAME = "DeepSight"
AUTHOR = "ExxDreamerCode"
COPYRIGHT = "Copyright (c) 2026 ExxDreamerCode and Boris Nagaev (@starius)"
BUNDLE_IDENTIFIER = "io.github.exxdreamercode.deepsight"

# DEEPSIGHT_ONEDIR=1 builds a folder instead of a single file, which is what the releases ship:
# a bundle with both engines inside is far too big to unpack again on every launch.
# DEEPSIGHT_REQUIRE_ENGINES=1 fails the build when an engine is missing, so a release can never
# go out without them. DEEPSIGHT_UPX=0 turns off UPX, whose packed executables some antivirus
# products flag.
ONE_DIR = os.environ.get("DEEPSIGHT_ONEDIR") == "1"
REQUIRE_ENGINES = os.environ.get("DEEPSIGHT_REQUIRE_ENGINES") == "1"
USE_UPX = os.environ.get("DEEPSIGHT_UPX", "1") == "1"
CODESIGN_IDENTITY = os.environ.get("DEEPSIGHT_CODESIGN_IDENTITY") or None
ENTITLEMENTS_FILE = os.environ.get("DEEPSIGHT_ENTITLEMENTS") or None


def read_version():
    """The version lives in deepsight/__init__.py and is only ever changed there."""
    text = Path(ROOT_DIR, "deepsight", "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if match is None:
        raise SystemExit("deepsight/__init__.py declares no __version__")
    return match.group(1)


def version_numbers(version):
    numbers = [int(part) for part in re.findall(r"\d+", version)[:3]]
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers)


def engine_files(prefix):
    """Engines are installed as ember-1.3.1.exe or stockfish, so match the prefix instead of a
    fixed name that would have to be bumped along with the version."""
    if not os.path.isdir(engines_dir):
        return []
    return sorted(
        fname
        for fname in os.listdir(engines_dir)
        if fname.lower().startswith(prefix)
        and not fname.startswith(".")
        and os.path.isfile(os.path.join(engines_dir, fname))
    )


VERSION = read_version()

engines_dir = os.path.join(ROOT_DIR, "Engines")
missing_engines = [prefix for prefix in ("ember", "stockfish") if not engine_files(prefix)]

download_script = os.path.join(engines_dir, "download-engines.bat")
if missing_engines and os.name == "nt" and os.path.isfile(download_script):
    print("Engine files missing, running download-engines.bat...")
    ret = subprocess.call(download_script, cwd=engines_dir, shell=True)
    if ret != 0:
        print("WARNING: download-engines.bat failed, engines may be missing in build")
    else:
        print("Engines downloaded successfully")

    missing_engines = [prefix for prefix in ("ember", "stockfish") if not engine_files(prefix)]

if missing_engines and REQUIRE_ENGINES:
    raise SystemExit("Missing engines for a release build: " + ", ".join(missing_engines))

piece_files = []
pieces_dir = os.path.join(ROOT_DIR, "Images", "Pieces")
for fname in os.listdir(pieces_dir):
    fpath = os.path.join(pieces_dir, fname)
    if os.path.isfile(fpath):
        piece_files.append((fpath, "Images/Pieces"))

move_icon_files = []
moves_dir = os.path.join(ROOT_DIR, "Images", "Moves")
for fname in os.listdir(moves_dir):
    fpath = os.path.join(moves_dir, fname)
    if os.path.isfile(fpath):
        move_icon_files.append((fpath, "Images/Moves"))

book_files = []
books_dir = os.path.join(ROOT_DIR, "Books")
for fname in os.listdir(books_dir):
    fpath = os.path.join(books_dir, fname)
    if os.path.isfile(fpath):
        book_files.append((fpath, "Books"))

engine_files_to_add = []
for prefix in ("ember", "stockfish"):
    for fname in engine_files(prefix):
        engine_files_to_add.append((os.path.join(engines_dir, fname), "Engines"))

all_datas = piece_files + move_icon_files + book_files + engine_files_to_add

# Stockfish is GPL-3.0, so its license text and the notices have to travel with the build and not
# only live in the repository. A missing notice fails the build on purpose - a build without them
# would be shipping a GPL binary with no license. See THIRD_PARTY_NOTICES.md.
notice_files = [
    (os.path.join(ROOT_DIR, "THIRD_PARTY_NOTICES.md"), "."),
    (os.path.join(ROOT_DIR, "licenses", "GPL-3.0.txt"), "licenses"),
]
missing_notices = [path for path, _ in notice_files if not os.path.isfile(path)]
if missing_notices:
    raise SystemExit("Missing license notices: " + ", ".join(missing_notices))

all_datas = all_datas + notice_files

icon_file = None
icon_names = {"win32": "DeepSight.ico", "darwin": "DeepSight.icns"}
if sys.platform in icon_names:
    candidate = os.path.join(ROOT_DIR, "Images", icon_names[sys.platform])
    if os.path.isfile(candidate):
        icon_file = candidate

version_file = None
VERSION_RESOURCE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{author}'),
        StringStruct('FileDescription', 'DeepSight chess analyzer'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{name}'),
        StringStruct('LegalCopyright', '{copyright}'),
        StringStruct('OriginalFilename', '{name}.exe'),
        StringStruct('ProductName', '{name}'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
if sys.platform == "win32":
    handle, version_file = tempfile.mkstemp(prefix="deepsight-version-", suffix=".txt")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(
            VERSION_RESOURCE.format(
                numbers=version_numbers(VERSION),
                version=VERSION,
                name=NAME,
                author=AUTHOR,
                copyright=COPYRIGHT,
            )
        )

a = Analysis(
    ['main.py'],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=all_datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'chess',
        'chess.pgn',
        'deepsight',
        'deepsight.models',
        'deepsight.engine_registry',
        'deepsight.engine_manager',
        'deepsight.main_window',
        'deepsight.board_widget',
        'deepsight.eval_bar',
        'deepsight.move_list_panel',
        'deepsight.input_panel',
        'deepsight.analysis_engine',
        'deepsight.move_classifier',
        'deepsight.quick_evaluator',
        'deepsight.self_check',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
        'pandas',
        'notebook',
        'IPython',
        'jupyter',
        'setuptools',
        'pip',
        'distutils',
        'test',
        'unittest',
        'pydoc',
        'doctest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_options = dict(
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=USE_UPX,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=CODESIGN_IDENTITY,
    entitlements_file=ENTITLEMENTS_FILE,
    icon=icon_file,
    version=version_file,
)

if ONE_DIR:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)
    collection = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=USE_UPX,
        name=NAME,
    )
    bundle_target = collection
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [], **exe_options)
    bundle_target = exe

app = BUNDLE(
    bundle_target,
    name=f'{NAME}.app',
    icon=icon_file,
    bundle_identifier=BUNDLE_IDENTIFIER,
    version=VERSION,
    info_plist={
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'CFBundleName': NAME,
        'CFBundleDisplayName': NAME,
        'NSHighResolutionCapable': True,
    },
)
