"""Bausteine für die Werkzeuge einer Seite im Menüband (1.00) – Office-Gruppen mit großen und kleinen Knöpfen.

Eine Seite baut ihre Werkzeuge damit in ``a.werkzeuge`` (bzw. ``a.leiste``), wenn ``menueband_ui.werkzeuge_oben(a)``
gilt – sonst bleibt ihre bisherige Leiste. Das Band hat immer dieselbe Höhe wie das Menüband (nichts springt, nichts
wird abgeschnitten; ist es zu breit, lässt es sich waagrecht schieben).
"""

from __future__ import annotations

from contextlib import contextmanager

from nicegui import ui

from . import symbole
from .ui_bausteine import attr


@contextmanager
def gruppe(titel: str, klasse: str = ""):
    """Office-Gruppe mit Unterschrift. ``klasse`` „m-bg-auto“ (1.07): Knöpfe/Umschalter darin werden ebenfalls als
    Band-Bausteine gebaut (sonst bleiben gemeinsame Bausteine in einer fertigen Gruppe unverändert)."""
    with ui.element("div").classes(f"m-bg {klasse}".strip()):
        with ui.element("div").classes("m-bg-i"):
            yield
        ui.label(titel).classes("m-bg-t")


@contextmanager
def stapel(reihe: bool = False, raster: bool = False):
    """Kleine Knöpfe untereinander (bis 3) – mit ``reihe`` nebeneinander in einer Zeile (1.02, z. B. Standorte), mit
    ``raster`` in Spalten zu je 3."""
    with ui.element("div").classes("m-bg-st" + (" m-bg-reihe" if reihe else "") + (" m-bg-raster" if raster else "")):
        yield


def _inhalt(text: str, symbol: str, farbe: str, gross: bool, zahl, pfeil: bool, overlay: str = "", ofarbe: str = "") -> None:
    with ui.element("span").classes("m-bg-sym"):
        ui.html(symbole.html(symbol, farbe, gross, overlay=overlay if gross else "", ofarbe=ofarbe),
                sanitize=False).classes("m-bg-svg")
        if zahl is not None and gross:
            ui.label(str(zahl)).classes("m-bg-zahl")
    with ui.element("span").classes("m-bg-text"):
        if zahl is not None and not gross:
            ui.label(str(zahl)).classes("m-bg-kz")
        ui.label(text)
        if pfeil:
            ui.icon("expand_more").classes("m-bg-pfeil")


def gross(text: str, symbol: str, farbe: str = "", klick=None, an: bool = False, zahl=None, tipp: str = "",
          pfeil: bool = False, primaer: bool = False, overlay: str = "", ofarbe: str = ""):
    """Großer Knopf (Symbol 32 px, Text darunter). Mit ``pfeil`` öffnet ``with knopf: ui.menu()`` ein Menü."""
    b = ui.element("button").classes("m-bg-g" + (" an" if an else "") + (" primaer" if primaer else ""))
    attr(b, title=tipp or text, aria_pressed=str(bool(an)).lower(), type="button")
    with b:
        _inhalt(text, symbol, farbe, True, zahl, pfeil, overlay, ofarbe)
    if klick is not None:
        b.on("click", klick)
    return b


def klein(text: str, symbol: str, farbe: str = "", klick=None, an: bool = False, zahl=None, tipp: str = "",
          pfeil: bool = False):
    """Kleiner Knopf (Symbol 18 px, Text daneben) – drei übereinander in einem ``stapel()``."""
    b = ui.element("button").classes("m-bg-k" + (" an" if an else ""))
    attr(b, title=tipp or text, aria_pressed=str(bool(an)).lower(), type="button")
    with b:
        _inhalt(text, symbol, farbe, False, zahl, pfeil)
    if klick is not None:
        b.on("click", klick)
    return b


def auswahl(text: str, an: bool, klick):
    """Auswahlknopf ohne Symbol (z. B. „2 Wochen“ / „4 Wochen“) – mit Optionspunkt wie in Office."""
    b = ui.element("button").classes("m-bg-k m-bg-wahl" + (" an" if an else ""))
    attr(b, aria_pressed=str(bool(an)).lower(), type="button", title=text)
    with b:
        ui.element("span").classes("m-bg-punkt")
        ui.label(text)
    b.on("click", klick)
    return b


def trenner():
    """1.07: dezenter Strich zwischen Auswahl-Stapeln derselben Gruppe."""
    return ui.element("span").classes("m-bg-tr")


def info(text_html: str):
    return ui.html(f'<span class="m-bg-info">{text_html}</span>', sanitize=False)


CSS = r"""
/* 1.00: Seiten-Werkzeuge als Office-Gruppen – gleiche Höhe und Farbe wie das Menüband */
.m-bg { display: flex; flex-direction: column; flex: none; padding: 0 10px; border-right: 1px solid var(--ob-rand, #D9DEDE);
  height: 104px; box-sizing: border-box; }
.m-bg-i { flex: 1; display: flex; align-items: flex-start; gap: 6px; min-height: 0; }
.m-bg-t { height: 28px; line-height: 13px; padding: 6px 0 9px; box-sizing: border-box; font-size: 11px; color: var(--ob-text2, #5E6E6E); text-align: center;
  white-space: nowrap; }
.m-bg-st { display: flex; flex-direction: column; gap: 3px; justify-content: flex-start; }
.m-bg-st.m-bg-reihe { flex-direction: row; align-items: flex-start; gap: 4px; }
.m-bg-st.m-bg-raster { display: grid; grid-template-rows: repeat(3, 24px); grid-auto-flow: column; gap: 3px 6px;
  justify-items: start; }
/* Hinweistexte im Seiten-Band umbrechen statt abgeschnitten zu werden */
body.ob-seite-an .m-kz .m-kpi { display: block; white-space: normal; max-width: 320px; font-size: 13px; line-height: 19px;
  margin: 6px 8px; }
.m-bg-g, .m-bg-k { font: inherit; color: var(--ob-text, #1F2A2A); background: none; border: 1px solid transparent;
  cursor: pointer; border-radius: 4px; }
.m-bg-g { display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 64px; max-width: 140px; height: 68px;
  padding: 4px 8px 3px; position: relative; box-sizing: content-box; }       /* 1.07: 68 px Inhalt */
.m-bg-k { display: inline-flex; align-items: center; gap: 7px; height: 24px; padding: 0 8px; white-space: nowrap; font-size: 13px; }
.m-bg-g:hover, .m-bg-k:hover { background: var(--ob-hover, #E3ECEC); }
.m-bg-g.an, .m-bg-k.an { background: var(--ob-an, #D3E8E8); border-color: var(--ob-rand, #D9DEDE); }
.m-bg-g.primaer { background: var(--ob-an, #D3E8E8); border-color: var(--ob-akzent, #007F7F); }
.m-bg-sym { position: relative; display: inline-flex; line-height: 0; }
.m-bg-svg { display: inline-flex; line-height: 0; }
.m-bg-g .m-bg-text { font-size: 12.5px; line-height: 15px; text-align: center; display: inline-flex; align-items: flex-start;
  justify-content: center; max-height: 30px; overflow: hidden; }
.m-bg-k .m-bg-text { display: inline-flex; align-items: center; gap: 4px; }
.m-bg-zahl { position: absolute; top: -4px; right: -12px; min-width: 18px; height: 16px; padding: 0 4px; border-radius: 8px;
  background: var(--sym-basis, #334155); color: var(--ob-band, #fff); font-size: 10px; line-height: 16px; text-align: center;
  font-weight: 600; }
.m-bg-kz { font-weight: 700; font-variant-numeric: tabular-nums; }
.m-bg-pfeil { font-size: 14px !important; }
.m-bg-info { display: block; height: 24px; line-height: 24px; padding: 0 6px; font-size: 13px; color: var(--ob-text2, #5E6E6E);
  white-space: nowrap; }
.m-bg-info b { color: var(--ob-text, #1F2A2A); }
.m-bg .m-feld, .m-bg .q-field { min-width: 0; }
.m-bg .q-field__control, .m-bg .q-field__native { min-height: 24px !important; height: 24px !important; font-size: 12px; }
.m-bg .q-field--dense .q-field__marginal { height: 24px !important; }
.m-bg-wahl .m-bg-punkt { width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid var(--sym-basis, #334155);
  flex: none; box-sizing: border-box; }
.m-bg-wahl.an .m-bg-punkt { border-width: 4px; border-color: var(--ob-akzent, #007F7F); }
/* 1.07: Auswahl als flache Office-Felder statt Optionspunkte */
.m-bg-k.m-bg-wahl { height: 22px; border-radius: 4px; padding: 0 9px; border: 0; font-size: 12.5px; color: var(--sym-basis, #334155); }
.m-bg-wahl .m-bg-punkt { display: none; }
.m-bg-k.m-bg-wahl.an { background: #e0f2fe; color: #0369a1; font-weight: 600; border: 0; }
body:not(.hell) .m-bg-k.m-bg-wahl.an { background: rgba(56, 189, 248, .18); color: #7dd3fc; }
.m-bg-tr { align-self: stretch; width: 1px; background: #e2e8f0; margin: 4px 3px 2px; flex: none; }
body:not(.hell) .m-bg-tr { background: rgba(255, 255, 255, .09); }
.m-bg-ansicht .m-bg-g.an { background: #e0f2fe; border-color: #bae6fd; }
.m-bg-ansicht .m-bg-g.an .m-bg-text { color: #0369a1; font-weight: 600; }
body:not(.hell) .m-bg-ansicht .m-bg-g.an { background: rgba(56, 189, 248, .18); border-color: rgba(56, 189, 248, .35); }
body:not(.hell) .m-bg-ansicht .m-bg-g.an .m-bg-text { color: #7dd3fc; }
/* lose Bausteine (ohne eigene Gruppe) im Seiten-Band: gleiche Luft wie in Gruppen */
body.ob-seite-an .m-kz > .m-leiste > .m-bg-g, body.ob-seite-an .m-kz .m-werkzeuge > .m-bg-g,
body.ob-seite-an .m-kz > .m-leiste > .m-bg-st, body.ob-seite-an .m-kz .m-werkzeuge > .m-bg-st { margin: 0 3px; }
body.ob-seite-an .m-kz > .m-leiste > .m-bg-st, body.ob-seite-an .m-kz .m-werkzeuge > .m-bg-st { padding: 0 6px;
  border-left: 1px solid var(--ob-rand, #D9DEDE); border-right: 1px solid var(--ob-rand, #D9DEDE); }
body.ob-seite-an .m-kz > .m-leiste > .m-feld, body.ob-seite-an .m-kz .m-werkzeuge > .m-feld,
body.ob-seite-an .m-kz > .m-leiste > .q-field, body.ob-seite-an .m-kz .m-werkzeuge > .q-field { margin: 4px 6px; align-self: flex-start; }
body.ob-seite-an .m-kz > .m-leiste > .m-kpi, body.ob-seite-an .m-kz .m-werkzeuge > .m-kpi { align-self: flex-start;
  margin: 6px 8px; font-size: 13px; line-height: 20px; max-width: 360px; white-space: normal; }
body.ob-seite-an .m-kz .m-trennlinie { align-self: stretch; width: 1px; margin: 0 4px 22px; background: var(--ob-rand, #D9DEDE); }
/* Zeitstrahl-Legende als Filter (ohne Menüband) */
.m-legende-filter { display: inline-flex; gap: 2px; }
.m-lf { font: inherit; color: inherit; background: none; border: 1px solid transparent; border-radius: 4px; padding: 2px 6px;
  cursor: pointer; display: inline-flex; align-items: center; }
.m-lf:hover { background: var(--fl2, #eef1f1); } .m-lf.an { border-color: var(--akzent, #007f7f); background: var(--fl2, #eef1f1); }
"""
