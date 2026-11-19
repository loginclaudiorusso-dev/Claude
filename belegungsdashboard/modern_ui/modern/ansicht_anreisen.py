"""1.29: Oberfläche – Seite Anreisen: Tabelle der Anreisen mit Zimmerwahl, Kontext-Band, Bereitschaft (bezugsfertig) und
Hinweise. Teil der Klasse Ansicht (oberflaeche.py), als Mixin ausgelagert – nur verschoben."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from . import (
    kern,
    seite_anreisen,
)
from .ui_bausteine import attr, badge_neu, kennzahlen, knopf, leer


class AnreisenMixin:
    """Teil von ``Ansicht`` (oberflaeche.py) – Methoden unverändert hierher verschoben."""

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
        from . import menueband_ui as _mbu

        if _mbu.werkzeuge_oben(self):                       # 1.00: Office-Gruppen im Menüband
            return self._anreisen_band()
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
                          ("nicht_nutzbar", k["nicht_nutzbar"], "nicht nutzbar", "neutral")]
                np_ = getattr(self, "np", None)
                if np_ and np_.tiefst:
                    text, frei, stufe = np_.tiefst
                    zimmer.append(("np", frei, f"nach Planung · {text.split(' · ')[0]}", {"ok": "ok", "knapp": "warn", "kritisch": "krit"}[stufe]))
                b = getattr(self, "bereit", None)
                if b is not None and b.n:
                    zimmer.insert(0, ("bereit", b.bereit, f"von {b.n} bezugsfertig", b.stufe))
                kennzahlen(zimmer, None, lambda k: self._bereit_panel() if k == "bereit" else
                           self.oeffnen("auswertung", ansicht="zimmer") if k == "np" else
                           self.oeffnen("zimmer", ansicht="uebersicht", zu_tag=tag, zu_filter=k),
                           {"np": "Mindestens so viele Zimmer bleiben frei, wenn alle Anreisen der nächsten 12 Wochen ein "
                                  "Zimmer hätten – Klick: alle Wochen",
                            "frei": "Klick: diese Zimmer in der Übersicht", "belegt": "Klick: diese Zimmer in der Übersicht",
                            "nicht_nutzbar": "Gesperrt oder unbewohnbar – Klick: diese Zimmer in der Übersicht",
                            "bereit": "Zimmer gespeichert, kein Konflikt, Reinigung erledigt – Klick: was fehlt und was "
                                      "vorzubereiten ist"})
        with self.inhalt:
            if not self.kennung:
                leer("Keine Anreisen ab heute in den Listen.")
                return
            # 0.74: Hauptaktion immer rechts außen in der Kontextzeile (feste Stelle auf jeder Seite)
            offen = [z for z in self.zeilen if z.vorschlag and z.status in ("ohne", "handeln")]
            if offen:
                with self.leiste:
                    knopf(f"Alle Vorschläge übernehmen ({len(offen)})" if len(offen) > 1 else "Vorschlag übernehmen",
                          self._alle_vorschlaege, "primaer", "done_all",
                          "Übernimmt die passenden freien Zimmer. Einzeln: ✓ in der Zimmerspalte.")
            with ui.element("div").classes("m-raster m-zuteil m-tkopf"):
                for t in ("", "Name", "Gruppe", "Zeitraum", "Zimmer", "Hinweis"):
                    ui.label(t)
            sichtbar = [z for z in self.zeilen if z.filter(self.filter, self.neu)]
            if not sichtbar:
                leer("Nichts in diesem Filter – alles in Ordnung.")
            for z in sichtbar:
                self._zeile(z)

    def _anreisen_band(self) -> None:
        """1.00: Zuteilen mit den Werkzeugen als Office-Gruppen im Menüband; der Inhalt bleibt derselbe."""
        if self.ohne_daten:
            seite_anreisen.zuteilen_band(self, None, {}, {}, 0, [])
            with self.inhalt:
                from belegung import konfig

                leer("Keine Daten gefunden – kein Gebäudeplan und keine Anreiselisten.\n"
                     f"Datenordner: {konfig.datenordner()}")
            return
        offen = [z for z in self.zeilen if z.vorschlag and z.status in ("ohne", "handeln")] if self.kennung else []
        if self.kennung:
            tag = date.fromisoformat(self.kennung)
            n_neu = sum(1 for z in self.zeilen if z.schluessel in self.neu)
            seite_anreisen.zuteilen_band(self, tag, kern.kennzahlen(self.stand, tag), kern.zaehlen(self.zeilen), n_neu, offen)
        else:
            seite_anreisen.zuteilen_band(self, None, {}, {}, 0, [])
        with self.inhalt:
            if not self.kennung:
                leer("Keine Anreisen ab heute in den Listen.")
                return
            with ui.element("div").classes("m-raster m-zuteil m-tkopf"):
                for t in ("", "Name", "Gruppe", "Zeitraum", "Zimmer", "Hinweis"):
                    ui.label(t)
            sichtbar = [z for z in self.zeilen if z.filter(self.filter, self.neu)]
            if not sichtbar:
                leer("Nichts in diesem Filter – alles in Ordnung.")
            for z in sichtbar:
                self._zeile(z)

    def _bereit_panel(self) -> None:
        b = getattr(self, "bereit", None)
        if b is None:
            return
        tag = date.fromisoformat(self.kennung)

        def bauen():
            ui.label(f"{b.bereit} von {b.n} Zimmern sind für die Anreise am {tag:%d.%m.%Y} bezugsfertig.").classes("m-ptext")
            for art, titel in (("blocker", "Was noch fehlt"), ("vorbereiten", "Vorbereiten")):
                punkte = [p for p in b.punkte if p[0] == art]
                if not punkte:
                    continue
                ui.label(titel).classes("m-ktitel")
                for _a, name, text in punkte:
                    with ui.element("div").classes(f"m-bereit-punkt {art}"):
                        ui.icon("error_outline" if art == "blocker" else "inventory_2")
                        with ui.element("div"):
                            ui.label(name).classes("m-name")
                            ui.label(text).classes("m-zweite").style("white-space:normal")
            if not b.punkte:
                leer("Alles bereit – nichts vorzubereiten.")
            with ui.element("div").classes("m-paktionen"):
                if any(p[0] == "blocker" and "nicht erledigt" in p[2] for p in b.punkte):
                    knopf("Zur Reinigung", lambda: self.oeffnen("reinigung", rg_zimmer=""), "", "cleaning_services")
                knopf("Schließen", self.panel_zu, "leise")

        self.panel(f"Anreise {tag:%d.%m.} – bezugsfertig?", bauen)

    def _hinweise(self, z: kern.Zeile) -> None:
        """Marken aus der Bemerkung der Anreiseliste (Allergiker, Hilfsmittel, Begleitung …); voller Text im Tooltip."""
        from . import hinweise_kern as hk

        weitere = hk.rest(z.bemerkung) if not [h for h in z.hinweise if h.art != "vortag"] else ""
        for h in z.hinweise:
            with ui.element("span").classes(f"m-merk {h.art}") as m:
                ui.icon(h.symbol)
                ui.label(h.text)
            attr(m, title=(hk.ALLERGIE_TEXT + " – " if h.art == "allergie" else "") + z.bemerkung)
        if weitere:
            with ui.element("span").classes("m-merk sonst") as m:
                ui.icon("sticky_note_2")
                ui.label("Hinweis")
            attr(m, title=z.bemerkung)

    def _zeile(self, z: kern.Zeile) -> None:
        with ui.element("div").classes("m-raster m-zuteil m-zeile"):
            with ui.element("div"):
                ui.element("div").classes(f"m-ampel {z.stufe}")
            with ui.element("div"):
                with ui.element("div").classes("m-namezeile"):
                    n = attr(ui.label(z.name).classes("m-name m-link"), title="Angaben zur Person (Geschlecht, Tier, Abreise …)")
                    n.on("click", lambda z=z: seite_anreisen.person_panel(self, z.schluessel))
                    if z.schluessel in self.neu:
                        badge_neu(self.neu[z.schluessel])
                    self._hinweise(z)
                if z.zweite:
                    ui.label(z.zweite).classes("m-zweite")
            ui.label(z.gruppe).classes("m-mono")
            ui.label(z.zeitraum).classes("m-mono")
            with ui.element("div").classes("m-zimmerzelle"):
                # 0.69: der grüne Vorschlag steht als 1-Klick-Knopf direkt im Zimmerfeld; das Auswahlfeld daneben
                # ist „andere …“ – Blick und Klick bleiben in einer Spalte
                vorschlag = bool(z.vorschlag and z.status in ("ohne", "handeln") and not z.gespeichert)
                if vorschlag:
                    knopf(kern.kurz(z.vorschlag), lambda z=z: self._zimmer_gewaehlt(z, z.vorschlag), "gruen", "check",
                          f"Vorschlag {kern.kurz(z.vorschlag)} übernehmen: frei und passend")
                optionen = {o.zimmer: ("✓ " if o.art == "vorschlag" else "") + o.text for o in z.optionen}
                konflikt = z.status == "handeln" and z.stufe == "krit"
                popup = "m-popup" + (" m-mitvorschlag" if z.vorschlag else "")
                s = ui.select(optionen, value=z.gespeichert,
                              on_change=lambda e, z=z: self._zimmer_gewaehlt(z, e.value)).classes(
                    "m-zimmer" + (" konflikt" if konflikt else "") + ("" if z.gespeichert else " offen")).props(
                    f'dense outlined dark options-dense popup-content-class="{popup}" '
                    f'placeholder="{"andere …" if vorschlag else "kein Zimmer"}"')
                attr(s, aria_label=f"Zimmer für {z.name}")
                s.style("flex: 1; min-width: 0")
            with ui.element("div").classes(f"m-hinweis {z.stufe if z.status != 'ok' else ''}"):
                if z.vorschlag and z.status == "handeln" and z.gespeichert:     # gespeichert, aber Konflikt: Ausweg
                    knopf(f"{kern.kurz(z.vorschlag)} nehmen", lambda z=z: self._zimmer_gewaehlt(z, z.vorschlag),
                          "gruen", "check", "Grüner Vorschlag: frei und passend")
                text = z.grund if z.status not in ("ok", "ohne") or not z.vorschlag else ""
                if z.maengel:
                    text = (text + " · " if text else "") + f"Mängel: {z.maengel}"
                if text:
                    attr(ui.label(text).classes("t"), title=text)
