# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path

block_cipher = None

ROOT_DIR = os.getcwd()

engines_dir = os.path.join(ROOT_DIR, "Engines")
download_script = os.path.join(engines_dir, "download-engines.bat")
engine_exes = ["ember.exe", "stockfish-windows-x86-64.exe"]
engines_missing = any(
    not os.path.isfile(os.path.join(engines_dir, exe))
    for exe in engine_exes
)
if engines_missing and os.path.isfile(download_script):
    print("Engine files missing, running download-engines.bat...")
    ret = subprocess.call(download_script, cwd=engines_dir, shell=True)
    if ret != 0:
        print("WARNING: download-engines.bat failed, engines may be missing in build")
    else:
        print("Engines downloaded successfully")

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

engine_files = []
engines_dir = os.path.join(ROOT_DIR, "Engines")
if os.path.isdir(engines_dir):
    for fname in os.listdir(engines_dir):
        fpath = os.path.join(engines_dir, fname)
        if os.path.isfile(fpath):
            engine_files.append((fpath, "Engines"))

all_datas = piece_files + move_icon_files + book_files + engine_files

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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DeepSight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
