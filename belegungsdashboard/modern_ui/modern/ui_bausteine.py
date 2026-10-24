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


def kennzahlen(werte: list[tuple], aktiv=None, bei_klick=None, titel: dict | None = None) -> None:
    """Klickbare Kennzahl-Kacheln: (Schlüssel, Zahl, Text, Farbe ok|warn|krit|akzent|neutral|blau).
    Die aktive Kachel ist hervorgehoben; ein Klick ruft ``bei_klick(Schlüssel)`` (Filter oder Sprung)."""
    with ui.element("div").classes("m-stats").props('role="group"'):
        for schluessel, zahl, text, farbe in werte:
            an = aktiv is not None and schluessel == aktiv
            b = ui.element("button").classes(f"m-stat {farbe}" + (" an" if an else ""))
            attr(b, aria_pressed=str(an).lower(), title=(titel or {}).get(schluessel, "Klick: filtern" if bei_klick else ""))
            with b:
                ui.label(str(zahl)).classes("z")
                with ui.element("span").classes("l"):
                    ui.element("i")
                    ui.label(text)
            if bei_klick:
                b.on("click", lambda s=schluessel: bei_klick(s))
