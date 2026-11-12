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
def gruppe(titel: str):
    with ui.element("div").classes("m-bg"):
        with ui.element("div").classes("m-bg-i"):
            yield
        ui.label(titel).classes("m-bg-t")


@contextmanager
def stapel():
    with ui.element("div").classes("m-bg-st"):
        yield


def _inhalt(text: str, symbol: str, farbe: str, gross: bool, zahl, pfeil: bool) -> None:
    with ui.element("span").classes("m-bg-sym"):
        ui.html(symbole.html(symbol, farbe, gross), sanitize=False).classes("m-bg-svg")
        if zahl is not None and gross:
            ui.label(str(zahl)).classes("m-bg-zahl")
    with ui.element("span").classes("m-bg-text"):
        if zahl is not None and not gross:
            ui.label(str(zahl)).classes("m-bg-kz")
        ui.label(text)
        if pfeil:
            ui.icon("expand_more").classes("m-bg-pfeil")


def gross(text: str, symbol: str, farbe: str = "", klick=None, an: bool = False, zahl=None, tipp: str = "",
          pfeil: bool = False, primaer: bool = False):
    """Großer Knopf (Symbol 32 px, Text darunter). Mit ``pfeil`` öffnet ``with knopf: ui.menu()`` ein Menü."""
    b = ui.element("button").classes("m-bg-g" + (" an" if an else "") + (" primaer" if primaer else ""))
    attr(b, title=tipp or text, aria_pressed=str(bool(an)).lower(), type="button")
    with b:
        _inhalt(text, symbol, farbe, True, zahl, pfeil)
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


def info(text_html: str):
    return ui.html(f'<span class="m-bg-info">{text_html}</span>', sanitize=False)


CSS = r"""
/* 1.00: Seiten-Werkzeuge als Office-Gruppen – gleiche Höhe und Farbe wie das Menüband */
.m-bg { display: flex; flex-direction: column; flex: none; padding: 0 6px; border-right: 1px solid var(--ob-rand, #D9DEDE);
  height: 92px; box-sizing: border-box; }
.m-bg-i { flex: 1; display: flex; align-items: flex-start; gap: 2px; min-height: 0; }
.m-bg-t { height: 16px; line-height: 16px; font-size: 11px; color: var(--ob-text2, #5E6E6E); text-align: center;
  white-space: nowrap; }
.m-bg-st { display: flex; flex-direction: column; gap: 1px; justify-content: flex-start; }
.m-bg-g, .m-bg-k { font: inherit; color: var(--ob-text, #1F2A2A); background: none; border: 1px solid transparent;
  cursor: pointer; border-radius: 4px; }
.m-bg-g { display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 56px; max-width: 100px; height: 74px;
  padding: 3px 6px 2px; position: relative; box-sizing: border-box; }
.m-bg-k { display: inline-flex; align-items: center; gap: 6px; height: 21px; padding: 0 6px; white-space: nowrap; font-size: 12px; }
.m-bg-g:hover, .m-bg-k:hover { background: var(--ob-hover, #E3ECEC); }
.m-bg-g.an, .m-bg-k.an { background: var(--ob-an, #D3E8E8); border-color: var(--ob-rand, #D9DEDE); }
.m-bg-g.primaer { background: var(--ob-an, #D3E8E8); border-color: var(--ob-akzent, #007F7F); }
.m-bg-sym { position: relative; display: inline-flex; line-height: 0; }
.m-bg-svg { display: inline-flex; line-height: 0; }
.m-bg-g .m-bg-text { font-size: 12px; line-height: 14px; text-align: center; display: inline-flex; align-items: flex-start;
  justify-content: center; max-height: 28px; overflow: hidden; }
.m-bg-k .m-bg-text { display: inline-flex; align-items: center; gap: 4px; }
.m-bg-zahl { position: absolute; top: -4px; right: -12px; min-width: 18px; height: 16px; padding: 0 4px; border-radius: 8px;
  background: var(--sym-basis, #334155); color: var(--ob-band, #fff); font-size: 10px; line-height: 16px; text-align: center;
  font-weight: 600; }
.m-bg-kz { font-weight: 700; font-variant-numeric: tabular-nums; }
.m-bg-pfeil { font-size: 14px !important; }
.m-bg-info { display: block; height: 21px; line-height: 21px; padding: 0 4px; font-size: 12px; color: var(--ob-text2, #5E6E6E);
  white-space: nowrap; }
.m-bg-info b { color: var(--ob-text, #1F2A2A); }
.m-bg .m-feld, .m-bg .q-field { min-width: 0; }
.m-bg .q-field__control, .m-bg .q-field__native { min-height: 24px !important; height: 24px !important; font-size: 12px; }
.m-bg .q-field--dense .q-field__marginal { height: 24px !important; }
/* Zeitstrahl-Legende als Filter (ohne Menüband) */
.m-legende-filter { display: inline-flex; gap: 2px; }
.m-lf { font: inherit; color: inherit; background: none; border: 1px solid transparent; border-radius: 4px; padding: 2px 6px;
  cursor: pointer; display: inline-flex; align-items: center; }
.m-lf:hover { background: var(--fl2, #eef1f1); } .m-lf.an { border-color: var(--akzent, #007f7f); background: var(--fl2, #eef1f1); }
"""
