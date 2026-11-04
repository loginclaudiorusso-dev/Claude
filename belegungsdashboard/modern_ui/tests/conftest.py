import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))              # modern
sys.path.insert(0, str(HIER.parent))       # belegung (Hauptprogramm, unverändert)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _lokal(tmp_path, monkeypatch):
    """Persönliche Einstellungen (0.54: je PC) nie in den echten Benutzerordner schreiben."""
    monkeypatch.setenv("INNTERNAT_LOKAL", str(tmp_path / "_lokal"))
    monkeypatch.delenv("INNTERNAT_START", raising=False)
