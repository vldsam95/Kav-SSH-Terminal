# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ROOT = Path(SPECPATH)
if not (ROOT / "src" / "main.py").exists():
    ROOT = ROOT.parent

hiddenimports = (
    collect_submodules("asyncssh")
    + collect_submodules("pyte")
)

excluded_modules = [
    "PySide6.QtHelp",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtVirtualKeyboard",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
    "pydantic.generics",
    "pytest",
    "tests",
    "tkinter",
    "unittest",
]

excluded_bundle_parts = (
    "PySide6\\opengl32sw.dll",
    "PySide6\\Qt6OpenGL.dll",
    "PySide6\\Qt6Pdf.dll",
    "PySide6\\Qt6Qml.dll",
    "PySide6\\Qt6QmlModels.dll",
    "PySide6\\Qt6Quick.dll",
    "PySide6\\Qt6VirtualKeyboard.dll",
    "PySide6\\plugins\\platforms\\qdirect2d.dll",
)


def keep_bundle_item(item):
    destination = str(item[0]).replace("/", "\\")
    source = str(item[1]).replace("/", "\\")
    if "\\translations\\" in destination.lower() or "\\translations\\" in source.lower():
        return False
    return not any(
        destination.endswith(part) or source.endswith(part)
        for part in excluded_bundle_parts
    )

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

a.binaries = TOC(item for item in a.binaries if keep_bundle_item(item))
a.datas = TOC(item for item in a.datas if keep_bundle_item(item))

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KavSSH",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KavSSH",
)
