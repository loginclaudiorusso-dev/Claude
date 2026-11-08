"""Bestandsmodell Schritt 1 (0.76): Prüfbericht unter Auswertung → Maßnahmen und Zuordnungstabelle der Maßnahmearten.
Noch KEINE Prognose – erst wenn der Bericht stimmt und die offenen Fragen geklärt sind, kommt Schritt 2."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from . import bestand_kern as bk
from . import massnahmen_kern as mk
from .ui_bausteine import attr, badge, knopf, leer

# 0.77: geklärt – Antworten stehen hier, damit sie im Bericht nachvollziehbar bleiben
GEKLAERT = [
    ("Assessment 4 oder 6 Wochen?", "Gemessen je Kursfamilie aus den Daten der Zimmerbelegung (Anmeldungen mit Abreise, "
                                     "Gebäudeplan) – siehe „Solldauer aus der Zimmerbelegung“."),
    ("RVT: Solldauer?", "Ebenso aus den RVT-Anmeldungen der Zimmerbelegung gemessen."),
    ("JobTrain, Bauhelfer und ähnliche Sonderkurse?", "Für uns ohne Belang – Gruppe „Ignoriert“, sie zählen nirgends."),
    ("Geplante künftige Tage im Pivot?", "Prüft der Bericht selbst (Block „Künftige Tage“)."),
    ("Maximale Kursgröße?", "Wird nur bei VW erreicht: 24 Plätze."),
]


def eintraege(stand) -> list:
    """(Maßnahme, von, bis, Quelle) aus der Zimmerbelegung: Anreiselisten mit eingetragener Abreise und belegte
    Zeiträume im Gebäudeplan (ohne Teilstücke eines Umzugs). Namen werden dabei nicht verwendet."""
    if stand is None:
        return []
    erg = [(b.massnahme, b.liste_anreise or b.von, b.bis, "Anmeldung") for b in getattr(stand, "bedarf", [])
           if b.massnahme and not b.bis_angenommen]
    lage = getattr(stand, "lage", None)
    for bs in (getattr(lage, "belegungen", {}) or {}).values():
        erg += [(x.massnahme, x.von, x.bis, "Gebäudeplan") for x in bs if x.art == "belegt" and x.massnahme and not x.umzug]
    return erg


def _z(x, nk: int = 0) -> str:
    return "–" if x is None else f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _monate(tage) -> str:
    return "–" if tage is None else f"{_z(tage)} Tage ≈ {_z(tage / 30.44, 1)} Mon."


def daten(a) -> dict:
    roh = mk._roh()
    aufenthalte, meta = bk.laden(roh)
    if not aufenthalte:
        return {"leer": bool(roh.get("pivot")), "bericht": None}
    stich = date.fromisoformat(meta["stichtag"]) if meta.get("stichtag") else a.heute
    gemessen = bk.anmeldedauern(eintraege(getattr(a, "stand", None)))        # nur zur Laufzeit, nie gespeichert
    return {"bericht": bk.bericht(aufenthalte, meta, bk.tabelle(roh), stich, gemessen), "leer": False}


def zeichnen(a, d: dict) -> None:
    b: bk.Bericht | None = d.get("bericht")
    with a.leiste:
        knopf("Maßnahmearten zuordnen …", lambda: zuordnung_panel(a), "primaer", "rule")
    with a.inhalt, ui.element("div").classes("m-rv m-bst"):
        if b is None:
            leer("Für den Prüfbericht den Maßnahmen-Pivot einmal neu einlesen (Daten & Import → Maßnahmen-Prognose) – "
                 "erst ab dieser Version werden die Aufenthalte je Person gebildet." if d.get("leer") else
                 "Noch kein Maßnahmen-Pivot eingelesen (Daten & Import → Maßnahmen-Prognose).")
            knopf("Zu Daten & Import", lambda: a.oeffnen("daten"), "", "upload_file")
            return
        a.status_info = (f"{b.personen} Personen · {b.kurse} Kurse · {b.aufenthalte} Aufenthalte · Stichtag "
                         f"{b.letzter_ist:%d.%m.%Y}")
        with ui.element("div").classes("m-hw-info"):
            ui.icon("info")
            ui.label("Schritt 1 von 4: nur prüfen, noch keine Prognose. Namen werden nicht gespeichert – jede Person hat "
                     "nur eine Nummer, die bei jedem Einlesen neu vergeben wird.")
        _abnahme(a, b)
        with ui.element("div").classes("m-bst-raster"):
            _block("Umfang", [("Personen", _z(b.personen)), ("Kurse", _z(b.kurse)), ("Aufenthalte (Person × Kurs)", _z(b.aufenthalte)),
                              ("Zeitraum der Aufenthalte", f"{b.von:%d.%m.%Y} – {b.bis:%d.%m.%Y}" if b.von else "–"),
                              ("Tagesgenau ab", f"{b.tagesgenau_ab:%d.%m.%Y}" if b.tagesgenau_ab else "–"),
                              ("Spalten nur als Halbjahr", _z(b.halbjahr_spalten)),
                              ("Aufenthalte mit Halbjahreswerten (nicht für Dauern)", _z(b.halbjahr_aufenthalte)),
                              ("Kurse mit Langnamen ohne Code", _z(b.langnamen))] +
                   ([("Personenzeilen mit Teilsumme", _z(b.teilsummen))] if b.teilsummen else []), b.hinweise)
            _block("Künftige Tage im Pivot",
                   [("Tagesspalten nach dem Stichtag", _z(b.kuenftig_spalten)),
                    ("Personentage darin", _z(b.kuenftig_personentage)), ("Personen mit künftigen Tagen", _z(b.kuenftig_personen))],
                   ["Ja – die Pivot enthält geplante künftige Belegung; sie zählt später als bekannter Bestand."
                    if b.kuenftig_personentage else "Nein – nach dem Stichtag stehen keine Tage mit 1 in der Pivot."])
            _block("Wochenend-Prüfung",
                   [("Anteil Sa/So an den Anwesenheitstagen", f"{b.wochenende_anteil:.0%}".replace(".", ",") if b.wochenende_anteil is not None else "–"),
                    ("Grundlage", f"{b.wochenende_basis} Aufenthalte ab 4 Wochen"),
                    ("Anwesenheit ÷ Kalendertage (regulär beendete Hauptmaßnahmen, Median)",
                     f"{b.anwesend_quote:.0%}" if b.anwesend_quote is not None else "– (noch keine regulär beendeten mit Solldauer)"),
                    ("Grundlage", f"{b.anwesend_basis} Aufenthalte")], [b.wochenende_text])
        _arten(b)
        with ui.element("div").classes("m-bst-raster"):
            _nicht_zugeordnet(a, b)
            _offen(b)
        _gemessen(b)
        _auffaellig(b)
        with ui.element("section").classes("m-block"):
            ui.label("Geklärte Fragen").classes("m-btitel")
            for frage, antwort in GEKLAERT:
                with ui.element("div").classes("m-bst-zeile"):
                    ui.label(frage).classes("m-name")
                    ui.label(antwort).classes("m-zweite")
            if b.ignoriert[0]:
                from .arbeitsflaeche import mehrzahl

                ui.label(f"Ignoriert: {mehrzahl(b.ignoriert[0], 'Kurs', 'Kurse')} mit "
                         f"{mehrzahl(b.ignoriert[1], 'Aufenthalt', 'Aufenthalten')}.").classes("m-ptext")


def _gemessen(b: bk.Bericht) -> None:
    with ui.element("section").classes("m-block"):
        ui.label("Solldauer aus der Zimmerbelegung (Anmeldungen mit Abreise, Gebäudeplan)").classes("m-btitel")
        if not b.gemessen:
            ui.label("Keine passenden Anmeldungen gefunden – es gilt die Solldauer aus der Tabelle.").classes("m-ptext")
            return
        sp = "minmax(160px,1.2fr) 120px 70px minmax(150px,1fr) minmax(150px,1fr)"
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Kursfamilie", "Quelle", "Fälle", "Median", "10 % – 90 %"):
                ui.label(t)
        for m in b.gemessen:
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                ui.label(m.familie).classes("m-name")
                ui.label(m.quelle).classes("m-zweite")
                ui.label(_z(m.n))
                ui.label(_monate(m.median))
                ui.label(f"{_z(m.p10)} – {_z(m.p90)} Tage")
        ui.label("Gemessen wird bei jedem Öffnen aus den aktuellen Daten der Zimmerbelegung (Abreise − Anreise + 1). "
                 "Ab 3 Anmeldungen je Kursfamilie gilt der Median als Solldauer für Einträge mit „Soll aus Anmeldung“; "
                 "sonst der Gebäudeplan, sonst die Tabelle.").classes("m-zweite").style("white-space:normal")


def _abnahme(a, b: bk.Bericht) -> None:
    ok = True              # Abnahme Schritt 1: Bericht da, alle Kurse zugeordnet oder offen gelistet (beides hier erfüllt)
    offen = len(b.nicht_zugeordnet)
    with ui.element("div").classes("m-bst-abnahme"):
        badge("frei" if ok and not offen else "pruefen",
              "Abnahme Schritt 1 erfüllt" if not offen else f"Abnahme erfüllt – {offen} Kurse noch ohne Maßnahmeart")
        ui.label("Kurse ohne Zuordnung gehen später nicht in die Prognose ein. Sie stehen unten mit Personenzahl und "
                 "Zeitraum.").classes("m-zweite")


def _block(titel: str, zeilen: list, saetze: list) -> None:
    with ui.element("section").classes("m-block"):
        ui.label(titel).classes("m-btitel")
        with ui.element("div").classes("m-bst-kv"):
            for k, v in zeilen:
                ui.label(k).classes("m-zweite")
                ui.label(v).classes("m-name")
        for s in saetze:
            ui.label(s).classes("m-ptext")


def _arten(b: bk.Bericht) -> None:
    with ui.element("section").classes("m-block"):
        ui.label("Dauern je Maßnahmeart (Kalendertage, nur abgeschlossene Aufenthalte)").classes("m-btitel")
        if not b.arten:
            ui.label("Noch keine Kurse zugeordnet.").classes("m-ptext")
            return
        sp = "minmax(160px,1.4fr) 120px 70px 70px minmax(150px,1fr) minmax(170px,1.1fr) 120px 90px"
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Maßnahmeart", "Gruppe", "Fälle", "laufend", "Median", "10 % – 90 %", "Soll", "Unterbr."):
                ui.label(t)
        for z in b.arten:
            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                with ui.element("div").classes("m-zeile-flex"):
                    ui.label(z.art).classes("m-name")
                    if z.offen:
                        attr(ui.icon("help_outline").classes("m-warn"), title=f"zu klären: {z.offen}")
                ui.label(z.gruppe).classes("m-zweite")
                ui.label(_z(z.n))
                ui.label(_z(z.laufend))
                ui.label(_monate(z.median))
                ui.label(f"{_z(z.p10)} – {_z(z.p90)} Tage" if z.p10 is not None else "–")
                ui.label(z.soll_text or ("flexibel" if z.gruppe == "IBTZ" else "offen")).style("white-space:normal")
                ui.label(_z(z.unterbrochen))
        ui.label("Laufend = Austritt höchstens 3 Tage vor dem Stichtag; diese Fälle gelten später als „noch nicht beendet“ "
                 "(zensiert) und fehlen in Median und Spanne.").classes("m-zweite").style("white-space:normal")


def _nicht_zugeordnet(a, b: bk.Bericht) -> None:
    with ui.element("section").classes("m-block"):
        with ui.element("div").classes("m-zeile-flex"):
            ui.label(f"Ohne Maßnahmeart ({len(b.nicht_zugeordnet)} Kurse)").classes("m-btitel")
            knopf("Zuordnen …", lambda: zuordnung_panel(a), "leise", "rule").style("margin-left:auto")
        if not b.nicht_zugeordnet:
            ui.label("Alle Kurse sind einer Maßnahmeart zugeordnet.").classes("m-ptext")
        for kurs, n, von, bis in b.nicht_zugeordnet[:40]:
            with ui.element("div").classes("m-bst-zeile"):
                ui.label(kurs).classes("m-name")
                ui.label(f"{n} Personen").classes("m-zweite")
                ui.label(f"{von:%m/%Y} – {bis:%m/%Y}").classes("m-zweite")
        if len(b.nicht_zugeordnet) > 40:
            ui.label(f"… und {len(b.nicht_zugeordnet) - 40} weitere").classes("m-zweite")


def _offen(b: bk.Bericht) -> None:
    with ui.element("section").classes("m-block"):
        ui.label("Zu klären (Zuordnung vorläufig)").classes("m-btitel")
        if not b.offene_regeln:
            ui.label("Keine offenen Einträge.").classes("m-ptext")
        for muster, hinweis, n in b.offene_regeln:
            with ui.element("div").classes("m-bst-zeile"):
                ui.label(muster).classes("m-name")
                ui.label(hinweis).classes("m-zweite")
                ui.label(f"{n} Kurse").classes("m-zweite")
        ui.label(f"Kurse ohne lesbares Startdatum im Namen: {len(b.ohne_start)} – dort gilt der früheste Eintritt als "
                 "Kursstart.").classes("m-ptext")
        for kurs, n in b.ohne_start[:8]:
            ui.label(f"{kurs} ({n})").classes("m-zweite")


def _auffaellig(b: bk.Bericht) -> None:
    with ui.element("section").classes("m-block"):
        ui.label("Auffällige Fälle").classes("m-btitel")
        for text, n, beispiele in b.auffaellig:
            with ui.expansion(f"{text}: {n}").classes("m-bst-exp").props("dense"):
                if not beispiele:
                    ui.label("keine").classes("m-zweite")
                for x in beispiele:
                    ui.label(x).classes("m-zweite")


# ---- Zuordnungstabelle bearbeiten --------------------------------------------------------------------------

def zuordnung_panel(a) -> None:
    zeilen = [dict(e) for e in bk.tabelle()]

    def bauen():
        ui.label("Reihenfolge zählt: der erste passende Eintrag gewinnt. Muster = Kürzel (ganzes Wort, z. B. „ASS“), "
                 "Teiltext ab 5 Zeichen (z. B. „Bauhelfer“) oder „re:“ + regulärer Ausdruck. Solldauer in Tagen "
                 "(leer = flexibel bzw. offen); „aus Anmeldung messen“ nimmt je Kurs die Dauer aus der Zimmerbelegung. "
                 "Standort leer = alle. Gruppe „Ignoriert“ = zählt nirgends. Max. Plätze nur, wo die Kursgröße erreicht "
                 "wird (VW).").classes("m-ptext")
        liste = ui.element("div").classes("m-bst-tab")

        def neu_zeichnen():
            liste.clear()
            with liste:
                for i, e in enumerate(zeilen):
                    with ui.element("div").classes("m-bst-regel"):
                        ui.input("Muster", value=e["muster"], on_change=lambda ev, e=e: e.update(muster=ev.value)).props(
                            "dense outlined").classes("m-feld")
                        ui.input("Maßnahmeart", value=e["art"], on_change=lambda ev, e=e: e.update(art=ev.value)).props(
                            "dense outlined").classes("m-feld")
                        ui.select(list(bk.GRUPPEN), value=e["gruppe"], label="Gruppe",
                                  on_change=lambda ev, e=e: e.update(gruppe=ev.value)).props("dense outlined").classes("m-feld")
                        ui.number("Soll (Tage)", value=e["soll_tage"], min=1, step=1,
                                  on_change=lambda ev, e=e: e.update(soll_tage=ev.value)).props("dense outlined").classes("m-feld")
                        ui.checkbox("Soll aus Anmeldung messen", value=e.get("soll_quelle") == "anmeldung",
                                    on_change=lambda ev, e=e: e.update(soll_quelle="anmeldung" if ev.value else "")).props("dense")
                        ui.number("max. Plätze je Kurs", value=e.get("max_plaetze"), min=1, step=1,
                                  on_change=lambda ev, e=e: e.update(max_plaetze=ev.value)).props("dense outlined").classes("m-feld")
                        ui.input("Standort", value=e["standort"], on_change=lambda ev, e=e: e.update(standort=ev.value)).props(
                            "dense outlined").classes("m-feld")
                        ui.input("Zu klären", value=e["offen"], on_change=lambda ev, e=e: e.update(offen=ev.value)).props(
                            "dense outlined").classes("m-feld")
                        with ui.element("div").classes("m-zeile-flex"):
                            knopf("", lambda i=i: tauschen(i, -1), "leise", "arrow_upward", "Nach oben")
                            knopf("", lambda i=i: tauschen(i, 1), "leise", "arrow_downward", "Nach unten")
                            knopf("", lambda i=i: (zeilen.pop(i), neu_zeichnen()), "leise", "delete", "Entfernen")

        def tauschen(i: int, r: int):
            j = i + r
            if 0 <= j < len(zeilen):
                zeilen[i], zeilen[j] = zeilen[j], zeilen[i]
                neu_zeichnen()

        neu_zeichnen()

        async def speichern():
            if await a.aendern(bk.tabelle_schritt, zeilen):
                a.panel_zu()

        async def standard():
            if await a.aendern(bk.tabelle_schritt, None):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Eintrag hinzufügen", lambda: (zeilen.append({"muster": "", "art": "", "gruppe": "Hauptmaßnahme",
                                                                 "soll_tage": 730, "standort": "", "offen": ""}), neu_zeichnen()),
                  "", "add")
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Startwerte", standard, "leise", "restart_alt")
    a.panel("Maßnahmearten zuordnen", bauen, breit=True)


CSS = r"""
.m-bst { display: flex; flex-direction: column; gap: 12px; }
.m-bst-raster { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; align-items: start; }
.m-bst-kv { display: grid; grid-template-columns: minmax(150px, 1.2fr) minmax(0, 1fr); gap: 4px 12px; margin-bottom: 6px; }
.m-bst-kv > * { white-space: normal !important; overflow: visible !important; }
.m-bst-kv .m-name { text-align: right; font-variant-numeric: tabular-nums; }
.m-bst-zeile { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) auto; gap: 8px; align-items: center;
  min-height: 30px; border-bottom: 1px solid var(--rand); }
.m-bst-zeile > * { white-space: normal !important; }
.m-bst-abnahme { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.m-hw-info { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; background: #E8F1FB;
  color: #1F4E8C; font-size: 14px; }
body.mod-dunkel .m-hw-info { background: rgba(31,78,140,.3); color: #BFD8F5; }
.m-bst-tab { display: flex; flex-direction: column; gap: 8px; margin: 8px 0; }
.m-bst-regel { display: grid; grid-template-columns: 1fr 1.4fr 1.1fr; gap: 6px; padding: 8px; border: 1px solid var(--rand);
  border-radius: 6px; }
.m-bst-exp .q-item { min-height: 32px; padding: 0 4px; font-size: 14px; }
"""
