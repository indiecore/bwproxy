# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

gui_a = Analysis(
    ['bwproxy-gui.py'],  # replace me with your path
    pathex=['./bwproxy'],
    binaries=[],
    datas=[
        ( 'resources', 'resources' ),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)
gui_pyz = PYZ(
    gui_a.pure,
    gui_a.zipped_data,
    cipher=block_cipher
)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    gui_a.binaries,
    gui_a.zipfiles,
    gui_a.datas,
    [],
    name='bwproxy-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='./resources/bwproxy_icon.ico'
)

coll = COLLECT(
    gui_exe,
    gui_a.binaries,
    gui_a.zipfiles,
    gui_a.datas,
    name="bwproxy_win"
)