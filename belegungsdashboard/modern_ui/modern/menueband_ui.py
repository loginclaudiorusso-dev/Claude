"""Menüband-Darstellung (0.65) wie in Microsoft Office: Titelleiste mit Suche, Registerkarten, Gruppen mit großen
Symbolen und Ausklappmenüs, Statusleiste unten. Nutzt dieselben Seiten wie die übrigen Layouts – nur die Navigation
ist anders. Aufbau (rein): ``menueband.py``."""

from __future__ import annotations

from nicegui import ui

from . import __version__, menueband as mb, standort_kern
from .ui_bausteine import attr

LAYOUT = "office"


def _ansichten() -> dict:
    from . import (seite_anreisen, seite_assistenz, seite_auswertung, seite_einstellungen, seite_inventar,
                   seite_steuerung, seite_termine, seite_zimmer)

    return {"anreisen": seite_anreisen.ANSICHTEN, "zimmer": seite_zimmer.ANSICHTEN, "termine": seite_termine.ANSICHTEN,
            "reinigung": {"liste": "Reinigungsliste", "last": "Vorschau 6 Wochen", "facility": "Facility-Checks"},
            "assistenz": seite_assistenz.ANSICHTEN, "auswertung": seite_auswertung.ANSICHTEN,
            "steuerung": seite_steuerung.ANSICHTEN, "inventar": seite_inventar.ANSICHTEN,
            "einstellungen": seite_einstellungen.ANSICHTEN}


STANDARD_ANSICHT = {"anreisen": "zuteilen", "zimmer": "uebersicht", "reinigung": "liste", "termine": "liste",
                    "assistenz": "auftraege", "auswertung": "lage", "steuerung": "cockpit", "inventar": "gegenstaende",
                    "einstellungen": "allgemein"}


def _seite_im_reiter(r: mb.Reiter, seite: str) -> bool:
    return any(q.ziel and q.ziel[0] == "seite" and q.ziel[1] == seite
               for g in r.gruppen for p in g.punkte for q in (p.menue or [p]))


async def ausfuehren(a, ziel: tuple | None) -> None:
    if not ziel:
        return
    if ziel[0] == "seite":
        _s, seite, ansicht, zustand = ziel
        await a.oeffnen(seite, ansicht, **zustand)
        return
    name = ziel[1]
    d = a.design
    if name == "rueckgaengig":
        await a.rueckgaengig()
    elif name == "suchen":
        await a.suchen()
    elif name == "aktualisieren":
        await a.laden()
    elif name == "aufgaben":
        a.center_umschalten(True)
    elif name == "neuigkeiten":
        a._neuigkeiten_panel()
    elif name == "modus":
        await a.design_setzen(modus="dunkel" if d["modus"] == "hell" else "hell")
    elif name == "dichte":
        await a.design_setzen(dichte="kompakt" if d["dichte"] == "normal" else "normal")
    elif name == "vollbild":
        await a.vollbild_umschalten()
    elif name == "leitstand":
        from . import leitstand_ui

        await leitstand_ui.umschalten(a)
    elif name == "standort":
        kurz = await a.standort_fragen()
        if kurz:
            await a.standort_wechseln(kurz)
    elif name == "info":
        from belegung import __version__ as haupt

        a.toast(f"INNternat – neue Oberfläche {__version__} · Daten und Regeln: Belegung {haupt} · "
                f"Standort {standort_kern.aktiv().name}", rueck=False)
    elif name.startswith("layout:"):
        await a.design_setzen(layout=name.split(":", 1)[1])
    elif name.startswith("farbe:"):
        await a.design_setzen(farbe=name.split(":", 1)[1])
    elif name.startswith("dg_typ:"):
        await a.design_setzen(dg_typ=name.split(":", 1)[1])
    elif name == "band_gross":
        await a.design_setzen(band_gross=not d["band_gross"])
    elif name.startswith("zoom:"):
        from . import darstellung_kern as dk

        w = name.split(":", 1)[1]
        z = 100 if w == "100" else dk.zoom_schritt(d["zoom"], 1 if w == "+" else -1)
        await a.design_setzen(zoom=z)
    elif name.startswith("optionen"):
        from . import optionen_ui

        optionen_ui.oeffnen(a, name.split(":", 1)[1] if ":" in name else "farben")


def _zahl(a, p: mb.Punkt) -> tuple[int, bool]:
    if p.ziel == ("aktion", "aufgaben"):
        return len(a.karten), any(k.stufe == "dringend" for k in a.karten)
    if p.ziel == ("aktion", "neuigkeiten"):
        return a.ungelesen, False
    return 0, False


def _menue(a, punkte: list[mb.Punkt]) -> None:
    with ui.menu().props('class="m-ob-menue" anchor="bottom left" self="top left"'):
        for q in punkte:
            an = _menue_an(a, q)
            icon = ("radio_button_checked" if an else "radio_button_unchecked") if q.icon.startswith("radio") else q.icon
            with ui.menu_item(on_click=lambda q=q: ausfuehren(a, q.ziel)).classes("m-ob-mpunkt" + (" an" if an else "")):
                if q.farbe:
                    ui.element("span").classes("m-ob-muster").style(f"background:{q.farbe}")
                else:
                    ui.icon(icon)
                ui.label(q.text)


def _menue_an(a, q: mb.Punkt) -> bool:
    z = q.ziel
    if z and z[0] == "aktion":
        for vor, key in (("layout:", "layout"), ("farbe:", "farbe"), ("dg_typ:", "dg_typ")):
            if z[1].startswith(vor):
                return z[1][len(vor):] == a.design.get(key)
        return False
    return mb.aktiv(q, a.seite, _av(a), _heute(a))


def _av(a):
    return lambda s: a.ansicht_von(s, STANDARD_ANSICHT.get(s, ""))


def _heute(a) -> str:
    return getattr(a, "heute_ansicht", "zentrale") if getattr(a, "heute_ansicht", "zentrale") == "postfach" else "zentrale"


def _knopf(a, p: mb.Punkt) -> None:
    an = mb.aktiv(p, a.seite, _av(a), _heute(a)) and not (p.ziel and p.ziel[0] == "aktion")
    b = ui.element("button").classes(("m-ob-gross" if p.gross else "m-ob-klein") + (" an" if an else "")
                                     + (" mit-menue" if p.menue else ""))
    attr(b, title=p.tipp or p.text)
    n, rot = _zahl(a, p)
    with b:
        with ui.element("span").classes("m-ob-sym"):
            ui.icon(p.icon)
            if n:
                ui.label(str(n)).classes("m-ob-zahl" + (" rot" if rot else ""))
        with ui.element("span").classes("m-ob-text"):
            ui.label(p.text)
            if p.menue:
                ui.icon("expand_more").classes("m-ob-pfeil")
        if p.menue:
            _menue(a, p.menue)
    if not p.menue:
        b.on("click", lambda p=p: ausfuehren(a, p.ziel))


def _gruppe(a, g: mb.Gruppe) -> None:
    with ui.element("div").classes("m-ob-gruppe"):
        with ui.element("div").classes("m-ob-punkte"):
            klein: list[mb.Punkt] = []

            def stapel():
                if klein:
                    with ui.element("div").classes("m-ob-stapel"):
                        for q in klein:
                            _knopf(a, q)
                    klein.clear()
            for p in g.punkte:
                if p.gross:
                    stapel()
                    _knopf(a, p)
                else:
                    klein.append(p)
                    if len(klein) == 3:
                        stapel()
            stapel()
        ui.label(g.titel).classes("m-ob-gtitel")


def fuellen(a, erzwingen: bool = False) -> None:
    """Menüband in ``a.topnav`` bauen – nur neu, wenn sich etwas Sichtbares geändert hat (ein Klick bleibt stehen)."""
    if a.design.get("layout") != LAYOUT:
        if getattr(a, "_ob_sig", None) is not None:
            a._ob_sig = None
            a.topnav.clear()
        return
    alle = mb.reiter(_ansichten())
    tab = getattr(a, "band_tab", None) or "start"
    aktuell = next((r for r in alle if r.key == tab), alle[0])
    if not _seite_im_reiter(aktuell, a.seite) and getattr(a, "_ob_seite", None) != a.seite:
        tab = mb.reiter_von(a.seite, _ansichten())         # Sprung über Suche/Aufgaben: das Band folgt der Seite
        aktuell = next((r for r in alle if r.key == tab), alle[0])
    a.band_tab, a._ob_seite = tab, a.seite
    sig = (tab, a.seite, repr(sorted(a.ansicht.items())), _heute(a), repr(sorted(a.design.items())), len(a.karten),
           sum(1 for k in a.karten if k.stufe == "dringend"), a.ungelesen, getattr(a.stand_anzeige, "text", ""))
    if sig == getattr(a, "_ob_sig", None) and not erzwingen:
        return
    a._ob_sig = sig
    a.topnav.clear()
    s = standort_kern.aktiv()
    with a.topnav, ui.element("div").classes("m-ob"):
        with ui.element("div").classes("m-ob-titel"):
            with ui.element("div").classes("m-ob-schnell"):
                for icon, titel, ziel in (("undo", "Rückgängig (Strg+Z)", mb.A("rueckgaengig")),
                                          ("refresh", "Aktualisieren", mb.A("aktualisieren"))):
                    k = ui.element("button").classes("m-ob-tk")
                    attr(k, title=titel, aria_label=titel)
                    with k:
                        ui.icon(icon)
                    k.on("click", lambda z=ziel: ausfuehren(a, z))
            ui.label(f"INNternat – {s.name}").classes("m-ob-app")
            such = ui.element("button").classes("m-ob-suche")
            attr(such, title="Suchen (Strg+K)")
            with such:
                ui.icon("search")
                ui.label("Suchen: Name, Zimmer, Seite …")
                ui.label("Strg+K").classes("m-ob-taste")
            such.on("click", a.suchen)
            ui.element("div").style("flex:1")
            st = ui.element("button").classes("m-ob-tk breit")
            attr(st, title="Standort wechseln")
            with st:
                ui.icon("location_city")
                ui.label(s.name)
            st.on("click", lambda: ausfuehren(a, mb.A("standort")))
        with ui.element("div").classes("m-ob-reiter"):
            datei = ui.element("button").classes("m-ob-datei")
            with datei:
                ui.label("Datei")
                _menue(a, mb.DATEI)
            for r in alle:
                rb = ui.element("button").classes("m-ob-tab" + (" an" if r.key == tab else ""))
                with rb:
                    ui.label(r.titel)
                rb.on("click", lambda r=r: _tab(a, r.key))
        with ui.element("div").classes("m-ob-band"):
            for g in aktuell.gruppen:
                _gruppe(a, g)
        with ui.element("footer").classes("m-ob-status"):
            ui.label("Bereit")
            ui.label(mb.statuszeile(s.name, a.karten, getattr(a.stand_anzeige, "text", ""))).classes("m-ob-status-m")
            ui.element("div").style("flex:1")
            ui.label(f"Version {__version__}")
            with ui.element("div").classes("m-ob-zoom"):                # wie der Zoom-Regler in Office
                for icon, w, titel in (("remove", "-", "Verkleinern"), (None, "100", "Zoom zurücksetzen (100 %)"),
                                       ("add", "+", "Vergrößern")):
                    z = ui.element("button").classes("m-ob-zk")
                    attr(z, title=titel)
                    with z:
                        if icon:
                            ui.icon(icon)
                        else:
                            ui.label(f"{a.design['zoom']} %")
                    z.on("click", lambda w=w: ausfuehren(a, mb.A(f"zoom:{w}")))


def _tab(a, key: str) -> None:
    a.band_tab = key
    a._ob_seite = a.seite
    fuellen(a, erzwingen=True)


CSS = r"""
body.lay-office { --ob-titel: #134F4F; --ob-titel-text: #ffffff; --ob-akzent: #007F7F; --ob-band: #F7F8F8;
  --ob-reiter: #EEF1F1; --ob-rand: #D9DEDE; --ob-text: #1F2A2A; --ob-text2: #5E6E6E; --ob-hover: #E3ECEC;
  --ob-an: #D3E8E8; --ob-fl: #ffffff;
  font-family: var(--ob-schrift, "Segoe UI", "PT Sans", system-ui, -apple-system, sans-serif); }
/* 0.66: Zoom wie in Office – nur der Inhalt (Kopf, Leiste, Seite), Menüband und Statusleiste bleiben gleich groß */
.m-kopf, .m-leiste, .m-inhalt { zoom: var(--m-zoom, 1); }
body.band-gross .m-ob-band, body.band-gross .m-ob-reiter { zoom: 1.18; }
body.lay-office.mod-dunkel { --ob-titel: #0E3838; --ob-akzent: #5ED6C6; --ob-band: #1E2626; --ob-reiter: #182020;
  --ob-rand: #334040; --ob-text: #E6EEEE; --ob-text2: #A9B9B9; --ob-hover: #2A3636; --ob-an: #23413F; --ob-fl: #141B1B; }
body.lay-office .m-nav, body.lay-office .m-tb, body.lay-office .m-kopf-doppelt { display: none !important; }
body.lay-office .m-topnav { display: block; padding: 0; margin: 0; border: 0; background: none; box-shadow: none;
  position: relative; z-index: 20; flex: none; }
body.lay-office .m-haupt { background: var(--ob-fl); }
body.lay-office .m-inhalt { padding-bottom: 26px; }
.m-ob { color: var(--ob-text); font-size: 13px; user-select: none; }
.m-ob button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
.m-ob-titel { display: flex; align-items: center; gap: 10px; height: 38px; padding: 0 10px; background: var(--ob-titel);
  color: var(--ob-titel-text); }
.m-ob-schnell { display: flex; gap: 2px; }
.m-ob-tk { display: inline-flex; align-items: center; gap: 6px; height: 28px; min-width: 30px; padding: 0 6px;
  border-radius: 4px; color: var(--ob-titel-text) !important; }
.m-ob-tk:hover { background: rgba(255,255,255,.14) !important; }
.m-ob-tk .q-icon { font-size: 18px; }
.m-ob-app { font-weight: 600; letter-spacing: .1px; white-space: nowrap; }
.m-ob-suche { display: inline-flex; align-items: center; gap: 8px; height: 28px; width: min(460px, 40vw); margin-left: 14px;
  padding: 0 10px; border-radius: 4px; background: rgba(255,255,255,.16) !important; color: rgba(255,255,255,.92) !important;
  border: 1px solid rgba(255,255,255,.25) !important; text-align: left; }
.m-ob-suche:hover { background: rgba(255,255,255,.24) !important; }
.m-ob-suche .q-icon { font-size: 17px; }
.m-ob-suche > div:nth-child(2) { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-ob-taste { font-size: 11px; opacity: .75; }
.m-ob-reiter { display: flex; align-items: flex-end; gap: 2px; height: 34px; padding: 0 8px; background: var(--ob-reiter); }
.m-ob-datei { height: 30px; padding: 0 16px; margin-right: 6px; border-radius: 4px 4px 0 0;
  background: var(--ob-akzent) !important; color: #fff !important; font-weight: 600 !important; }
.m-ob-datei:hover { filter: brightness(1.08); }
body.lay-office.mod-dunkel .m-ob-datei { color: #0B2222 !important; }
.m-ob-tab { position: relative; height: 32px; padding: 0 14px; border-radius: 4px 4px 0 0; color: var(--ob-text) !important; }
.m-ob-tab:hover { background: var(--ob-hover) !important; }
.m-ob-tab.an { background: var(--ob-band) !important; font-weight: 600 !important; color: var(--ob-akzent) !important; }
.m-ob-tab.an::after { content: ""; position: absolute; left: 14px; right: 14px; bottom: 3px; height: 3px; border-radius: 2px;
  background: var(--ob-akzent); }
.m-ob-band { display: flex; align-items: stretch; min-height: 96px; padding: 4px 6px 0; background: var(--ob-band);
  border-bottom: 1px solid var(--ob-rand); box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow-x: auto; scrollbar-width: thin; }
.m-ob-gruppe { display: flex; flex-direction: column; padding: 0 6px; border-right: 1px solid var(--ob-rand); flex: none; }
.m-ob-gruppe:last-child { border-right: 0; }
.m-ob-punkte { flex: 1; display: flex; align-items: flex-start; gap: 2px; }
.m-ob-gtitel { text-align: center; font-size: 11px; color: var(--ob-text2); padding: 2px 0 4px; white-space: nowrap; }
.m-ob-gross { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; gap: 3px;
  min-width: 58px; max-width: 86px; height: 70px; padding: 6px 6px 4px; border-radius: 4px; text-align: center;
  border: 1px solid transparent !important; }
.m-ob-gross .m-ob-sym { position: relative; display: inline-flex; }
.m-ob-gross .m-ob-sym .q-icon { font-size: 28px; color: var(--ob-akzent); }
.m-ob-gross .m-ob-text { display: flex; align-items: center; gap: 0; font-size: 12px; line-height: 1.15;
  hyphens: manual; overflow-wrap: normal; word-break: normal; }
.m-ob-klein { display: flex; align-items: center; gap: 6px; height: 23px; padding: 0 8px 0 5px; border-radius: 4px;
  white-space: nowrap; font-size: 12px; border: 1px solid transparent !important; }
.m-ob-klein .m-ob-sym { position: relative; display: inline-flex; }
.m-ob-klein .m-ob-sym .q-icon { font-size: 17px; color: var(--ob-akzent); }
.m-ob-klein .m-ob-text { display: flex; align-items: center; }
.m-ob-stapel { display: flex; flex-direction: column; gap: 1px; padding-top: 2px; }
.m-ob-gross:hover, .m-ob-klein:hover { background: var(--ob-hover) !important; }
.m-ob-gross.an, .m-ob-klein.an { background: var(--ob-an) !important; border-color: var(--ob-rand) !important; }
.m-ob-pfeil { font-size: 15px !important; color: var(--ob-text2) !important; }
.m-ob-zahl { position: absolute; top: -5px; right: -10px; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px;
  font-size: 10px; line-height: 16px; font-weight: 700; background: var(--ob-text2); color: #fff; }
.m-ob-zahl.rot { background: #C4314B; }
.m-ob-status { position: fixed; left: 0; right: 0; bottom: 0; z-index: 30; display: flex; align-items: center; gap: 18px;
  height: 24px; padding: 0 12px; font-size: 12px; background: var(--ob-reiter); border-top: 1px solid var(--ob-rand);
  color: var(--ob-text2); }
.m-ob-status-m { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-ob-zoom { display: flex; align-items: center; gap: 2px; margin-left: 8px; }
.m-ob-zk { display: inline-flex; align-items: center; justify-content: center; height: 20px; min-width: 22px; padding: 0 4px;
  border-radius: 3px; color: var(--ob-text2) !important; font-size: 12px !important; }
.m-ob-zk .q-icon { font-size: 15px; }
.m-ob-zk:hover { background: var(--ob-hover) !important; }
.m-ob-muster { width: 16px; height: 16px; border-radius: 3px; flex: none; display: inline-block; }
.m-ob-menue { min-width: 220px; padding: 4px 0; border-radius: 6px !important; background: var(--ob-fl, #fff) !important;
  color: var(--ob-text, #1F2A2A) !important; border: 1px solid var(--ob-rand, #D9DEDE);
  box-shadow: 0 8px 24px rgba(0,0,0,.14) !important; font-family: var(--ob-schrift, "Segoe UI", "PT Sans", system-ui, sans-serif); }
.m-ob-mpunkt { min-height: 32px !important; padding: 0 14px !important; gap: 10px; align-items: center; font-size: 13px; }
.m-ob-mpunkt .q-icon { font-size: 18px; color: var(--ob-akzent, #007F7F); }
.m-ob-mpunkt.an { background: var(--ob-an, #D3E8E8); font-weight: 600; }
.m-ob-mpunkt:hover { background: var(--ob-hover, #E3ECEC); }
body.lay-office .m-kopf { min-height: 46px; padding: 8px 18px; }
body.lay-office .m-kopf .m-titel { font-size: 17px; font-weight: 600; }
@media (max-width: 760px) { .m-ob-suche > div:nth-child(2), .m-ob-taste, .m-ob-app { display: none; }
  .m-ob-suche { width: auto; } }
"""
