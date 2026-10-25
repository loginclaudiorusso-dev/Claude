"""Kleine Bausteine der Oberfläche: Knopf, Attribute, Segmented Control, Leer-Hinweis."""

from __future__ import annotations

from nicegui import ui


def attr(el, **werte):
    """HTML-Attribute ohne Quoting-Probleme (Namen und Texte können Anführungszeichen enthalten)."""
    for k, v in werte.items():
        el._props[k.replace("_", "-")] = v
    el.update()
    return el


def knopf(text: str, on_click=None, art: str = "", icon: str = "", titel: str = ""):
    b = ui.element("button").classes(f"m-knopf {art}".strip())
    if titel:
        attr(b, title=titel)
    with b:
        if icon:
            ui.icon(icon)
        if text:
            ui.label(text)
    if on_click:
        b.on("click", on_click)
    return b


def segmente(optionen: dict, aktiv, bei_klick) -> None:
    """Segmented Control: ein Knopf je Option, der aktive hervorgehoben."""
    with ui.element("div").classes("m-segm").props('role="group"'):
        for wert, text in optionen.items():
            b = ui.element("button").classes("an" if wert == aktiv else "")
            attr(b, aria_pressed=str(wert == aktiv).lower())
            with b:
                ui.label(str(text))
            b.on("click", lambda wert=wert: bei_klick(wert))


def leer(text: str) -> None:
    ui.label(text).classes("m-leer")


# Zustände – überall dieselbe Farbe, dasselbe Symbol, derselbe Text
ZUSTAND = {
    "frei": ("ok", "check_circle", "frei"), "teilweise": ("ok", "adjust", "1 Bett frei"),
    "belegt": ("blau", "person", "belegt"), "geplant": ("akzent", "schedule", "geplant"),
    "gesperrt": ("neutral", "block", "gesperrt"), "maengel": ("warn", "priority_high", "Mängel"),
    "unbewohnbar": ("krit", "report", "unbewohnbar"), "pruefen": ("warn", "warning", "prüfen"),
    "ohne": ("krit", "person_off", "ohne Zimmer"),
}
SYMBOLE = {**{k: v[1] for k, v in ZUSTAND.items()}, "ohne": "person_off", "handeln": "error", "alle": "groups",
           "np": "trending_flat", "offen": "pending", "eilig": "bolt", "erledigt": "task_alt", "laufend": "key",
           "mail": "mail", "weitere": "apartment", "neu": "fiber_new", 3: "report", 2: "priority_high", 1: "info"}


def badge(zustand: str, text: str | None = None, zahl: int | None = None) -> None:
    """Farbiges Zustands-Badge mit Symbol (frei, belegt, geplant, gesperrt, Mängel, unbewohnbar) – optional mit Anzahl."""
    farbe, icon, standard = ZUSTAND.get(zustand, ("neutral", "help", zustand))
    with ui.element("span").classes(f"m-badge {farbe}"):
        ui.icon(icon)
        ui.label(text or standard)
        if zahl is not None:
            ui.label(str(zahl)).classes("m-badge-n")


def badge_neu(seit) -> None:
    """Kleines „NEU“-Badge – seit wann die Person in den Listen steht."""
    from datetime import date

    tage = (date.today() - seit).days
    attr(ui.label("NEU").classes("m-neu-badge"),
         title="heute neu in den Listen" if tage <= 0 else f"neu seit {seit:%d.%m.} ({tage} Tag{'e' if tage > 1 else ''})")


def kennzahlen(werte: list[tuple], aktiv=None, bei_klick=None, titel: dict | None = None) -> None:
    """Klickbare Kennzahl-Kacheln: (Schlüssel, Zahl, Text, Farbe ok|warn|krit|akzent|neutral|blau).
    Die aktive Kachel ist hervorgehoben; ein Klick ruft ``bei_klick(Schlüssel)`` (Filter oder Sprung)."""
    with ui.element("div").classes("m-stats").props('role="group"'):
        for schluessel, zahl, text, farbe in werte:
            an = aktiv is not None and schluessel == aktiv
            b = ui.element("button").classes(f"m-stat {farbe}" + (" an" if an else ""))
            attr(b, aria_pressed=str(an).lower(), title=(titel or {}).get(schluessel, "Klick: filtern" if bei_klick else ""))
            with b:
                with ui.element("span").classes("k"):
                    ui.icon(SYMBOLE.get(schluessel, "circle")).classes("s")
                    ui.label(str(zahl)).classes("z")
                with ui.element("span").classes("l"):
                    ui.label(text)
            if bei_klick:
                b.on("click", lambda s=schluessel: bei_klick(s))
