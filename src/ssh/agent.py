from __future__ import annotations

import os
import sys


def agent_available() -> bool:
    if sys.platform == "win32":
        return True
    return bool(os.environ.get("SSH_AUTH_SOCK"))
