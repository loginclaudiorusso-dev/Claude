"""1.63: Ein Ort für alle Exporte (Excel, CSV, Bild, Austauschdatei) – und nie mehr „Excel ist noch geöffnet“, wenn
gar kein Excel offen ist.

Bisher bekam jede Liste im gemeinsamen Export-Ordner einen festen Namen je Tag („Zimmer_…_2026-11-25.xlsx“). Hatte
eine Kollegin dieselbe Liste offen, oder durfte der PC nicht in den Export-Ordner schreiben, kam „Zugriff verweigert“ –
und das Programm meldete pauschal „Die Datei ist noch geöffnet“.

Jetzt, der Reihe nach:
1. Export-Ordner (Einstellung ``export_ordner`` bzw. ``Export`` im Standortordner), gewünschter Name;
2. belegt → derselbe Ordner mit „ (2)“, „ (3)“ … ;
3. Ordner gesperrt (kein Schreibrecht, Netzlaufwerk weg) → persönlicher Ordner „Dokumente\\INNternat Export“.
Schlägt alles fehl, kommt eine Meldung, die sagt, woran es liegt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

PRIVAT = "INNternat Export"
VERSUCHE = 6


class ExportGesperrt(PermissionError):
    """Kein Ort zum Speichern gefunden – mit verständlicher Begründung."""


def ordner(unterordner: str = "Export") -> Path:
    from belegung import speicher

    return Path(speicher.einstellungen().get("export_ordner") or speicher.pfad(unterordner))


def privat() -> Path:
    """Persönlicher Ausweichordner (Windows: Dokumente\\INNternat Export)."""
    home = Path.home()
    doku = home / "Documents"
    return (doku if doku.exists() else home) / PRIVAT


def kandidaten(ziel: Path, name: str, anzahl: int = VERSUCHE) -> list[Path]:
    """„Liste.xlsx“ → Liste.xlsx, Liste (2).xlsx, Liste (3).xlsx …"""
    p = Path(name)
    return [ziel / name] + [ziel / f"{p.stem} ({i}){p.suffix}" for i in range(2, anzahl + 1)]


def speichern(name: str, schreiben: Callable[[Path], object], unterordner: str = "Export",
              ausweich: Path | None = None) -> Path:
    """``schreiben(pfad)`` an den ersten möglichen Ort. Rückgabe: der tatsächliche Pfad (siehe ``hinweis``)."""
    gruende: list[str] = []
    for basis, wo in ((ordner(unterordner), "Export-Ordner"), (ausweich or privat(), "persönlichen Ordner")):
        try:
            basis.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            gruende.append(f"{wo} nicht erreichbar ({exc.strerror or exc})")
            continue
        belegt = 0
        for pfad in kandidaten(basis, name):
            try:
                schreiben(pfad)
                return pfad
            except PermissionError:
                belegt += 1
                if not _ordner_beschreibbar(basis):
                    gruende.append(f"kein Schreibrecht im {wo} {basis}")
                    break
            except FileNotFoundError as exc:
                gruende.append(f"{wo} nicht erreichbar ({exc.strerror or exc})")
                break
        else:
            gruende.append(f"im {wo} sind {belegt} Dateien dieses Namens gerade geöffnet")
    raise ExportGesperrt("Nicht gespeichert: " + "; ".join(gruende) + ".")


def _ordner_beschreibbar(basis: Path) -> bool:
    import os
    import uuid

    probe = basis / f".innternat_probe_{uuid.uuid4().hex[:8]}"
    try:
        probe.write_bytes(b"")
        os.remove(probe)
        return True
    except OSError:
        return False


def hinweis(pfad: Path, name: str, unterordner: str = "Export") -> str:
    """Zusatz für die Meldung, wenn nicht wie gewünscht gespeichert wurde."""
    try:
        im_export = Path(pfad).parent.resolve() == ordner(unterordner).resolve()
    except OSError:
        im_export = False
    if not im_export:
        return f" – im persönlichen Ordner {Path(pfad).parent}, weil der Export-Ordner gesperrt ist"
    if Path(pfad).name != name:
        return " – unter neuem Namen, weil die Datei gerade geöffnet ist (z. B. bei einer Kollegin)"
    return ""


def meldung(exc: BaseException) -> str:
    """Verständliche Meldung zu einem Speicherfehler – statt pauschal „Datei ist noch geöffnet“."""
    if isinstance(exc, ExportGesperrt):
        return str(exc)
    datei = getattr(exc, "filename", "") or ""
    return ("Nicht gespeichert: Zugriff verweigert" + (f" auf {datei}" if datei else "")
            + " – die Datei ist geöffnet oder es fehlt das Schreibrecht im Ordner.")
