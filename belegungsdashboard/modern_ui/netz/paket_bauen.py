"""Paket für den Netzwerkordner bauen (0.54): ``python3 modern_ui/netz/paket_bauen.py <ziel.zip> [git-ref]``.

Inhalt des Zips (wird direkt in den Netzwerkordner entpackt)::

    INNternat starten.bat
    LIESMICH.txt
    Programm/…        ← nur Dateien, die im Repository stehen (git archive) – nie lokale oder echte Daten

Nicht mitgeliefert werden Startdateien und Skripte, die im Netzwerkordner Schaden anrichten würden (das bisherige
Programm und ``modern_ui/Start.bat`` würden den Programmordner als Datenordner bzw. für eine gemeinsame Python-Umgebung
benutzen) sowie Tests und Entwicklungsnotizen. Der Ordner ``Daten`` entsteht beim ersten Start.
"""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = "belegungsdashboard"
WEGLASSEN_DATEIEN = {"Start.bat", "belegungsdashboard_gui.py", "belegungsdashboard_gui.spec",
                     "belegungsdashboard_export.py", "OFFENE_PUNKTE.md", "UX_KONZEPT.md", "ROLLBACK.md",
                     "modern_ui/Start.bat", "modern_ui/modern_ui.log"}
WEGLASSEN_ORDNER = ("tests/", "modern_ui/tests/", "modern_ui/netz/", "belegung/ui/")
OBEN = ("INNternat starten.bat", "LIESMICH.txt")


def mitliefern(rel: str) -> bool:
    return rel not in WEGLASSEN_DATEIEN and not rel.startswith(WEGLASSEN_ORDNER) and "__pycache__" not in rel


def _repo() -> Path:
    return Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=HIER, text=True).strip())


def bauen(ziel: Path, ref: str = "HEAD", praefix: str = "", zusatz: dict[str, bytes] | None = None,
          pakete: Path | None = None) -> list[str]:
    """Zip schreiben; Rückgabe: Namen im Zip (ohne praefix).

    Installationspaket (0.83): praefix = oberster Ordner im Zip (z. B. „INNternat_Test/“), zusatz = weitere
    Dateien oben (INSTANZ.txt, INSTALLATION.txt), pakete = Ordner mit Windows-Wheels → „Pakete/“ (ohne Internet)."""
    roh = subprocess.check_output(["git", "archive", "--format=tar", f"{ref}:{WURZEL}"], cwd=_repo())
    namen = []
    with tarfile.open(fileobj=io.BytesIO(roh)) as tar, zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        for name in OBEN:
            info = tar.getmember(f"modern_ui/netz/{name}")
            z.writestr(praefix + name, tar.extractfile(info).read())
            namen.append(name)
        for name, inhalt in (zusatz or {}).items():
            z.writestr(praefix + name, inhalt)
            namen.append(name)
        for whl in sorted(pakete.glob("*.whl")) if pakete else ():
            z.write(whl, f"{praefix}Pakete/{whl.name}", zipfile.ZIP_STORED)       # Wheels sind schon gepackt
            namen.append(f"Pakete/{whl.name}")
        for info in tar.getmembers():
            if not info.isfile() or not mitliefern(info.name):
                continue
            n = f"Programm/{info.name}"
            z.writestr(zipfile.ZipInfo(praefix + n, date_time=_zeit(info.mtime)), tar.extractfile(info).read(),
                       zipfile.ZIP_DEFLATED)
            namen.append(n)
    return namen


def _zeit(mtime: float) -> tuple:
    from datetime import datetime

    t = datetime.fromtimestamp(mtime)
    return (max(t.year, 1980), t.month, t.day, t.hour, t.minute, t.second)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    n = bauen(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "HEAD")
    print(f"{sys.argv[1]}: {len(n)} Dateien")
