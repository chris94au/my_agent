from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_SITE_PACKAGES = ROOT / ".venv" / "lib" / "python3.12" / "site-packages"

if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_SITE_PACKAGES))
