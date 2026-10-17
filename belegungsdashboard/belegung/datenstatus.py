"""Datenstand an einer Stelle: Pivot (Statistik) und Gebäudeplan (Zimmerplan) – Alter aus echten Zeitstempeln.

Die Anzeige behauptet nie „aktuell“, wenn der letzte Lade- oder Abrufversuch fehlgeschlagen ist, und sagt ehrlich,
wenn es keinen verlässlichen Zeitstempel gibt. Rein, ohne Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

PLAN_ALT_TAGE = 7        # ab hier gilt der Gebäudeplan als alt (wie der Hinweis im Zimmerplan)


@dataclass
class Status:
    stufe: str                      # ok | knapp | ueber | neutral
    pille: str                      # kurzer Zustand, z. B. „aktuell“, „19 Tage alt“, „Laden fehlgeschlagen“
    datum: str = "–"                # Stichtag/Stand groß
    zeilen: list[str] = field(default_factory=list)    # Zusatzzeilen (klein)
    tipp: str = ""


def _alter(tage: int) -> str:
    return {0: "von heute", 1: "von gestern"}.get(tage, f"{tage} Tage alt")


def pivot(ds, fehler: str | None = None, fehler_zeit: datetime | None = None, heute: date | None = None) -> Status:
    """Status der Pivot-Daten. ``fehler``: Meldung des letzten fehlgeschlagenen Ladens (hat Vorrang)."""
    heute = heute or date.today()
    if ds is None:
        if fehler:
            return Status("ueber", "Laden fehlgeschlagen", "–", ["Keine Pivot-Daten geladen"],
                          f"Letzter Versuch {fehler_zeit:%d.%m. %H:%M}: {fehler}" if fehler_zeit else fehler)
        return Status("neutral", "keine Daten", "–", ["Keine Pivot-Daten geladen"], "Unten „Aktualisieren“ wählen.")
    abruf = ds.pivot.abrufdatum
    zeilen = [f"{ds.quelle.name} · geladen {ds.geladen_am:%H:%M} Uhr" if ds.quelle else "Pivot geladen"]
    tipp = [f"Stichtag (letzter Ist-Tag): {ds.stichtag:%d.%m.%Y}",
            f"Vom Server abgerufen: {abruf:%d.%m.%Y}" if abruf else "Abrufdatum unbekannt"]
    if fehler:
        tipp.insert(0, f"Letzter Ladeversuch fehlgeschlagen ({fehler_zeit:%d.%m. %H:%M}): {fehler}" if fehler_zeit
                    else f"Letzter Ladeversuch fehlgeschlagen: {fehler}")
        return Status("ueber", "Laden fehlgeschlagen", f"{ds.stichtag:%d.%m.%Y}", zeilen + ["angezeigt: letzter Stand"],
                      "<br>".join(tipp))
    if ds.pivot_aktualisiert is False:
        return Status("knapp", "Abruf fehlgeschlagen", f"{ds.stichtag:%d.%m.%Y}", zeilen + ["angezeigt: gespeicherter Stand"],
                      "<br>".join(["Server-Abruf fehlgeschlagen (Netz/VPN/Berechtigung)."] + tipp))
    if abruf is None:
        return Status("neutral", "Alter unbekannt", f"{ds.stichtag:%d.%m.%Y}", zeilen, "<br>".join(tipp))
    tage = (heute - abruf).days
    return Status("ok" if tage <= 0 else ("knapp" if tage > 1 else "neutral"), "aktuell" if tage <= 0 else _alter(tage),
                  f"{ds.stichtag:%d.%m.%Y}", zeilen, "<br>".join(tipp))


def gebaeudeplan(plan, heute: date | None = None) -> tuple[str, str]:
    """(Zeile, Stufe) zum Gebäudeplan – Stand laut Plan, sonst ehrlich „Stand unbekannt“ / „kein Plan“."""
    heute = heute or date.today()
    if plan is None:
        return "Gebäudeplan: noch keiner importiert", "knapp"
    if plan.stand is None:
        return "Gebäudeplan: Stand unbekannt", "neutral"
    tage = (heute - plan.stand).days
    return f"Gebäudeplan: {plan.stand:%d.%m.%Y} · {_alter(tage)}", ("knapp" if tage > PLAN_ALT_TAGE else "ok")
