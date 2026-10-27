"""Seite „Termine“: Liste (fällig, demnächst, erledigt) und Monatsansicht. Eigene Termine anlegen, ändern,
löschen; jede Erinnerung abhaken. Daten: ``belegung.termine`` (gleiche Termine wie im Hauptprogramm)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from nicegui import run, ui

from belegung import termine as tm

from .kern import WT, _schritt
from .ui_bausteine import attr, knopf, leer, segmente

ANSICHTEN = {"liste": "Liste", "monat": "Monat"}
FARBE = {"abreise": "warn", "anreise": "ok", "uwt": "akzent", "eigen": "akzent", "notiz": "neutral", "wiedervorlage": "neutral"}
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember"]


def daten(a) -> None:
    a.daten = {"termine": tm.alle()}


# ---- Ändern -----------------------------------------------------------------------------

def erledigt_setzen(tid: str, an: bool) -> str:
    t = next((x for x in tm.alle() if x.id == tid), None)
    if t is None:
        raise ValueError("Den Termin gibt es nicht mehr.")
    from belegung import anreiseliste

    _schritt("Termin erledigt" if an else "Termin offen", lambda: tm.erledigt_setzen(t, an), [tm.DATEI, anreiseliste.DATEI])
    return f"„{t.titel}“ " + ("erledigt" if an else "wieder offen")


def eigener_speichern(tid: str, datum: date, titel: str, text: str, vorlauf: int) -> str:
    if not titel.strip():
        raise ValueError("Bitte einen Titel eingeben.")
    t = tm.Termin(tid, datum, titel.strip(), text.strip(), "eigen", vorlauf=vorlauf)
    _schritt("Termin gespeichert", lambda: tm.eigenen_speichern(t), [tm.DATEI])
    return f"Termin „{t.titel}“ am {datum:%d.%m.%Y} gespeichert"


def eigener_loeschen(tid: str) -> str:
    _schritt("Termin gelöscht", lambda: tm.eigenen_loeschen(tid), [tm.DATEI])
    return "Termin gelöscht"


# ---- Zeichnen ---------------------------------------------------------------------------

def zeichnen(a) -> None:
    ansicht = a.ansicht_von("termine", "liste")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("termine", ansicht=v))
        knopf("Neuer Termin", lambda: termin_panel(a, None, a.heute), "primaer", "add")
    (_liste if ansicht == "liste" else _monat)(a)


def _zeile(a, t, heute: date) -> None:
    faellig = t.faellig(heute)
    with ui.element("div").classes("m-raster m-zeile" + (" fertig" if t.erledigt else "")).style(
            "grid-template-columns: 36px 100px minmax(180px, 1.4fr) minmax(160px, 1.6fr) 130px 40px"):
        with ui.element("div"):
            b = ui.element("button").classes("m-haken" + (" an" if t.erledigt else ""))
            attr(b, title="Erledigt", aria_pressed=str(t.erledigt).lower())
            with b:
                ui.icon("check")
            b.on("click", lambda t=t: a.aendern(erledigt_setzen, t.id, not t.erledigt))
        ui.label(f"{WT[t.datum.weekday()]} {t.datum:%d.%m.%y}").classes("m-mono" + (" m-warn" if faellig else ""))
        attr(ui.label(t.titel).classes("m-name"), title=t.titel)
        attr(ui.label(t.text).classes("m-zweite"), title=t.text)
        with ui.element("div"):
            ui.label(tm.ARTEN.get(t.art, t.art)).classes(f"m-pille {FARBE.get(t.art, '')}")
        with ui.element("div"):
            if t.art == "eigen":
                knopf("", lambda t=t: termin_panel(a, t, t.datum), "leise", "edit", "Bearbeiten")


def _liste(a) -> None:
    heute = a.heute
    alle = a.daten["termine"]
    faellig = [t for t in alle if t.faellig(heute)]
    bald = [t for t in alle if not t.erledigt and not t.faellig(heute) and heute <= t.datum <= heute + timedelta(days=a.tm_tage)]
    erledigt = [t for t in alle if t.erledigt and heute - timedelta(days=14) <= t.datum <= heute + timedelta(days=a.tm_tage)]
    with a.leiste:
        ui.html(f'<span class="m-kpi"><b style="color:var(--orange)">{len(faellig)}</b> fällig'
                f'<span class="m-punktt">·</span><b>{len(bald)}</b> in den nächsten {a.tm_tage} Tagen</span>', sanitize=False)
        segmente({14: "14 Tage", 30: "30 Tage", 90: "90 Tage"}, a.tm_tage, lambda d: a.setzen(tm_tage=d, laden=False))
    with a.inhalt:
        if not (faellig or bald or erledigt):
            leer("Keine Termine.")
            return
        for titel, liste in (("Fällig – Erinnerung ist da", faellig), ("Demnächst", bald), ("Erledigt (letzte 14 Tage)", erledigt)):
            if liste:
                ui.label(titel).classes("m-abschnitt")
                for t in liste:
                    _zeile(a, t, heute)


def _monat(a) -> None:
    """Monatskalender: Klick auf einen Tag legt dort einen Termin an, Klick auf einen Eintrag öffnet ihn,
    „+N weitere“ zeigt den ganzen Tag."""
    m = a.tm_monat
    with a.leiste:
        with ui.element("div").classes("m-monat-nav"):
            knopf("", lambda: a.setzen(tm_monat=(m.replace(day=1) - timedelta(days=1)).replace(day=1), laden=False), "leise",
                  "chevron_left", "Voriger Monat")
            ui.label(f"{MONATE[m.month - 1]} {m.year}").classes("m-btitel")
            knopf("", lambda: a.setzen(tm_monat=(m.replace(day=28) + timedelta(days=4)).replace(day=1), laden=False), "leise",
                  "chevron_right", "Nächster Monat")
            knopf("Heute", lambda: a.setzen(tm_monat=a.heute.replace(day=1), laden=False), "leise")
        ui.label("Klick auf einen Tag: neuer Termin · Klick auf einen Eintrag: öffnen").classes("m-zweite m-monat-tipp")
    je_tag: dict[date, list] = {}
    for t in a.daten["termine"]:
        je_tag.setdefault(t.datum, []).append(t)
    with a.inhalt:
        with ui.element("div").classes("m-monat"):
            for w in ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"):
                ui.label(w).classes("m-monat-kopf")
            for woche in calendar.Calendar().monthdatescalendar(m.year, m.month):
                for d in woche:
                    kl = "m-monat-tag" + (" fremd" if d.month != m.month else "") + (" heute" if d == a.heute else "") + \
                         (" we" if d.weekday() >= 5 else "")
                    zelle = ui.element("div").classes(kl)
                    attr(zelle, title=f"{WT[d.weekday()]} {d:%d.%m.%Y} – Klick: neuer Termin", role="button", tabindex="0")
                    with zelle:
                        with ui.element("div").classes("m-monat-zk"):
                            ui.label(str(d.day)).classes("m-monat-nr")
                            ui.icon("add").classes("m-monat-plus")
                        ts = je_tag.get(d, [])
                        for t in ts[:4]:
                            c = ui.label(t.titel).classes(f"m-chip {FARBE.get(t.art, '')}" + (" fertig" if t.erledigt else ""))
                            attr(c, title=f"{tm.ARTEN.get(t.art, t.art)}: {t.titel}\n{t.text}".strip())
                            c.on("click.stop", lambda t=t: termin_oeffnen(a, t))
                        if len(ts) > 4:
                            mehr = ui.label(f"+{len(ts) - 4} weitere").classes("m-zweite m-monat-mehr")
                            mehr.on("click.stop", lambda d=d: tag_panel(a, d))
                    zelle.on("click", lambda d=d: termin_panel(a, None, d))
                    zelle.on("keydown.enter", lambda d=d: termin_panel(a, None, d))


def termin_oeffnen(a, t) -> None:
    """Eigene Termine zum Bearbeiten, alle anderen (Anreise, Abreise, UWT …) zum Ansehen und Abhaken."""
    if t.art == "eigen":
        return termin_panel(a, t, t.datum)

    def bauen():
        ui.label(f"{tm.ARTEN.get(t.art, t.art)} · {WT[t.datum.weekday()]} {t.datum:%d.%m.%Y}").classes("m-zweite")
        ui.label(t.titel).classes("m-name")
        if t.text:
            ui.label(t.text).classes("m-ptext")
        ui.label("Dieser Eintrag kommt aus Anreiseliste/UWT und wird dort geändert – hier nur abhaken.").classes("m-zweite")

        async def umschalten():
            if await a.aendern(erledigt_setzen, t.id, not t.erledigt):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Wieder offen" if t.erledigt else "Erledigt", umschalten, "primaer", "check")
            knopf("Neuer Termin an diesem Tag", lambda: termin_panel(a, None, t.datum), "leise", "add")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(tm.ARTEN.get(t.art, "Termin"), bauen)


def tag_panel(a, d: date) -> None:
    """Alle Einträge eines Tages (wenn im Kalender nicht alle Platz haben)."""
    ts = [t for t in a.daten["termine"] if t.datum == d]

    def bauen():
        for t in ts:
            with ui.element("div").classes("m-mzeile"):
                ui.label(tm.ARTEN.get(t.art, t.art)).classes(f"m-pille {FARBE.get(t.art, '')}")
                c = ui.label(t.titel).classes("m-ptext m-link" + (" fertig" if t.erledigt else ""))
                c.on("click", lambda t=t: termin_oeffnen(a, t))
        with ui.element("div").classes("m-paktionen"):
            knopf("Neuer Termin an diesem Tag", lambda: termin_panel(a, None, d), "primaer", "add")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(f"{WT[d.weekday()]} {d:%d.%m.%Y} · {len(ts)} Einträge", bauen)


def termin_panel(a, t, tag: date) -> None:
    def bauen():
        ui.label("Eigener Termin mit Erinnerung – er erscheint an dem Tag (bzw. so viele Tage vorher) unter Heute."
                 ).classes("m-ptext")
        if not t:
            ui.label(f"für {WT[tag.weekday()]} {tag:%d.%m.%Y}").classes("m-zweite")
        titel = ui.input("Titel", value=t.titel if t else "").classes("m-feld").props("dense outlined dark autofocus")
        datum = ui.input("Datum", value=(t.datum if t else tag).isoformat()).classes("m-feld").props("dense outlined dark type=date")
        vorlauf = ui.select({0: "am Tag selbst", 1: "1 Tag vorher", 2: "2 Tage vorher", 3: "3 Tage vorher", 7: "1 Woche vorher",
                             -1: "keine Erinnerung"}, value=t.vorlauf if t else 1, label="Erinnern").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        text = ui.textarea("Notiz (optional)", value=t.text if t else "").classes("m-feld").props("outlined dark autogrow")

        async def speichern():
            try:
                d = date.fromisoformat(datum.value)
            except (TypeError, ValueError):
                a.toast("Bitte ein Datum wählen.", fehler=True)
                return
            if await a.aendern(eigener_speichern, t.id if t else "", d, titel.value or "", text.value or "", int(vorlauf.value)):
                a.panel_zu()

        async def loeschen():
            if await a.aendern(eigener_loeschen, t.id):
                a.panel_zu()

        titel.on("keydown.enter", speichern)

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            if t:
                knopf("Löschen", loeschen, "leise", "delete")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Termin bearbeiten" if t else "Neuer Termin", bauen)
