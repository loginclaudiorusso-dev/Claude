"""Startseite „Heute“: links alles, was zu tun ist (Aufgaben-Karten mit 1-Klick-Lösung), rechts der Tag auf einen
Blick – Zimmer, Anreisen der nächsten Tage, Abreisen, Reinigung, Neuigkeiten."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from nicegui import ui

from .kern import WT, kurz
from .ui_bausteine import attr, knopf, leer


@dataclass
class Tag:
    zimmer: dict
    anreisen: list = field(default_factory=list)        # (Kennung, Text, Personen, mit Zimmer)
    abreisen: list = field(default_factory=list)        # (Tag-Text, Name, Zimmer)
    reinigung: tuple = (0, 0)                            # (eilig, offen heute)
    neuigkeiten: list = field(default_factory=list)     # (Zeit-Text, Text, Art)


def tag_daten(stand, heute: date) -> Tag:
    from belegung import cockpit, neuigkeiten

    t = Tag(cockpit.zimmer_heute(stand, heute))
    for a in cockpit.anreisen(stand, heute, 7):
        t.anreisen.append((a.tag.isoformat(), f"{WT[a.tag.weekday()]} {a.tag:%d.%m.} · {a.text}", a.personen, a.mit_zimmer))
    for a in cockpit.abreisen(stand, heute, 1):
        t.abreisen.append(("heute" if a.tag == heute else "morgen", a.name, kurz(a.zimmer)))
    dringend, offen = cockpit.reinigung_heute(stand, heute)
    t.reinigung = (len(dringend), len(offen))
    grenze = datetime.now() - timedelta(hours=48)
    for n in neuigkeiten.laden()[:30]:
        if n.zeit >= grenze:
            t.neuigkeiten.append((f"{n.zeit:%d.%m. %H:%M}", n.text, n.art))
    t.neuigkeiten = t.neuigkeiten[:8]
    return t


def daten(a) -> None:
    a.daten = tag_daten(a.stand, a.heute)


def zeichnen(a) -> None:
    t: Tag = a.daten
    z = t.zimmer
    with a.leiste:
        wt = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][a.heute.weekday()]
        ui.html(f'<span class="m-kpi">{wt}, {a.heute:%d.%m.%Y}<span class="m-punktt">·</span><b>{z["frei"]}</b> frei'
                f'<span class="m-punktt">·</span><b>{z["belegt"]}</b> belegt<span class="m-punktt">·</span>'
                f'<b>{z["gesperrt"]}</b> gesperrt<span class="m-punktt">·</span>'
                f'<b>{z["ohne_zimmer"]}</b> Anreisen ohne Zimmer (8 Wochen)</span>', sanitize=False)
    with a.inhalt:
        with ui.element("div").classes("m-heute"):
            with ui.element("section").classes("m-heute-links"):
                ui.label("Zu tun").classes("m-btitel")
                if not a.karten:
                    leer("Alles erledigt. Neue Aufgaben erscheinen hier von selbst.")
                for stufe, titel in (("dringend", "Dringend"), ("bald", "Als Nächstes"), ("info", "Zur Info")):
                    ks = [k for k in a.karten if k.stufe == stufe]
                    if ks:
                        ui.label(titel).classes("m-cgruppe")
                    for k in ks:
                        a._karte(k)
            with ui.element("section").classes("m-heute-rechts"):
                with ui.element("div").classes("m-block"):
                    ui.label("Anreisen der nächsten 7 Tage").classes("m-btitel")
                    if not t.anreisen:
                        ui.label("Keine Anreisen.").classes("m-ptext")
                    for kennung, text, n, mit in t.anreisen:
                        z_ = ui.element("button").classes("m-liste-zeile")
                        with z_:
                            ui.element("div").classes("m-ampel " + ("ok" if mit == n else "krit")).style("margin:0")
                            attr(ui.label(text).classes("m-name"), title=text)
                            ui.label(f"{mit}/{n}").classes("m-mono")
                        z_.on("click", lambda k=kennung: a.oeffnen("anreisen", kennung=k))
                with ui.element("div").classes("m-block"):
                    ui.label("Abreisen heute und morgen").classes("m-btitel")
                    if not t.abreisen:
                        ui.label("Keine Abreisen.").classes("m-ptext")
                    for wann, name, zimmer in t.abreisen[:12]:
                        with ui.element("div").classes("m-liste-zeile"):
                            ui.label(wann).classes("m-zweite").style("width:52px")
                            ui.label(name).classes("m-name")
                            ui.label(zimmer).classes("m-mono")
                    if len(t.abreisen) > 12:
                        knopf(f"Alle {len(t.abreisen)} ansehen", lambda: a.oeffnen("anreisen", ansicht="abreisen"), "leise")
                with ui.element("div").classes("m-block"):
                    ui.label("Reinigung heute").classes("m-btitel")
                    eilig, offen = t.reinigung
                    ui.html(f'<span class="m-kpi"><b style="color:var(--rot)">{eilig}</b> vor Einzug noch offen'
                            f'<span class="m-punktt">·</span><b>{offen}</b> weitere heute</span>', sanitize=False)
                    knopf("Reinigungsliste öffnen", lambda: a.oeffnen("reinigung", rg_zeitraum="heute"), "", "cleaning_services")
                if t.neuigkeiten:
                    with ui.element("div").classes("m-block"):
                        ui.label("Neu seit gestern").classes("m-btitel")
                        for zeit, text, art in t.neuigkeiten:
                            with ui.element("div").classes("m-neu"):
                                ui.element("div").classes("m-ampel " + {"warnung": "warn", "fehler": "krit"}.get(art, "ok")).style(
                                    "margin:6px 0 0")
                                with ui.element("div"):
                                    ui.label(text).classes("m-ptext").style("color:var(--text)")
                                    ui.label(zeit).classes("m-zweite")
