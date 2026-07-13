"""python -m batch entry point for h5-shell-pipeline."""

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from batch.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
