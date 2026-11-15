"""Windows DLL search path bootstrap for source runs.

PySide6_Essentials installs PySide6 and shiboken6 DLLs in sibling package
directories. Adding both directories before Qt is imported lets the app run
from source without installing the full PySide6 Addons package.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def _package_dir(package_name: str) -> Path | None:
    spec = importlib.util.find_spec(package_name)
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin).resolve().parent


if os.name == "nt" and hasattr(os, "add_dll_directory"):
    for _package_name in ("shiboken6", "PySide6"):
        _directory = _package_dir(_package_name)
        if _directory is not None and _directory.exists():
            os.add_dll_directory(str(_directory))
