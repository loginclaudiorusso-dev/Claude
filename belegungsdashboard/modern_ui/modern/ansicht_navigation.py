"""Oberfläche – Navigation: Standort wählen, Menüband füllen, Suche. Teil der Klasse Ansicht (oberflaeche.py).

1.35: Seitenleiste, Showcase-Dock und AI-Canvas sind entfernt – es gibt nur noch das Menüband (``menueband_ui``)."""

from __future__ import annotations

import logging

from nicegui import run, ui

from . import standort_kern, suche_palette
from .ui_bausteine import attr

log = logging.getLogger("modern.oberflaeche")      # derselbe Name wie vorher im Protokoll
LOGO_DATEI = "INNternat_Logo.png"


def _erlaubte() -> list:
    """1.33: Standorte, die das angemeldete Konto sehen darf (ohne Konten: alle)."""
    from . import benutzer_kern as bk

    erl = bk.erlaubte_standorte()
    return [(k, s) for k, s in standort_kern.STANDORTE.items() if k in erl]


def _logo() -> str:
    """Logo als data-URI, wenn ``INNternat_Logo.png`` im INNternat-Ordner (oder in ``modern_ui``) liegt – sonst "".
    Das Logo wird unverändert gezeigt und nicht ins Programm eingebaut (es gehört nicht ins Repository)."""
    import base64
    from pathlib import Path

    from belegung import konfig

    from .standort_kern import _BASIS

    orte = (_BASIS(), _BASIS() / "Vorlagen", konfig.programmordner(), Path(__file__).resolve().parent.parent,
            konfig.programmordner() / "Vorlagen")
    for ordner in dict.fromkeys(orte):          # 0.54: zuerst im Datenordner (Netzwerk: bleibt bei Updates erhalten)
        p = ordner / LOGO_DATEI
        try:
            if p.is_file() and p.stat().st_size < 3_000_000:
                return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
        except OSError:
            continue
    return ""


class NavigationMixin:
    """Teil von ``Ansicht`` (oberflaeche.py) – Methoden unverändert hierher verschoben."""

    # ---- Standort (Goslar, Bad Pyrmont, Weser-Ems) ----------------------------------------

    async def standort_wechseln(self, kurz: str) -> None:
        if kurz == standort_kern.aktiv().kurz or kurz not in dict(_erlaubte()):
            return
        await run.io_bound(standort_kern.waehlen, kurz)
        ui.navigate.reload()                   # alles frisch aus dem Ordner des neuen Standorts

    async def standort_fragen(self) -> str:
        """Beim Start: Welcher Standort? Der zuletzt gewählte ist vorausgewählt (Enter)."""
        gemerkt = standort_kern.gemerkt()
        erlaubt = dict(_erlaubte())
        if len(erlaubt) == 1:                  # 1.33: nur ein Standort freigegeben → nicht fragen
            return next(iter(erlaubt))
        if gemerkt not in erlaubt:
            gemerkt = next(iter(erlaubt))
        with ui.dialog().props("persistent") as dlg, ui.element("div").classes("m-frage m-standortwahl"):
            attr(dlg, role="dialog", aria_label="Standort wählen")
            ui.label("Welcher Standort?").classes("m-titel")
            ui.label("Zimmer, Anreisen, Reinigung und alles Weitere gelten für den gewählten Standort. Auswertung und "
                     "Prognose zeigen immer alle drei.").classes("m-ptext")
            with ui.element("div").classes("m-standorte"):
                for k, s in erlaubt.items():
                    b = ui.element("button").classes("m-standort-k" + (" an" if k == gemerkt else ""))
                    if k == gemerkt:
                        attr(b, autofocus="")
                    with b:
                        ui.label(s.name).classes("m-name")
                        ui.label(standort_kern.daten_text(k)).classes("m-zweite")
                    b.on("click", lambda k=k: dlg.submit(k))
        dlg.open()
        ui.run_javascript("setTimeout(() => document.querySelector('.m-standort-k.an')?.focus(), 150)")
        return await dlg or gemerkt

    def _nav_fuellen(self) -> None:
        """Menüband bauen bzw. auffrischen (nur neu, wenn sich etwas Sichtbares geändert hat)."""
        from . import menueband_ui

        menueband_ui.fuellen(self)

    async def suchen(self) -> None:
        """Strg+K: Suchpalette."""
        suche_palette.oeffnen(self)
