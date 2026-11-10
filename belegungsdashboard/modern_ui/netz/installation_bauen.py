"""Komplettes Installationspaket bauen (0.83) – zum Installieren auf einem anderen Laufwerk und zum Testen durch Kollegen:
``python3 modern_ui/netz/installation_bauen.py <ziel.zip> <wheel-ordner> [instanz] [git-ref]``.

Inhalt (alles unter einem Ordner, z. B. ``INNternat_Test/``)::

    INNternat starten.bat  LIESMICH.txt  INSTALLATION.txt  INSTANZ.txt
    Programm/…   ← wie im Paket für den Netzwerkordner (nur Dateien aus dem Repository, nie Daten)
    Pakete/…     ← alle Python-Pakete für Windows (Python 3.13, 64 Bit) – Installation ohne Internet

``INSTANZ.txt`` (Standard „Test“) trennt die Installation von der bisherigen: eigene lokale Umgebung und
Einstellungen (%LOCALAPPDATA%\\INNternat-Test), eigene Desktop-Verknüpfung und eigener Autostart; das Tagesbriefing
wird nicht von selbst verschickt. Den Wheel-Ordner füllt man vorher, z. B. mit ``pip download --platform win_amd64
--python-version 3.13 --only-binary=:all: …`` samt der Abhängigkeiten, die nur unter Windows gelten.
"""

from __future__ import annotations

import sys
from importlib import util
from pathlib import Path

HIER = Path(__file__).resolve().parent


def _paket_bauen():
    spec = util.spec_from_file_location("paket_bauen", HIER / "paket_bauen.py")
    m = util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def bauen(ziel: Path, pakete: Path | None, instanz: str = "Test", ref: str = "HEAD") -> list[str]:
    """pakete: Ordner mit Windows-Wheels (→ „Pakete/“, Python muss installiert sein) – oder (0.84) ein portables
    Python mit allen Paketen (enthält python.exe → „Python/“, dann braucht der PC gar kein Python)."""
    instanz = "".join(c for c in instanz if c.isalnum() or c in "_-") or "Test"
    zusatz = {"INSTANZ.txt": f"{instanz}\r\n".encode("ascii"),
              "INSTALLATION.txt": (HIER / "INSTALLATION.txt").read_bytes()}
    portabel = pakete is not None and (pakete / "pythonw.exe").exists()
    return _paket_bauen().bauen(ziel, ref, f"INNternat_{instanz}/", zusatz, None if portabel else pakete,
                                pakete if portabel else None)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    n = bauen(Path(sys.argv[1]), Path(sys.argv[2]), *(sys.argv[3:5]))
    print(f"{sys.argv[1]}: {len(n)} Dateien, davon {sum(1 for x in n if x.startswith('Pakete/'))} Pakete")
