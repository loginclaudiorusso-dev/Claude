"""1.74: Checkliste je Mietvertrag – was zum Einzug (und Auszug) erledigt sein muss, zum Abhaken.

* Punkte zum Einzug (immer): Mietvertrag unterschrieben zurück, SEPA-Mandat unterschrieben, Wohnungsgeberbestätigung
  ausgehändigt, Hausordnung ausgehändigt, Übergabeprotokoll Einzug, Schlüssel übergeben; mit Mietsicherheit zusätzlich
  „Mietsicherheit eingegangen“.
* Punkte zum Auszug – sobald gekündigt oder das Vertragsende in 30 Tagen ist: Übergabeprotokoll Auszug, Schlüssel
  zurück, Mietsicherheit abgerechnet (mit Kaution) bzw. Mietschuldenfreiheit auf Wunsch.
* Eigene Punkte je Vertrag (z. B. „Kopie Ausweis“), abhakbar und wieder entfernbar.
* Je Haken: wann und von wem (Anmeldename bzw. PC). Gespeichert je Standort in ``importe/modern_mieter_checkliste.json``.
* ``offen``: offene Punkte – für die Mieterliste („Checkliste 5/7“) und die Cockpit-Karte (Einzug liegt über 14 Tage
  zurück, aber noch etwas offen).
Rein bis auf Lesen und Schreiben.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

DATEI = "importe/modern_mieter_checkliste.json"
EINZUG = [("vertrag", "Mietvertrag unterschrieben zurück"), ("sepa", "SEPA-Lastschriftmandat unterschrieben"),
          ("wohnungsgeber", "Wohnungsgeberbestätigung ausgehändigt"), ("hausordnung", "Hausordnung ausgehändigt"),
          ("uebergabe_ein", "Übergabeprotokoll Einzug"), ("schluessel_aus", "Schlüssel übergeben")]
KAUTION_EIN = ("kaution_ein", "Mietsicherheit eingegangen")
AUSZUG = [("uebergabe_aus", "Übergabeprotokoll Auszug"), ("schluessel_zurueck", "Schlüssel zurück")]
KAUTION_AUS = ("kaution_aus", "Mietsicherheit abgerechnet")
AUSZUG_VORLAUF = 30
COCKPIT_NACH = 14                 # Tage nach Einzug: offene Einzugs-Punkte erscheinen im Cockpit


@dataclass
class Punkt:
    id: str
    text: str
    abschnitt: str                # Einzug | Auszug | Eigene
    am: str = ""                  # ISO-Zeit, leer = offen
    wer: str = ""
    eigen: bool = False

    @property
    def erledigt(self) -> bool:
        return bool(self.am)


def laden() -> dict:
    from belegung import speicher

    d = speicher.lesen(DATEI, {})
    return d if isinstance(d, dict) else {}


def _speichern(d: dict) -> None:
    from belegung import speicher

    speicher.schreiben(DATEI, d)


def _auszug_dran(mv, heute: date, gekuendigt: bool) -> bool:
    return gekuendigt or mv.bis <= heute + timedelta(days=AUSZUG_VORLAUF)


def punkte(mv, heute: date, daten: dict | None = None, gekuendigt: bool = False) -> list[Punkt]:
    d = (daten if daten is not None else laden()).get(mv.nr, {})
    haken = d.get("haken", {}) if isinstance(d, dict) else {}
    erg = [Punkt(i, t, "Einzug") for i, t in EINZUG]
    if getattr(mv, "kaution", False):
        erg.append(Punkt(*KAUTION_EIN, "Einzug"))
    if _auszug_dran(mv, heute, gekuendigt):
        erg += [Punkt(i, t, "Auszug") for i, t in AUSZUG]
        if getattr(mv, "kaution", False):
            erg.append(Punkt(*KAUTION_AUS, "Auszug"))
    for i, t in (d.get("eigene", {}) if isinstance(d, dict) else {}).items():
        erg.append(Punkt(i, t, "Eigene", eigen=True))
    for p in erg:
        h = haken.get(p.id) or {}
        p.am, p.wer = h.get("am", ""), h.get("wer", "")
    return erg


def stand(mv, heute: date, daten: dict | None = None, gekuendigt: bool = False) -> tuple[int, int]:
    """(erledigt, gesamt)."""
    ps = punkte(mv, heute, daten, gekuendigt)
    return sum(p.erledigt for p in ps), len(ps)


def _wer() -> str:
    try:
        from . import netz_kern

        return netz_kern.wer()
    except Exception:                              # noqa: BLE001
        return ""


def setzen(nr: str, pid: str, an: bool) -> str:
    from .kern import _schritt

    def tun():
        d = laden()
        e = d.setdefault(nr, {})
        h = e.setdefault("haken", {})
        if an:
            h[pid] = {"am": datetime.now().isoformat(timespec="minutes"), "wer": _wer()}
        else:
            h.pop(pid, None)
        _speichern(d)
    _schritt(f"Checkliste MV {nr}", tun, [DATEI])
    return f"MV {nr}: " + ("abgehakt" if an else "wieder offen")


def eigener_punkt(nr: str, text: str) -> str:
    from .kern import _schritt

    text = (text or "").strip()
    if not text:
        raise ValueError("Bitte einen Text eingeben.")

    def tun():
        d = laden()
        e = d.setdefault(nr, {}).setdefault("eigene", {})
        e[f"eigen_{datetime.now():%Y%m%d%H%M%S%f}"] = text[:120]
        _speichern(d)
    _schritt(f"Checkliste MV {nr}: Punkt", tun, [DATEI])
    return f"„{text[:40]}“ zur Checkliste hinzugefügt"


def eigenen_entfernen(nr: str, pid: str) -> str:
    from .kern import _schritt

    def tun():
        d = laden()
        e = d.get(nr, {})
        (e.get("eigene") or {}).pop(pid, None)
        (e.get("haken") or {}).pop(pid, None)
        _speichern(d)
    _schritt(f"Checkliste MV {nr}: Punkt entfernt", tun, [DATEI])
    return "Punkt entfernt"


def offen_im_cockpit(vertraege: list, heute: date, daten: dict | None = None) -> list[tuple]:
    """(Vertrag, offene Einzugs-Punkte) – Einzug liegt über ``COCKPIT_NACH`` Tage zurück, Vertrag läuft noch."""
    daten = laden() if daten is None else daten
    erg = []
    for mv in vertraege:
        if not (mv.von + timedelta(days=COCKPIT_NACH) <= heute <= mv.bis):
            continue
        offen = [p for p in punkte(mv, heute, daten) if p.abschnitt == "Einzug" and not p.erledigt]
        if offen:
            erg.append((mv, offen))
    return erg
