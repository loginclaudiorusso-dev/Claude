"""Die neue Oberfläche (NiceGUI): Seitenleiste, Kopf, Aufgaben-Center rechts und die Seiten. „Anreisen“ ist hier
gebaut, die übrigen Seiten in ``seiten``. Alle Daten und Regeln kommen aus dem Hauptprogramm (``kern``)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from nicegui import app, run, ui

from belegung import __version__ as haupt_version

from . import __version__, kern, register, seite_anreisen, suche_palette, themes
from .stil import CSS
from .ui_bausteine import attr, badge_neu, kennzahlen, knopf, leer

log = logging.getLogger(__name__)

TOAST_S = 6
PRUEF_S = 30                # so oft wird geprüft, ob das Hauptprogramm etwas gespeichert hat
STUFEN = [("dringend", "Dringend"), ("bald", "Als Nächstes"), ("info", "Zur Info")]
AMPEL = {"dringend": "krit", "bald": "warn", "info": "ok"}


def _stempel() -> tuple:
    """Änderungszeit der Daten – ändert sie sich, wird neu geladen."""
    from belegung import aenderungen, speicher
    from belegung import mieter as mt
    from belegung import reinigungsliste as rl
    from belegung import termine as tm
    from belegung import zimmerplan as zp

    erg = []
    for name in aenderungen.dateien_mit_plan() + [rl.DATEI, tm.DATEI, mt.DATEI, zp.REINIGUNG_MANUELL]:
        p = speicher.pfad(name)
        erg.append(p.stat().st_mtime if p.exists() else 0)
    return tuple(erg)


class Ansicht:
    def __init__(self) -> None:
        self.heute = date.today()
        self.seite = "heute"
        self.ansicht: dict[str, str] = {}      # Unteransicht je Seite (z. B. Zimmer → Zeitstrahl)
        self.stand = None
        self.anreisen: list[kern.Anreise] = []
        self.kennung: str | None = None
        self.zeilen: list[kern.Zeile] = []
        self.neu: dict = {}                    # neue Personen (Schlüssel → erstmals gesehen)
        try:
            self.design = kern.design_lesen()
        except Exception:                      # noqa: BLE001 – im Zweifel der Original-Zustand
            self.design = dict(themes.STANDARD)
        themes.AKTIV = self.design
        self.prompt = ""                       # AI-Canvas: aktuelle Eingabe
        self._antwort = None
        self.filter = "alle"
        self.karten: list[kern.Karte] = []
        self.daten = None                      # Daten der aktuellen Seite (außer Anreisen)
        self.center_offen = False
        self.panel_def = None                  # (Titel, Baufunktion) – Formular im Panel rechts statt Aufgaben
        self.stempel: tuple = ()
        self.fehler = ""
        self.ohne_daten = False
        # Zustand der Seiten
        self.zs_haus, self.zs_tage, self.zs_haeuser = "", 28, []
        self.zs_start = self.heute - timedelta(days=self.heute.weekday())
        self.rg_zeitraum, self.rg_filter = "woche", "offen"
        self.rg_von = self.rg_bis = self.heute
        self.zl_haus, self.zl_status, self.zl_text = "", "", ""
        self.zl_schnell: set[str] = set()
        self.zl_mehr: dict = {}                # seltenere Zimmerfilter (Boden, Mangel, Renovierung, Gruppe …)
        self.zk_auswahl: set[str] = set()      # markierte Zimmer in der Liste (für „Eigenschaften setzen“)
        self.ps_filter, self.ps_text = "alle", ""
        self.iv_haus, self.iv_text, self.iv_ohne = "", "", False
        self.zu_vergangene = False             # Zuteilen: auch vergangene Anreisen (letztes Jahr) zur Auswahl
        self.ein_alle = False                  # Firmenprogramm: auch abgehakte zeigen
        self.ab_zeitraum, self.ein_tage = "heute", 14
        self.tm_tage, self.tm_monat = 30, self.heute.replace(day=1)
        self.as_text, self.as_verstanden, self.as_chat = "", [], []
        self.zu_tag = self.heute
        self.zu_filter = self.dz_filter = self.mt_filter = None
        from belegung import konfig

        self.aw_standort, self.aw_brutto, self.aw_horizont = konfig.GESAMT, False, 24
        self.aw_95, self.aw_backtest = True, False
        self.aw_chart, self.aw_summary = "trend", True          # Prognose: Diagrammart, Kernaussagen offen
        self.aw_kap, self.aw_kap_basis, self.aw_offset = None, None, 0.0   # Was-wäre-wenn (Kapazität, Auslastung ±%)
        self.aw_von, self.aw_bis = self.heute.replace(day=1), self.heute
        self.aw_modus, self.aw_schritt = "analyse", 4                     # Prognose: Analyse/Präsentation, Aufbauschritt
        self.aw_anim, self.aw_anim_gezeigt, self._anim_jetzt = True, False, False   # Aufbau-Animation nur beim ersten Öffnen
        self.aw_uwt, self.aw_mieter = True, True   # Prognose: UWTler / Mieter in Kurve und Kennzahlen einbeziehen
        self.aw_status = False
        self.aw_parallel = False
        self.aw_bereich = "dashboard"           # Prognose: Dashboard · Szenarien & Simulation · Details & Protokoll               # bei „Gesamt“: die drei Standorte parallel                 # Prognosegraph: Gesamt oder gestapelt nach Status (UWTler · Mieter · übrige)
        self.aw_details, self.aw_vergleich_praes = False, False           # Tabelle ausführlich, Standorte in der Präsentation
        self.weniger_bewegung = False          # System-Einstellung „Bewegung reduzieren“ (prefers-reduced-motion)
        self._prognose_chart = None

    # ---- Daten ---------------------------------------------------------------------------

    def _laden(self) -> None:
        from belegung import zimmerplan as zp

        self.heute = date.today()
        self.stand = zp.laden()
        self.ohne_daten = self.stand.plan is None and not self.stand.bedarf
        self.karten = kern.karten(self.stand, self.heute)
        try:
            self.neu = kern.neue_personen(self.stand, self.heute)
        except Exception:                      # noqa: BLE001 – Merkhilfe darf nie das Laden verhindern
            self.neu = {}
        if self.seite == "anreisen" and self.ansicht_von("anreisen", "zuteilen") != "zuteilen":
            seite_anreisen.daten(self)
        elif self.seite == "anreisen":
            self.anreisen = kern.anreisen(self.stand, self.heute, self.zu_vergangene)
            if self.kennung not in {a.kennung for a in self.anreisen}:
                self.kennung = kern.erste_offene(self.anreisen)
            self.zeilen = kern.zeilen(self.stand, self.kennung, self.heute)
            try:
                self.np = kern.nach_planung(self.stand, self.heute, 12)
            except Exception:                  # noqa: BLE001 – Kennzahl darf das Zuteilen nie blockieren
                self.np = None
        else:
            register.SEITEN[self.seite][0](self)
        self.stempel = _stempel()

    async def laden(self, zeichnen: bool = True) -> None:
        try:
            await run.io_bound(self._laden)
            self.fehler = ""
        except Exception as exc:              # noqa: BLE001 – Fehler sichtbar machen statt leerer Seite
            log.exception("Laden fehlgeschlagen")
            self.fehler = f"Die Daten konnten nicht geladen werden: {exc}"
        if zeichnen:
            self.zeichnen()

    async def pruefen(self) -> None:
        """Hat das Hauptprogramm (oder jemand anderes) inzwischen gespeichert? Dann neu laden."""
        try:
            neu = await run.io_bound(_stempel)
        except OSError:
            return
        if neu != self.stempel and self.panel_def is None:     # offenes Formular nicht unter den Händen neu bauen
            await self.laden()

    async def setzen(self, laden: bool = True, nur_seite: bool = False, **werte) -> None:
        """Zustand der Seite ändern (z. B. Haus im Zeitstrahl) und neu zeichnen.

        ``nur_seite``: reiner Filterwechsel – nur die Daten der Seite neu rechnen, nicht Zimmerplan und Aufgaben (schnell)."""
        for k, v in werte.items():
            setattr(self, k, v)
        if laden and nur_seite and self.stand is not None:
            try:
                await run.io_bound(register.SEITEN[self.seite][0], self)
                self.fehler = ""
            except Exception as exc:          # noqa: BLE001 – Fehler sichtbar machen statt leerer Seite
                log.exception("Laden fehlgeschlagen")
                self.fehler = f"Die Daten konnten nicht geladen werden: {exc}"
            self.zeichnen()
        elif laden:
            await self.laden()
        else:
            self.zeichnen()

    async def seite_wechseln(self, seite: str) -> None:
        if seite != self.seite:
            await self.oeffnen(seite)

    async def oeffnen(self, seite: str, ansicht: str | None = None, **zustand) -> None:
        """Zu einer Seite springen (Seitenleiste, Suche, Karten) – optional mit Unteransicht und Zustand."""
        karte = zustand.pop("karte", None)
        for k, v in zustand.items():
            setattr(self, k, v)
        if ansicht:
            self.ansicht[seite] = ansicht
        self.seite, self.daten = seite, None
        self.panel_zu()
        self.zeichnen()                        # sofort umschalten („Lädt …“), dann Daten
        await self.laden()
        if karte:
            from . import seite_zimmer

            await seite_zimmer.karte_oeffnen(self, karte)

    def ansicht_von(self, seite: str, standard: str) -> str:
        return self.ansicht.get(seite, standard)

    # ---- Aufbau --------------------------------------------------------------------------

    def aufbauen(self) -> None:
        ui.add_css(CSS)
        ui.add_css(themes.CSS)                 # greift nur mit body.pro – im Original-Zustand gilt allein das bisherige CSS
        self.body = ui.query("body")           # einmal holen – später auch ohne Slot-Kontext nutzbar
        self.body.classes(" ".join(["dark"] + themes.klassen(self.design)))
        with ui.element("div").classes("m-app"):
            with ui.element("nav").classes("m-nav"):
                with ui.element("div").classes("m-marke"):
                    ui.label("B").classes("m-logo")
                    ui.label("Belegung")
                self.nav = ui.element("div").classes("m-navliste")
                ui.label(f"Neue Oberfläche {__version__}\nDaten und Regeln: Belegung {haupt_version}").classes(
                    "m-navfuss").style("white-space: pre-line")
            with ui.element("div").classes("m-haupt"):
                self.topnav = ui.element("nav").classes("m-topnav")     # Showcase: schwebendes Dock
                self._prompt_bauen()                                    # AI-Canvas: zentrale Eingabe
                with ui.element("header").classes("m-kopf"):
                    self.titel = ui.label("Anreisen").classes("m-titel")
                    self.werkzeuge = ui.element("div").classes("m-werkzeuge")
                    ui.element("div").style("flex: 1")
                    knopf("", self.rueckgaengig, "leise", "undo", "Letzte Änderung zurücknehmen (Strg+Z)")
                    self.aufgaben_knopf = ui.element("button").classes("m-knopf")
                    attr(self.aufgaben_knopf, title="Aufgaben-Center (A)")
                    self.aufgaben_knopf.on("click", lambda: self.center_umschalten())
                self.leiste = ui.element("div").classes("m-leiste")
                self.inhalt = ui.element("div").classes("m-inhalt")
            self.schleier = ui.element("div").classes("m-schleier")
            self.schleier.on("click", self._schliessen)
            self.center = ui.element("aside").classes("m-center")
            attr(self.center, aria_label="Aufgaben")
        self.toolbar = ui.element("div").classes("m-tb")
        attr(self.toolbar, role="toolbar", aria_label="Darstellung")
        self._toolbar_fuellen()
        ui.add_body_html(_TOOLBAR_JS)
        from .seite_prognose import GRAPH_JS

        ui.add_body_html(GRAPH_JS)            # Prognosegraph: Reiterwechsel im Browser
        from .seite_heute import BRIEFING_JS

        ui.add_body_html(BRIEFING_JS)         # Heute: Morgen-Briefing vorlesen (Sprachausgabe des Systems)
        self.toast_box = ui.element("div")
        ui.keyboard(self._taste, ignore=["input", "select", "textarea"])   # Esc auch, wenn ein Knopf den Fokus hat
        ui.timer(PRUEF_S, self.pruefen)
        if self.design["vollbild"]:
            ui.timer(1.0, lambda: self._vollbild_nativ(True), once=True)

    def _nav_fuellen(self) -> None:
        self.nav.clear()
        dringend = sum(1 for k in self.karten if k.stufe == "dringend")
        pro = self.design["layout"] != "original"
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
                    if k == "heute" and self.karten:
                        ui.label(str(len(self.karten))).classes("m-zahl" + (" rot" if dringend else "")).style(
                            "margin-left:auto")
                p.on("click", lambda k=k: self.seite_wechseln(k))
            with ui.element("button").classes("m-navpunkt m-suche") as p:
                ui.icon("search")
                ui.label("Suchen")
                ui.label("Strg K").classes("m-taste").style("margin-left:auto")
            if pro:
                attr(p, title="Suchen (Strg+K)")
            p.on("click", self.suchen)
            if self.design["layout"] == "grid":
                schmal = self.design["schmal"]
                with ui.element("button").classes("m-navpunkt m-navklapp") as k:
                    ui.icon("keyboard_double_arrow_left")
                    ui.label("Leiste einklappen")
                attr(k, title="Leiste ausklappen (Strg+B)" if schmal else "Leiste einklappen (Strg+B)")
                k.on("click", lambda: self.design_setzen(schmal=not schmal))
        self._topnav_fuellen(dringend)

    def _topnav_fuellen(self, dringend: int) -> None:
        """Showcase-Dock: alle Seiten direkt sichtbar, „Verwalten“ als Dropdown – kein Menüpunkt fällt weg."""
        self.topnav.clear()
        if self.design["layout"] != "showcase":
            return
        with self.topnav:
            with ui.element("div").classes("m-marke"):
                ui.label("B").classes("m-logo")
            gruppen = {}
            for k, text, icon, g in register.NAV:
                gruppen.setdefault(g, []).append((k, text, icon))
            for g, punkte in gruppen.items():
                if g == "Verwalten":
                    continue
                if g:
                    ui.element("div").classes("m-trenner")
                for k, text, icon in punkte:
                    p = ui.element("button").classes("m-navpunkt" + (" aktiv" if k == self.seite else ""))
                    attr(p, title=text)
                    with p:
                        ui.icon(icon)
                        ui.label(text)
                        if k == "heute" and self.karten:
                            ui.label(str(len(self.karten))).classes("m-zahl" + (" rot" if dringend else ""))
                    p.on("click", lambda k=k: self.seite_wechseln(k))
            verwalten = [x for x in register.NAV if x[3] == "Verwalten"]
            ui.element("div").classes("m-trenner")
            aktiv = any(k == self.seite for k, *_r in verwalten)
            with ui.element("button").classes("m-navpunkt" + (" aktiv" if aktiv else "")) as v:
                ui.icon("tune")
                ui.label("Verwalten")
                ui.icon("expand_more")
                with ui.menu().props('dark class="m-menue"'):
                    for k, text, icon, _g in verwalten:
                        with ui.menu_item(on_click=lambda k=k: self.seite_wechseln(k)).classes("m-mpunkt"):
                            ui.icon(icon).classes("m-mhaken" + (" an" if k == self.seite else ""))
                            ui.label(text)
            attr(v, title="Daten & Import, Inventar, Einstellungen")
            with ui.element("button").classes("m-navpunkt m-suche") as p:
                ui.icon("search")
                ui.label("Suchen")
                ui.label("Strg K").classes("m-taste")
            p.on("click", self.suchen)

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

    # ---- Darstellung: Layout, Theme, Hell/Dunkel, Dichte, Vollbild, Notiz -----------------

    def _toolbar_fuellen(self) -> None:
        d = self.design
        original = d["layout"] == "original"
        self.toolbar.clear()

        def k(icon: str, titel: str, klick=None, extra: str = ""):
            b = ui.element("button").classes(f"m-tb-k {extra}".strip())
            attr(b, title=titel, aria_label=titel)
            with b:
                ui.icon(icon)
            if klick:
                b.on("click", klick)
            return b

        def punkt(text: str, unter: str, an: bool, klick, aus: bool = False):
            item = ui.menu_item(on_click=klick).classes("m-mpunkt")
            if aus:
                item.props("disable")
            with item:
                ui.icon("radio_button_checked" if an else "radio_button_unchecked").classes("m-mhaken" + (" an" if an else ""))
                with ui.element("div"):
                    ui.label(text)
                    if unter:
                        ui.label(unter).classes("m-zweite").style("white-space:normal; max-width:280px")

        with self.toolbar:
            griff = k("tune", "Darstellung – Leiste anheften/lösen", extra="m-tb-griff")
            griff.on("click", js_handler="() => document.querySelector('.m-tb')?.classList.toggle('fest')")
            with k("space_dashboard", "Layout"):
                with ui.menu().props('class="m-tb-menue" anchor="top right" self="bottom right"'):
                    ui.label("Layout").classes("m-mgruppe")
                    for key, (name, text, _i) in themes.LAYOUTS.items():
                        punkt(name, text, d["layout"] == key, lambda key=key: self.design_setzen(layout=key))
            with k("palette", "Theme (Farben)"):
                with ui.menu().props('class="m-tb-menue" anchor="top right" self="bottom right"'):
                    ui.label("Theme" + (" – wechselt ins Classic Grid" if original else "")).classes("m-mgruppe")
                    for key, (name, text, _m) in themes.THEMES.items():
                        punkt(name, text, not original and d["theme"] == key, lambda key=key: self.design_setzen(theme=key))
            zwei = len(themes.modi(d["theme"])) > 1 and not original
            k("dark_mode" if d["modus"] == "hell" else "light_mode",
              ("Dunkel" if d["modus"] == "hell" else "Hell") if zwei else "Hell/Dunkel – im Original bzw. Original-Theme nicht verfügbar",
              (lambda: self.design_setzen(modus="dunkel" if d["modus"] == "hell" else "hell")) if zwei else None,
              "" if zwei else "aus")
            k("density_small" if d["dichte"] == "normal" else "density_medium",
              ("Kompakt (mehr Zeilen)" if d["dichte"] == "normal" else "Normale Dichte") if not original else "Dichte – im Original nicht verfügbar",
              (lambda: self.design_setzen(dichte="kompakt" if d["dichte"] == "normal" else "normal")) if not original else None,
              ("an" if d["dichte"] == "kompakt" else "") if not original else "aus")
            ui.element("div").classes("m-tb-t")
            k("search", "Suchen / Prompt (Strg+K)", self.suchen)
            k("fullscreen_exit" if d["vollbild"] else "fullscreen", "Vollbild beenden" if d["vollbild"] else "Vollbild",
              self.vollbild_umschalten, "an" if d["vollbild"] else "")
            with k("sticky_note_2", "Notiz", extra="an" if d["notiz"].strip() else ""):
                with ui.menu().props('class="m-tb-menue" anchor="top right" self="bottom right"'):
                    with ui.element("div").classes("m-tb-notiz"):
                        ui.label("Schnelle Notiz – bleibt gespeichert").classes("m-mgruppe").style("padding:0")
                        notiz = ui.textarea(value=d["notiz"], placeholder="z. B. Rückruf Hausmeister wegen 2-408 …").props(
                            "dark outlined autogrow")
                        notiz.on("blur", lambda: self._notiz_speichern(notiz.value or ""))
            ui.element("div").classes("m-tb-t")
            k("restart_alt", "Original-Zustand – bisheriges Design und Layout (1 Klick)",
              lambda: self.design_setzen(**{**themes.STANDARD, "notiz": self.design["notiz"]}), "reset" + (" aus" if original else ""))

    async def _notiz_speichern(self, text: str) -> None:
        if text == self.design["notiz"]:
            return
        self.design["notiz"] = text
        try:
            await run.io_bound(kern.design_setzen, self.design)
        except Exception:                      # noqa: BLE001
            log.exception("Notiz nicht gespeichert")

    def _vollbild_nativ(self, an: bool) -> bool:
        """Vollbild im eigenen Fenster (pywebview). False = kein natives Fenster (dann der Browser)."""
        fenster = getattr(app.native, "main_window", None)
        if fenster is None:
            return False
        try:
            fenster.toggle_fullscreen()
            return True
        except Exception:                      # noqa: BLE001
            return False

    async def vollbild_umschalten(self) -> None:
        an = not self.design["vollbild"]
        if not self._vollbild_nativ(an):
            ui.run_javascript("document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()")
        await self.design_setzen(vollbild=an)

    async def design_setzen(self, **aenderung) -> None:
        """Layout/Theme/Hell-Dunkel/Dichte/schmale Leiste sofort umschalten – nur Klassen am <body>, nichts wird neu
        geladen (keine Eingabe geht verloren). Diagramme und Canvas werden neu gezeichnet."""
        alt = dict(self.design)
        neu = {**self.design, **aenderung}
        if "theme" in aenderung and aenderung.get("layout") != "original":
            if neu["layout"] == "original":
                neu["layout"] = "grid"             # ein Theme gibt es nur in den neuen Layouts
            if "modus" not in aenderung:
                neu["modus"] = themes.THEMES[aenderung["theme"]][2]
        if "layout" in aenderung and aenderung["layout"] != "original" and alt["layout"] == "original" and "theme" not in aenderung:
            neu["theme"] = "original"
        if aenderung.get("layout") == "original":
            neu["theme"] = "original"
            if alt["vollbild"] and "vollbild" in aenderung and not aenderung["vollbild"]:
                if not self._vollbild_nativ(False):
                    ui.run_javascript("document.fullscreenElement && document.exitFullscreen()")
        self.design = themes.bereinigen(neu)
        themes.AKTIV = self.design
        self.body.classes(remove=" ".join(themes.ALLE_KLASSEN))
        if themes.klassen(self.design):
            self.body.classes(add=" ".join(themes.klassen(self.design)))
        self._toolbar_fuellen()
        if self.design["layout"] != "canvas" and self.prompt:
            self.prompt_eingabe.set_value("")
            self.prompt, self._antwort = "", None
        farben_neu = (alt["layout"], alt["theme"], alt["modus"]) != (self.design["layout"], self.design["theme"], self.design["modus"])
        if alt["layout"] != self.design["layout"] or (farben_neu and self.seite == "auswertung") or self.seite == "einstellungen":
            self.zeichnen()
        else:
            self._nav_fuellen()
        try:
            await run.io_bound(kern.design_setzen, self.design)
        except Exception:                      # noqa: BLE001 – Merken ist Komfort, Umschalten klappt trotzdem
            log.exception("Darstellung nicht gespeichert")

    # ---- Zeichnen ------------------------------------------------------------------------

    def _praesentation(self) -> bool:
        return self.aw_modus == "praes" and self.seite == "auswertung" and self.ansicht_von("auswertung", "lage") == "prognose"

    def zeichnen(self) -> None:
        if self.aw_modus == "praes" and not self._praesentation():   # Seite verlassen → Präsentation endet
            self.aw_modus = "analyse"
            self.body.classes(remove="praesentation")
        self._nav_fuellen()
        self._aufgaben_knopf()
        for c in (self.werkzeuge, self.leiste, self.inhalt):
            c.clear()
        titel = register.TITEL[self.seite]
        self.titel.set_text(titel)
        if self.design["layout"] == "canvas" and self.prompt.strip() and self._antwort is not None:
            self._canvas_zeichnen()
        elif self.fehler:
            with self.inhalt:
                leer(self.fehler)
        elif self.stand is None or (self.daten is None and (self.seite != "anreisen"
                                                            or self.ansicht_von("anreisen", "zuteilen") != "zuteilen")):
            with self.inhalt:
                leer("Lädt …")
        elif self.seite == "anreisen":
            self._anreisen()
        else:
            register.SEITEN[self.seite][1](self)
        self.leiste.set_visibility(bool(self.leiste.default_slot.children))
        if self.panel_def is None:
            self._center()

    def _aufgaben_knopf(self) -> None:
        self.aufgaben_knopf.clear()
        dringend = sum(1 for k in self.karten if k.stufe == "dringend")
        with self.aufgaben_knopf:
            ui.icon("inbox")
            ui.label("Aufgaben")
            ui.label(str(len(self.karten))).classes("m-zahl" + (" rot" if dringend else ""))

    # ---- Seite Anreisen ------------------------------------------------------------------

    def _anreisen(self) -> None:
        seite_anreisen.werkzeuge(self)
        ansicht = self.ansicht_von("anreisen", "zuteilen")
        if ansicht == "abreisen":
            return seite_anreisen.abreisen_zeichnen(self)
        if ansicht == "eintragen":
            return seite_anreisen.eintragen_zeichnen(self)
        if ansicht == "personen":
            return seite_anreisen.personen_zeichnen(self)
        with self.werkzeuge:
            optionen = {a.kennung: a.text for a in self.anreisen}
            # Sprung mit neuer Anreise (z. B. aus dem Canvas): vor dem Laden ist sie evtl. noch nicht in der Liste
            wahl = ui.select(optionen, value=self.kennung if self.kennung in optionen else None,
                             on_change=self._anreise_gewaehlt).classes("m-zimmer").props(
                'dense outlined dark options-dense popup-content-class="m-popup"')
            wahl.style("min-width: 220px; width: 400px; flex: 0 1 auto")
            knopf("", lambda: self._schritt(-1), "leise", "chevron_left", "Vorherige Anreise")
            knopf("", lambda: self._schritt(1), "leise", "chevron_right", "Nächste Anreise")
        seite_anreisen.mehr_menue(self)
        if self.ohne_daten:
            with self.inhalt:
                from belegung import konfig

                leer("Keine Daten gefunden – kein Gebäudeplan und keine Anreiselisten.\n"
                     f"Datenordner: {konfig.datenordner()}\n"
                     "Der Ordner modern_ui muss im Programmordner INNternat liegen (dort, wo Start.bat und die Daten sind).")
            return
        if self.kennung:
            tag = date.fromisoformat(self.kennung)
            k = kern.kennzahlen(self.stand, tag)
            n = kern.zaehlen(self.zeilen)
            with self.leiste:
                # links: die Personen dieser Anreise (Filter) – rechts: Zimmer am Anreisetag (Sprung zur Übersicht)
                n_neu = sum(1 for z in self.zeilen if z.schluessel in self.neu)
                kennzahlen([("alle", n["alle"], "Personen", "neutral"), ("handeln", n["handeln"], "Handlungsbedarf", "krit"),
                            ("ohne", n["ohne"], "ohne Zimmer", "akzent"), ("maengel", n["maengel"], "Mängel", "warn"),
                            ("neu", n_neu, "neu (7 Tage)", "blau")],
                           self.filter, lambda f: self._filtern("alle" if f == self.filter else f),
                           {"neu": "Personen, die in den letzten 7 Tagen in die Listen gekommen sind"})
                ui.element("div").classes("m-trennlinie")
                zimmer = [("frei", k["frei"], f"frei am {tag:%d.%m.}", "ok"), ("belegt", k["belegt"], "belegt", "blau"),
                          ("gesperrt", k["gesperrt"], "gesperrt", "neutral")]
                np_ = getattr(self, "np", None)
                if np_ and np_.tiefst:
                    text, frei, stufe = np_.tiefst
                    zimmer.append(("np", frei, f"nach Planung · {text.split(' · ')[0]}", {"ok": "ok", "knapp": "warn", "kritisch": "krit"}[stufe]))
                kennzahlen(zimmer, None, lambda k: self.oeffnen("auswertung", ansicht="zimmer") if k == "np" else
                           self.oeffnen("zimmer", ansicht="uebersicht", zu_tag=tag, zu_filter=k),
                           {"np": "Mindestens so viele Zimmer bleiben frei, wenn alle Anreisen der nächsten 12 Wochen ein "
                                  "Zimmer hätten – Klick: alle Wochen",
                            "frei": "Klick: diese Zimmer in der Übersicht", "belegt": "Klick: diese Zimmer in der Übersicht",
                            "gesperrt": "Klick: diese Zimmer in der Übersicht"})
                offen = [z for z in self.zeilen if z.vorschlag and z.status in ("ohne", "handeln")]
                if offen:
                    knopf(f"Alle {len(offen)} Vorschläge übernehmen" if len(offen) > 1 else "Vorschlag übernehmen",
                          self._alle_vorschlaege, "gruen", "done_all").style("margin-left:auto")
        with self.inhalt:
            if not self.kennung:
                leer("Keine Anreisen ab heute in den Listen.")
                return
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("", "Name", "Gruppe", "Zeitraum", "Zimmer", "Hinweis"):
                    ui.label(t)
            sichtbar = [z for z in self.zeilen if z.filter(self.filter, self.neu)]
            if not sichtbar:
                leer("Nichts in diesem Filter – alles in Ordnung.")
            for z in sichtbar:
                self._zeile(z)

    def _zeile(self, z: kern.Zeile) -> None:
        with ui.element("div").classes("m-raster m-zeile"):
            with ui.element("div"):
                ui.element("div").classes(f"m-ampel {z.stufe}")
            with ui.element("div"):
                with ui.element("div").classes("m-namezeile"):
                    n = attr(ui.label(z.name).classes("m-name m-link"), title="Angaben zur Person (Geschlecht, Tier, Abreise …)")
                    n.on("click", lambda z=z: seite_anreisen.person_panel(self, z.schluessel))
                    if z.schluessel in self.neu:
                        badge_neu(self.neu[z.schluessel])
                if z.zweite:
                    ui.label(z.zweite).classes("m-zweite")
            ui.label(z.gruppe).classes("m-mono")
            ui.label(z.zeitraum).classes("m-mono")
            with ui.element("div"):
                optionen = {o.zimmer: ("✓ " if o.art == "vorschlag" else "") + o.text for o in z.optionen}
                konflikt = z.status == "handeln" and z.stufe == "krit"
                popup = "m-popup" + (" m-mitvorschlag" if z.vorschlag else "")
                s = ui.select(optionen, value=z.gespeichert,
                              on_change=lambda e, z=z: self._zimmer_gewaehlt(z, e.value)).classes(
                    "m-zimmer" + (" konflikt" if konflikt else "") + ("" if z.gespeichert else " offen")).props(
                    f'dense outlined dark options-dense popup-content-class="{popup}" placeholder="kein Zimmer"')
                attr(s, aria_label=f"Zimmer für {z.name}")
                s.style("width: 100%")
            with ui.element("div").classes(f"m-hinweis {z.stufe if z.status != 'ok' else ''}"):
                if z.vorschlag and z.status in ("ohne", "handeln"):
                    knopf(f"{kern.kurz(z.vorschlag)} nehmen", lambda z=z: self._zimmer_gewaehlt(z, z.vorschlag),
                          "gruen", "check", "Grüner Vorschlag: frei und passend")
                text = z.grund if z.status not in ("ok", "ohne") or not z.vorschlag else ""
                if z.maengel:
                    text = (text + " · " if text else "") + f"Mängel: {z.maengel}"
                if text:
                    attr(ui.label(text).classes("t"), title=text)

    # ---- Panel rechts: Aufgaben oder Formular --------------------------------------------

    def _schliessen(self) -> None:
        if self.panel_def is not None:
            self.panel_zu()
        else:
            self.center_umschalten(False)

    def _schleier_setzen(self) -> None:
        self.schleier.classes(add="offen" if self.center_offen else "", remove="" if self.center_offen else "offen")

    def _center(self) -> None:
        self.center.clear()
        self.center.classes(add="offen" if self.center_offen else "", remove="" if self.center_offen else "offen")
        self._schleier_setzen()
        with self.center:
            with ui.element("div").classes("m-ckopf"):
                ui.label("Aufgaben").classes("m-titel")
                ui.label(str(len(self.karten))).classes("m-zahl")
                knopf("", lambda: self.center_umschalten(False), "leise", "close", "Schließen (Esc)")
            with ui.element("div").classes("m-cinhalt"):
                if not self.karten:
                    ui.label("Alles erledigt.\nNeue Aufgaben erscheinen hier von selbst.").classes("m-cleer").style(
                        "white-space: pre-line")
                for stufe, titel in STUFEN:
                    ks = [k for k in self.karten if k.stufe == stufe]
                    if ks:
                        ui.label(titel).classes("m-cgruppe")
                    for k in ks:
                        self._karte(k)

    def _karte(self, k: kern.Karte) -> None:
        pro = self.design["layout"] != "original"          # neue Layouts: „Später“ als Symbol im Kartenkopf
        with ui.element("article").classes(f"m-karte {k.stufe}"):
            with ui.element("div").classes("k1"):
                with ui.element("span").classes(f"m-ksymbol {AMPEL[k.stufe]}"):
                    ui.icon(kern.symbol(k.id))
                with ui.element("div").classes("k1t"):
                    ui.label(k.titel)
                    ui.label({"dringend": "Dringend", "bald": "Als Nächstes", "info": "Zur Info"}[k.stufe]).classes(
                        f"m-kstufe {AMPEL[k.stufe]}")
                if pro:
                    knopf("", lambda k=k: self._spaeter(k), "leise m-kspaeter", "snooze", "Später – bis morgen ausblenden")
            if k.detail:
                attr(ui.label(k.detail).classes("k2"), title=k.detail)
            with ui.element("div").classes("k3"):
                if k.aktion:
                    knopf(k.aktion.text, lambda k=k: self._karte_loesen(k), "primaer")
                if k.zweite:
                    knopf(k.zweite.text, lambda k=k: self._zeigen(k.zweite.zeigen), "")
                if k.hinweis:
                    ui.label(k.hinweis).classes("k4")
                if not pro:
                    knopf("Später", lambda k=k: self._spaeter(k), "leise", titel="Bis morgen ausblenden").style(
                        "margin-left: auto")

    def panel(self, titel: str, bauen, breit: bool = False) -> None:
        """Formular im Panel rechts (gleitet über den abgedunkelten Inhalt, Klick daneben schließt)."""
        self.panel_def = (titel, bauen)
        self.center_offen = True
        self.center.clear()
        self.center.classes(add="offen" + (" breit" if breit else ""), remove="" if breit else "breit")
        self._schleier_setzen()
        with self.center:
            with ui.element("div").classes("m-ckopf"):
                ui.label(titel).classes("m-titel")
                knopf("", self.panel_zu, "leise", "close", "Schließen (Esc)")
            with ui.element("div").classes("m-cinhalt m-formular"):
                bauen()

    def panel_zu(self) -> None:
        if self.panel_def is not None:
            self.panel_def = None
            self.center_offen = False
            self.center.classes(remove="breit")
            self._center()

    # ---- Toast ---------------------------------------------------------------------------

    def toast(self, text: str, rueck: bool = True, fehler: bool = False) -> None:
        self.toast_box.clear()
        with self.toast_box:
            with ui.element("div").classes("m-toast" + (" fehler" if fehler else "")).props('role="status"'):
                ui.label(text)
                if rueck and not fehler:
                    knopf("Rückgängig", self.rueckgaengig, icon="undo")
            ui.timer(TOAST_S, self.toast_box.clear, once=True)

    # ---- Handlungen ----------------------------------------------------------------------

    async def aendern(self, aktion, *args) -> bool:
        """Änderung im Hintergrund speichern, neu laden, Hinweis mit Rückgängig. True = gespeichert."""
        try:
            text = await run.io_bound(aktion, *args)
        except ValueError as exc:
            self.toast(str(exc), fehler=True)
            await self.laden()
            return False
        except Exception as exc:              # noqa: BLE001
            log.exception("Speichern fehlgeschlagen")
            self.toast(f"Nicht gespeichert: {exc}", fehler=True)
            await self.laden()
            return False
        await self.laden()
        self.toast(text)
        return True

    async def _zimmer_gewaehlt(self, z: kern.Zeile, zimmer: str | None) -> None:
        if not zimmer or zimmer == z.gespeichert:
            return
        await self.aendern(kern.zuweisen, z.schluessel, zimmer)

    async def _alle_vorschlaege(self) -> None:
        await self.aendern(kern.vorschlaege_uebernehmen, self.kennung, "alle")

    async def _karte_loesen(self, k: kern.Karte) -> None:
        if k.aktion.zeigen:
            self.kennung = k.aktion.zeigen
        await self.aendern(kern.ausfuehren, k.aktion.schluessel, self.heute)

    async def _spaeter(self, k: kern.Karte) -> None:
        await run.io_bound(kern.spaeter_setzen, k.id, True, self.heute)
        await self.laden()
        self.toast(f"„{k.titel}“ bis morgen ausgeblendet", rueck=False)

    async def _zeigen(self, ziel: str) -> None:
        """Zweiter Knopf einer Karte: Anreise (ISO-Datum) oder „Seite/Ansicht“ aus ``kern.ZIELE``."""
        if ziel[:4].isdigit():
            await self.oeffnen("anreisen", ansicht="zuteilen", kennung=ziel, filter="alle")
            return
        seite, _, ansicht = ziel.partition("/")
        zustand = {"zl_schnell": {"maengel"}} if ziel == "zimmer/liste" else {}
        await self.oeffnen(seite, ansicht=ansicht or None, **zustand)

    async def rueckgaengig(self) -> None:
        ok, text = await run.io_bound(kern.rueckgaengig)
        await self.laden()
        self.toast(text, rueck=False, fehler=not ok)

    async def _anreise_gewaehlt(self, e) -> None:
        if e.value and e.value != self.kennung:
            self.kennung = e.value
            await self.laden()

    async def _schritt(self, n: int) -> None:
        ks = [a.kennung for a in self.anreisen]
        if self.kennung in ks:
            i = ks.index(self.kennung) + n
            if 0 <= i < len(ks):
                self.kennung = ks[i]
                await self.laden()

    def _filtern(self, f: str) -> None:
        self.filter = f
        self.zeichnen()

    def center_umschalten(self, an: bool | None = None) -> None:
        self.panel_def = None
        self.center_offen = (not self.center_offen) if an is None else an
        self._center()

    async def _taste(self, e) -> None:
        if not e.action.keydown:
            return
        if e.modifiers.ctrl and e.key.name.lower() == "z":
            await self.rueckgaengig()
        elif e.modifiers.ctrl and e.key.name.lower() == "k":
            await self.suchen()
        elif e.modifiers.ctrl and e.key.name.lower() == "b" and self.design["layout"] == "grid":
            await self.design_setzen(schmal=not self.design["schmal"])
        elif e.key.name == "/" and self.design["layout"] == "canvas":
            self._prompt_fokus()
        elif self._praesentation() and e.key.name in ("Escape", "ArrowLeft", "ArrowRight"):
            from . import seite_prognose

            if e.key.name == "Escape":
                seite_prognose.praes_beenden(self)
            else:
                seite_prognose.praes_schritt(self, 1 if e.key.name == "ArrowRight" else -1)
        elif (e.key.name.lower() == "p" and not e.modifiers.ctrl and self.panel_def is None and self.seite == "auswertung"
              and self.ansicht_von("auswertung", "lage") == "prognose" and self.daten and self.daten.get("pg")):
            from . import seite_prognose

            seite_prognose.praes_umschalten(self)
        elif e.key.name == "Escape" and self.center_offen:
            if self.panel_def is not None:
                self.panel_zu()
            else:
                self.center_umschalten(False)
        elif e.key.name.lower() == "a" and not e.modifiers.ctrl and self.panel_def is None:
            self.center_umschalten()


_TOOLBAR_JS = """<script>
(() => {   // Werkzeugleiste: nach 3,5 s ohne Bewegung zurücknehmen (nur der Griff bleibt), bei Bewegung wieder zeigen
  let t = null;
  const wach = () => { const tb = document.querySelector('.m-tb'); if (!tb) return; tb.classList.add('wach');
    clearTimeout(t); t = setTimeout(() => tb.classList.remove('wach'), 3500); };
  ['mousemove', 'keydown', 'touchstart'].forEach(ev => document.addEventListener(ev, wach, { passive: true }));
})();
</script>"""


@app.get("/druck/{name}")
def druckansicht(name: str):
    """Druckansicht aus dem Temp-Ordner (nur eigene .html-Dateien) – wenn kein Standardbrowser geöffnet werden kann."""
    import tempfile
    from pathlib import Path

    from fastapi.responses import FileResponse, PlainTextResponse

    pfad = Path(tempfile.gettempdir()) / Path(name).name
    if pfad.suffix != ".html" or not pfad.exists():
        return PlainTextResponse("Nicht gefunden", status_code=404)
    return FileResponse(pfad, media_type="text/html")


@ui.page("/")
async def startseite() -> None:
    a = Ansicht()
    a.aufbauen()
    a.zeichnen()                               # sofort Rahmen zeigen („Lädt …“), dann Daten
    await ui.context.client.connected()
    try:
        a.weniger_bewegung = bool(await ui.run_javascript("matchMedia('(prefers-reduced-motion: reduce)').matches", timeout=3))
    except Exception:                          # noqa: BLE001 – ohne Antwort: Animation wie gewohnt
        pass
    from . import daten_kern

    eingelesen = await run.io_bound(daten_kern.ordner_importieren)   # neue Dateien in „UWT“/„Listen“ (wie das Hauptprogramm)
    await a.laden()
    if eingelesen:
        a.toast("Neu eingelesen – " + " · ".join(eingelesen[:3]) + (f" (+{len(eingelesen) - 3})" if len(eingelesen) > 3 else ""))
    if await run.io_bound(kern.automatisch_oeffnen, a.karten, a.heute) and a.seite != "heute":
        a.center_umschalten(True)              # einmal am Tag von selbst, wenn Dringendes neu ist (Heute zeigt sie schon)
