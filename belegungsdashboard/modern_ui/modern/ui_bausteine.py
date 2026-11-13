"""Kleine Bausteine der Oberfläche: Knopf, Attribute, Segmented Control, Leer-Hinweis."""

from __future__ import annotations

from nicegui import ui


def attr(el, **werte):
    """HTML-Attribute ohne Quoting-Probleme (Namen und Texte können Anführungszeichen enthalten)."""
    for k, v in werte.items():
        el._props[k.replace("_", "-")] = v
    el.update()
    return el


# 1.01: Werkzeuge der Seite im Menüband – die gemeinsamen Bausteine zeichnen sich dort als Office-Knöpfe (groß, mit
# Fluent-Symbol), sobald sie in der Werkzeugzeile einer Seite stehen. ``BAND["an"]`` setzt die Oberfläche je Zeichnen.
BAND = {"an": False}


def im_band() -> bool:
    """Wird gerade in die Werkzeugzeile (m-werkzeuge / m-leiste) gebaut – und nicht in eine schon gebaute Band-Gruppe?"""
    if not BAND["an"]:
        return False
    try:
        el = ui.context.slot.parent
        for _ in range(12):
            if el is None:
                return False
            k = getattr(el, "_classes", []) or []
            if ("m-bg" in k and "m-bg-auto" not in k) or "q-menu" in k or el.tag in ("q-menu", "q-dialog"):
                return False
            if "m-werkzeuge" in k or "m-leiste" in k:
                return True
            el = el.parent_slot.parent if getattr(el, "parent_slot", None) else None
    except Exception:                                   # noqa: BLE001 – im Zweifel wie bisher zeichnen
        return False
    return False


def knopf(text: str, on_click=None, art: str = "", icon: str = "", titel: str = ""):
    if im_band() and "m-seg-ansicht" not in art:
        from . import band_ui, symbole

        name, farbe = symbole.aus_material(icon) if icon else symbole.aus_text(text)
        if not text and on_click is None:                # Menü-Knopf ohne Text (z. B. „⋯ Mehr“) → großer Knopf mit Pfeil
            text = "Mehr" if icon in ("more_horiz", "") else (titel.split(":")[0].split(" – ")[0][:22] or "Menü")
        if text:
            return band_ui.gross(text, name, farbe, on_click, tipp=titel, pfeil=on_click is None,
                                 primaer="primaer" in art)
        return band_ui.klein("", name, farbe, on_click, tipp=titel, pfeil=False)
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


def segmente(optionen: dict, aktiv, bei_klick, sofort: bool = False, ansicht: bool = False) -> None:
    """Segmented Control: ein Knopf je Option, der aktive hervorgehoben.

    ``ansicht``: Umschalter der Unteransichten einer Seite – im Menüband-Layout ausgeblendet (dort stehen sie im Band).

    ``sofort``: der Knopf wird schon im Browser umgestellt (ohne auf den Server zu warten) – für Filter, die neu laden."""
    if not ansicht and im_band():                      # 1.01: im Menüband als gestapelte Auswahlknöpfe
        from . import band_ui

        werte = list(optionen.items())
        # 1.02: EIN Block statt verteilter Stapel – bis 3 untereinander, 4 (z. B. die Standorte) in einer Reihe,
        # ab 5 in Spalten zu je 3 (ohne Trennlinie dazwischen)
        art = "reihe" if len(werte) == 4 else ("raster" if len(werte) > 4 else "")
        with band_ui.stapel(reihe=art == "reihe", raster=art == "raster"):
            for wert, text in werte:
                band_ui.auswahl(str(text), wert == aktiv, lambda wert=wert: bei_klick(wert))
        return
    with ui.element("div").classes("m-segm" + (" m-seg-ansicht" if ansicht else "")).props('role="group"'):
        for wert, text in optionen.items():
            b = ui.element("button").classes("an" if wert == aktiv else "")
            attr(b, aria_pressed=str(wert == aktiv).lower())
            with b:
                ui.label(str(text))
            b.on("click", lambda wert=wert: bei_klick(wert),
                 js_handler="(...args) => { if (window.mSofort) mSofort(args[0]); emit(...args); }" if sofort
                 else "(...args) => emit(...args)")


def tabelle(spalten: str, klasse: str = ""):
    """0.46: Tabellenvorlage – Kopfzeile und Zeilen teilen EIN Spaltenraster (CSS subgrid). So steht die Kopfzeile immer
    genau über den Werten, auch wenn Spalten nach Inhalt breiter werden. Darin wie gewohnt ``m-raster m-tkopf`` und
    ``m-raster m-zeile`` anlegen (deren eigene Spaltenangabe wird überschrieben); Sortieren per Klick bleibt."""
    return ui.element("div").classes(f"m-tab {klasse}".strip()).style(f"grid-template-columns:{spalten}")


def leer(text: str) -> None:
    ui.label(text).classes("m-leer")


# Zustände – überall dieselbe Farbe, dasselbe Symbol, derselbe Text
ZUSTAND = {
    "frei": ("ok", "check_circle", "frei"), "teilweise": ("ok", "adjust", "1 Bett frei"),
    "belegt": ("blau", "person", "belegt"), "geplant": ("akzent", "schedule", "geplant"),
    "gesperrt": ("neutral", "block", "gesperrt"), "maengel": ("warn", "priority_high", "Mängel"),
    "nicht_nutzbar": ("neutral", "block", "nicht nutzbar"),                # 0.70: Zustand (Grund im Detail)
    "unbewohnbar": ("krit", "report", "unbewohnbar"), "pruefen": ("warn", "warning", "prüfen"),
    "ohne": ("warn", "person_off", "ohne Zimmer"),
}
SYMBOLE = {**{k: v[1] for k, v in ZUSTAND.items()}, "ohne": "person_off", "handeln": "error", "alle": "groups",
           "np": "trending_flat", "offen": "pending", "eilig": "bolt", "erledigt": "task_alt", "laufend": "key",
           "mail": "mail", "weitere": "apartment", "neu": "fiber_new", "bereit": "verified", "unfertig": "cleaning_services",
           "nicht_nutzbar": "block", 3: "report", 2: "priority_high",
           1: "info"}


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
    Die aktive Kachel (oder bei einer Menge: alle darin) ist hervorgehoben; ein Klick ruft ``bei_klick(Schlüssel)`` (Filter oder Sprung)."""
    if im_band():                                      # 1.01: im Menüband große Knöpfe mit Zahl
        from . import band_ui, symbole

        for schluessel, zahl, text, farbe in werte:
            an = aktiv is not None and (schluessel in aktiv if isinstance(aktiv, (set, frozenset)) else schluessel == aktiv)
            name, fb = symbole.ZUSTAND.get(schluessel) or symbole.TON.get(farbe, ("filter", ""))
            band_ui.gross(text, name, fb, (lambda s=schluessel: bei_klick(s)) if bei_klick else None, an=an, zahl=zahl,
                          tipp=(titel or {}).get(schluessel, "Klick: filtern" if bei_klick else ""))
        return
    with ui.element("div").classes("m-stats").props('role="group"'):
        for schluessel, zahl, text, farbe in werte:
            an = aktiv is not None and (schluessel in aktiv if isinstance(aktiv, (set, frozenset)) else schluessel == aktiv)
            null = str(zahl).strip() in ("0", "0 %", "–") and not an     # 0.69: Null-Werte leise (Menüband: grau)
            b = ui.element("button").classes(f"m-stat {farbe}" + (" an" if an else "") + (" null" if null else ""))
            attr(b, aria_pressed=str(an).lower(), title=(titel or {}).get(schluessel, "Klick: filtern" if bei_klick else ""))
            with b:
                with ui.element("span").classes("k"):
                    ui.icon(SYMBOLE.get(schluessel, "circle")).classes("s")
                    ui.label(str(zahl)).classes("z")
                with ui.element("span").classes("l"):
                    ui.label(text)
            if bei_klick:
                b.on("click", lambda s=schluessel: bei_klick(s))


def live_suche(feld, setzen, kennung: str, warten_ms: int = 350) -> None:
    """0.58: Suche beim Tippen – sobald man kurz innehält (``warten_ms``), ohne Enter. Nach dem Neuzeichnen steht der
    Cursor wieder im Suchfeld am Ende. ``setzen(text)`` gibt eine Coroutine zurück (z. B. ``a.setzen(...)``)."""
    feld.classes(f"m-live-{kennung}")
    fokus = (f"setTimeout(() => {{ const i = document.querySelector('.m-live-{kennung} input'); if (i) {{ i.focus(); "
             "const n = i.value.length; i.setSelectionRange(n, n); } }, 40)")

    async def los(e) -> None:
        text = e.args if isinstance(e.args, str) else (feld.value or "")
        await setzen(text or "")
        ui.run_javascript(fokus)
    feld.on("update:model-value", los,
            js_handler=f"(v) => {{ clearTimeout(window._mLive_{kennung}); "
                       f"window._mLive_{kennung} = setTimeout(() => emit(v ?? ''), {warten_ms}); }}")
