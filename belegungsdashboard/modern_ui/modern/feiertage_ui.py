"""1.75: Feiertage & Schließzeiten (Panel) – Bundesland wählen, Feiertage ansehen, eigene Schließzeiten pflegen."""

from __future__ import annotations

from datetime import date, timedelta

from nicegui import ui

from . import feiertage_kern as fk
from .ui_bausteine import knopf, leer

WT = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
POPUP = 'dense outlined dark options-dense popup-content-class="m-popup"'


def panel(a) -> None:
    land = fk.land()
    sz = fk.schliesszeiten()

    def bauen():
        ui.label("Feiertage werden berechnet (auch für kommende Jahre). An- und Abreisen an Feiertagen und in "
                 "Schließzeiten meldet das Cockpit zwei Wochen vorher; der Kalender zeigt die Tage.").classes("m-ptext")
        wahl = ui.select(fk.LAENDER, value=land, label="Bundesland des Standorts").classes("m-feld w-full").props(POPUP)

        async def land_speichern(e):
            if e.value != land and await a.aendern(fk.land_setzen, e.value):
                panel(a)
        wahl.on_value_change(land_speichern)

        ui.label("Eigene Schließzeiten").classes("m-abschnitt")
        aktuell = [s for s in sz if s.bis_d >= a.heute - timedelta(days=7)]
        if not aktuell:
            ui.label("Keine eingetragen.").classes("m-zweite")
        for s in aktuell:
            with ui.element("div").classes("m-mzeile").style("grid-template-columns:1fr auto"):
                with ui.element("div"):
                    ui.label(s.titel).classes("m-name")
                    ui.label(f"{s.von_d:%d.%m.} – {s.bis_d:%d.%m.%Y}").classes("m-zweite")

                async def weg(s=s):
                    if await a.aendern(fk.schliesszeit_entfernen, s.id):
                        panel(a)
                knopf("", weg, "leise", "delete", "Schließzeit löschen")
        titel = ui.input("Bezeichnung (z. B. „Weihnachtsschließung“)").classes("m-feld w-full").props(
            "dense outlined dark")
        with ui.element("div").classes("m-zweispaltig"):
            von = ui.input("von", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
            bis = ui.input("bis einschließlich", value=a.heute.isoformat()).classes("m-feld").props(
                "dense outlined dark type=date")

        async def neu():
            try:
                v, b = date.fromisoformat(von.value), date.fromisoformat(bis.value)
            except (TypeError, ValueError):
                a.toast("Bitte beide Daten wählen.", fehler=True, rueck=False)
                return
            if await a.aendern(fk.schliesszeit_anlegen, titel.value or "", v, b):
                panel(a)
        knopf("Schließzeit eintragen", neu, "", "add")

        ui.label(f"Feiertage {fk.LAENDER[land]} – nächste 12 Monate").classes("m-abschnitt")
        ft = [(d, n) for d, n in fk.tage(a.heute, a.heute + timedelta(days=365), land, []).items()]
        if not ft:
            leer("Keine Feiertage gefunden.")
        for d, n in ft:
            with ui.element("div").classes("m-mzeile").style("grid-template-columns:110px 1fr"):
                ui.label(f"{WT[d.weekday()]} {d:%d.%m.%Y}").classes("m-mono")
                ui.label(n)
        knopf("Schließen", a.panel_zu, "leise")

    a.panel("Feiertage & Schließzeiten", bauen)
