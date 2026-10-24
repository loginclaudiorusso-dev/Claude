"""Die neue Oberfläche (NiceGUI): Seitenleiste, Kopf, Aufgaben-Center rechts und die Seiten. „Anreisen“ ist hier
gebaut, die übrigen Seiten in ``seiten``. Alle Daten und Regeln kommen aus dem Hauptprogramm (``kern``)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from nicegui import run, ui

from belegung import __version__ as haupt_version

from . import __version__, kern, seiten
from .stil import CSS
from .ui_bausteine import attr, knopf, leer

log = logging.getLogger(__name__)

TOAST_S = 6
PRUEF_S = 30                # so oft wird geprüft, ob das Hauptprogramm etwas gespeichert hat
STUFEN = [("dringend", "Dringend"), ("bald", "Als Nächstes"), ("info", "Zur Info")]
AMPEL = {"dringend": "krit", "bald": "warn", "info": "ok"}
NAV = [("anreisen", "Anreisen", "flight_land")] + [(k, t, i) for k, (t, i, _d, _z) in seiten.SEITEN.items()]


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
        self.seite = "anreisen"
        self.stand = None
        self.anreisen: list[kern.Anreise] = []
        self.kennung: str | None = None
        self.zeilen: list[kern.Zeile] = []
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

    # ---- Daten ---------------------------------------------------------------------------

    def _laden(self) -> None:
        from belegung import zimmerplan as zp

        self.heute = date.today()
        self.stand = zp.laden()
        self.ohne_daten = self.stand.plan is None and not self.stand.bedarf
        self.karten = kern.karten(self.stand, self.heute)
        if self.seite == "anreisen":
            self.anreisen = kern.anreisen(self.stand, self.heute)
            if self.kennung not in {a.kennung for a in self.anreisen}:
                self.kennung = kern.erste_offene(self.anreisen)
            self.zeilen = kern.zeilen(self.stand, self.kennung, self.heute)
        else:
            seiten.SEITEN[self.seite][2](self)
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

    async def setzen(self, laden: bool = True, **werte) -> None:
        """Zustand der Seite ändern (z. B. Haus im Zeitstrahl) und neu zeichnen."""
        for k, v in werte.items():
            setattr(self, k, v)
        if laden:
            await self.laden()
        else:
            self.zeichnen()

    async def seite_wechseln(self, seite: str) -> None:
        if seite != self.seite:
            self.seite, self.daten = seite, None
            self.panel_zu()
            self.zeichnen()                    # sofort umschalten („Lädt …“), dann Daten
            await self.laden()

    # ---- Aufbau --------------------------------------------------------------------------

    def aufbauen(self) -> None:
        ui.add_css(CSS)
        ui.query("body").classes("dark")
        with ui.element("div").classes("m-app"):
            with ui.element("nav").classes("m-nav"):
                with ui.element("div").classes("m-marke"):
                    ui.label("B").classes("m-logo")
                    ui.label("Belegung")
                self.nav = ui.element("div").classes("m-navliste")
                ui.label(f"Neue Oberfläche {__version__}\nDaten und Regeln: Belegung {haupt_version}").classes(
                    "m-navfuss").style("white-space: pre-line")
            with ui.element("div").classes("m-haupt"):
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
            self.center = ui.element("aside").classes("m-center")
            attr(self.center, aria_label="Aufgaben")
        self.toast_box = ui.element("div")
        ui.keyboard(self._taste)
        ui.timer(PRUEF_S, self.pruefen)

    def _nav_fuellen(self) -> None:
        self.nav.clear()
        with self.nav:
            for i, (k, text, icon) in enumerate(NAV):
                if i == 1:
                    ui.label("Planung & Betrieb").classes("m-navgruppe")
                if k == "auswertung":
                    ui.label("Überblick").classes("m-navgruppe")
                p = ui.element("button").classes("m-navpunkt" + (" aktiv" if k == self.seite else ""))
                with p:
                    ui.icon(icon)
                    ui.label(text)
                p.on("click", lambda k=k: self.seite_wechseln(k))
            ui.label("Aufgaben").classes("m-navgruppe")
            p = ui.element("button").classes("m-navpunkt")
            with p:
                ui.icon("inbox")
                ui.label("Aufgaben-Center")
                dringend = sum(1 for k in self.karten if k.stufe == "dringend")
                if self.karten:
                    ui.label(str(len(self.karten))).classes("m-zahl" + (" rot" if dringend else "")).style("margin-left:auto")
            p.on("click", lambda: self.center_umschalten(True))

    # ---- Zeichnen ------------------------------------------------------------------------

    def zeichnen(self) -> None:
        self._nav_fuellen()
        self._aufgaben_knopf()
        for c in (self.werkzeuge, self.leiste, self.inhalt):
            c.clear()
        titel = "Anreisen" if self.seite == "anreisen" else seiten.SEITEN[self.seite][0]
        self.titel.set_text(titel)
        if self.fehler:
            with self.inhalt:
                leer(self.fehler)
        elif self.stand is None or (self.seite != "anreisen" and self.daten is None):
            with self.inhalt:
                leer("Lädt …")
        elif self.seite == "anreisen":
            self._anreisen()
        else:
            seiten.SEITEN[self.seite][3](self)
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
        with self.werkzeuge:
            wahl = ui.select({a.kennung: a.text for a in self.anreisen}, value=self.kennung,
                             on_change=self._anreise_gewaehlt).classes("m-zimmer").props(
                'dense outlined dark options-dense popup-content-class="m-popup"')
            wahl.style("min-width: 220px; width: 400px; flex: 0 1 auto")
            knopf("", lambda: self._schritt(-1), "leise", "chevron_left", "Vorherige Anreise")
            knopf("", lambda: self._schritt(1), "leise", "chevron_right", "Nächste Anreise")
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
                ui.html(f'<span class="m-kpi"><b>{k["frei"]}</b> frei<span class="m-punktt">·</span><b>{k["belegt"]}</b> '
                        f'belegt<span class="m-punktt">·</span><b>{k["gesperrt"]}</b> gesperrt'
                        f'<span class="m-punktt">·</span>am {tag:%d.%m.}</span>', sanitize=False)
                offen = [z for z in self.zeilen if z.vorschlag and z.status in ("ohne", "handeln")]
                if offen:
                    knopf(f"Alle {len(offen)} Vorschläge übernehmen" if len(offen) > 1 else "Vorschlag übernehmen",
                          self._alle_vorschlaege, "gruen", "done_all")
                with ui.element("div").classes("m-segm").props('role="group" aria-label="Filter"'):
                    for f, text in kern.FILTER.items():
                        b = ui.element("button").classes("an" if f == self.filter else "")
                        attr(b, aria_pressed=str(f == self.filter).lower())
                        with b:
                            ui.label(text)
                            ui.label(str(n[f])).classes("n")
                        b.on("click", lambda f=f: self._filtern(f))
        with self.inhalt:
            if not self.kennung:
                leer("Keine Anreisen ab heute in den Listen.")
                return
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("", "Name", "Gruppe", "Zeitraum", "Zimmer", "Hinweis"):
                    ui.label(t)
            sichtbar = [z for z in self.zeilen if z.filter(self.filter)]
            if not sichtbar:
                leer("Nichts in diesem Filter – alles in Ordnung.")
            for z in sichtbar:
                self._zeile(z)

    def _zeile(self, z: kern.Zeile) -> None:
        with ui.element("div").classes("m-raster m-zeile"):
            with ui.element("div"):
                ui.element("div").classes(f"m-ampel {z.stufe}")
            with ui.element("div"):
                attr(ui.label(z.name).classes("m-name"), title=z.name)
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

    def _center(self) -> None:
        self.center.clear()
        self.center.classes(add="offen" if self.center_offen else "", remove="" if self.center_offen else "offen")
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
        with ui.element("article").classes("m-karte"):
            with ui.element("div").classes("k1"):
                ui.element("div").classes(f"m-ampel {AMPEL[k.stufe]}")
                ui.label(k.titel)
            if k.detail:
                attr(ui.label(k.detail).classes("k2"), title=k.detail)
            with ui.element("div").classes("k3"):
                if k.aktion:
                    knopf(k.aktion.text, lambda k=k: self._karte_loesen(k), "primaer")
                if k.zweite:
                    knopf(k.zweite.text, lambda k=k: self._zeigen(k.zweite.zeigen), "")
                if k.hinweis:
                    ui.label(k.hinweis).classes("k4")
                knopf("Später", lambda k=k: self._spaeter(k), "leise", titel="Bis morgen ausblenden").style(
                    "margin-left: auto")

    def panel(self, titel: str, bauen) -> None:
        """Formular im Panel rechts (statt eines Dialogs, der die Tabelle verdeckt)."""
        self.panel_def = (titel, bauen)
        self.center_offen = True
        self.center.clear()
        self.center.classes(add="offen")
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

    async def _zeigen(self, kennung: str) -> None:
        self.kennung, self.filter = kennung, "alle"
        if self.seite != "anreisen":
            self.seite, self.daten = "anreisen", None
        await self.laden()

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
        elif e.key.name == "Escape" and self.center_offen:
            if self.panel_def is not None:
                self.panel_zu()
            else:
                self.center_umschalten(False)
        elif e.key.name.lower() == "a" and not e.modifiers.ctrl and self.panel_def is None:
            self.center_umschalten()


@ui.page("/")
async def startseite() -> None:
    a = Ansicht()
    a.aufbauen()
    a.zeichnen()                               # sofort Rahmen zeigen („Lädt …“), dann Daten
    await ui.context.client.connected()
    await a.laden()
    if a.karten and await run.io_bound(kern.automatisch_oeffnen, a.karten, a.heute):
        a.center_umschalten(True)              # einmal am Tag von selbst, wenn Dringendes neu ist
