"""Anteils-Diagramme anzeigen (0.96): links „wie viel insgesamt“ (Ring oder Kreis), rechts „wann“ (100 %-Säulen oder
-Fläche). Die Art wählt man im Menüband (Diagrammentwurf → Anteile) – ohne Menüband direkt über den Diagrammen."""

from __future__ import annotations

from nicegui import ui

from . import anteile_kern as ank
from . import diagramm_karte, themes
from .ui_bausteine import segmente

RUND = ("ring", "kreis")
ZEIT = ("saeule100", "flaeche100")


def arten() -> tuple[str, str]:
    art = (themes.AKTIV or {}).get("dg_anteil", "ring") if isinstance(themes.AKTIV, dict) else "ring"
    return (art if art in RUND else "ring"), (art if art in ZEIT else "saeule100")


def zeigen(a, titel: str, an: ank.Anteile, farben, verlauf_text: str, mitte: str = "") -> None:
    """Abschnitt mit Aussage-Satz und zwei Karten. ``farben``: Name → Farbe (gleich wie in den übrigen Diagrammen)."""
    from . import menueband_ui
    from . import darstellung_kern as dk

    if len(an.namen) < 2:
        return
    t = themes.farben(themes.AKTIV)
    rund, zeit = arten()
    with ui.element("section").classes("m-block m-breit m-anteile"):
        with ui.element("div").classes("m-anteile-kopf"):
            ui.label(titel).classes("m-btitel")
            if not menueband_ui.band_sichtbar(a):
                aktiv = (themes.AKTIV or {}).get("dg_anteil", "ring")
                segmente({k: tx for k, (tx, _i) in dk.DG_ANTEILE.items()}, aktiv,
                         lambda v: a.design_setzen(dg_anteil=v))
        ui.label(an.satz).classes("m-anteile-satz")
        with ui.element("div").classes("m-anteile-zwei"):
            with diagramm_karte.Karte(a, "Anteile insgesamt", an.fenster) as k:
                k.chart(ank.option(an, rund, t, farben, mitte)).classes("m-anteile-rund")
                k.wurzel.classes(add="blick-zu")
            with diagramm_karte.Karte(a, "Anteile im Verlauf", verlauf_text) as k:
                k.chart(ank.option(an, zeit, t, farben)).classes("m-anteile-zeit")
                k.wurzel.classes(add="blick-zu")
        if an.zusammengefasst:
            ui.label(f"„{ank.UEBRIGE}“: " + ", ".join(an.zusammengefasst)).classes("m-zweite").style("white-space:normal")


CSS = """
.m-anteile-kopf { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.m-anteile-kopf .m-segm { margin-left: auto; }
.m-anteile-satz { font-size: 15px; font-weight: 600; margin: 4px 0 10px; white-space: normal; color: var(--text); }
.m-anteile-zwei { display: grid; grid-template-columns: minmax(280px, 2fr) minmax(360px, 3fr); gap: 14px; }
@media (max-width: 1100px) { .m-anteile-zwei { grid-template-columns: 1fr; } }
.m-anteile .m-dk-blick, .m-anteile .m-dk-fx { display: none !important; }
.m-anteile .m-dk-koerper { grid-template-columns: minmax(0, 1fr) !important; }
.m-anteile .m-chart.m-anteile-rund, .m-anteile .m-chart.m-anteile-zeit { height: 320px !important; }
"""
