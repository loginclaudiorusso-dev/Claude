"""Diagramm-Karte (0.87) – EIN Baustein für Diagramme mit Kopf, Knöpfen, „Auf einen Blick“ und ƒx.

Aufbau::

    ┌ Titel ─────────────────────────────── [Diagramm|Tabelle] [ƒx Berechnung] [Kopieren] [Vollbild] ┐
    │ Untertitel: Filter · Datenstand                                                                │
    │ ┌ Diagramm (≈ 75 %) ─────────────────────────────┐ ┌ Auf einen Blick (≈ 300 px, einklappbar) ┐ │
    │ │                                              ◢ │ │ 3–5 Sätze (Klick → Punkt im Diagramm)   │ │
    │ └────────────────────────────────────────────────┘ │ Monat (Klick ins Diagramm): Werte + ƒx  │ │
    │                                                     │ Datenstand · ab … Prognose              │ │
    │ ƒx Berechnung (aufklappbar)                         └─────────────────────────────────────────┘ │
    └────────────────────────────────────────────────────────────────────────────────────────────────┘

Die Knöpfe, der Ziehgriff (◢), Vollbild (Esc schließt), Einklappen und die Verbindung Satz ↔ Punkt laufen im
Browser (``diagramm_ui.JS``); der Klick auf einen Monat kommt zum Server und füllt den Monatsblock im Panel.
Bei schmaler Karte (Kacheln, kleines Fenster) steht „Auf einen Blick“ unter dem Diagramm.
"""

from __future__ import annotations

import json

from nicegui import ui

from . import blick_kern as bk
from . import kennzahlen_katalog as kk
from .ui_bausteine import attr

KNOEPFE = (("diagramm", "show_chart", "Diagramm", "Zahlen als Diagramm"),
           ("tabelle", "table_rows", "Tabelle", "Dieselben Zahlen als Tabelle (zum Nachlesen, für Vorleseprogramme)"),
           ("fx", "", "<b>ƒx</b> Berechnung", "Wie werden die Zahlen gerechnet? (Formel mit eingesetzten Werten)"),
           ("kopieren", "content_copy", "Kopieren", "Zahlen für Excel kopieren (dann Strg+V)"),
           ("voll", "fullscreen", "Vollbild", "Karte im ganzen Fenster zeigen – Esc schließt"))


class Karte:
    """``with Karte(...) as k:`` – darin das Diagramm mit ``k.chart(opt)`` (oder eigenes ui.echart in ``k.flaeche``)."""

    def __init__(self, a, titel: str, untertitel: str = "", blick: bk.Blick | None = None, klein: bool = False,
                 titel_je: dict | None = None, monate_alt: dict | None = None) -> None:
        self.a = a
        self.wurzel = ui.element("section").classes("m-dk" + (" klein" if klein else ""))
        attr(self.wurzel, role="figure", aria_label=titel)
        with self.wurzel:
            with ui.element("div").classes("m-dk-kopf"):
                with ui.element("div").classes("m-dk-titelblock"):
                    t = ui.element("div").classes("m-dk-titel")
                    with t:
                        if titel_je:                       # je Reiter ein Titel – der Browser zeigt den passenden
                            for k, text in titel_je.items():
                                attr(ui.label(text), data_titel=k)
                        else:
                            ui.label(titel)
                    self.unter = ui.label(untertitel).classes("m-dk-unter")
                with ui.element("div").classes("m-dk-knoepfe").props('role="toolbar" aria-label="Diagramm"'):
                    with ui.element("span").classes("m-dg-gruppe"):
                        for k, sym, text, tip in KNOEPFE[:2]:
                            _knopf(k, sym, text, tip, an=k == "diagramm")
                    for k, sym, text, tip in KNOEPFE[2:]:
                        _knopf(k, sym, text, tip)
            self.koerper = ui.element("div").classes("m-dk-koerper")
            with self.koerper:
                self.flaeche = ui.element("div").classes("m-dk-flaeche")
                self.panel = ui.element("aside").classes("m-dk-blick")
                attr(self.panel, aria_label="Auf einen Blick")
            self.fx_platz = ui.element("div").classes("m-dk-fx")
        self.monat = None
        self.blick(blick, monate_alt)

    # ---- „Auf einen Blick“ -----------------------------------------------------------------------------------------

    def blick(self, b: bk.Blick | None, monate_alt: dict | None = None) -> None:
        """Panel (neu) füllen. ``monate_alt``: {Index: [andere Beschriftungen derselben Stelle]} – für Diagramme, deren
        Reiter die Monate verschieden beschriften („Sep 26“ / „Sep 2026“)."""
        self.panel.clear()
        with self.panel:
            with ui.element("div").classes("m-dk-blick-kopf"):
                ui.label("Auf einen Blick").classes("m-dk-blick-titel")
                k = ui.element("button").classes("m-dk-zu")
                attr(k, type="button", data_dk="blick", title="Auf einen Blick ein-/ausklappen", aria_label="Einklappen")
                with k:
                    ui.icon("chevron_right")
            with ui.element("ol").classes("m-dk-saetze"):
                for s in (b.saetze if b else []):
                    li = ui.element("li").classes("m-dk-satz" + ("" if s.index is not None else " still"))
                    if s.index is not None:
                        attr(li, data_i=str(s.index), data_w="" if s.wert is None else str(round(s.wert, 1)),
                             data_r=s.reihe, data_xs="|".join((monate_alt or {}).get(s.index, [])), tabindex="0",
                             title="Klick: im Diagramm zeigen")
                    with li:
                        ui.label(s.text)
            self.monat = ui.element("div").classes("m-dk-monat")
            if b and b.stand:
                ui.label(b.stand).classes("m-dk-stand")

    # ---- Diagramm ---------------------------------------------------------------------------------------------------

    def chart(self, opt: dict, klassen: str = ""):
        with self.flaeche:
            c = ui.echart(opt, renderer="svg").classes("m-chart m-dk-chart" + (f" {klassen}" if klassen else ""))   # 0.95: scharf
        return c

    def anbinden(self, chart, details=None) -> None:
        """Klick auf eine Stelle (Monat, Tag, Welle) → deren Werte und ƒx im Panel „Auf einen Blick“."""
        chart.classes(add="m-dg")
        chart.on("m_achse", lambda e: self._stelle(chart, e.args, details), ["index"])

    def _stelle(self, chart, args, details) -> None:
        try:
            i = int((args or {}).get("index"))
        except (TypeError, ValueError):
            return
        werte = kk.werte_an(chart.options, i)
        if not werte or self.monat is None:
            return
        self.wurzel.classes(remove="blick-zu")
        self.monat.clear()
        with self.monat:
            with ui.element("div").classes("m-dk-monat-kopf"):
                ui.label(kk.kategorie(chart.options, i)).classes("m-name")
                z = ui.element("button").classes("m-dk-zu")
                attr(z, type="button", title="Schließen", aria_label="Schließen")
                with z:
                    ui.icon("close")
                z.on("click", lambda: self.monat.clear())
            with ui.element("div").classes("m-dg-werte"):
                for name, text in werte:
                    ui.label(name).classes("m-zweite")
                    ui.label(text).classes("m-name")
            from . import diagramm_ui

            bloecke = details(i) if details else [(kk.REIHE[n], {}, []) for n, _t in werte if n in kk.REIHE]
            gesehen = set()
            for schluessel, w, aktionen in bloecke or []:
                if schluessel in gesehen or schluessel not in kk.KATALOG:
                    continue
                gesehen.add(schluessel)
                diagramm_ui.block(schluessel, w, aktionen)

    def fx(self, eintraege: list) -> None:
        """ƒx Berechnung unter dem Diagramm (Knopf im Kopf blendet sie ein)."""
        from . import diagramm_ui

        with self.fx_platz:
            diagramm_ui.fx_kasten(eintraege)

    def __enter__(self):
        return self

    def __exit__(self, *_x) -> None:
        return None


def _knopf(k: str, symbol: str, text: str, tip: str, an: bool = False) -> None:
    b = ui.element("button").classes("m-dg-knopf" + (" an" if an else ""))
    attr(b, type="button", data_dk=k, title=tip, aria_label=tip)
    with b:
        if symbol:
            ui.html(f"<i>{symbol}</i>", sanitize=False)
        ui.html(text, sanitize=False)


def monate_alt(labels: list[list[str]]) -> dict:
    """Hilfe für ``Karte.blick``: Liste je Stelle mit allen Beschriftungen."""
    return {i: xs for i, xs in enumerate(labels)}


def daten(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# ---- 0.89: Darstellung wählbar – Karte | Klassisch | Einfach ---------------------------------------------------------

def modus() -> str:
    from . import themes

    return (themes.AKTIV or {}).get("dg_modus", "karte") if isinstance(themes.AKTIV, dict) else "karte"


def modus_wahl(a) -> None:
    """Schnellwahl über dem Diagramm – gleiche Einstellung wie Datei → Optionen → Diagramme (je PC gemerkt)."""
    from . import darstellung_kern as dk
    from .ui_bausteine import segmente

    with ui.element("div").classes("m-dk-modus"):
        attr(ui.label("Darstellung").classes("m-zweite"), title="Wie die Diagramme der Auswertung aussehen – je PC gemerkt")
        segmente({k: t for k, (t, _b) in dk.DG_MODI.items()}, modus(), lambda v: a.design_setzen(dg_modus=v))
