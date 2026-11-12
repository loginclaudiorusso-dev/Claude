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


def seitentitel(a, titel: str) -> str:
    """Im Menüband-Layout fehlen die Ansichts-Umschalter im Seitenkopf – darum steht die Ansicht im Titel."""
    if a.design.get("layout") != LAYOUT:
        return titel
    if a.seite == "heute":                             # 0.69: Datum im Titel statt eigener großer Überschrift
        if _heute(a) == "postfach":
            return titel + " · Aufgaben"
        tage = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
        return f"{titel} · {tage[a.heute.weekday()]}, {a.heute:%d.%m.%Y}"
    views = _ansichten().get(a.seite) or {}
    k = a.ansicht_von(a.seite, STANDARD_ANSICHT.get(a.seite, ""))
    return f"{titel} · {views[k]}" if k in views else titel


def _seite_im_reiter(r: mb.Reiter, seite: str) -> bool:
    return any(q.ziel and q.ziel[0] == "seite" and q.ziel[1] == seite
               for g in r.gruppen for p in g.punkte for q in [p] + p.menue)


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
    elif name == "modus":                                   # 0.72: Hell → Gedämpft → Dunkel
        from . import darstellung_kern as dk

        await a.design_setzen(helligkeit=dk.naechste_helligkeit(d.get("helligkeit", "hell")))
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
    elif name == "hilfe":
        from . import hilfe_ui

        hilfe_ui.oeffnen(a)
    elif name == "drucken":
        from . import hilfe_ui

        hilfe_ui.drucken(a)
    elif name == "exportieren":                             # 0.73
        from . import hilfe_ui

        await hilfe_ui.exportieren(a)
    elif name == "info":
        from belegung import __version__ as haupt

        a.toast(f"INNternat – neue Oberfläche {__version__} · Daten und Regeln: Belegung {haupt} · "
                f"Standort {standort_kern.aktiv().name}", rueck=False)
    elif name.startswith("nav:"):                           # 0.91: Seitenleiste ↔ Menüband
        await a.design_setzen(nav=name.split(":", 1)[1])
    elif name.startswith("layout:"):
        await a.design_setzen(layout=name.split(":", 1)[1])
    elif name.startswith("farbe:"):
        await a.design_setzen(farbe=name.split(":", 1)[1])
    elif name.startswith("dg_typ:"):
        await a.design_setzen(dg_typ=name.split(":", 1)[1])
    elif name.startswith("dg_modus:"):                      # 0.96: Darstellung im Menüband
        await a.design_setzen(dg_modus=name.split(":", 1)[1])
    elif name.startswith("dg_anteil:"):
        await a.design_setzen(dg_anteil=name.split(":", 1)[1])
    elif name.startswith("aw:"):                            # 0.96: Filter der Prognose im Menüband
        key, wert = mb.aw_wert(name[3:])
        if key == "aw_chart" and wert != "trend":           # Ansichten gibt es nur bei „Trend & Prognose“
            a.aw_status = a.aw_parallel = False
        await a.setzen(nur_seite=True, **{key: wert})
    elif name.startswith("awt:"):
        key = name[4:]
        neu = {key: not getattr(a, key, False)}
        if key in ("aw_status", "aw_parallel") and neu[key]:          # eine der beiden Ansichten, nur bei „Trend“
            neu.update({"aw_status": False, "aw_parallel": False, key: True, "aw_chart": "trend"})
        await a.setzen(nur_seite=True, **neu)
    elif name.startswith("foto"):                           # 0.96: Bildschirmfoto
        await bildschirmfoto(a, ausschnitt=name == "foto:ausschnitt")
    elif name.startswith("dg_legende:"):
        await a.design_setzen(dg_legende=name.split(":", 1)[1])
    elif name.startswith("dg:"):
        key = name.split(":", 1)[1]
        await a.design_setzen(**{key: not d.get(key)})
    elif name == "band_gross":
        await a.design_setzen(band_gross=not d["band_gross"])
    elif name.startswith("zoom:"):
        from . import darstellung_kern as dk

        w = name.split(":", 1)[1]
        z = int(w) if w.isdigit() else dk.zoom_schritt(d["zoom"], 1 if w == "+" else -1)
        await a.design_setzen(zoom=z)
    elif name.startswith("optionen"):
        from . import optionen_ui

        optionen_ui.oeffnen(a, name.split(":", 1)[1] if ":" in name else "farben")


def _zahl(a, p: mb.Punkt) -> tuple[int, bool]:
    if p.ziel and p.ziel[0] == "seite" and p.ziel[1] == "heute" and p.ziel[3].get("heute_ansicht") == "postfach":
        return len(a.karten), True                       # 0.99: rotes Zähler-Abzeichen wie in Office
    if p.ziel == ("aktion", "neuigkeiten"):
        return a.ungelesen, False
    return 0, False


def _menue(a, punkte: list[mb.Punkt]) -> None:
    with ui.menu().props('class="m-ob-menue" anchor="bottom left" self="top left"'):
        for q in punkte:
            an = _menue_an(a, q)
            if q.icon == "haken":
                icon = "check_box" if an else "check_box_outline_blank"
            else:
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
        if z[1].startswith("dg:"):
            return bool(a.design.get(z[1][3:]))
        if z[1].startswith("zoom:") and z[1][5:].isdigit():
            return int(z[1][5:]) == a.design.get("zoom")
        if z[1].startswith("aw:"):
            key, wert = mb.aw_wert(z[1][3:])
            return getattr(a, key, None) == wert
        if z[1].startswith("awt:"):
            return bool(getattr(a, z[1][4:], False))
        for vor, key in (("layout:", "layout"), ("farbe:", "farbe"), ("dg_typ:", "dg_typ"), ("dg_legende:", "dg_legende"),
                         ("dg_modus:", "dg_modus"), ("dg_anteil:", "dg_anteil")):
            if z[1].startswith(vor):
                return z[1][len(vor):] == a.design.get(key)
        return False
    return mb.aktiv(q, a.seite, _av(a), _heute(a))


def _av(a):
    return lambda s: a.ansicht_von(s, STANDARD_ANSICHT.get(s, ""))


def _heute(a) -> str:
    return getattr(a, "heute_ansicht", "zentrale") if getattr(a, "heute_ansicht", "zentrale") == "postfach" else "zentrale"


def _knopf(a, p: mb.Punkt) -> None:
    if p.menue and p.ziel:
        return _split(a, p)
    an = (mb.aktiv(p, a.seite, _av(a), _heute(a)) and not (p.ziel and p.ziel[0] == "aktion")) or \
        (p.ziel is not None and p.ziel[0] == "aktion"
         and p.ziel[1].startswith(("dg_typ:", "dg_modus:", "dg_anteil:", "aw:", "awt:")) and _menue_an(a, p))
    b = ui.element("button").classes(("m-ob-gross" if p.gross else "m-ob-klein") + (" an" if an else "")
                                     + (" mit-menue" if p.menue else ""))
    attr(b, title=p.tipp or p.text)
    n, rot = _zahl(a, p)
    with b:
        with ui.element("span").classes("m-ob-sym"):
            duotone_symbol(p, _dunkel(a), p.gross)
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


def _dunkel(a) -> bool:
    return (getattr(a, "design", None) or {}).get("helligkeit", "hell") != "hell"


def duotone_symbol(p: mb.Punkt, dunkel: bool = False, gross: bool = True) -> None:
    """1.00: Fluent-2-Symbol, zweifarbig (groß) bzw. einfarbig in der Bedeutungsfarbe (kompakt)."""
    from . import symbole

    name, farbe = mb.symbol(p)
    if dunkel and farbe and not gross:              # kompakte Kontur im Dunkeln heller (≥ 3 : 1 zum Band)
        from . import diagramm_stil as _ds

        farbe = _ds.angleichen(farbe, "#1E2626", 3)
    ui.html(symbole.html(name, farbe, gross), sanitize=False).classes("m-ob-fluent")


def _split(a, p: mb.Punkt) -> None:
    """Split-Button wie in Office: oberer Teil öffnet die Standardansicht, der untere (Text + Pfeil) das Menü."""
    an = mb.aktiv(p, a.seite, _av(a), _heute(a))
    with ui.element("div").classes("m-ob-split" + (" an" if an else "")):
        oben = ui.element("button").classes("m-ob-split-o")
        attr(oben, title=p.tipp or p.text)
        n, rot = _zahl(a, p)
        with oben, ui.element("span").classes("m-ob-sym"):
            duotone_symbol(p, _dunkel(a), True)
            if n:
                ui.label(str(n)).classes("m-ob-zahl" + (" rot" if rot else ""))
        oben.on("click", lambda p=p: ausfuehren(a, p.ziel))
        unten = ui.element("button").classes("m-ob-split-u")
        attr(unten, title=f"{p.text} – weitere Ansichten")
        with unten:
            with ui.element("span").classes("m-ob-text"):
                ui.label(p.text)
                ui.icon("expand_more").classes("m-ob-pfeil")
            _menue(a, p.menue)


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
        with ui.element("div").classes("m-ob-gfuss"):
            ui.label(g.titel).classes("m-ob-gtitel")
            if g.starter:                                    # ↘ wie in Office: Dialog zur Gruppe
                st = ui.element("button").classes("m-ob-starter")
                attr(st, title=f"{g.titel}: alle Einstellungen", aria_label=f"{g.titel} – Dialog öffnen")
                with st:
                    ui.icon("south_east")
                st.on("click", lambda z=g.starter: ausfuehren(a, z))


def werkzeuge_oben(a) -> bool:
    """0.99: Werkzeuge der Seite (Filter, Knöpfe) stehen in einer eigenen Kontext-Registerkarte des Menübands."""
    return band_sichtbar(a) and bool(a.design.get("werkzeuge_oben", True))


def hat_werkzeuge(a) -> bool:
    return any(getattr(x, "default_slot", None) is not None and x.default_slot.children
               for x in (getattr(a, "werkzeuge", None), getattr(a, "leiste", None)))


def seiten_reiter_titel(a) -> str:
    from . import register

    t = seitentitel(a, register.TITEL.get(a.seite, a.seite))
    return t.split(" · ")[-1] if " · " in t and a.seite != "heute" else t.split(" · ")[0]


def fuellen(a, erzwingen: bool = False, nach_zeichnen: bool = False) -> None:
    """Menüband in ``a.topnav`` bauen – nur neu, wenn sich etwas Sichtbares geändert hat (ein Klick bleibt stehen).
    ``nach_zeichnen``: Aufruf nach dem Zeichnen der Seite – erst dann ist bekannt, ob sie Werkzeuge hat."""
    if a.design.get("layout") != LAYOUT:
        if getattr(a, "_ob_sig", None) is not None:
            a._ob_sig = None
            a.topnav.clear()
        return
    alle = mb.reiter(_ansichten(), a.design.get("leitung", True), _standorte())
    oben = werkzeuge_oben(a)
    ort = (a.seite, a.ansicht_von(a.seite, STANDARD_ANSICHT.get(a.seite, "")))
    if getattr(a, "_ob_ort", None) not in (None, ort) and oben:
        a._ob_sprung = True                         # Seite/Ansicht gewechselt → nach dem Zeichnen ihre Werkzeuge zeigen
    a._ob_ort = ort
    tab = getattr(a, "band_tab", None) or "start"
    if tab == "seite" and not (oben and (hat_werkzeuge(a) or not nach_zeichnen)):
        tab = mb.reiter_von(a.seite, _ansichten(), a.ansicht.get(a.seite))
    if tab != "seite":
        aktuell = next((r for r in alle if r.key == tab), alle[0])
        if not mb.sichtbar(aktuell, a.seite) or (not _seite_im_reiter(aktuell, a.seite)
                                                  and getattr(a, "_ob_seite", None) != a.seite):
            tab = mb.reiter_von(a.seite, _ansichten(), a.ansicht.get(a.seite))   # Sprung: das Band folgt der Seite
            aktuell = next((r for r in alle if r.key == tab), alle[0])
    if nach_zeichnen and getattr(a, "_ob_sprung", False) and oben and hat_werkzeuge(a):
        a._ob_sprung = False                        # (erst wenn die Seite fertig ist – nicht beim „Lädt …“)
        tab = "seite"                               # wie Office: Ansicht gewählt → ihre Registerkarte öffnet sich
    if tab == "seite":
        aktuell = mb.Reiter("seite", seiten_reiter_titel(a), [])
    a.band_tab, a._ob_seite = tab, a.seite
    if getattr(a, "body", None) is not None:
        if tab == "seite":
            a.body.classes(add="ob-seite-an")
        else:
            a.body.classes(remove="ob-seite-an")
        if oben and hat_werkzeuge(a):               # 1.00: Kopf immer gleich hoch – Titelzeile nur ohne Seiten-Reiter
            a.body.classes(add="ob-hat-werkzeuge")
        else:
            a.body.classes(remove="ob-hat-werkzeuge")
    from belegung import aenderungen as _ae

    letzt = _ae.letzter()
    sig = (tab, a.seite, repr(sorted(a.ansicht.items())), _heute(a), repr(sorted(a.design.items())), len(a.karten),
           letzt.titel if letzt else "", len(_ae._verlauf),
           sum(1 for k in a.karten if k.stufe == "dringend"), a.ungelesen, getattr(a.stand_anzeige, "text", ""),
           tuple(getattr(a, k, None) for k in AW_KEYS), oben and hat_werkzeuge(a))
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
            ui.label("INNternat").classes("m-ob-app")
            st = ui.element("button").classes("m-ob-tk breit m-ob-standort")    # Standort nur hier (Regel 2)
            attr(st, title="Standort wechseln")
            with st:
                ui.icon("location_on")
                ui.label(s.name)
                ui.icon("expand_more").classes("m-ob-pfeil-hell")
            st.on("click", lambda: ausfuehren(a, mb.A("standort")))
            such = ui.element("button").classes("m-ob-suche")
            attr(such, title="Suchen (Strg+K)")
            with such:
                ui.icon("search")
                ui.label("Suchen oder Befehl: Name, Zimmer, „drucken“ …")
                ui.label("Strg+K").classes("m-ob-taste")
            such.on("click", a.suchen)
            ui.element("div").style("flex:1")
            if a.design.get("nav", "band") == "leiste":              # 0.91: was Rückgängig zurücknimmt, steht dran
                from belegung import aenderungen

                s_ = aenderungen.letzter()
                if s_ is not None:
                    rk = ui.element("button").classes("m-ob-rueck")
                    attr(rk, title="Letzten eigenen Schritt zurücknehmen (Strg+Z)")
                    with rk:
                        ui.label(f"Rückgängig: {s_.titel}")
                    rk.on("click", lambda: ausfuehren(a, mb.A("rueckgaengig")))
            # 0.68: Glocke (Neuigkeiten) und Hilfe in der Titelleiste – wie in Office
            leiste = a.design.get("nav", "band") == "leiste"
            glocke = ui.element("button").classes("m-ob-tk m-ob-glocke" + (" m-ob-neu" if leiste else ""))
            attr(glocke, title=f"Neuigkeiten – {a.ungelesen} ungelesen (Meldungen, keine Aufgaben)" if a.ungelesen
                 else "Neuigkeiten", aria_label="Neuigkeiten")
            with glocke:
                if leiste:                       # 0.91: als Wort – die Zahl ist keine Aufgabenzahl
                    ui.label(f"Neuigkeiten · {a.ungelesen}" if a.ungelesen else "Neuigkeiten")
                else:
                    ui.icon("notifications" if a.ungelesen else "notifications_none")
                    if a.ungelesen:
                        ui.label(str(a.ungelesen)).classes("m-ob-zahl rot" if a.ungelesen else "m-ob-zahl")
            glocke.on("click", lambda: ausfuehren(a, mb.A("neuigkeiten")))
            hilfe = ui.element("button").classes("m-ob-tk")
            attr(hilfe, title="Hilfe zu dieser Seite (F1)", aria_label="Hilfe")
            with hilfe:
                ui.icon("help_outline")
            hilfe.on("click", lambda: ausfuehren(a, mb.A("hilfe")))
        with ui.element("div").classes("m-ob-reiter"):
            datei = ui.element("button").classes("m-ob-datei")
            with datei:
                ui.label("Datei")
                _menue(a, mb.DATEI)
            for r in alle:
                if not mb.sichtbar(r, a.seite):
                    continue
                hier = not r.kontext and r.key != tab and r.key == mb.reiter_von(a.seite, _ansichten(),
                                                                                  a.ansicht.get(a.seite))
                rb = ui.element("button").classes("m-ob-tab" + (" an" if r.key == tab else "")
                                                  + (" kontext" if r.kontext else "") + (" hier" if hier else ""))
                if hier:                                     # Orientierung: hier liegt die offene Seite
                    attr(rb, title="Hier liegt die gerade offene Seite")
                if r.kontext:
                    attr(rb, title="Kontext-Registerkarte – erscheint nur auf Seiten mit Diagrammen")
                with rb:
                    ui.label(r.titel)
                rb.on("click", lambda r=r: _tab(a, r.key))
            if oben and hat_werkzeuge(a):            # 0.99: Kontext-Registerkarte mit den Werkzeugen der Seite
                rb = ui.element("button").classes("m-ob-tab kontext seite" + (" an" if tab == "seite" else ""))
                attr(rb, title="Filter und Knöpfe dieser Seite – wie die Kontext-Registerkarten in Office")
                with rb:
                    ui.label(seiten_reiter_titel(a))
                rb.on("click", lambda: _tab(a, "seite"))
        with ui.element("div").classes("m-ob-band" + (" m-ob-band-seite" if tab == "seite" else "")):
            ansicht = a.ansicht_von(a.seite, STANDARD_ANSICHT.get(a.seite, ""))
            for g in aktuell.gruppen:
                if mb.gruppe_sichtbar(g, a.seite, ansicht):
                    _gruppe(a, g)
        with ui.element("footer").classes("m-ob-status"):
            ui.label("Bereit")
            ui.label(getattr(a.stand_anzeige, "text", "")).classes("m-ob-status-m")   # Datenstand – ohne Doppel-Zähler
            a._ob_info = ui.label(getattr(a, "status_info", "")).classes("m-ob-status-m m-ob-info")  # 0.74: Zahlen der Ansicht
            ui.element("div").style("flex:1")
            ui.label(f"Version {__version__}")
            with ui.element("div").classes("m-ob-zoom"):    # wie in Word/Excel: Ansicht-Schalter und Zoom unten rechts
                an = {"dichte": a.design.get("dichte") == "kompakt", "vollbild": bool(a.design.get("vollbild")),
                      "modus": a.design.get("helligkeit", "hell") != "hell"}
                for p in mb.STATUSLEISTE:
                    z = ui.element("button").classes("m-ob-zk" + (" an" if an.get(p.ziel[1]) else ""))
                    attr(z, title=p.tipp or p.text, aria_label=p.text)
                    with z:
                        if p.icon:
                            ui.icon(p.icon)
                        else:
                            ui.label(f"{a.design['zoom']} %")
                    if p.ziel == mb.A("zoom:-"):
                        ui.element("span").classes("m-ob-strich")
                    z.on("click", lambda p=p: ausfuehren(a, p.ziel))


AW_KEYS = ("aw_standort", "aw_brutto", "aw_horizont", "aw_chart", "aw_status", "aw_parallel", "aw_95", "aw_backtest")


def _standorte() -> dict:
    try:
        from . import auswertung_kern as ak

        return dict(ak.STANDORTE)
    except Exception:                                       # noqa: BLE001
        return {}


def band_sichtbar(a) -> bool:
    """0.96: Menüband sichtbar (Office-Layout ohne Seitenleiste) – dann stehen die Diagramm-Filter oben im Band."""
    d = getattr(a, "design", None) or {}
    return d.get("layout") == LAYOUT and d.get("nav", "band") != "leiste"


async def bildschirmfoto(a, ausschnitt: bool = False) -> None:
    """0.96: Fenster als Bild → Zwischenablage + PNG (Bilder\\INNternat). Kurz warten, damit Menüs und Tooltips weg sind."""
    import asyncio

    from nicegui import run

    from . import bildschirmfoto_kern as bf

    if ausschnitt:
        erg = bf.ausschnitt()
        if not erg["ok"]:
            ui.notify(erg["fehler"], type="warning")
        return
    await asyncio.sleep(.35)
    titel = f"{a.seite}_{a.ansicht_von(a.seite, STANDARD_ANSICHT.get(a.seite, ''))}" if getattr(a, "seite", "") else ""
    erg = await run.io_bound(bf.aufnehmen, titel)
    if not erg["ok"]:
        ui.notify(erg["fehler"], type="warning", timeout=6000)
        return
    teile = ["In der Zwischenablage – mit Strg+V einfügen"] if erg.get("ablage") else []
    if erg.get("pfad"):
        teile.append(f"gespeichert: {erg['pfad']}")
    ui.notify("📷 Bildschirmfoto · " + " · ".join(teile), type="positive", timeout=5000, multi_line=True)


def _tab(a, key: str) -> None:
    a._ob_sprung = False                            # eigene Wahl des Reiters geht vor
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
.m-ob-glocke { position: relative; }
.m-ob-glocke .m-ob-zahl { top: 1px; right: -2px; }
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
.m-ob-punkte { flex: 1; display: flex; align-items: flex-start; gap: 4px; }
.m-ob-gtitel { text-align: center; font-size: 11px; color: var(--ob-text2); padding: 2px 0 4px; white-space: nowrap; }
.m-ob-gross { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; gap: 3px;
  min-width: 58px; max-width: 86px; height: 76px; padding: 4px 6px 2px; box-sizing: border-box; border-radius: 4px; text-align: center;
  border: 1px solid transparent !important; }
.m-ob-gross .m-ob-sym { position: relative; display: inline-flex; }
.m-ob-gross .m-ob-sym .q-icon { font-size: 28px; color: var(--ob-sym-basis); }
.m-ob-gross .m-ob-text { display: flex; align-items: center; gap: 0; font-size: 12px; line-height: 1.15;
  hyphens: manual; overflow-wrap: normal; word-break: normal; }
.m-ob-klein { display: flex; align-items: center; gap: 6px; height: 23px; padding: 0 8px 0 5px; border-radius: 4px;
  white-space: nowrap; font-size: 12px; border: 1px solid transparent !important; }
.m-ob-klein .m-ob-sym { position: relative; display: inline-flex; }
.m-ob-klein .m-ob-sym .q-icon { font-size: 17px; color: var(--ob-sym-basis); }
/* 1.00: Fluent-2-Symbole im Menüband */
.m-ob-fluent { display: inline-flex; line-height: 0; }
.m-ob-gross .m-ob-sym, .m-ob-split-o .m-ob-sym { width: 32px; height: 32px; }
body.lay-office .m-ob { --sym-basis: #334155; }
body.lay-office:not(.hell) .m-ob { --sym-basis: #CBD5E1; }
/* 0.99: zweifarbige Symbole (Microsoft 365 / Fluent): feines Basissymbol + kleiner farbiger Akzent unten rechts */
body.lay-office { --ob-sym-basis: #334155; --ob-duo-grund: #ffffff; }
body.lay-office.mod-dunkel, body.lay-office:not(.hell) { --ob-sym-basis: #CBD5E1; --ob-duo-grund: var(--ob-band); }
.m-ob-duo { position: relative; display: inline-flex; align-items: center; justify-content: center; }
.m-ob-gross .m-ob-duo, .m-ob-split-o .m-ob-duo { width: 32px; height: 32px; }
.m-ob-duo .q-icon.m-ob-duo-basis { color: var(--ob-sym-basis); }
.m-ob-gross .m-ob-duo .q-icon.m-ob-duo-basis, .m-ob-split-o .m-ob-duo .q-icon.m-ob-duo-basis { font-size: 28px !important; }
.m-ob-duo .q-icon.m-ob-duo-akzent { position: absolute; right: -3px; bottom: -2px; font-size: 14px !important;
  background: var(--ob-duo-grund); border-radius: 50%; padding: 1px; line-height: 1; color: var(--ob-sym-basis); }
.m-ob-klein .m-ob-duo .q-icon.m-ob-duo-akzent { font-size: 9px !important; right: -4px; bottom: -3px; padding: 0; }
.m-ob-duo.horizont::after { content: ""; position: absolute; left: 3px; right: 3px; bottom: 3px; height: 2px;
  border-radius: 1px; background: #0284c7; opacity: .55; }                /* Tagesübersicht: dezenter blauer Horizont */
.m-ob-klein .m-ob-duo.horizont::after { bottom: 0; }
.m-ob-klein .m-ob-text { display: flex; align-items: center; }
.m-ob-stapel { display: flex; flex-direction: column; gap: 1px; padding-top: 2px; }
.m-ob-gross:hover, .m-ob-klein:hover { background: var(--ob-hover) !important; }
.m-ob-gross.an, .m-ob-klein.an { background: var(--ob-an) !important; border-color: var(--ob-rand) !important; }
.m-ob-pfeil { font-size: 15px !important; color: var(--ob-text2) !important; }
/* 0.67: Split-Button (oben: Standardansicht, unten: Menü) und Kontext-Registerkarte */
.m-ob-split { display: flex; flex-direction: column; align-items: stretch; min-width: 58px; max-width: 86px; height: 70px;
  border-radius: 4px; border: 1px solid transparent; }
.m-ob-split:hover { border-color: var(--ob-rand); }
.m-ob-split.an { background: var(--ob-an); border-color: var(--ob-rand); }
.m-ob-split-o { flex: none; height: 37px; display: flex; align-items: flex-start; justify-content: center; padding-top: 6px;
  border-radius: 4px 4px 0 0; }
.m-ob-split-o .m-ob-sym { position: relative; display: inline-flex; }
.m-ob-split-o .q-icon { font-size: 28px; color: var(--ob-akzent); }
.m-ob-split-u { flex: 1; display: flex; align-items: flex-start; justify-content: center; padding: 0 4px 4px;
  border-radius: 0 0 4px 4px; text-align: center; }
.m-ob-split-u .m-ob-text { display: inline-flex; align-items: center; font-size: 12px; line-height: 1.15; }
.m-ob-split-o:hover, .m-ob-split-u:hover { background: var(--ob-hover) !important; }
.m-ob-tab.kontext { color: var(--ob-akzent) !important; }
.m-ob-tab.kontext::before { content: ""; position: absolute; left: 6px; right: 6px; top: 0; height: 3px; border-radius: 0 0 2px 2px;
  background: var(--ob-akzent); opacity: .55; }
body.lay-office .m-seg-ansicht { display: none !important; }
/* 0.91: Seitenleiste im Windows-Look – Titel- und Statusleiste bleiben, die Registerkarten entfallen */
body.lay-office.nav-leiste .m-ob-reiter, body.lay-office.nav-leiste .m-ob-band { display: none !important; }
body.lay-office.nav-leiste .m-seg-ansicht { display: inline-flex !important; }
body.lay-office.nav-leiste .m-nav { display: flex !important; width: 232px; background: var(--ob-fl);
  border-right: 1px solid var(--ob-rand); padding: 8px 8px 10px; gap: 1px; overflow-y: auto; backdrop-filter: none;
  position: fixed; left: 0; top: var(--ob-titel-h, 38px); bottom: 24px; z-index: 5; }
body.lay-office.nav-leiste .m-nav .m-marke, body.lay-office.nav-leiste .m-nav .m-navfuss { display: none !important; }
body.lay-office.nav-leiste .m-navliste { display: flex; flex-direction: column; gap: 1px; flex: 1; }
body.lay-office.nav-leiste .m-haupt { margin-left: 232px; min-width: 0; }
body.lay-office.nav-leiste .m-haupt > .m-topnav { margin-left: -232px; }
.m-lz { display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; border: 0; background: transparent;
  font: inherit; font-size: 14.5px; color: var(--ob-text); padding: 5px 12px; border-radius: 6px; cursor: pointer; min-height: 31px; }
.m-lz:hover { background: var(--ob-hover); }
.m-lz.an { background: var(--ob-an); color: var(--ob-titel); font-weight: 600; }
body.mod-dunkel .m-lz.an { color: var(--ob-akzent); }
.m-lz:focus-visible { outline: 2px solid var(--ob-akzent); outline-offset: -2px; }
.m-lz .m-zahl { margin-left: auto; }
.m-lz-gruppe { font-size: 12.5px; color: var(--ob-text2); padding: 11px 12px 3px; }
.m-lz-klein { font-size: 12.5px; color: var(--ob-text2); min-height: 28px; }
.m-ob-rueck { border: 0; background: transparent; color: var(--ob-titel-text); font: inherit; font-size: 13.5px;
  padding: 4px 10px; border-radius: 4px; cursor: pointer; max-width: 340px; overflow: hidden; white-space: nowrap;
  text-overflow: ellipsis; opacity: .92; }
.m-ob-rueck:hover { background: rgba(255,255,255,.14); opacity: 1; }
.m-ob-tk.m-ob-neu { width: auto; padding: 0 12px; border: 1px solid rgba(255,255,255,.45); border-radius: 4px;
  font-size: 13.5px; color: var(--ob-titel-text); }
/* 0.69 Arbeitsfläche: Kennzahlen als EINE Zeile flacher Chips, Null-Werte grau; Heute ohne große Überschrift */
body.lay-office .m-leiste { padding: 6px 18px; gap: 8px; row-gap: 6px; }
body.lay-office .m-stats { gap: 6px; }
body.lay-office .m-stat { flex-direction: row !important; align-items: center; gap: 6px; min-width: 0 !important; height: 30px;
  padding: 0 11px 0 9px !important; border-radius: 15px !important; }
body.lay-office .m-stat .k { gap: 4px; }
body.lay-office .m-stat .s { font-size: 15px !important; }
body.lay-office .m-stat .z { font-size: 14px !important; font-weight: 700 !important; letter-spacing: 0 !important; }
body.lay-office .m-stat .l { font-size: 12.5px !important; color: var(--text2) !important; white-space: nowrap; }
body.lay-office .m-stat.null { display: none; }           /* Null-Werte nicht als Chip (Review: „Null-Lärm“) */
body.lay-office .m-stat.null .s, body.lay-office .m-stat.null .z { color: var(--text3) !important; }
body.lay-office .m-trennlinie { height: 22px; }
body.lay-office .m-tz-kopf { display: none; }
body.lay-office .m-tz { padding-top: 10px !important; }
body.lay-office .m-tz-zahlen { display: flex; flex-wrap: wrap; gap: 6px; border: 0; margin-bottom: 12px; }
body.lay-office .m-tz-zahl-k { display: inline-flex !important; align-items: center; gap: 7px; height: 32px; padding: 0 12px !important;
  border: 1px solid var(--rand) !important; border-radius: 16px; background: var(--fl); }
body.lay-office .m-tz-zahl-k .m-tz-zahl { font-size: 15px; font-weight: 700; font-family: inherit; }
body.lay-office .m-tz-zahl-k .m-tz-zahl-t { display: flex; gap: 0; }
body.lay-office .m-tz-zahl-k .m-tz-zahl-l { font-size: 12.5px; font-weight: 500; letter-spacing: 0; text-transform: none; color: var(--text2); }
body.lay-office .m-tz-zahl-k .m-tz-zahl-l .q-icon { display: none; }
body.lay-office .m-tz-zahl-k .m-tz-zahl-u { display: none; }
body.lay-office .m-tz-zahl-k.null { opacity: .55; }
body.lay-office .m-tz-zahl-k.null .m-tz-zahl { color: var(--text3) !important; }
.m-w-leiste { display: flex; align-items: center; gap: 10px; margin: 10px 24px 0; padding: 6px 8px 6px 14px; border-radius: 6px;
  background: var(--ob-an, rgba(0,127,127,.1)); font-size: 13px; }
.m-w-leiste > .q-icon { color: var(--ob-akzent, var(--akzent)); font-size: 18px; }
.m-w-leiste > div:nth-child(2) { flex: 1; }
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
.m-ob-zk.an { background: var(--ob-an) !important; color: var(--ob-akzent) !important; }
.m-ob-strich { display: none; }
.m-ob-zoom > .m-ob-zk:nth-child(3) { margin-right: 10px; }
.m-ob-gfuss { display: flex; align-items: center; justify-content: center; gap: 2px; position: relative; }
.m-ob-starter { position: absolute; right: -4px; bottom: 2px; width: 16px; height: 16px; display: inline-flex;
  align-items: center; justify-content: center; border-radius: 3px; color: var(--ob-text2) !important; }
.m-ob-starter .q-icon { font-size: 12px; }
.m-ob-starter:hover { background: var(--ob-hover) !important; color: var(--ob-akzent) !important; }
.m-ob-standort { margin-left: -4px; background: rgba(255,255,255,.08) !important; }
.m-ob-pfeil-hell { font-size: 16px !important; opacity: .8; }
/* 0.99: Werkzeuge der Seite im Menüband – die Kontextzeile wird zum Band der Registerkarte „<Seite>“ */
body.lay-office.ob-oben:not(.ob-seite-an) .m-kz .m-werkzeuge,
body.lay-office.ob-oben:not(.ob-seite-an) .m-kz > .m-leiste { display: none !important; }
body.lay-office.ob-oben.ob-seite-an .m-ob-band { display: none !important; }
/* 1.00: Seiten-Band = gleiche Höhe (96 px), gleiche Farbe, gleiche Kante wie das Menüband – nichts springt, nichts
   wird abgeschnitten (zu breit → waagrecht schieben; Leisten ohne Gruppen dürfen zweizeilig umbrechen). */
body.lay-office .m-ob-band { height: 110px; min-height: 110px; box-sizing: border-box; padding: 6px 8px 0; }
/* 1.01: mehr Luft – Gruppentitel nicht am Rand, Texte nicht an Knopfkanten, Gruppen deutlich getrennt */
.m-ob-gruppe { padding: 0 10px !important; }
.m-ob-gtitel { padding: 5px 0 9px !important; line-height: 13px; }
.m-ob-punkte { gap: 6px !important; }
.m-ob-gross { padding: 4px 8px 3px !important; min-width: 64px !important; max-width: 110px !important; }
.m-ob-gross .m-ob-text { font-size: 12.5px !important; line-height: 15px !important; }
body.lay-office.ob-oben.ob-seite-an .m-kz { background: var(--ob-band); height: 110px; min-height: 110px; box-sizing: border-box;
  align-items: flex-start; align-content: flex-start; padding: 6px 8px 0; border-bottom: 1px solid var(--ob-rand);
  box-shadow: 0 1px 3px rgba(15, 23, 42, .08); overflow-x: auto; overflow-y: hidden; row-gap: 4px; }
body.lay-office.ob-oben.ob-seite-an .m-kz:has(.m-bg) { flex-wrap: nowrap; gap: 0; }
/* 1.02: auch Bänder aus losen Band-Knöpfen brechen nie um – zu breit → waagrecht schieben */
body.lay-office.ob-oben.ob-seite-an .m-kz:has(.m-bg-g, .m-bg-st) { flex-wrap: nowrap; }
body.lay-office.ob-oben.ob-seite-an .m-kz:has(.m-bg-g, .m-bg-st) .m-leiste,
body.lay-office.ob-oben.ob-seite-an .m-kz:has(.m-bg-g, .m-bg-st) .m-werkzeuge { flex-wrap: nowrap; flex: none; }
body.lay-office.ob-oben.ob-hat-werkzeuge:not(.ob-seite-an) .m-kz { display: none !important; }   /* kein Springen */
body.lay-office.ob-oben.ob-seite-an .m-kz:not(:has(.m-bg)) { overflow-y: auto; align-content: flex-start; padding-top: 8px; }
body.lay-office.ob-oben.ob-seite-an .m-kz:not(:has(.m-bg)) .m-chip, body.lay-office.ob-oben.ob-seite-an .m-kz:not(:has(.m-bg)) .m-knopf {
  min-height: 28px; }
body.lay-office.ob-oben.ob-seite-an .m-kz:has(.m-bg) .m-kopf > .m-titel { display: none !important; }
body.lay-office.ob-oben.ob-seite-an .m-kz .m-kopf > .m-titel { font-size: 13px !important; font-weight: 600 !important;
  color: var(--ob-text2); padding-right: 12px; margin-right: 4px; border-right: 1px solid var(--ob-rand); align-self: stretch;
  display: flex; align-items: center; }
.m-ob-tab.kontext.seite { color: #0284c7 !important; }
.m-ob-tab.kontext.seite::before { background: #0284c7 !important; }
.m-ob-tab.hier::before { content: none; }           /* 0.99: Punkt rechts neben dem Wort („Start •“), nicht darüber */
.m-ob-tab.hier > div { display: inline-flex; align-items: center; gap: 6px; }
.m-ob-tab.hier > div::after { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--ob-akzent);
  flex: none; }
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
