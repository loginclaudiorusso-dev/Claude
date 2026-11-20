"""1.29: Oberfläche – Navigation: Marke/Logo, Standort wählen, Seitenleiste, Registerkarten (Menüband), Showcase-Dock und
AI-Canvas mit Prompt-Leiste. Teil der Klasse Ansicht (oberflaeche.py), als Mixin ausgelagert – nur verschoben."""

from __future__ import annotations

import logging

from nicegui import run, ui

from . import register, standort_kern, suche_palette, themes
from .ui_bausteine import attr, badge_neu, knopf

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

    def _marke_bauen(self) -> None:
        """Logo + „Belegung“ + Standort; Klick öffnet „Standort wechseln“."""
        aktiv = standort_kern.aktiv()
        with ui.element("button").classes("m-marke m-standort") as mk:
            attr(mk, title=f"Standort: {aktiv.name} – wechseln")
            ui.label("B").classes("m-logo")
            with ui.element("div").classes("m-marke-t"):
                if logo := _logo():                    # Markenlogo (Datei im INNternat-Ordner), nur im Theme INNternat
                    ui.html(f'<img class="m-logo-bild" src="{logo}" alt="INNternat">', sanitize=False)
                ui.label("Belegung").classes("m-marke-alt" + (" mit-logo" if logo else ""))
                ui.label("INNternat").classes("m-marke-neu" + (" mit-logo" if logo else ""))
                ui.label(aktiv.name).classes("m-standort-name")
            ui.icon("unfold_more").classes("m-standort-pfeil")
            self._standort_menue()

    def _standort_menue(self) -> None:
        aktiv = standort_kern.aktiv()
        with ui.menu().props('dark class="m-menue"'):
            ui.label("Standort wechseln").classes("m-mgruppe")
            for k, s in _erlaubte():
                with ui.menu_item(on_click=lambda k=k: self.standort_wechseln(k)).classes("m-mpunkt"):
                    ui.icon("check" if k == aktiv.kurz else "").classes("m-mhaken" + (" an" if k == aktiv.kurz else ""))
                    ui.label(s.name)
            ui.label("Auswertung und Prognose zeigen immer alle Standorte.").classes("m-zweite").style(
                "white-space:normal; max-width:240px; padding: 4px 12px 8px")

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
        dringend = sum(1 for k in self.karten if k.stufe == "dringend")
        pro = self.design["layout"] != "original"
        # Nur neu bauen, wenn sich Seite oder Darstellung ändert – sonst nur die Zahl an „Heute“ anpassen. So bleibt ein
        # Knopf, auf den gerade geklickt wird, stehen (z. B. direkt nach dem Start, wenn die Daten ankommen).
        from . import menueband_ui

        menueband_ui.fuellen(self)                                     # 0.65: Menüband (nur im Layout „office“)
        sig = (self.seite, repr(sorted(self.design.items())))
        if sig == getattr(self, "_nav_sig", None):
            self._nav_zahlen_setzen()
            return
        self._nav_sig, self._nav_zahlen = sig, []
        self.nav.clear()
        if self.design["layout"] == "office" and self.design.get("nav", "band") == "leiste":
            self._leiste_fuellen()                                     # 0.91: Seitenleiste im Windows-Look
            self._nav_zahlen_setzen()
            return
        with self.nav:
            gruppe = None
            for k, text, icon, g in register.NAV:
                if g and g != gruppe:
                    ui.label(g).classes("m-navgruppe")
                gruppe = g
                p = ui.element("button").classes("m-navpunkt" + (" aktiv" if k == self.seite else ""))
                if pro:
                    attr(p, title=text)                                  # Tooltip für die schmale Leiste
                with p:
                    ui.icon(icon)
                    ui.label(text)
                    self._nav_zahlen.append((k, ui.label("").classes("m-zahl").style("margin-left:auto")))
                p.on("click", lambda k=k: self.seite_wechseln(k))
            with ui.element("button").classes("m-navpunkt m-suche") as p:
                ui.icon("search")
                ui.label("Suchen")
                ui.label("Strg K").classes("m-taste").style("margin-left:auto")
            if pro:
                attr(p, title="Suchen (Strg+K)")
            p.on("click", self.suchen)
            if pro and len(themes.modi(self.design["theme"])) > 1:
                hell = self.design["modus"] == "hell"
                with ui.element("button").classes("m-navpunkt m-modus") as mo:
                    ui.icon("dark_mode" if hell else "light_mode")
                    ui.label("Dunkle Darstellung" if hell else "Helle Darstellung")
                attr(mo, title="Zwischen hell und dunkel wechseln – wird gespeichert")
                mo.on("click", lambda: self.design_setzen(modus="dunkel" if self.design["modus"] == "hell" else "hell"))
            if self.design["layout"] == "grid":                     # wie in Office: anheften oder beim Darüberfahren aufklappen
                schmal = self.design["schmal"]
                with ui.element("button").classes("m-navpunkt m-navklapp") as k:
                    ui.icon("push_pin" if schmal else "keyboard_double_arrow_left")
                    ui.label("Leiste anheften" if schmal else "Leiste einklappen")
                attr(k, title="Leiste dauerhaft offen halten (Strg+B)" if schmal else
                     "Leiste einklappen – sie klappt beim Darüberfahren mit der Maus auf (Strg+B)")
                k.on("click", lambda: self.design_setzen(schmal=not schmal))
        self._topnav_fuellen(dringend)
        self._nav_zahlen_setzen()

    def _leiste_fuellen(self) -> None:
        """0.91: Seitenleiste mit allen häufigen Zielen; Zähler am ersten Eintrag einer Seite (nur Dringendes an Heute)."""
        from . import menueband as mb
        from . import menueband_ui as mbu

        eintraege = mb.leiste(mbu._ansichten(), self.design.get("leitung", True))
        an = mb.leiste_aktiv(eintraege, self.seite, mbu._av(self), mbu._heute(self))
        gezaehlt = set()
        with self.nav:
            for gruppe, punkte in eintraege:
                if gruppe:
                    ui.label(gruppe).classes("m-lz-gruppe")
                for p in punkte:
                    b = ui.element("button").classes("m-lz" + (" an" if p is an else ""))
                    attr(b, title=p.text)
                    with b:
                        ui.label(p.text)
                        seite = p.ziel[1]
                        if seite not in gezaehlt:
                            gezaehlt.add(seite)
                            self._nav_zahlen.append((seite, ui.label("").classes("m-zahl")))
                    b.on("click", lambda p=p: mbu.ausfuehren(self, p.ziel))
            ui.element("div").style("flex:1")
            k = ui.element("button").classes("m-lz m-lz-klein")
            attr(k, title="Registerkarten oben wie in Word und Excel – jederzeit über Datei zurück")
            with k:
                ui.label("Menüband zeigen")
            k.on("click", lambda: self.design_setzen(nav="band"))

    def _nav_zahlen_setzen(self) -> None:
        """Zahlen an den Menüpunkten (Seitenleiste und Dock) – ohne die Knöpfe neu zu bauen."""
        for k, z in getattr(self, "_nav_zahlen", []):
            if k == "heute":                                    # 0.64: nur Dringendes zählt (rot), sonst keine Zahl
                n = sum(1 for x in self.karten if x.stufe == "dringend")
                rot, tipp = True, f"{n} dringende Aufgabe{'n' if n != 1 else ''}"
            else:
                w = self.nav_zahl.get(k)
                n, rot, tipp = (w.n, w.rot, w.tipp) if w else (0, False, "")
            z.set_text(str(n))
            z.classes(add="rot") if rot else z.classes(remove="rot")
            if tipp:
                z.props(f'title="{tipp}"')
            else:
                z.props(remove="title")
            z.set_visibility(n > 0)

    DOCK = ("heute", "anreisen", "zimmer", "reinigung", "auswertung")   # Showcase: Standard im Dock, der Rest in den Gruppen

    def dock_seiten(self) -> list[str]:
        gueltig = {k for k, *_r in register.NAV}
        d = self.design.get("dock")
        return [k for k in (d if d is not None else self.DOCK) if k in gueltig]

    def _topnav_fuellen(self, dringend: int) -> None:
        """Showcase-Dock (0.46): Standort · angeheftete Bereiche · je Gruppe ein Menü mit dem Rest (Betrieb, Überblick,
        Verwalten, Leitung) · rechts Suche, Hell/Dunkel, Anheften und „Dock anpassen“."""
        if self.design["layout"] == "office":                          # dort liegt das Menüband
            return
        self.topnav.clear()
        if self.design["layout"] != "showcase":
            return
        dock = self.dock_seiten()
        aktiv_s = standort_kern.aktiv()
        with self.topnav:
            with ui.element("button").classes("m-marke m-dock-standort") as mk:
                attr(mk, title=f"Standort: {aktiv_s.name} – wechseln")
                ui.label("B").classes("m-logo")
                ui.label(aktiv_s.name).classes("m-standort-name")
                ui.icon("expand_more").classes("m-standort-pfeil")
                self._standort_menue()
            ui.element("div").classes("m-trenner")
            for k in dock:
                text, icon = next((t, i) for kk, t, i, _g in register.NAV if kk == k)
                p = ui.element("button").classes("m-navpunkt" + (" aktiv" if k == self.seite else ""))
                attr(p, title=text)
                with p:
                    ui.icon(icon)
                    ui.label(text)
                    self._nav_zahlen.append((k, ui.label("").classes("m-zahl")))
                p.on("click", lambda k=k: self.seite_wechseln(k))
            gruppen: dict[str, list] = {}
            for x in register.NAV:
                if x[0] not in dock:
                    gruppen.setdefault(x[3] or "Start", []).append(x)
            if gruppen:
                ui.element("div").classes("m-trenner")
            for g, punkte in gruppen.items():
                aktiv = next((t for k, t, *_r in punkte if k == self.seite), None)
                offen = sum(1 for k, *_r in punkte if (w := self.nav_zahl.get(k)) and w.n)
                with ui.element("button").classes("m-navpunkt m-dock-gruppe" + (" aktiv" if aktiv else "")) as v:
                    ui.label(aktiv or g)
                    if offen:
                        ui.label("").classes("m-punkt-neu")
                    ui.icon("expand_more").classes("m-dock-pfeil")
                    with ui.menu().props('dark class="m-menue"'):
                        ui.label(g).classes("m-mgruppe")
                        for k, text, icon, _g in punkte:
                            w = self.nav_zahl.get(k)
                            with ui.menu_item(on_click=lambda k=k: self.seite_wechseln(k)).classes("m-mpunkt"):
                                ui.icon(icon).classes("m-mhaken" + (" an" if k == self.seite else ""))
                                ui.label(text)
                                if w and w.n:
                                    ui.label(str(w.n)).classes("m-zahl" + (" rot" if w.rot else "")).style("margin-left:auto")
                attr(v, title=f"{g}: " + ", ".join(t for _k, t, *_r in punkte))
            ui.element("div").classes("m-trenner")
            with ui.element("div").classes("m-dock-rechts"):
                with ui.element("button").classes("m-navpunkt m-suche m-nur-symbol") as p:
                    ui.icon("search")
                attr(p, title="Suchen (Strg+K)")
                p.on("click", self.suchen)
                if len(themes.modi(self.design["theme"])) > 1:
                    hell = self.design["modus"] == "hell"
                    with ui.element("button").classes("m-navpunkt m-nur-symbol") as mo:
                        ui.icon("dark_mode" if hell else "light_mode")
                    attr(mo, title="Dunkle Darstellung" if hell else "Helle Darstellung")
                    mo.on("click", lambda: self.design_setzen(modus="dunkel" if self.design["modus"] == "hell" else "hell"))
                fest = self.design["dock_fest"]
                with ui.element("button").classes("m-navpunkt m-nur-symbol m-dock-pin" + (" an" if fest else "")) as pin:
                    ui.icon("push_pin")
                attr(pin, title="Dock angeheftet – klicken: automatisch ausblenden (Strg+B)" if fest
                     else "Dock blendet sich aus – klicken: dauerhaft anheften (Strg+B)")
                pin.on("click", lambda: self.design_setzen(dock_fest=not self.design["dock_fest"]))
                with ui.element("button").classes("m-navpunkt m-nur-symbol") as an:
                    ui.icon("tune")
                attr(an, title="Dock anpassen – welche Bereiche direkt im Dock stehen")
                an.on("click", self._dock_anpassen)

    def _dock_anpassen(self) -> None:
        """Welche Bereiche stehen direkt im Dock? Der Rest bleibt über die Gruppenmenüs erreichbar."""
        def bauen():
            ui.label("Angeheftete Bereiche stehen direkt im Dock; alle anderen erreichst du über die Gruppenmenüs "
                     "(Betrieb, Überblick, Verwalten, Leitung).").classes("m-ptext")
            jetzt = set(self.dock_seiten())
            schalter = {}
            gruppe = None
            for k, text, _icon, g in register.NAV:
                if (g or "Start") != gruppe:
                    gruppe = g or "Start"
                    ui.label(gruppe).classes("m-mgruppe")
                schalter[k] = ui.switch(text, value=k in jetzt).props("dense color=indigo-4")
            fest = ui.switch("Dock immer sichtbar (angeheftet)", value=self.design["dock_fest"]).props("dense color=indigo-4")

            async def speichern():
                await self.design_setzen(dock=[k for k, *_r in register.NAV if schalter[k].value], dock_fest=bool(fest.value))
                self.panel_zu()

            async def standard():
                await self.design_setzen(dock=None, dock_fest=True)
                self.panel_zu()

            with ui.element("div").classes("m-paktionen"):
                knopf("Speichern", speichern, "primaer", "check")
                knopf("Standard", standard, "leise", "restart_alt")
                knopf("Abbrechen", self.panel_zu, "leise")
        self.panel("Dock anpassen", bauen)

    # ---- AI-Canvas: Prompt-Bar ------------------------------------------------------------

    def _prompt_bauen(self) -> None:
        from .canvas_kern import VORSCHLAEGE

        with ui.element("div").classes("m-prompt-zeile"):
            with ui.element("div").classes("m-prompt"):
                ui.icon("auto_awesome")
                self.prompt_eingabe = ui.input(placeholder="Frag oder filtere … z. B. „freie Zimmer Haus 2“, „ohne Zimmer“, "
                                                           "„neu“, „Abreisen diese Woche“, ein Name").props("dense borderless dark")
                self.prompt_eingabe.on("update:model-value", self._prompt_geaendert, throttle=0.3, leading_events=False)
                self.prompt_eingabe.on("keydown.esc", self._prompt_leeren)
                ui.label("Strg K  ·  /").classes("m-taste")
            with ui.element("div").classes("m-vorschlaege"):
                for v in VORSCHLAEGE:
                    b = ui.element("button").classes("m-vorschlag")
                    with b:
                        ui.label(v)
                    b.on("click", lambda v=v: self._prompt_setzen(v))

    def _prompt_fokus(self) -> None:
        ui.run_javascript("document.querySelector('.m-prompt input')?.focus()")

    def _prompt_setzen(self, text: str) -> None:
        self.prompt_eingabe.set_value(text)
        self._prompt_fokus()

    async def _prompt_leeren(self) -> None:
        self.prompt_eingabe.set_value("")
        ui.run_javascript("document.querySelector('.m-prompt input')?.blur()")
        self.prompt, self._antwort = "", None
        self.zeichnen()

    async def _prompt_geaendert(self) -> None:
        self.prompt = self.prompt_eingabe.value or ""
        if self.design["layout"] != "canvas":
            return
        if not self.prompt.strip():
            self._antwort = None
            self.zeichnen()
            return
        from . import canvas_kern

        text = self.prompt
        try:
            antwort = await run.io_bound(canvas_kern.antwort, self.stand, text, self.heute, self.neu)
        except Exception as exc:               # noqa: BLE001 – eine Eingabe darf nie die Seite blockieren
            log.exception("Canvas")
            self.toast(f"Nicht verstanden: {exc}", fehler=True)
            return
        if text == self.prompt:                # inzwischen weitergetippt → die neuere Antwort gewinnt
            self._antwort = antwort
            self.zeichnen()

    async def suchen(self) -> None:
        """Strg+K: im AI-Canvas die zentrale Eingabe, sonst die Suchpalette."""
        if self.design["layout"] == "canvas":
            self._prompt_fokus()
        else:
            suche_palette.oeffnen(self)

    async def _canvas_ziel(self, seite: str, zustand: dict) -> None:
        self.prompt_eingabe.set_value("")
        self.prompt, self._antwort = "", None
        await self.oeffnen(seite, **zustand)

    def _canvas_zeichnen(self) -> None:
        from .ui_bausteine import badge

        a = self._antwort
        self.titel.set_text("Antwort")
        with self.inhalt, ui.element("div").classes("m-cv"):
            with ui.element("div").classes("m-cv-verstanden"):
                ui.label("Verstanden:" if a.verstanden else "Überblick")
                for t in a.verstanden:
                    ui.label(t).classes("m-cv-tag")
                knopf("Eingabe leeren (Esc)", self._prompt_leeren, "leise", "close").style("margin-left:auto")
            with ui.element("div").classes("m-cv-raster zahlen"):
                for z in a.zahlen:
                    k = ui.element("button").classes("m-cv-karte")
                    with k:
                        ui.label(z.titel).classes("m-zweite")
                        ui.label(str(z.wert)).classes("z")
                        ui.label(z.unter).classes("m-zweite")
                    k.on("click", lambda z=z: self._canvas_ziel(*z.ziel))
            if a.seiten:
                ui.label("Seiten").classes("m-btitel")
                with ui.element("div").classes("m-cv-raster"):
                    for titel, key in a.seiten:
                        k = ui.element("button").classes("m-cv-karte")
                        with k, ui.element("div").classes("k"):
                            ui.icon("arrow_forward")
                            ui.label(titel).classes("m-name")
                        k.on("click", lambda key=key: self._canvas_ziel(key, {}))
            if a.personen:
                with ui.element("div").classes("m-cv-gruppe"):
                    ui.label(f"Personen · {a.personen_gesamt}").classes("m-btitel")
                    if a.alle_personen:
                        knopf("Alle als Liste", lambda: self._canvas_ziel(*a.alle_personen), "leise", "list")
                with ui.element("div").classes("m-cv-raster"):
                    for p in a.personen:
                        k = ui.element("button").classes("m-cv-karte")
                        with k:
                            with ui.element("div").classes("k"):
                                ui.label(p.name).classes("m-name")
                                if p.neu_seit:
                                    badge_neu(p.neu_seit)
                            ui.label(p.zweite).classes("m-zweite")
                            badge("belegt", p.zimmer) if p.zimmer else badge("ohne")
                        if p.zimmer_id:
                            k.on("click", lambda p=p: self._canvas_ziel("zimmer", {"karte": p.zimmer_id}))
                        else:
                            k.on("click", lambda p=p: self._canvas_ziel("anreisen", {"ansicht": "zuteilen", "kennung": p.kennung}))
            if a.zimmer:
                with ui.element("div").classes("m-cv-gruppe"):
                    ui.label(f"Zimmer · {a.zimmer_gesamt}").classes("m-btitel")
                    if a.alle_zimmer:
                        knopf("Alle als Liste", lambda: self._canvas_ziel(*a.alle_zimmer), "leise", "list")
                with ui.element("div").classes("m-cv-raster"):
                    for z in a.zimmer:
                        k = ui.element("button").classes("m-cv-karte")
                        with k:
                            with ui.element("div").classes("k"):
                                ui.label(z.kurz).classes("m-name m-mono")
                                badge(z.status)
                            ui.label(f"{z.lage} · {z.heute}").classes("m-zweite")
                            if z.maengel:
                                ui.label(z.maengel).classes("m-zweite " + ("m-krit" if z.stufe == 3 else "m-warn"))
                        k.on("click", lambda z=z: self._canvas_ziel("zimmer", {"karte": z.zimmer}))
            if a.abreisen:
                ui.label(f"Abreisen · {len(a.abreisen)}").classes("m-btitel")
                with ui.element("div").classes("m-cv-raster"):
                    for x in a.abreisen:
                        k = ui.element("button").classes("m-cv-karte")
                        with k:
                            with ui.element("div").classes("k"):
                                ui.label(x.name).classes("m-name")
                                ui.label(x.zimmer).classes("m-mono")
                            ui.label(f"{x.tag} · {x.massnahme}").classes("m-zweite")
                        if x.zimmer_id:
                            k.on("click", lambda x=x: self._canvas_ziel("zimmer", {"karte": x.zimmer_id}))
            if not (a.personen or a.zimmer or a.abreisen or a.seiten) and a.verstanden:
                ui.label("Keine Treffer – andere Wörter probieren, z. B. „frei“, „Haus 3.1“, „ohne Zimmer“, einen Namen.").classes(
                    "m-cv-leer")
