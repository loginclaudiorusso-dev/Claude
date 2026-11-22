"""Die neue Oberfläche (NiceGUI): Seitenleiste, Kopf, Aufgaben-Center rechts und die Seiten. „Anreisen“ ist hier
gebaut, die übrigen Seiten in ``seiten``. Alle Daten und Regeln kommen aus dem Hauptprogramm (``kern``)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from nicegui import app, run, ui
from nicegui.elements.mixins.value_element import ValueElement

from belegung import __version__ as haupt_version

from . import __version__, kern, register, seite_anreisen, seite_heute, suche_palette, themes
from .stil import CSS
from . import standort_kern
from .ansicht_anreisen import AnreisenMixin               # 1.29: Teile von Ansicht (Mixins, nur verschoben)
from .ansicht_navigation import LOGO_DATEI, NavigationMixin, _logo  # noqa: F401 – _logo/LOGO_DATEI hier weiter erreichbar
from .ansicht_postfach import PostfachMixin
from .ui_bausteine import attr, knopf, leer


def knopf_zahlen(karten, ungelesen: int) -> dict:
    """0.64: Was der eine Kopf-Knopf (Aufgaben + Neuigkeiten) anzeigt – rote Zahl nur für dringende Aufgaben,
    ungelesene Neuigkeiten nur als Punkt."""
    dringend = sum(1 for k in karten if k.stufe == "dringend")
    teile = [f"{len(karten)} Aufgabe{'n' if len(karten) != 1 else ''}" + (f", davon {dringend} dringend" if dringend else "")]
    if ungelesen:
        teile.append(f"{ungelesen} neue Neuigkeit{'en' if ungelesen != 1 else ''}")
    return {"dringend": dringend, "neu": ungelesen, "tipp": "Aufgaben & Neuigkeiten (A) – " + " · ".join(teile)}

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
    from belegung import neuigkeiten as nk

    for name in aenderungen.dateien_mit_plan() + [rl.DATEI, tm.DATEI, mt.DATEI, zp.REINIGUNG_MANUELL, nk.DATEI]:
        p = speicher.pfad(name)
        erg.append(p.stat().st_mtime if p.exists() else 0)
    return tuple(erg)


class Ansicht(NavigationMixin, AnreisenMixin, PostfachMixin):
    def __init__(self) -> None:
        self.heute = date.today()
        self.seite = "heute"
        self.zurueck = None                     # 1.12: Rückweg nach einem Sprung zwischen Seiten
        self.ansicht: dict[str, str] = {}      # Unteransicht je Seite (z. B. Zimmer → Zeitstrahl)
        self.stand = None
        self.anreisen: list[kern.Anreise] = []
        self.kennung: str | None = None
        self.zeilen: list[kern.Zeile] = []
        self.neu: dict = {}                    # neue Personen (Schlüssel → erstmals gesehen)
        try:
            self.design = kern.design_lesen()
        except Exception:                      # noqa: BLE001 – im Zweifel der Original-Zustand
            self.design = themes.bereinigen({})
        themes.AKTIV = self.design
        from . import symbole as _sy

        _sy.VARIANTE["art"] = self.design.get("symbole", "fluent")
        self.prompt = ""                       # AI-Canvas: aktuelle Eingabe
        self._antwort = None
        self.filter = "alle"
        self.karten: list[kern.Karte] = []
        self.nav_zahl: dict[str, kern.NavZahl] = {}   # Zähler an den Menüpunkten (Termine, Mieter, Assistenz …)
        self.neu_liste: list[kern.Neu] = []            # Glocke: letzte Neuigkeiten …
        self.ungelesen = 0                              # … und wie viele davon ungelesen sind
        self.daten = None                      # Daten der aktuellen Seite (außer Anreisen)
        self.center_offen = False
        self.panel_def = None                  # (Titel, Baufunktion) – Formular im Panel rechts statt Aufgaben
        self.stempel: tuple = ()
        self.fehler = ""
        self.ohne_daten = False
        # Zustand der Seiten
        self.zs_haus, self.zs_tage, self.zs_haeuser = "", 28, []
        self.zs_start = self.heute - timedelta(days=self.heute.weekday())
        self.zs_modus, self.zs_flur, self.fl_wochen = "zimmer", "", 8   # Zeitstrahl: Zimmer | Flure (Abreisewellen)
        self.rg_zeitraum, self.rg_filter = "woche", "offen"
        self.rg_zimmer = ""
        self.dg_details = False                   # 0.89: „Einfach“ – Details (Diagramm-Karte) eingeblendet?                       # 0.86: Reinigungsliste nur für ein Zimmer (Klick auf den Besen)
        self.rg_von = self.rg_bis = self.heute
        self.fc_zeitraum, self.fc_filter = "sechs", "offen"          # 0.82: Facility-Checks mit Zeitraum und Filter
        self.fc_von, self.fc_bis = self.heute - timedelta(days=14), self.heute + timedelta(days=45)
        self.zl_haus, self.zl_status, self.zl_text = "", "", ""
        self.zl_schnell: set[str] = set()
        self.zl_mehr: dict = {}                # seltenere Zimmerfilter (Boden, Mangel, Renovierung, Gruppe …)
        self.zk_auswahl: set[str] = set()      # markierte Zimmer in der Liste (für „Eigenschaften setzen“)
        self.ps_filter, self.ps_text = "alle", ""
        self.iv_haus, self.iv_text, self.iv_ohne = "", "", False
        self.zu_vergangene = False             # Zuteilen: auch vergangene Anreisen (letztes Jahr) zur Auswahl
        self.ein_alle = False                  # RIOS-Daten: auch abgehakte zeigen
        self.ein_abtipp, self.ein_pos = False, 0   # 0.55: Abtipp-Modus (ein Eintrag nach dem anderen)
        self.ab_zeitraum, self.ein_tage = "heute", 14
        self.tm_tage, self.tm_monat = 30, self.heute.replace(day=1)
        self.as_text, self.as_verstanden, self.as_chat = "", [], []
        self.zu_tag = self.heute
        self.zu_filter = self.dz_filter = self.mt_filter = None
        from belegung import konfig

        self.aw_standort, self.aw_brutto, self.aw_horizont = konfig.GESAMT, False, 12   # 0.94: 12 Monate Standard
        self.aw_95, self.aw_backtest = True, False           # 1.23: 95 %-Band an (abschaltbar) – in jeder Darstellung gleich
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
        try:
            from . import regeln_kern

            regeln_kern.aktualisieren(self.stand)          # Haus 6: welche Etagen sind renoviert?
        except Exception:                      # noqa: BLE001 – Zusatz, darf das Laden nie verhindern
            log.exception("Haus-6-Regel")
        self.ohne_daten = self.stand.plan is None and not self.stand.bedarf
        self.karten = kern.karten(self.stand, self.heute)
        try:
            self.neu = kern.neue_personen(self.stand, self.heute)
        except Exception:                      # noqa: BLE001 – Merkhilfe darf nie das Laden verhindern
            self.neu = {}
        self.nav_zahl = kern.nav_zahlen(self.stand, self.heute)
        try:
            from . import historie_kern

            historie_kern.erfassen(self.stand, self.heute)      # Zimmerhistorie: wer wann wo gewohnt hat
        except Exception:                      # noqa: BLE001 – darf das Laden nie verhindern
            log.exception("Zimmerhistorie")
        try:
            self.neu_liste, self.ungelesen = kern.neuigkeiten()
        except Exception:                      # noqa: BLE001
            self.neu_liste, self.ungelesen = [], 0
        if self.seite == "anreisen" and self.ansicht_von("anreisen", "zuteilen") != "zuteilen":
            seite_anreisen.daten(self)
        elif self.seite == "anreisen":
            self.anreisen = kern.anreisen(self.stand, self.heute, self.zu_vergangene)
            if self.kennung not in {a.kennung for a in self.anreisen}:
                self.kennung = kern.erste_offene(self.anreisen)
            self.zeilen = kern.zeilen(self.stand, self.kennung, self.heute)
            try:
                self.bereit = kern.bereitschaft(self.stand, self.zeilen, date.fromisoformat(self.kennung)) if self.kennung else None
            except Exception:                  # noqa: BLE001 – Zusatzinfo darf das Zuteilen nie blockieren
                log.exception("Bereitschaft")
                self.bereit = None
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
        self._datenstand()
        if zeichnen:
            self.zeichnen()

    def _datenstand(self, extern: bool = False, wartet: bool = False) -> None:
        """„Stand 14:32“ in der Kopfzeile – wann die Daten zuletzt geladen wurden. Blinkt kurz, wenn das Hauptprogramm
        gespeichert hat; „neue Daten“, solange ein offenes Formular das Neuladen aufhält."""
        el = getattr(self, "stand_anzeige", None)
        if el is None:
            return
        if not wartet:
            self.geladen_um = datetime.now()
        um = getattr(self, "geladen_um", None) or datetime.now()
        el.set_text(f"Stand {um:%H:%M}" + (" · neue Daten" if wartet else ""))
        attr(el, title=(f"Daten zuletzt geladen um {um:%H:%M:%S}. "
                        + ("Ein anderer PC (oder das Hauptprogramm) hat inzwischen gespeichert – nach dem Schließen des Formulars wird neu geladen."
                           if wartet else f"Speichert ein anderer PC (oder das Hauptprogramm), wird innerhalb von {PRUEF_S} s neu geladen.")))
        el.classes(remove="neu warten")
        if extern or wartet:
            el.classes(add="warten" if wartet else "neu")

    async def pruefen(self) -> None:
        """Hat das Hauptprogramm (oder ein anderer PC) inzwischen gespeichert? Dann neu laden."""
        from . import netz_kern

        if not getattr(self, "_version_gemeldet", False):   # 0.54: Update im Netzwerkordner eingespielt?
            v = await run.io_bound(netz_kern.version_auf_platte)
            if v and v != __version__:
                self._version_gemeldet = True
                self.toast(f"Neue Version {v} ist eingespielt – bitte INNternat schließen und neu starten.",
                           rueck=False, dauer=120)
        try:
            neu = await run.io_bound(_stempel)
        except OSError:
            return
        if neu == self.stempel:
            return
        if self.panel_def is not None:                     # offenes Formular nicht unter den Händen neu bauen
            self._datenstand(wartet=True)
            return
        await self.laden()
        self._datenstand(extern=True)
        await self._fremd_melden()

    async def _fremd_melden(self) -> None:
        """0.54: Hat ein anderer PC gespeichert, kurz zeigen, was und von wem."""
        from . import netz_kern

        d = await run.io_bound(netz_kern.letzte_aenderung)
        if not netz_kern.von_anderem(d) or d.get("zeit") == getattr(self, "_fremd_zeit", None):
            return
        self._fremd_zeit = d.get("zeit")
        try:
            alter = (datetime.now() - datetime.fromisoformat(d["zeit"])).total_seconds()
        except (KeyError, ValueError):
            return
        if abs(alter) <= 300:
            self.toast(f"Aktualisiert: {d.get('titel', '')} – gespeichert von {d.get('wer', 'einem anderen PC')} "
                       f"um {d['zeit'][11:16]}", rueck=False)

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
        von = zustand.pop("von", None)          # 1.12: (Titel, Seite, Ansicht) – woher man gesprungen ist → „Zurück“
        self.zurueck = (*von, seite, ansicht or self.ansicht_von(seite, "")) if von else None
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

    def _zurueck_knopf(self) -> None:
        """1.12: Nach einem Sprung (z. B. Belegungsprognose → Teilnehmer je Maßnahme) steht vorne „Zurück“ – solange
        man auf der angesprungenen Seite bleibt."""
        z = getattr(self, "zurueck", None)
        if not z:
            return
        titel, seite, ansicht, ziel_seite, ziel_ansicht = z
        if self.seite != ziel_seite or self.ansicht_von(ziel_seite, "") != ziel_ansicht:
            self.zurueck = None
            return
        from . import ui_bausteine as _ub

        zurueck = lambda: self.oeffnen(seite, ansicht)          # noqa: E731
        if _ub.BAND.get("an"):
            from . import band_ui, symbole

            with self.werkzeuge, band_ui.gruppe("Zurück"):
                band_ui.gross(titel, "arrow_left", symbole.BLAU, zurueck, tipp=f"Zurück zu: {titel}")
        else:
            with self.leiste:
                knopf(f"Zurück: {titel}", zurueck, "leise", "arrow_back")

    def ansicht_von(self, seite: str, standard: str) -> str:
        return self.ansicht.get(seite, standard)

    # ---- Aufbau --------------------------------------------------------------------------

    def aufbauen(self) -> None:
        ui.add_css(CSS)
        ui.add_css(themes.CSS)                 # greift nur mit body.pro – im Original-Zustand gilt allein das bisherige CSS
        from . import menueband_ui

        ui.add_css(menueband_ui.CSS)           # 0.65: Menüband wie in Office (nur mit body.lay-office)
        from . import hilfe_ui, optionen_ui

        ui.add_css(optionen_ui.CSS)            # 0.66: Optionen-Dialog
        ui.add_css(hilfe_ui.CSS)               # 0.68: Hilfe, Drucken (auch Druck-CSS für Strg+P)
        ui.add_css(suche_palette.CSS)          # 0.71: Befehlssuche
        from . import arbeitsflaeche

        ui.add_css(arbeitsflaeche.CSS)
        from . import cockpit_ui

        ui.add_css(cockpit_ui.CSS)              # 1.16: Cockpit (neu)         # 0.74: Arbeitsfläche – Kontextzeile, feste Größen, Detailpanel
        ui.add_body_html(arbeitsflaeche.JS)
        from . import diagramm_ui

        ui.add_css(diagramm_ui.CSS)            # 0.75: Diagramme – Größe ziehen, Tabelle, ƒx Berechnung, Klick → Panel
        from . import anteile_ui

        ui.add_css(anteile_ui.CSS)             # 0.96: Anteils-Diagramme (Ring, Kreis, 100 %)
        from . import symbole as _symbole

        ui.add_css(_symbole.CSS)               # 1.00: Fluent-2-Symbole (zweifarbig)
        from . import band_ui as _band_ui

        ui.add_css(_band_ui.CSS)               # 1.00: Seiten-Werkzeuge als Office-Gruppen
        from . import seite_massnahmen as _mn_css

        ui.add_css(_mn_css.CSS)                # 1.04: Menü der Maßnahmen-Auswahl im Menüband
        from . import seite_heute as _heute_css

        ui.add_css(_heute_css.CSS)             # 0.91: Heute als eine Seite
        ui.add_body_html(diagramm_ui.JS)
        from . import bestand_ui

        ui.add_css(bestand_ui.CSS)             # 0.76: Bestandsmodell – Prüfbericht, Zuordnungstabelle
        from . import bestand_prognose_ui

        ui.add_css(bestand_prognose_ui.CSS)    # 0.79: Bestandsprognose – Planung und Leitung, Wenn-dann
        self.body = ui.query("body")           # einmal holen – später auch ohne Slot-Kontext nutzbar
        self.body.classes(" ".join(["dark"] + themes.klassen(self.design)))
        self.body.style(replace=themes.stil(self.design))            # 0.66: Akzentfarbe, Schrift, Zoom
        self.dialog_ablage = ui.element("div")                     # Dialoge, die ein Neuzeichnen überstehen
        with ui.element("div").classes("m-app"):
            with ui.element("nav").classes("m-nav"):
                self._marke_bauen()
                self.nav = ui.element("div").classes("m-navliste")
                ui.label(f"Neue Oberfläche {__version__}\nDaten und Regeln: Belegung {haupt_version}").classes(
                    "m-navfuss").style("white-space: pre-line")
            with ui.element("div").classes("m-haupt"):
                self.topnav = ui.element("nav").classes("m-topnav")     # Showcase: schwebendes Dock
                self._prompt_bauen()                                    # AI-Canvas: zentrale Eingabe
                # 0.74: Kopf + Leiste bilden zusammen die EINE Kontextzeile (im Office-Layout eine Zeile, sonst wie bisher)
                self.kontextzeile = ui.element("div").classes("m-kz")
                with self.kontextzeile, ui.element("header").classes("m-kopf"):
                    self.titel = ui.label("Anreisen").classes("m-titel")
                    self.werkzeuge = ui.element("div").classes("m-werkzeuge")
                    ui.element("div").classes("m-kz-luft").style("flex: 1")
                    self.stand_anzeige = ui.label("").classes("m-datenstand m-kopf-doppelt")   # Menüband: Statusleiste
                    knopf("", self.rueckgaengig, "leise", "undo", "Letzte Änderung zurücknehmen (Strg+Z)").classes(
                        "m-kopf-doppelt")                            # im Menüband steht beides schon oben
                    self.glocke = ui.element("span")                 # 0.64: Neuigkeiten stecken im Aufgaben-Knopf
                    self.glocke.set_visibility(False)
                    self.aufgaben_knopf = ui.element("button").classes("m-knopf m-glocke m-kopf-doppelt")
                    attr(self.aufgaben_knopf, title="Aufgaben & Neuigkeiten (A)")
                    self.aufgaben_knopf.on("click", lambda: self.center_umschalten())
                with self.kontextzeile:
                    self.leiste = ui.element("div").classes("m-leiste")
                self.inhalt = ui.element("div").classes("m-inhalt")
            self.schleier = ui.element("div").classes("m-schleier")
            self.schleier.on("click", self._schliessen)
            self._frage_bauen()
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
        ui.add_body_html(SORTIER_JS)          # alle Tabellen: Klick auf die Spaltenüberschrift sortiert
        self.toast_box = ui.element("div")
        ui.keyboard(self._taste, ignore=["input", "select", "textarea"])   # Esc auch, wenn ein Knopf den Fokus hat
        ui.timer(PRUEF_S, self.pruefen)
        if self.design["vollbild"]:
            ui.timer(1.0, lambda: self._vollbild_nativ(True), once=True)


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
            # Layout und Farben in einem Menü „Weitere Darstellungen“ – für den Alltag reicht „Original“
            with k("space_dashboard", "Weitere Darstellungen (Layout und Farben)", extra="" if original else "an"):
                with ui.menu().props('class="m-tb-menue" anchor="top right" self="bottom right"'):
                    ui.label("Weitere Darstellungen").classes("m-mgruppe")
                    ui.label("Für den Alltag reicht „Original“. Die anderen sind Alternativen zum Ausprobieren.").classes(
                        "m-zweite").style("white-space:normal; max-width:300px; padding: 0 12px 6px")
                    ui.label("Layout (Aufbau)").classes("m-mgruppe")
                    for key, (name, text, _i) in themes.LAYOUTS.items():
                        punkt(name + (" (Standard)" if key == "original" else ""), text, d["layout"] == key,
                              lambda key=key: self.design_setzen(layout=key))
                    ui.label("Farben (Theme)" + (" – wechselt auch das Layout zu Classic Grid" if original else "")).classes(
                        "m-mgruppe")
                    for key, (name, text, _m) in themes.THEMES.items():
                        punkt(name, text, not original and d["theme"] == key, lambda key=key: self.design_setzen(theme=key))
            if not original:                   # Hell/Dunkel und Dichte gibt es nur in den weiteren Darstellungen
                if len(themes.modi(d["theme"])) > 1:
                    k("dark_mode" if d["modus"] == "hell" else "light_mode", "Dunkel" if d["modus"] == "hell" else "Hell",
                      lambda: self.design_setzen(modus="dunkel" if d["modus"] == "hell" else "hell"))
                k("density_small" if d["dichte"] == "normal" else "density_medium",
                  "Kompakt (mehr Zeilen)" if d["dichte"] == "normal" else "Normale Dichte",
                  lambda: self.design_setzen(dichte="kompakt" if d["dichte"] == "normal" else "normal"),
                  "an" if d["dichte"] == "kompakt" else "")
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
        neu = {**self.design, **aenderung}            # 1.34: Layout und Theme sind fest – die Prüfung setzt sie
        if alt["vollbild"] and "vollbild" in aenderung and not aenderung["vollbild"]:
            if not self._vollbild_nativ(False):
                ui.run_javascript("document.fullscreenElement && document.exitFullscreen()")
        self.design = themes.bereinigen(neu)
        themes.AKTIV = self.design
        from . import symbole as _sy

        _sy.VARIANTE["art"] = self.design.get("symbole", "fluent")           # 1.34: Symbole klar | farbig
        self.body.classes(remove=" ".join(themes.ALLE_KLASSEN))
        if themes.klassen(self.design):
            self.body.classes(add=" ".join(themes.klassen(self.design)))
        self.body.style(replace=themes.stil(self.design))
        self._toolbar_fuellen()
        if self.design["layout"] != "canvas" and self.prompt:
            self.prompt_eingabe.set_value("")
            self.prompt, self._antwort = "", None
        diagramm = ("farbe", "farbe_eigen", "helligkeit", "faerbung", "dg_modus", "dg_typ", "dg_glatt", "dg_punkte", "dg_werte", "dg_gitter", "dg_legende", "dg_anim",
                    "dg_anteil", "dg_anteil_zeit")
        farben_neu = ((alt["layout"], alt["theme"], alt["modus"]) != (self.design["layout"], self.design["theme"], self.design["modus"])
                      or any(alt.get(k) != self.design.get(k) for k in diagramm))
        if alt.get("symbole") != self.design.get("symbole") or (farben_neu and self.seite in ("auswertung", "steuerung")) \
                or self.seite == "einstellungen":
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
        self._glocke_fuellen()
        for c in (self.werkzeuge, self.leiste, self.inhalt):
            c.clear()
        from . import menueband_ui as _mbu_z
        from . import ui_bausteine as _ub

        _ub.BAND["an"] = _mbu_z.werkzeuge_oben(self) if self.design.get("layout") == "office" else False   # 1.01
        self._zurueck_knopf()
        self.status_info = ""                   # 0.74: Zahlen der Ansicht für die Statusleiste (wie in Excel)
        titel = register.TITEL[self.seite]
        from . import menueband_ui

        self.titel.set_text(menueband_ui.seitentitel(self, titel))   # Menüband: „Auswertung · Maßnahmen“
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
        menueband_ui.fuellen(self, nach_zeichnen=True)   # 0.99: jetzt ist bekannt, ob die Seite Werkzeuge hat
        if (info := getattr(self, "_ob_info", None)) is not None:
            info.set_text(self.status_info)
        if self.panel_def is None:
            self._center()

    def _glocke_fuellen(self) -> None:
        """0.64: Keine eigene Glocke mehr – Neuigkeiten zeigt der Aufgaben-Knopf (Punkt) und das Aufgaben-Center."""
        self._aufgaben_knopf()
        if self.center_offen and self.panel_def is None:
            self._center()

    def _neuigkeiten_panel(self) -> None:
        """Glocke: letzte Neuigkeiten (gemeinsam mit dem Hauptprogramm); ungelesene hervorgehoben, Klick öffnet das Ziel."""
        async def oeffnen(n: kern.Neu):
            if not n.gelesen:
                await run.io_bound(kern.neu_gelesen, n.id)
            if n.seite:
                await self.oeffnen(n.seite, n.ansicht or None)
            else:
                await self._neu_aktualisieren()

        async def alle_gelesen():
            await run.io_bound(kern.neu_gelesen, None)
            await self._neu_aktualisieren()

        def bauen():
            if not self.neu_liste:
                leer("Keine Neuigkeiten.")
                return
            with ui.element("div").classes("m-paktionen"):
                if self.ungelesen:
                    knopf(f"Alle als gelesen markieren ({self.ungelesen})", alle_gelesen, "", "done_all")
            for n in self.neu_liste:
                with ui.element("button").classes("m-neu" + ("" if n.gelesen else " ungelesen") + f" {n.art}") as b:
                    ui.element("span").classes("m-neu-punkt")
                    with ui.element("div").classes("m-neu-text"):
                        ui.label(n.text)
                        ui.label(n.zeit + (" · öffnen" if n.seite else "")).classes("m-zweite")
                b.on("click", lambda n=n: oeffnen(n))

        self.panel("Neuigkeiten", bauen)

    async def _neu_aktualisieren(self) -> None:
        self.neu_liste, self.ungelesen = await run.io_bound(kern.neuigkeiten)
        self._glocke_fuellen()
        if self.panel_def and self.panel_def[0] == "Neuigkeiten":
            self._neuigkeiten_panel()

    def _aufgaben_knopf(self) -> None:
        self.aufgaben_knopf.clear()
        z = knopf_zahlen(self.karten, self.ungelesen)
        with self.aufgaben_knopf:
            ui.icon("inbox")
            ui.label("Aufgaben")
            if z["dringend"]:                                   # 0.64: rote Zahl nur für Dringendes
                ui.label(str(z["dringend"])).classes("m-zahl rot")
            elif z["neu"]:
                ui.element("span").classes("m-neu-marke")
        attr(self.aufgaben_knopf, title=z["tipp"])


    # ---- Panel rechts: Aufgaben oder Formular --------------------------------------------

    def _schliessen(self) -> None:
        if self.panel_def is not None:
            self.panel_schliessen()
        else:
            self.center_umschalten(False)

    # ---- Formular-Schutz: nichts geht beim Schließen still verloren ------------------------

    def _werte(self) -> dict:
        return {el.id: el.value for el in self.center.descendants() if isinstance(el, ValueElement)}

    def panel_geaendert(self) -> bool:
        """Wurde im offenen Panel etwas eingegeben/angehakt, das noch nicht gespeichert ist?"""
        if self.panel_def is None:
            return False
        if self._panel_geaendert:
            return True
        jetzt = self._werte()
        return any(k in jetzt and jetzt[k] != v for k, v in self._panel_werte.items())

    def panel_schliessen(self) -> None:
        """Schließen durch Esc, ✕ oder Klick daneben – mit Eingaben erst nachfragen. (Nach dem Speichern: ``panel_zu``.)"""
        if self.panel_geaendert():
            self.frage.open()
        else:
            self.panel_zu()

    def _frage_bauen(self) -> None:
        with ui.dialog().props("no-esc-dismiss") as self.frage, ui.element("div").classes("m-frage"):
            attr(self.frage, role="alertdialog")
            ui.label("Eingaben verwerfen?").classes("m-titel")
            ui.label("Im Formular wurde etwas eingegeben, das noch nicht gespeichert ist.").classes("m-ptext")
            with ui.element("div").classes("m-paktionen"):
                knopf("Weiter bearbeiten", self.frage.close, "primaer")
                knopf("Verwerfen", self._verwerfen, "", "delete_outline")

    def _verwerfen(self) -> None:
        self.frage.close()
        self.panel_zu()

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
                ui.element("div").style("flex: 1")
                knopf(f"Neuigkeiten ({self.ungelesen} neu)" if self.ungelesen else "Neuigkeiten", self._neuigkeiten_panel,
                      "leise", "notifications" if self.ungelesen else "notifications_none",
                      "Letzte Neuigkeiten aus dem Programm und dem Hauptprogramm")
                knopf("", lambda: self.center_umschalten(False), "leise", "close", "Schließen (Esc)")
            with ui.element("div").classes("m-cinhalt"):
                if not self.karten:
                    ui.label("Keine offenen Aufgaben.\nNeue Aufgaben erscheinen hier automatisch.").classes("m-cleer").style(
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
                d = attr(ui.label(k.detail).classes("k2"), title=k.detail)
                if self._hat_details(k):                        # Klick zeigt alle Fälle, nicht nur die ersten
                    d.classes(add="m-klickbar")
                    attr(d, title=k.detail + "\n\nKlick: alle anzeigen")
                    d.on("click", lambda k=k: self._karte_details(k))
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
        """Formular im Panel rechts (gleitet über den abgedunkelten Inhalt, Klick daneben schließt). Im Postfach auf
        *Heute* erscheint es stattdessen direkt in der rechten Spalte."""
        if (ziel := getattr(self, "_pf_ziel", None)) is not None:
            self._pf_ziel = None
            ziel.clear()
            with ziel, ui.element("div").classes("m-formular m-pf-inhalt"):
                bauen()
            for el in ziel.descendants():           # „Schließen“/„Abbrechen“ gibt es im Postfach nicht
                if isinstance(el, ui.label) and el.text in ("Schließen", "Abbrechen") and el.parent_slot \
                        and "m-knopf" in el.parent_slot.parent.classes:
                    el.parent_slot.parent.set_visibility(False)
            return
        weiter = self.panel_def is not None and self.panel_def[0] == titel and self.panel_geaendert()
        self.panel_def = (titel, bauen)
        self.center_offen = True
        self.center.clear()
        self.center.classes(add="offen" + (" breit" if breit else ""), remove="" if breit else "breit")
        self._schleier_setzen()
        with self.center:
            with ui.element("div").classes("m-ckopf"):
                ui.label(titel).classes("m-titel")
                knopf("", self.panel_schliessen, "leise", "close", "Schließen (Esc)")
            with ui.element("div").classes("m-cinhalt m-formular"):
                bauen()
        self._panel_werte, self._panel_geaendert = self._werte(), weiter    # neu gezeichnet (z. B. nach „Prüfen“): bleibt geändert

    def panel_zu(self) -> None:
        if self.panel_def is not None:
            self.panel_def = None
            self.center_offen = False
            self.center.classes(remove="breit")
            self._center()

    # ---- Toast ---------------------------------------------------------------------------

    def toast(self, text: str, rueck: bool = True, fehler: bool = False, extra: tuple | None = None,
              dauer: int = TOAST_S) -> None:
        """Kurzer Hinweis unten; ``extra`` = (Text, Klick) für einen zusätzlichen Knopf, z. B. „Was hat sich geändert?“."""
        self.toast_box.clear()
        with self.toast_box:
            with ui.element("div").classes("m-toast" + (" fehler" if fehler else "")).props('role="status"'):
                if not fehler and self.design.get("layout", "original") != "original":
                    ui.icon("check_circle").classes("m-toast-ok")      # Haptik: die Bestätigung rastet ein
                ui.label(text)
                if extra:
                    knopf(extra[0], lambda: (self.toast_box.clear(), extra[1]()), "primaer")
                if rueck and not fehler:
                    knopf("Rückgängig", self.rueckgaengig, icon="undo")
            ui.timer(dauer, self.toast_box.clear, once=True)

    # ---- Handlungen ----------------------------------------------------------------------

    async def aendern(self, aktion, *args) -> bool:
        """Änderung im Hintergrund speichern, neu laden, Hinweis mit Rückgängig. True = gespeichert."""
        self.body.classes(add="m-arbeitet")       # Haptik: oben läuft ein Balken, bis gespeichert ist (nur in den Layouts)
        try:
            return await self._aendern(aktion, *args)
        finally:
            self.body.classes(remove="m-arbeitet")

    async def _aendern(self, aktion, *args) -> bool:
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

    @staticmethod
    def _hat_details(k: kern.Karte) -> bool:
        return k.id in ("unbewohnbar", "konflikte", "allergie", "strittig", "fm") or bool(k.zweite) or bool(k.aktion and k.aktion.zeigen)

    async def _karte_details(self, k: kern.Karte) -> None:
        if k.id in ("unbewohnbar", "konflikte"):
            await self._faelle_panel(k.id == "unbewohnbar")
        elif k.id == "allergie":
            await self._allergie_panel()
        elif k.id == "strittig":
            await self._strittig_panel()
        elif k.id == "fm":
            await self._fm_panel()
        elif k.zweite:
            await self._zeigen(k.zweite.zeigen)
        elif k.aktion and k.aktion.zeigen:
            await self._zeigen(k.aktion.zeigen)

    # ---- Postfach auf „Heute“: Fälle der gewählten Aufgabe rechts ---------------------------

    PF_LISTEN = ("unbewohnbar", "konflikte", "allergie", "strittig", "fm")


    async def _karte_loesen(self, k: kern.Karte) -> None:
        if k.aktion.schluessel.startswith("ausweich:"):          # 0.91: ein Fall, ein Klick
            await self.aendern(kern.ausweich_uebernehmen, [k.aktion.schluessel.split(":", 1)[1]], self.heute)
            return
        if k.aktion.schluessel == "strittig":
            await self._strittig_panel()
            return
        if k.aktion.schluessel == "fm":
            await self._fm_panel()
            return
        if k.aktion.schluessel == "konflikte":                  # erst prüfen, dann nur das Angehakte umplanen
            await self._faelle_panel(k.id == "unbewohnbar")
            return
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
        if e.modifiers.ctrl and e.modifiers.shift and e.key.name.lower() == "f":   # 0.96: Bildschirmfoto
            from . import menueband_ui

            await menueband_ui.bildschirmfoto(self)
            return
        if (extra := getattr(self, "_extra_taste", None)) is not None and await extra(e):
            return
        if e.modifiers.ctrl and e.key.name.lower() == "z":
            await self.rueckgaengig()
        elif e.modifiers.ctrl and e.key.name.lower() == "k":
            await self.suchen()
        elif e.key.name == "F1" and e.modifiers.ctrl and self.design["layout"] == "office":   # 0.74: wie Office
            await self.design_setzen(band_zu=not self.design.get("band_zu"))
        elif e.key.name == "F1":                                         # 0.68: Hilfe zur offenen Seite
            from . import hilfe_ui

            hilfe_ui.oeffnen(self)
        elif e.modifiers.ctrl and e.key.name.lower() == "b" and self.design["layout"] == "showcase":
            await self.design_setzen(dock_fest=not self.design["dock_fest"])
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
        elif (e.key.name in ("ArrowDown", "ArrowUp") and self.seite == "heute" and self.panel_def is None
              and not self.center_offen and getattr(self, "pf_schritt", None) and seite_heute.postfach_an(self)):
            self.pf_schritt(1 if e.key.name == "ArrowDown" else -1)
        elif e.key.name == "Escape" and self.frage.value:
            self.frage.close()                   # Esc in der Rückfrage = weiter bearbeiten
        elif e.key.name == "Escape" and self.center_offen:
            if self.panel_def is not None:
                self.panel_schliessen()
            else:
                self.center_umschalten(False)
        elif (self.panel_def is None and not e.modifiers.ctrl and not e.modifiers.alt and getattr(self, "tasten", None)
              and self.tasten[0]() and e.key.name.lower() in self.tasten[1]):
            # 0.58: Ein-Tasten-Kürzel der gerade offenen Ansicht (Postfach, Abtipp-Modus) – nie in Eingabefeldern
            import inspect

            erg = self.tasten[1][e.key.name.lower()]()
            if inspect.isawaitable(erg):
                await erg
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


SORTIER_JS = r"""<script>
(() => {   // Tabellen sortieren: Klick auf eine Spaltenüberschrift → aufsteigend, nochmal → absteigend, nochmal → wie vorher.
  // Nur Darstellung (CSS „order“), die Zeilen bleiben im DOM, wo sie sind – das Neuzeichnen der Seite stört nicht.
  let zustand = {};
  try { zustand = JSON.parse(sessionStorage.getItem('mSort') || '{}'); } catch (e) { zustand = {}; }
  const merken = () => { try { sessionStorage.setItem('mSort', JSON.stringify(zustand)); } catch (e) {} };
  const sig = (kopf) => [...kopf.children].map(c => c.innerText.trim()).join('|');
  const schluessel = (t) => {
    t = (t || '').trim();
    if (!t || t === '–' || t === '—') return [2, ''];
    const ds = [...t.matchAll(/(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})?/g)].slice(0, 2).map(d => {
      const tg = +d[1], m = +d[2], h = new Date();
      let j = d[3] ? +d[3] : h.getFullYear();
      if (d[3] && j < 100) j += 2000;
      if (!d[3]) { const x = new Date(j, m - 1, tg); if (x - h < -182 * 864e5) j++; else if (x - h > 182 * 864e5) j--; }
      return j * 10000 + m * 100 + tg;
    });
    if (ds.length) return [0, ds[0] * 1e8 + (ds[1] || 0)];     // Zeitraum: erst Beginn, dann Ende
    const n = t.replace(/\s/g, '').replace(',', '.').replace(/[%€]$/, '');
    if (/^-?\d+(\.\d+)?$/.test(n)) return [0, parseFloat(n)];
    return [1, t];
  };
  const zellText = (el) => {   // ohne die Namen der Symbole (Material-Icons stehen als Text im Element)
    if (!el) return '';
    let t = el.innerText;
    el.querySelectorAll('.q-icon, .material-icons').forEach(ic => { const x = ic.innerText.trim(); if (x) t = t.replace(x, ''); });
    return t;
  };
  const vergleich = (a, b) => (typeof a[1] === 'number' && typeof b[1] === 'number') ? a[1] - b[1]
    : String(a[1]).localeCompare(String(b[1]), 'de', { numeric: true, sensitivity: 'base' });
  // Zeilen einer Tabelle = die Zeilen direkt unter ihrer Kopfzeile, bis etwas anderes kommt (mehrere Tabellen untereinander,
  // z. B. „Defekte Zimmer“ je Dringlichkeit, sortieren jede für sich)
  const zeilenVon = (kopf) => {
    const k = [...kopf.parentElement.children], erg = [];
    for (let j = k.indexOf(kopf) + 1; j < k.length && k[j].classList.contains('m-zeile'); j++) erg.push(k[j]);
    return erg;
  };
  const kopfMarken = (kopf, sp, ri, ok) => [...kopf.children].forEach((c, i) => {
    c.classList.toggle('m-sort-auf', ri === 1 && i === sp); c.classList.toggle('m-sort-ab', ri === -1 && i === sp);
    if (!c.innerText.trim()) return;
    if (ok) {   // per Tab erreichbar, Enter/Leertaste sortiert; Bildschirmleser hören Spalte und Richtung
      if (c.getAttribute('tabindex') !== '0') c.setAttribute('tabindex', '0');
      if (c.getAttribute('role') !== 'columnheader') c.setAttribute('role', 'columnheader');
      c.setAttribute('aria-sort', i === sp && ri ? (ri === 1 ? 'ascending' : 'descending') : 'none');
    } else { c.removeAttribute('tabindex'); c.removeAttribute('aria-sort'); }
  });
  const anwenden = (kopf, sp, ri) => {   // die Plätze dieser Tabelle neu verteilen – alles andere bleibt, wo es ist
    const k = [...kopf.parentElement.children], zeilen = zeilenVon(kopf), plaetze = zeilen.map(z => k.indexOf(z));
    const mit = zeilen.map((z, i) => ({ z, i, k: schluessel(zellText(z.children[sp])) }));
    mit.sort((a, b) => a.k[0] !== b.k[0] ? a.k[0] - b.k[0] : (vergleich(a.k, b.k) * ri || a.i - b.i));
    mit.forEach((x, r) => { x.z.style.order = plaetze[r]; });
  };
  const sortierbar = (kopf) => {
    const eltern = kopf.parentElement;
    if (!eltern || zeilenVon(kopf).length < 2) return false;
    const st = getComputedStyle(eltern);
    return st.display === 'block' || (st.display === 'flex' && st.flexDirection === 'column') || eltern.classList.contains('m-sortiert')
      || eltern.classList.contains('m-tab');
  };
  let geplant = false;
  const pruefen = () => {
    geplant = false;
    const eltern = new Map();
    document.querySelectorAll('.m-tkopf').forEach(kopf => {
      const ok = sortierbar(kopf), s = ok ? zustand[sig(kopf)] : null;
      kopf.classList.toggle('m-sortbar', ok);
      kopfMarken(kopf, s ? s[0] : -1, s ? s[1] : 0, ok);
      if (kopf.parentElement) {
        if (!eltern.has(kopf.parentElement)) eltern.set(kopf.parentElement, []);
        if (s) eltern.get(kopf.parentElement).push([kopf, s]);
      }
    });
    eltern.forEach((sortiert, el) => {
      if (!sortiert.length) {
        if (el.classList.contains('m-sortiert')) { el.classList.remove('m-sortiert'); [...el.children].forEach(c => c.style.order = ''); }
        return;
      }
      el.classList.add('m-sortiert');
      [...el.children].forEach((c, i) => { c.style.order = i; });   // Grundordnung = Reihenfolge im Dokument
      sortiert.forEach(([kopf, s]) => anwenden(kopf, s[0], s[1]));
    });
  };
  new MutationObserver(() => { if (!geplant) { geplant = true; requestAnimationFrame(pruefen); } })
    .observe(document.body, { childList: true, subtree: true, characterData: true });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const zelle = e.target.closest && e.target.closest('.m-tkopf.m-sortbar > div');
    if (zelle && zelle === e.target) { e.preventDefault(); zelle.click(); }
  });
  document.addEventListener('click', (e) => {
    const zelle = e.target.closest('.m-tkopf.m-sortbar > div');
    if (!zelle || !zelle.innerText.trim()) return;
    const kopf = zelle.parentElement, sp = [...kopf.children].indexOf(zelle), s = zustand[sig(kopf)];
    const ri = !s || s[0] !== sp ? 1 : s[1] === 1 ? -1 : 0;
    if (ri) zustand[sig(kopf)] = [sp, ri]; else delete zustand[sig(kopf)];
    merken();
    pruefen();
  });
  requestAnimationFrame(pruefen);
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


async def _melde_takt() -> None:
    """Wie im Hauptprogramm: 20 Sekunden nach dem Start und dann alle 15 Minuten Fälliges als Windows-Meldung zeigen
    (Termine, offene Reinigung vor Anreise, Facility-Checks) – jede Meldung nur einmal, auch neben dem Hauptprogramm.
    Im selben Takt: das Tagesbriefing (Outlook-Termin oder Mail), sobald die eingestellte Uhrzeit erreicht ist."""
    import asyncio

    from . import briefing_kern, melder

    await asyncio.sleep(20)                    # erst wenn der Start fertig ist – nicht mit dem ersten Laden konkurrieren
    while True:
        try:
            if await run.io_bound(melder.an):
                for m in await run.io_bound(melder.sammeln):
                    melder.windows_zeigen(m.titel, m.text)
        except Exception:                      # noqa: BLE001 – der Takt läuft weiter
            log.exception("Meldungen konnten nicht geprüft werden")
        try:
            await run.io_bound(briefing_kern.pruefen)  # Tagesbriefing per Outlook, einmal am Tag ab der Uhrzeit
        except Exception:                      # noqa: BLE001
            log.exception("Tagesbriefing nicht gesendet")
        await asyncio.sleep(melder.TAKT_MINUTEN * 60)


app.on_startup(_melde_takt)


async def _qr_takt() -> None:
    from . import qr_ui

    await qr_ui.takt()


app.on_startup(_qr_takt)                       # 1.28: Meldungen per QR-Code einlesen und melden


_START = {"gefragt": False}                    # Standort einmal je Programmstart abfragen (nicht bei jedem Neuladen)


@ui.page("/")
async def startseite() -> None:
    from . import benutzer_kern as bk

    erster = not _START["gefragt"]
    erlaubt = bk.erlaubte_standorte()                    # 1.33: nur die Standorte des angemeldeten Kontos
    if erster or standort_kern.aktiv().kurz not in erlaubt:
        g = standort_kern.gemerkt()
        await run.io_bound(standort_kern.waehlen, g if g in erlaubt else erlaubt[0], False)
    ui.page_title(f"Belegung – {standort_kern.aktiv().name}")
    a = Ansicht()                                        # 1.34: nur noch das Menüband (Leitstand entfällt)
    a.aufbauen()
    try:
        anmelden = bk.aktuell() is None and await run.io_bound(bk.eingerichtet)   # 1.33: Anmeldung
    except ValueError as exc:                            # Benutzerdatei beschädigt: nicht ohne Anmeldung weiter
        await ui.context.client.connected()
        with ui.dialog().props("persistent") as dlg, ui.element("div").classes("m-frage"):
            ui.label("Anmeldung nicht möglich").classes("m-titel")
            ui.label(str(exc)).classes("m-ptext")
        dlg.open()
        return
    if anmelden:
        from . import benutzer_ui

        await ui.context.client.connected()
        await benutzer_ui.anmelden(windows_erlaubt=not _START.pop("manuell", False))
        if not erster or standort_kern.aktiv().kurz not in bk.erlaubte_standorte():
            ui.navigate.reload()                         # mit Name und Standorten des Kontos neu aufbauen
            return
    if erster:
        await ui.context.client.connected()
        _START["gefragt"] = True
        from . import netz_kern, seite_netz

        # 0.54: neuer (leerer) Datenordner im Netzwerk → zuerst die bisherigen Daten übernehmen
        if netz_kern.netzbetrieb() and not await run.io_bound(netz_kern.hat_daten, netz_kern.basis()):
            if await seite_netz.uebernahme_dialog(a, beim_start=True):
                seite_netz.neustart_hinweis()
                return
        kurz = await a.standort_fragen()
        if kurz != standort_kern.aktiv().kurz:
            await run.io_bound(standort_kern.waehlen, kurz)
            ui.navigate.reload()
            return
        await run.io_bound(standort_kern.merken, kurz)
    a.zeichnen()                               # sofort Rahmen zeigen („Lädt …“), dann Daten
    await ui.context.client.connected()
    try:
        a.weniger_bewegung = bool(await ui.run_javascript("matchMedia('(prefers-reduced-motion: reduce)').matches", timeout=3))
    except Exception:                          # noqa: BLE001 – ohne Antwort: Animation wie gewohnt
        pass
    from . import daten_kern, netz_kern

    if erster:                                 # 0.54: einmal am Tag sichern (genau ein PC, unter der Schreibsperre)
        try:
            for z in await run.io_bound(netz_kern.tagessicherung):
                log.info("Tagessicherung %s", z)
        except Exception:                      # noqa: BLE001 – Sicherung darf den Start nie verhindern
            log.exception("Tagessicherung")
    # neue Dateien in „UWT“/„Listen“ (wie das Hauptprogramm) – mit Bericht, was sich dadurch geändert hat
    eingelesen, aenderungen = await run.io_bound(daten_kern.ordner_importieren_bericht)
    await a.laden()
    if eingelesen:
        from .seite_daten import eingelesen_melden

        eingelesen_melden(a, eingelesen, aenderungen)
    if await run.io_bound(kern.automatisch_oeffnen, a.karten, a.heute) and a.seite != "heute":
        a.center_umschalten(True)              # einmal am Tag von selbst, wenn Dringendes neu ist (Heute zeigt sie schon)
