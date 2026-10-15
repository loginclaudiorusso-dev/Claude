"""Änderungen an der Zimmerplanung vorher zeigen und hinterher rückgängig machen.

* **Vorschau** – ``zuweisungen_vorschau`` vergleicht, was gespeichert werden soll, mit dem, was *jetzt* gespeichert ist
  (frisch von der Platte, nicht der Stand beim Öffnen der Seite). Sie zeigt je Person „vorher → nachher“ und trennt
  dabei zwischen dem, was angefordert wurde, und den Folgen: Planung entfernt, „fest“ entfällt, inzwischen woanders
  geändert. Konflikte blockieren das Speichern, z. B. wenn das Zielzimmer inzwischen belegt ist.
* **Rückgängig** – vor jeder Änderung wird ein Schnappschuss der Planungsdateien gemerkt (Zuweisungen, Umzüge,
  UWT-Automatik). Zurück geht es nur, solange danach nichts anderes gespeichert wurde, z. B. aus einem anderen Fenster
  oder von einem Kollegen. Sonst würde das Zurückspielen fremde Änderungen überschreiben, und das Rückgängig wird
  abgelehnt. Der Verlauf liegt nur im Arbeitsspeicher, beim Programmende ist er weg. Das Änderungsprotokoll bleibt.

Rein, ohne Qt.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import protokoll, speicher
from . import zimmerplan as zp

MAX_SCHRITTE = 20


def _dateien() -> list[str]:
    from . import umzug

    return [zp.ZUWEISUNGEN, umzug.DATEI, zp.UWT_AUTO]


# ---------------------------------------------------------------------------------------
# Vorschau
# ---------------------------------------------------------------------------------------

ART_TEXT = {"neu": "neu geplant", "umgeplant": "umgeplant", "entfernt": "Planung entfernt"}


@dataclass
class Aenderung:
    person: str
    name: str
    art: str                    # neu | umgeplant | entfernt
    alt: str = ""               # Zimmer-ID vorher ("" = keins)
    neu: str = ""               # Zimmer-ID nachher ("" = keins)
    von: date | None = None
    bis: date | None = None
    angefordert: bool = True    # False: Folge eines Vorschlags (nicht von Hand gewählt)
    folgen: list[str] = field(default_factory=list)   # zwingende Folgen, z. B. „fest“ entfällt

    @property
    def text(self) -> str:
        alt, neu = self.alt.removeprefix("GS-") or "–", self.neu.removeprefix("GS-") or "–"
        zeit = f" ({self.von:%d.%m.} – {self.bis:%d.%m.%Y})" if self.von and self.bis else ""
        return f"{self.name}: {alt} → {neu}{zeit}"


@dataclass
class Vorschau:
    aenderungen: list[Aenderung] = field(default_factory=list)
    konflikte: list[str] = field(default_factory=list)     # blockieren das Speichern

    def nach_art(self, art: str) -> list[Aenderung]:
        return [a for a in self.aenderungen if a.art == art]

    @property
    def einfach(self) -> bool:
        """Nur neue Planungen, keine Folgen, keine Konflikte – dann reicht eine Rückmeldung danach."""
        return not self.konflikte and all(a.art == "neu" and not a.folgen for a in self.aenderungen)

    @property
    def leer(self) -> bool:
        return not self.aenderungen and not self.konflikte


def zuweisungen_vorschau(stand: zp.Planstand, zuteilungen: list[zp.Zuteilung], entfernen: set[str] = frozenset(),
                         angefordert: set[str] | None = None, gesehen: list[dict] | None = None) -> Vorschau:
    """Was ``zp.zuweisungen_speichern(zuteilungen)`` (plus ``zuweisungen_entfernen(entfernen)``) jetzt ändern würde.

    ``stand`` muss frisch geladen sein. ``angefordert``: Personen, deren Zimmer von Hand gewählt wurde (None = alle).
    ``gesehen``: die Zuweisungen, die beim Planen angezeigt wurden. Weicht der gespeicherte Stand für eine betroffene
    Person davon ab, wurde sie inzwischen woanders geändert. Das ist ein Konflikt, damit nichts unbemerkt
    überschrieben wird."""
    v = Vorschau()
    jetzt = {z["person"]: z for z in zp.zuweisungen_laden()}
    damals = {z["person"]: z.get("zimmer", "") for z in gesehen} if gesehen is not None else None
    betroffen = {zt.bedarf.schluessel for zt in zuteilungen} | set(entfernen)
    if damals is not None:
        for p in sorted(betroffen):
            war, ist = damals.get(p, ""), jetzt.get(p, {}).get("zimmer", "")
            if war != ist:
                name = next((zt.bedarf.name for zt in zuteilungen if zt.bedarf.schluessel == p), jetzt.get(p, {}).get("name", p))
                v.konflikte.append(f"{name}: wurde inzwischen woanders geändert ({war.removeprefix('GS-') or 'ohne Zimmer'}"
                                   f" → {ist.removeprefix('GS-') or 'ohne Zimmer'}). Bitte neu laden und erneut prüfen.")
    lage = stand.lage
    ziele = {zt.zimmer.id for zt in zuteilungen if zt.zimmer is not None}   # wer zieht wohin (auch unverändert)
    neu_im_zimmer: dict[str, list[zp.Bedarf]] = {}
    for zt in zuteilungen:
        b, alt_d = zt.bedarf, jetzt.get(zt.bedarf.schluessel, {})
        alt, neu = alt_d.get("zimmer", ""), zt.zimmer.id if zt.zimmer else ""
        if not neu:
            continue
        if alt == neu:
            neu_im_zimmer.setdefault(neu, []).append(b)
            continue
        a = Aenderung(b.schluessel, b.name, "umgeplant" if alt else "neu", alt, neu, b.von, b.bis,
                      angefordert is None or b.schluessel in angefordert)
        if alt and alt_d.get("status") == "belegt":
            a.folgen.append(f"war „fest“ in {alt.removeprefix('GS-')} – gilt im neuen Zimmer wieder als geplant")
        if alt and alt not in ziele:          # rückt jemand aus dieser Zuteilung nach, wird es nicht frei
            a.folgen.append(f"{alt.removeprefix('GS-')} wird dafür frei")
        v.aenderungen.append(a)
        # Ist das Zielzimmer (jetzt, ohne die Personen dieser Zuteilung) noch frei?
        z = lage.zimmer.get(neu)
        mit = [x for x in neu_im_zimmer.get(neu, []) if x.von < b.bis and b.von < x.bis]
        if z is None or not z.aktiv:
            v.konflikte.append(f"{b.name}: Zimmer {neu.removeprefix('GS-')} gehört nicht (mehr) zum Internat.")
        elif lage.freie_betten(neu, b.von, b.bis, betroffen) - len(mit) <= 0:
            v.konflikte.append(f"{b.name}: {z.kurz} ist vom {b.von:%d.%m.} bis {b.bis:%d.%m.%Y} inzwischen belegt "
                               "oder gesperrt.")
        neu_im_zimmer.setdefault(neu, []).append(b)
    gespeichert_bleibt = {zt.bedarf.schluessel for zt in zuteilungen if zt.zimmer is not None}
    for zt in zuteilungen:
        p = zt.bedarf.schluessel
        if zt.zimmer is None and p in jetzt and p not in gespeichert_bleibt:
            entfernen = set(entfernen) | {p}
    for p in sorted(entfernen):
        if p in jetzt:
            d = jetzt[p]
            b = next((zt.bedarf for zt in zuteilungen if zt.bedarf.schluessel == p), None)
            a = Aenderung(p, d.get("name", p), "entfernt", d.get("zimmer", ""), "",
                          b.von if b else None, b.bis if b else None, angefordert is None or p in angefordert)
            a.folgen.append("Person steht danach ohne Zimmer da" + (" – war „fest“" if d.get("status") == "belegt" else ""))
            v.aenderungen.append(a)
    v.aenderungen.sort(key=lambda a: ({"umgeplant": 0, "entfernt": 1, "neu": 2}[a.art], a.name))
    return v


def vorschau_text(v: Vorschau, max_zeilen: int = 14) -> str:
    """Kurzfassung als Text, z. B. für ein Meldungsfenster."""
    teile = []
    for art, titel in (("umgeplant", "Umgeplant (war schon gespeichert)"), ("entfernt", "Planung wird entfernt"),
                       ("neu", "Neu geplant")):
        liste = v.nach_art(art)
        if liste:
            zeilen = [f"• {a.text}" + (f" – {'; '.join(a.folgen)}" if a.folgen and art != "neu" else "")
                      for a in liste[:max_zeilen]]
            if len(liste) > max_zeilen:
                zeilen.append(f"• … und {len(liste) - max_zeilen} weitere")
            teile.append(f"{titel} – {len(liste)}:\n" + "\n".join(zeilen))
    if v.konflikte:
        teile.insert(0, "Konflikte – erst lösen:\n" + "\n".join(f"• {k}" for k in v.konflikte[:max_zeilen]))
    return "\n\n".join(teile)


# ---------------------------------------------------------------------------------------
# Rückgängig
# ---------------------------------------------------------------------------------------

Schnappschuss = dict  # Dateiname -> Inhalt (None = Datei gab es nicht)


def schnappschuss() -> Schnappschuss:
    erg = {}
    for name in _dateien():
        p = speicher.pfad(name)
        try:
            erg[name] = p.read_text(encoding="utf-8") if p.exists() else None
        except OSError:
            erg[name] = None
    return erg


@dataclass
class Schritt:
    titel: str
    vorher: Schnappschuss
    nachher: Schnappschuss


_verlauf: list[Schritt] = []


def merken(titel: str, vorher: Schnappschuss) -> Schritt | None:
    """Nach einer erfolgreichen Änderung aufrufen (``vorher`` = Schnappschuss davor). Ohne Unterschied: nichts."""
    nachher = schnappschuss()
    if nachher == vorher:
        return None
    s = Schritt(titel, vorher, nachher)
    _verlauf.append(s)
    del _verlauf[:-MAX_SCHRITTE]
    return s


def letzter() -> Schritt | None:
    return _verlauf[-1] if _verlauf else None


def verlauf_leeren() -> None:
    _verlauf.clear()


def _roh_schreiben(name: str, inhalt: str | None) -> None:
    p = speicher.pfad(name)
    if inhalt is None:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(inhalt)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def rueckgaengig(quelle: str = "Rückgängig") -> tuple[bool, str]:
    """Letzte Änderung zurückspielen. (Erfolg, Meldung). Nur wenn seitdem nichts anderes gespeichert wurde."""
    s = letzter()
    if s is None:
        return False, "Nichts zum Rückgängigmachen."
    jetzt = schnappschuss()
    if jetzt != s.nachher:
        _verlauf.clear()                        # ältere Schritte passen dann auch nicht mehr
        return False, (f"„{s.titel}“ kann nicht mehr rückgängig gemacht werden: Danach wurde noch etwas an der "
                       "Planung gespeichert (z. B. in einem anderen Fenster). Bitte von Hand korrigieren – was sich "
                       "geändert hat, steht unter Zimmerplan → Quellen → Änderungsprotokoll.")
    geschrieben = []
    try:
        for name, inhalt in s.vorher.items():
            if jetzt.get(name) != inhalt:
                _roh_schreiben(name, inhalt)
                geschrieben.append(name)
    except OSError as exc:
        for name in geschrieben:                # nicht halb zurück: wieder auf „nachher“
            try:
                _roh_schreiben(name, s.nachher[name])
            except OSError:
                pass
        return False, f"Rückgängig fehlgeschlagen ({exc}). Die Planung ist unverändert."
    _verlauf.pop()
    protokoll.eintragen([{"aktion": "rückgängig", "name": s.titel, "person": "", "alt": "", "neu": "", "von": "",
                          "quelle": quelle}])
    return True, f"Rückgängig: {s.titel}."
