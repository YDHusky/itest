# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import vosk

# 获取 vosk 库的实际路径（包含 DLL）
vosk_path = os.path.dirname(vosk.__file__)

block_cipher = None

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[
        # 添加 vosk 的 DLL 文件（关键）
        (os.path.join(vosk_path, '*.dll'), 'vosk'),
        # 如果有 libvosk.dll 或类似文件，也需要添加
        (os.path.join(vosk_path, 'libvosk*'), 'vosk'),
    ],
    datas=[
        # 包含 vosk 库的所有数据文件（包括 DLL 和模型）
        (vosk_path, 'vosk'),
        # 如果你有自定义模型，也加在这里
        # ('path/to/model', 'model'),
    ],
    hiddenimports=[
        'vosk',
        'vosk.vosk',
        'pydub',
        'pydub.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    name='main_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 先设为 True 看详细错误，成功后再改为 False
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 如果是目录模式（非单文件），需要额外配置
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main_gui',
)