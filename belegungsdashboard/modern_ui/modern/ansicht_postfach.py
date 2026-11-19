"""1.29: Oberfläche – Postfach auf „Heute“: rechts die Fälle der gewählten Aufgabe (Anreise, Reinigung, FM-Auftrag,
Konflikte, Allergiker, strittige Planung). Teil der Klasse Ansicht (oberflaeche.py), als Mixin ausgelagert – nur
verschoben."""

from __future__ import annotations

from nicegui import run, ui

from . import (
    kern,
)
from .ui_bausteine import attr, knopf


class PostfachMixin:
    """Teil von ``Ansicht`` (oberflaeche.py) – Methoden unverändert hierher verschoben."""

    def pf_hat_liste(self, k: kern.Karte) -> bool:
        return k.id in self.PF_LISTEN or k.id.startswith(("anreise:", "reinigung"))

    async def pf_detail(self, k: kern.Karte, ziel) -> None:
        """Rechte Spalte des Postfachs füllen – dieselben Prüflisten wie in den Panels, nur ohne Überblenden."""
        try:
            if k.id in self.PF_LISTEN:
                self._pf_ziel = ziel
                await self._karte_details(k)
            elif k.id.startswith("anreise:"):
                await self._pf_anreise(k, ziel)
            elif k.id.startswith("reinigung"):
                await self._pf_reinigung(k, ziel)
        finally:
            self._pf_ziel = None

    async def _pf_anreise(self, k: kern.Karte, ziel) -> None:
        kennung = k.id.split(":", 1)[1]
        zs = [z for z in await run.io_bound(kern.zeilen, self.stand, kennung, self.heute) if z.status != "ok"]
        ziel.clear()
        with ziel:
            if not zs:
                ui.label("Alle Personen dieser Anreise haben ein passendes Zimmer.").classes("m-ptext")
                return
            mit = [z for z in zs if z.vorschlag]
            with ui.element("div").classes("m-paktionen"):
                if mit and k.aktion:
                    knopf(f"Alle {len(mit)} Vorschläge übernehmen", lambda: self._karte_loesen(k), "primaer", "done_all")
                knopf("Zur Anreise", lambda: self._zeigen(kennung), "", "flight_land")
            for z in zs:
                with ui.element("div").classes("m-fall"):
                    with ui.element("div").classes("m-fall-t"):
                        ui.label(f"{z.name} · {z.gruppe} · {z.zeitraum}").classes("m-name")
                        ui.label(z.grund or "noch kein Zimmer").classes("m-zweite").style("white-space:normal")
                    if z.vorschlag:
                        knopf(f"{kern.kurz(z.vorschlag)} übernehmen",
                              lambda z=z: self.aendern(kern.zuweisen, z.schluessel, z.vorschlag), "gruen", "check")
                    else:
                        ui.label("kein freies Zimmer").classes("m-pille warn")

    async def _pf_reinigung(self, k: kern.Karte, ziel) -> None:
        dringend = k.id == "reinigung_dringend"
        rs = await run.io_bound(kern.reinigungen_offen, dringend, self.heute)
        ziel.clear()
        with ziel:
            if not rs:
                ui.label("Alles gereinigt.").classes("m-ptext")
                return
            with ui.element("div").classes("m-paktionen"):
                if k.aktion:
                    knopf(f"Alle {len(rs)} als gereinigt markieren", lambda: self._karte_loesen(k), "primaer", "done_all")
                knopf("Reinigungsliste", lambda: self.oeffnen("reinigung", rg_zeitraum="heute", rg_zimmer=""), "", "cleaning_services")
            for r in rs:
                with ui.element("div").classes("m-fall"):
                    with ui.element("div").classes("m-fall-t"):
                        ui.label(f"{kern.kurz(r.zimmer.id)}").classes("m-name")
                        ui.label((f"Einzug {r.naechste_anreise:%d.%m.}" if r.naechste_anreise else "kein Einzug geplant")
                                 + (" · Auszug heute" if r.auszug else " · vorbereiten")).classes("m-zweite")
                    knopf("Gereinigt", lambda r=r: self.aendern(kern.reinigung_einzeln, r.zimmer.id, dringend, self.heute),
                          "gruen", "check")

    async def _fm_panel(self) -> None:
        """Schloss/Schlüssel defekt: Auftrag ans FM mit Frist (nächster Einzug) – kopieren, nach Erledigung abhaken."""
        import json

        from . import seite_zimmer

        fs = await run.io_bound(kern.fm_faelle, self.stand, self.heute)
        wahl = {f.zimmer: True for f in fs}

        def bauen():
            if not fs:
                ui.label("Keine Zimmer mit defektem Schloss oder Schlüssel.").classes("m-ptext")
                return
            ui.label("Diese Zimmer sind nicht nutzbar, weil Schloss oder Schlüssel defekt ist. Das FM behebt das "
                     f"schnell. Darum wird erst umgeplant, wenn die Anreise weniger als {kern.SCHNELL_VORLAUF} Tage "
                     "entfernt ist. Frist ist der nächste Einzug.").classes("m-ptext")
            for f in fs:
                with ui.element("div").classes("m-fall" + (" knapp" if f.knapp else "")):
                    cb = ui.checkbox(value=True).props("dense dark")
                    cb.on_value_change(lambda e, z=f.zimmer: wahl.__setitem__(z, bool(e.value)))
                    with ui.element("div").classes("m-fall-t"):
                        n_ = ui.label(f"{kern.kurz(f.zimmer)} · {f.maengel}").classes("m-name m-link")
                        n_.on("click", lambda z=f.zimmer: seite_zimmer.karte_oeffnen(self, z))
                        ui.label((f"Frist {f.frist:%d.%m.%Y}" + (f" – {f.wer}" if f.wer else "") if f.frist else "kein Einzug geplant")
                                 + f" · gemeldet {f.seit:%d.%m.}").classes("m-zweite")
                    if f.knapp:
                        ui.label("knapp").classes("m-pille krit")

            def gewaehlt():
                return [f for f in fs if wahl.get(f.zimmer)]

            def kopieren():
                text = kern.fm_text(gewaehlt())
                ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")
                self.toast(f"FM-Auftrag für {len(gewaehlt())} Zimmer kopiert – in Mail oder Teams einfügen", rueck=False)

            async def behoben():
                if await self.aendern(kern.fm_behoben, [f.zimmer for f in gewaehlt()]):
                    self.panel_zu()
            with ui.element("div").classes("m-paktionen"):
                knopf("FM-Auftrag kopieren", kopieren, "primaer", "content_copy")
                knopf("Als behoben markieren", behoben, "", "check")
                knopf("Schließen", self.panel_zu, "leise")

        self.panel("FM-Auftrag: Schloss/Schlüssel", bauen)

    async def _faelle_panel(self, nur_unbewohnbar: bool) -> None:
        """Planungen mit Konflikt / in unbewohnbaren Zimmern prüfen – umgeplant wird nur, was angehakt ist."""
        from . import seite_zimmer

        fs = await run.io_bound(kern.faelle, self.stand, self.heute, nur_unbewohnbar)
        wahl: dict[str, bool] = {}

        def bauen():
            moeglich = [f for f in fs if f.vorschlag]
            wohnen = sum(1 for f in fs if f.wohnt)
            ui.label(f"{len(fs)} Planungen · {len(moeglich)} mit freiem Ausweichzimmer"
                     + (f" · {wohnen} wohnen schon dort (Umzug über die Zimmerkarte)" if wohnen else "")
                     + ". Geändert wird nur, was Sie anhaken.").classes("m-ptext")
            sp = "34px minmax(150px, 1.3fr) minmax(160px, 1.4fr) 120px 40px"
            kaestchen = {}

            def neu_zaehlen():
                n = sum(1 for v in wahl.values() if v)
                zahl.text = f"{n} ausgewählt"
                los.default_slot.children[-1].text = f"{n} Ausweichzimmer übernehmen" if n != 1 else "1 Ausweichzimmer übernehmen"
                los.props("disabled") if not n else los.props(remove="disabled")

            def alle(an: bool):
                for f in moeglich:
                    wahl[f.schluessel] = an
                    kaestchen[f.schluessel].value = an
                neu_zaehlen()

            with ui.element("div").classes("m-paktionen"):
                knopf(f"Alle {len(moeglich)} mit Vorschlag auswählen", lambda: alle(True), "", "done_all")
                knopf("Keine", lambda: alle(False), "leise")
            with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                for t in ("", "Person", "Zimmer jetzt · Grund", "Ausweichzimmer", ""):
                    ui.label(t)
            for f in fs:
                with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                    cb = ui.checkbox(value=False).props("dark dense")
                    kaestchen[f.schluessel] = cb
                    wahl[f.schluessel] = False
                    if not f.vorschlag:
                        cb.props("disable")
                    cb.on_value_change(lambda e, f=f: (wahl.__setitem__(f.schluessel, bool(e.value)), neu_zaehlen()))
                    with ui.element("div"):
                        ui.label(f.name).classes("m-name")
                        ui.label(("wohnt seit " if f.wohnt else "Anreise ") + f"{f.von:%d.%m.%Y}").classes("m-zweite")
                    with ui.element("div"):
                        z = ui.label(kern.kurz(f.zimmer)).classes("m-mono m-link")
                        z.on("click", lambda f=f: seite_zimmer.karte_oeffnen(self, f.zimmer))
                        attr(ui.label(f.grund).classes("m-zweite"), title=f.grund)
                    if f.vorschlag:
                        v = ui.label(f"→ {kern.kurz(f.vorschlag)}").classes("m-mono m-link")
                        v.on("click", lambda f=f: seite_zimmer.karte_oeffnen(self, f.vorschlag))
                    else:
                        ui.label("Umzug planen" if f.wohnt else "kein freies").classes("m-zweite")
                    knopf("", lambda f=f: seite_zimmer.karte_oeffnen(self, f.zimmer), "leise", "open_in_new", "Zimmerkarte")
            with ui.element("div").classes("m-paktionen"):
                los = knopf("Ausweichzimmer übernehmen", lambda: uebernehmen(), "primaer", "check")
                knopf("Abbrechen", self.panel_zu, "leise")
                zahl = ui.label("").classes("m-zweite")
            neu_zaehlen()

        async def uebernehmen():
            gewaehlt = [p for p, an in wahl.items() if an]
            if gewaehlt and await self.aendern(kern.ausweich_uebernehmen, gewaehlt, self.heute):
                self.panel_zu()

        self.panel("Unbewohnbare Zimmer – prüfen" if nur_unbewohnbar else "Konflikte – prüfen", bauen, breit=True)

    async def _allergie_panel(self) -> None:
        from . import hinweise_kern as hk

        fs = await run.io_bound(hk.allergie_faelle, self.stand, self.heute)

        def bauen():
            ui.label(f"{len(fs)} Allergiker in den nächsten 3 Wochen · {hk.ALLERGIE_TEXT}").classes("m-ptext")
            sp = "minmax(160px, 1.4fr) 110px 110px 150px 110px"
            with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                for t in ("Person", "Anreise", "Zimmer", "Etage", ""):
                    ui.label(t)
            for f in fs:
                with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                    ui.label(f.name).classes("m-name")
                    ui.label(f"{f.anreise:%d.%m.%Y}").classes("m-mono")
                    ui.label(kern.kurz(f.zimmer) if f.zimmer else "noch ohne").classes("m-mono")
                    ui.label("auf der Etage ✓" if f.auf_etage else "nicht auf der Etage").classes(
                        "m-zweite" if f.auf_etage else "m-zweite m-warn")
                    knopf("Zur Anreise", lambda f=f: self._zeigen(f.anreise.isoformat()), "leise")

        self.panel("Allergiker", bauen, breit=True)

    async def _strittig_panel(self) -> None:
        """Eigene Planung ↔ Gebäudeplan: je Person entscheiden, was stimmt (Rückgängig je Entscheidung)."""
        from . import seite_zimmer

        sts = await run.io_bound(kern.strittige, self.stand)

        def bauen():
            ui.label("Laut Gebäudeplan wohnt die Person in einem anderen Zimmer als in der eigenen Planung. Bisher gilt "
                     "dann still der Gebäudeplan – das geplante Zimmer erschien frei. Bis zur Klärung wird es niemand "
                     "anderem angeboten. Was stimmt? (Im Zweifel: wo wurde der Schlüssel ausgegeben?)").classes("m-ptext")
            if not sts:
                ui.label("Alles geklärt.").classes("m-ptext")
            for x in sts:
                with ui.element("div").classes("m-strittig"):
                    ui.label(x.name).classes("m-name")
                    ui.label(f"{x.von:%d.%m.%Y} – {x.bis:%d.%m.%Y}").classes("m-zweite")
                    with ui.element("div").classes("m-schalter"):
                        ui.label("Planung").classes("m-zweite")
                        g = ui.label(kern.kurz(x.geplant)).classes("m-mono m-link")
                        g.on("click", lambda x=x: seite_zimmer.karte_oeffnen(self, x.geplant))
                        ui.label("· Gebäudeplan").classes("m-zweite")
                        p_ = ui.label(kern.kurz(x.gebucht)).classes("m-mono m-link")
                        p_.on("click", lambda x=x: seite_zimmer.karte_oeffnen(self, x.gebucht))
                    with ui.element("div").classes("m-paktionen"):
                        knopf(f"Gebäudeplan stimmt ({kern.kurz(x.gebucht)})", lambda x=x: klaeren(x.person, "plan"), "",
                              "description", f"{x.name} wohnt in {kern.kurz(x.gebucht)} – eigene Planung wird darauf gesetzt")
                        knopf(f"Planung stimmt ({kern.kurz(x.geplant)})", lambda x=x: klaeren(x.person, "planung"), "",
                              "event_available", f"{x.name} wohnt in {kern.kurz(x.geplant)} – gilt dann auch gegen den Gebäudeplan")

        async def klaeren(person: str, wahl: str):
            if await self.aendern(kern.strittig_klaeren, person, wahl):
                await self._strittig_panel()

        self.panel("Planung widerspricht dem Gebäudeplan", bauen, breit=True)
