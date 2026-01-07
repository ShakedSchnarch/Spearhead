import sys
from pathlib import Path

# Ensure project src is on sys.path for test discovery without editable install.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
