"""1.48: Mietverträge sind bindend – das Zimmer aus dem Vertrag gilt, nicht der Gebäudeplan.

Bisher galt beim Abgleich: Steht eine Person (gleicher Name, überschneidender Zeitraum) im eingelesenen Gebäudeplan,
gilt dessen Zimmer – auch für Mieter. Bucht der Gebäudeplan einen Mieter in ein anderes Zimmer, stand er im
Programm plötzlich dort. Für Mieter ist das falsch: Das Zimmer steht im Vertrag, für die ganze Laufzeit.

* ``binden``: Jede Zuweisung eines Mietvertrags (Schlüssel ``mv:<Nr>``) bekommt das Vertragszimmer und den Vorrang
  „unsere Planung gilt“; fehlt sie, wird sie aus dem Vertrag ergänzt. Umzüge (eigene Liste) wirken weiter.
* ``einrichten``: hängt ``binden`` einmal an ``zimmerplan.zuweisungen_laden`` (nur in der neuen Oberfläche – das
  bisherige Programm bleibt unverändert).
* ``abweichungen``: Mieter, die der Gebäudeplan in einem anderen Zimmer führt – als Hinweis „Gebäudeplan
  korrigieren“ im Cockpit.
* 1.48 Verlängern: ``neues_ende`` (+N Monate) und „automatisch verlängern“ je Vertrag (``auto``), mit Hinweis im
  Cockpit, wenn das Vertragsende näher rückt.
Rein bis auf das Lesen und Schreiben der Dateien.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from belegung import speicher

AUTO_DATEI = f"{speicher.IMPORT_ORDNER}/modern_mieter_auto.json"
AUTO_VORLAUF = 30            # Tage vor Vertragsende: Hinweis „automatische Verlängerung fällig“
MONATE = (3, 6, 12)


def _eintrag(mv) -> dict:
    return {"person": mv.person, "name": f"{mv.nachname}, {mv.vorname}", "massnahme": f"Miete Goslar MV {mv.nr}",
            "gruppe": "Mieter", "geschlecht": "w" if mv.weiblich else "m", "zimmer": mv.zimmer,
            "von": mv.von.isoformat(), "bis": mv.bis.isoformat(), "vorrang": "planung"}


def binden(zuw: list[dict], vertraege: list) -> list[dict]:
    """Zuweisungen der Mietverträge auf das Vertragszimmer setzen (Vorrang vor dem Gebäudeplan), fehlende ergänzen."""
    nach = {m.person: m for m in vertraege}
    gesehen = set()
    for z in zuw:
        m = nach.get(z.get("person"))
        if m is None:
            continue
        gesehen.add(m.person)
        z["zimmer"] = m.zimmer
        z["vorrang"] = "planung"
    zuw.extend(_eintrag(m) for m in vertraege if m.person not in gesehen and m.zimmer)
    return zuw


def einrichten() -> None:
    from belegung import mieter as mt
    from belegung import zimmerplan as zp

    if getattr(zp.zuweisungen_laden, "_mietbindung", False):
        return
    roh = zp.zuweisungen_laden

    def zuweisungen_laden() -> list[dict]:
        zuw = roh()
        try:
            return binden(zuw, mt.laden())
        except Exception:                      # noqa: BLE001 – Verträge unlesbar: wie bisher
            return zuw
    zuweisungen_laden._mietbindung = True
    zuweisungen_laden._roh = roh
    zp.zuweisungen_laden = zuweisungen_laden


# ---- Gebäudeplan weicht vom Vertrag ab ----------------------------------------------------------------------------

@dataclass
class Abweichung:
    nr: str
    name: str
    vertrag: str          # Zimmer-ID laut Vertrag
    gebaeudeplan: str     # Zimmer-ID laut Gebäudeplan
    von: date


def abweichungen(plan, vertraege: list, heute: date) -> list[Abweichung]:
    """Laufende und künftige Verträge, die der Gebäudeplan (Name, Zeitraum ±3 Tage) in einem anderen Zimmer führt."""
    from belegung import zimmerplan as zp

    if plan is None:
        return []
    gebucht = [(zp._namenswoerter(b.name), b) for b in plan.belegungen if b.name and b.art == "belegt"]
    tol = timedelta(days=3)
    erg = []
    for m in vertraege:
        if m.bis < heute or not m.zimmer:
            continue
        w = zp._namenswoerter(f"{m.nachname}, {m.vorname}")
        treffer = [b for ww, b in gebucht if w and w <= ww and b.von <= m.bis + tol and m.von - tol <= b.bis]
        if treffer and all(b.zimmer != m.zimmer for b in treffer):
            erg.append(Abweichung(m.nr, f"{m.vorname} {m.nachname}", m.zimmer, treffer[0].zimmer, m.von))
    return sorted(erg, key=lambda x: x.von)


# ---- Verlängern ---------------------------------------------------------------------------------------------------

def neues_ende(bis: date, monate: int) -> date:
    """Vertrag läuft bis ``bis`` – um ``monate`` verlängert endet er am Tag vor demselben Tag N Monate später."""
    from belegung import mieter as mt

    return mt.standard_ende(bis + timedelta(days=1), monate)


def auto() -> dict[str, int]:
    """{Vertragsnummer: Monate} – Verträge, die sich automatisch verlängern sollen."""
    d = speicher.lesen(AUTO_DATEI, {})
    return {str(k): int(v) for k, v in (d.get("vertraege") or {}).items()} if isinstance(d, dict) else {}


def auto_setzen(nr: str, monate: int | None) -> str:
    """Automatische Verlängerung ein (``monate``) oder aus (None) – ein Schritt, rückgängig machbar."""
    from .kern import _schritt

    def tun():
        d = auto()
        if monate:
            d[nr] = int(monate)
        else:
            d.pop(nr, None)
        speicher.schreiben(AUTO_DATEI, {"vertraege": d})
    _schritt(f"Automatische Verlängerung MV {nr}", tun, [AUTO_DATEI])
    return (f"MV {nr} verlängert sich automatisch um {monate} Monate – {AUTO_VORLAUF} Tage vor Ende erscheint der "
            "Hinweis im Cockpit, ein Klick erstellt die Nebenabrede") if monate else f"MV {nr}: automatische Verlängerung aus"


@dataclass
class Faellig:
    nr: str
    name: str
    zimmer: str
    bis: date
    neu: date
    monate: int


def auto_faellig(vertraege: list, heute: date, einstellungen: dict[str, int] | None = None) -> list[Faellig]:
    """Verträge mit automatischer Verlängerung, deren Ende in höchstens ``AUTO_VORLAUF`` Tagen liegt."""
    e = auto() if einstellungen is None else einstellungen
    erg = []
    for m in vertraege:
        n = e.get(m.nr)
        if n and heute <= m.bis <= heute + timedelta(days=AUTO_VORLAUF):
            erg.append(Faellig(m.nr, f"{m.vorname} {m.nachname}", m.zimmer, m.bis, neues_ende(m.bis, n), n))
    return sorted(erg, key=lambda f: f.bis)
