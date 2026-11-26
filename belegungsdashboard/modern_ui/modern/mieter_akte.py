"""1.72: Mieter-Akte – je Mietvertrag ein Ordner mit allen Unterlagen.

* Ordner im Datenordner des Standorts: ``Mieter-Akten\\MV<Nr>_<Nachname>`` (wird über die Vertragsnummer gefunden,
  auch wenn sich der Name später ändert). Liegt im gemeinsamen Datenordner – bleibt bei Updates, alle PCs sehen ihn.
* ``ablegen``: Datei in die Akte (gleicher Name → „ (2)“ …). ``entfernen``: verschiebt in ``_Papierkorb`` der Akte –
  nichts wird endgültig gelöscht. ``dateien``: Inhalt mit Größe und Datum.
* Erstellte Unterlagen (Mietvertrag, Nebenabrede, Unterlagen neu) legt das Programm selbst in die Akte.
* Bewusst nur Mietunterlagen (Vertrag, Kündigung, Übergabeprotokoll, Schriftverkehr) – keine Gesundheitsdaten.
  Wer welche Akte sehen darf, regeln die Ordnerrechte im Netzwerk (die Rollen im Programm schützen Dateien nicht).
Rein bis auf das Lesen und Schreiben der Dateien.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ORDNER = "Mieter-Akten"
PAPIERKORB = "_Papierkorb"
MAX_MB = 50
VERBOTEN = {".exe", ".bat", ".cmd", ".com", ".js", ".vbs", ".ps1", ".scr", ".msi", ".lnk", ".dll"}


def _basis() -> Path:
    from belegung import speicher

    return Path(speicher.pfad(ORDNER))


def _sauber(text: str) -> str:
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text or "").strip().strip(".")
    return re.sub(r"\s+", " ", t)[:80] or "Datei"


def ordner(nr: str, nachname: str = "", anlegen: bool = False) -> Path | None:
    """Akte des Vertrags (über die Nummer gefunden); ``anlegen``: notfalls neu."""
    b = _basis()
    kennung = f"MV{_sauber(nr)}"
    try:
        vorhanden = sorted(p for p in b.iterdir() if p.is_dir() and (p.name == kennung or p.name.startswith(kennung + "_")))
    except OSError:
        vorhanden = []
    if vorhanden:
        return vorhanden[0]
    if not anlegen:
        return None
    p = b / (kennung + (f"_{_sauber(nachname).replace(' ', '_')}" if nachname else ""))
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Datei:
    name: str
    groesse: int
    geaendert: datetime
    pfad: Path

    @property
    def groesse_text(self) -> str:
        g = self.groesse
        return f"{g / 1_048_576:.1f} MB" if g >= 1_048_576 else f"{max(1, round(g / 1024))} KB"


def dateien(nr: str) -> list[Datei]:
    o = ordner(nr)
    if o is None:
        return []
    erg = []
    for p in o.iterdir():
        if p.is_file() and not p.name.startswith((".", "~$")):
            st = p.stat()
            erg.append(Datei(p.name, st.st_size, datetime.fromtimestamp(st.st_mtime), p))
    return sorted(erg, key=lambda d: d.geaendert, reverse=True)


def _frei(ziel: Path) -> Path:
    if not ziel.exists():
        return ziel
    for i in range(2, 1000):
        k = ziel.with_name(f"{ziel.stem} ({i}){ziel.suffix}")
        if not k.exists():
            return k
    raise ValueError("Zu viele Dateien mit diesem Namen.")


def pruefen(name: str, groesse: int) -> None:
    if Path(name).suffix.lower() in VERBOTEN:
        raise ValueError(f"Dateien vom Typ {Path(name).suffix} werden aus Sicherheitsgründen nicht abgelegt.")
    if groesse > MAX_MB * 1_048_576:
        raise ValueError(f"Die Datei ist größer als {MAX_MB} MB.")


def ablegen(nr: str, nachname: str, name: str, inhalt: bytes) -> str:
    """Datei in die Akte legen (vorhandene bleiben – neuer Name bekommt „ (2)“)."""
    from belegung import protokoll

    pruefen(name, len(inhalt))
    o = ordner(nr, nachname, anlegen=True)
    ziel = _frei(o / _sauber(Path(name).name))
    ziel.write_bytes(inhalt)
    protokoll.eintragen([{"aktion": "Datei in Mieter-Akte", "name": nachname, "person": f"mv:{nr}", "alt": "",
                          "neu": ziel.name, "von": "", "quelle": f"Mieter-Akte MV {nr}"}])
    return f"„{ziel.name}“ in der Akte MV {nr} abgelegt"


def kopie_ablegen(nr: str, nachname: str, quelle: Path) -> Path | None:
    """Vom Programm erstellte Unterlagen zusätzlich in die Akte (Fehler stören das Erstellen nie)."""
    try:
        if not Path(quelle).is_file():
            return None
        o = ordner(nr, nachname, anlegen=True)
        ziel = o / Path(quelle).name
        if ziel.exists() and ziel.stat().st_size == Path(quelle).stat().st_size and \
                ziel.read_bytes() == Path(quelle).read_bytes():
            return ziel
        ziel = _frei(ziel)
        shutil.copy2(quelle, ziel)
        return ziel
    except Exception:                              # noqa: BLE001
        return None


def entfernen(nr: str, name: str) -> str:
    """In den Papierkorb der Akte verschieben (nicht endgültig löschen)."""
    from belegung import protokoll

    o = ordner(nr)
    p = (o / name) if o else None
    if p is None or not p.is_file() or p.parent != o:
        raise ValueError("Diese Datei gibt es nicht mehr.")
    korb = o / PAPIERKORB
    korb.mkdir(exist_ok=True)
    ziel = _frei(korb / p.name)
    p.replace(ziel)
    protokoll.eintragen([{"aktion": "Datei aus Mieter-Akte entfernt", "name": "", "person": f"mv:{nr}", "alt": name,
                          "neu": f"{PAPIERKORB}/{ziel.name}", "von": "", "quelle": f"Mieter-Akte MV {nr}"}])
    return f"„{name}“ in den Papierkorb der Akte verschoben"


def anzahl(nr: str) -> int:
    try:
        return len(dateien(nr))
    except OSError:
        return 0


ablegen.ohne_rueckgaengig = True
entfernen.ohne_rueckgaengig = True
