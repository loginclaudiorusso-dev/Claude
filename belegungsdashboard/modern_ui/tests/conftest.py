import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))              # modern
sys.path.insert(0, str(HIER.parent))       # belegung (Hauptprogramm, unverändert)
