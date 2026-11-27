"""1.75: Belegungsprognose → Ansicht „Berechnung“ – der genaue Rechenweg als eigene Seite (statt versteckt unter
„Details anzeigen“ → Monat anklicken).

Oben die Monate der Prognose zum Auswählen (mit erwartetem Wert und Band), darunter der vollständige Rechenweg des
gewählten Monats aus ``rechenweg_kern`` (Datenbasis, Rückwärtstest aller Modelle, Zerlegung des gewählten Modells,
gebuchter Bestand, Unsicherheitsband, bei „Gesamt“ die Korrelation der Standorte) und die Modellwahl mit dem
Backtest. Rechnet mit denselben Zahlen wie das Diagramm – nichts wird gespeichert.
"""

from __future__ import annotations

from nicegui import ui

from belegung import konfig

from . import auswertung_kern as ak
from .ui_bausteine import knopf, leer


def _z(x) -> str:
    return "–" if x is None else f"{x:,.0f}".replace(",", ".")


def monate(pg, kap: int) -> list:
    """Prognosemonate (ohne Ist) als Szenario-Zeilen mit ihrem Index in ``pg.zeilen``."""
    return [(i, z) for i, z in enumerate(ak.szenario(pg, kap, 0)) if z.art != "ist"]


def zeichnen(a, pg, kap: int) -> None:
    from . import diagramm_ui
    from . import rechenweg_kern as rw

    zs = monate(pg, kap)
    with a.inhalt:
        wurzel = ui.element("div").classes("m-ex m-rb")
    with wurzel:
        if not zs:
            leer("Für diese Auswahl gibt es keine Prognosemonate.")
            return
        idx = [i for i, _z_ in zs]
        if getattr(a, "aw_rw_monat", None) not in idx:
            a.aw_rw_monat = idx[0]
        ort = konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort)
        with ui.element("section").classes("m-block"):
            with ui.element("div").classes("m-paktionen").style("align-items:center"):
                ui.html('<b class="m-fx-zeichen">ƒx</b>', sanitize=False)
                ui.label(f"Berechnung der Belegungsprognose · {ort}").classes("m-btitel")
                ui.label(("Brutto" if a.aw_brutto else "Netto") + f" · Datenstand {a.daten['stichtag']:%d.%m.%Y}"
                         ).classes("m-zweite")
                knopf("Zum Diagramm", lambda: a.setzen(aw_chart="trend", nur_seite=True), "leise", "show_chart",
                      "Zurück zu Trend & Prognose").style("margin-left:auto")
            ui.label("Monat wählen – darunter steht jeder Rechenschritt mit Formel, eingesetzten Zahlen und Ergebnis.") \
                .classes("m-zweite")
            with ui.element("div").classes("m-rb-monate"):
                for i, z in zs:
                    b = ui.element("button").classes("m-rb-monat" + (" an" if i == a.aw_rw_monat else ""))
                    with b:
                        ui.label(ak.monat_text(z.monat)).classes("m-name")
                        ui.label(f"{_z(z.erwartet)} · 80 %: {_z(z.lo80)}–{_z(z.hi80)}").classes("m-zweite")
                    b.on("click", lambda i=i: a.setzen(aw_rw_monat=i, nur_seite=True))
        i = a.aw_rw_monat
        z, pz = dict(zs)[i], pg.zeilen[i]
        try:
            schritte = rw.rechenweg((a.daten or {}).get("ds"), a.aw_standort, z.monat, pz.vertraege,
                                    {"erwartet": z.erwartet, "lo80": z.lo80, "hi80": z.hi80, "lo95": z.lo95,
                                     "hi95": z.hi95})
        except Exception as exc:                          # noqa: BLE001 – lieber erklären als abstürzen
            schritte = []
            ui.label(f"Der Rechenweg ließ sich nicht nachrechnen: {exc}").classes("m-zweite")
        with ui.element("section").classes("m-block"):
            if schritte:
                diagramm_ui.rechenweg_block(schritte, ak.monat_text(z.monat))
            else:
                leer("Für diesen Monat liegt kein Rechenweg vor.")
        from .seite_prognose import _methodik

        _methodik(a, pg)
        with ui.element("div").classes("m-paktionen"):
            knopf("Rechenweg Teilnehmer-Prognose", lambda: a.oeffnen(
                "auswertung", ansicht="massnahmen", mn_ansicht="prognose",
                von=("Belegungs­prognose", "auswertung", "prognose")), "leise", "groups",
                "Teilnehmer je Maßnahme – dort im Diagramm einen Monat anklicken: Rechenweg der Simulation")


CSS = """
.m-rb-monate { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.m-rb-monat { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; padding: 6px 10px;
  border-radius: var(--r, 8px); border: 1px solid var(--rand);
  background: transparent; color: inherit; cursor: pointer; text-align: left; }
.m-rb-monat:hover { border-color: var(--akzent); }
.m-rb-monat.an { border-color: var(--akzent); box-shadow: inset 0 0 0 1px var(--akzent); }
.m-rb .m-rw-rechnung { font-variant-numeric: tabular-nums; }
"""
