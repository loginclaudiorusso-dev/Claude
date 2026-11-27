"""1.75: Belegungsprognose → Ansicht „Berechnung“ – der genaue Rechenweg als eigene Seite (statt versteckt unter
„Details anzeigen“ → Monat anklicken). 1.76: für Laien – „Kurz gesagt“, jeder Schritt in Alltagssprache mit den
echten Zahlen, Begriffe erklärt; Formel und Rechnung für Fachleute aufklappbar und als Gleichung gesetzt.

Oben die Monate der Prognose zum Auswählen (mit erwartetem Wert und Band), darunter der vollständige Rechenweg des
gewählten Monats aus ``rechenweg_kern`` (Datenbasis, Rückwärtstest aller Modelle, Zerlegung des gewählten Modells,
gebuchter Bestand, Unsicherheitsband, bei „Gesamt“ die Korrelation der Standorte) und die Modellwahl mit dem
Backtest. Rechnet mit denselben Zahlen wie das Diagramm – nichts wird gespeichert.
"""

from __future__ import annotations

from nicegui import ui

from belegung import konfig

from . import auswertung_kern as ak
from .ui_bausteine import knopf, leer


def _z(x) -> str:
    return "–" if x is None else f"{x:,.0f}".replace(",", ".")


def monate(pg, kap: int) -> list:
    """Prognosemonate (ohne Ist) als Szenario-Zeilen mit ihrem Index in ``pg.zeilen``."""
    return [(i, z) for i, z in enumerate(ak.szenario(pg, kap, 0)) if z.art != "ist"]


def _mathe(text: str) -> str:
    """1.76: Formel/Rechnung lesbar setzen – Mathematik-Schrift, Rechenzeichen mit Luft, Ergebnis hervorgehoben."""
    import html
    import re

    t = html.escape(text)
    t = re.sub(r"\^(?:\(([^)]+)\)|([A-Za-z0-9]+))", lambda m: f"<sup>{m.group(1) or m.group(2)}</sup>", t)        # φ^H → φᴴ (hochgestellt)
    t = re.sub(r"\s*(=|÷|×|\+|→|←|≈)\s*", lambda m: f' <span class="op">{m.group(1)}</span> ', t)
    t = re.sub(r"\s+−\s+", ' <span class="op">−</span> ', t)          # Minus nur als Rechenzeichen, nicht „−3“
    t = re.sub(r"(\d)\s*·\s*(?=[\d√(])", r'\1 <span class="op">·</span> ', t)
    return t


def _zeilen(text: str, pfeil: bool = False) -> list[str]:
    """Eine Gleichung je Zeile („ · “ trennt); ``pfeil``: auch an „ → “ umbrechen (Pfeil bleibt am Zeilenanfang)."""
    import re

    teile = [x.strip() for x in text.split(" · ") if x.strip()]
    if pfeil:
        teile = [y for x in teile for y in re.split(r"\s+(?=→ )", x)]
    return teile


def _formel_block(s) -> None:
    """„Für Fachleute“: Formel und Rechnung als gesetzte Gleichungen, Zusatzwerte als kleine Liste."""
    if s.formel:
        ui.label("Formel").classes("m-rb-mk")
        ui.html("".join(f'<div class="m-rb-gl">{_mathe(z)}</div>' for z in _zeilen(s.formel)), sanitize=False)
    if s.rechnung:
        ui.label("Mit den Zahlen dieses Monats").classes("m-rb-mk")
        zeilen = []
        import re

        for z in _zeilen(s.rechnung, pfeil=True):
            m = _mathe(z)
            rest = z.rsplit("=", 1)[-1].strip() if "=" in z else ""
            links = z.rsplit("=", 1)[0]
            gerechnet = z.startswith("→") or re.search(r"[+×÷·]| − |Ø\(|max\(|√", links)
            if gerechnet and re.fullmatch(r"[±−+]?\d[\d.]*(,\d+)?( %)?", rest):   # nur ein Rechenergebnis hervorheben
                gl = '<span class="op">=</span>'
                i = m.rfind(gl)
                m = m[:i] + gl + ' <b class="m-rb-erg">' + m[i + len(gl):].strip() + "</b>"
            zeilen.append(f'<div class="m-rb-gl">{m}</div>')
        ui.html("".join(zeilen), sanitize=False)
    if s.details:
        with ui.element("ul").classes("m-rb-det"):
            for x in s.details:
                with ui.element("li"):
                    ui.label(x)


GLOSSAR = [
    ("Vorhersage (erwartet)", "Die Zahl, mit der am ehesten zu rechnen ist – ein Mittelwert, kein Versprechen."),
    ("8 von 10 Fällen (dunkles Band)", "In diesem Bereich lag der echte Wert früher in 8 von 10 Fällen. Gut zum Planen."),
    ("19 von 20 Fällen (helles Band)", "Fast sicher: nur in 1 von 20 Fällen lag der echte Wert außerhalb. Gut für "
                                       "„Was ist das Schlimmste, womit wir rechnen müssen?“"),
    ("Rückwärtstest", "Das Programm tut so, als wäre es ein früherer Zeitpunkt, sagt von dort voraus und vergleicht mit "
                      "dem, was wirklich kam. So sieht man, wie gut ein Rechenweg trifft."),
    ("Saison / Monatsmuster", "Wiederkehrende Schwankungen im Jahr, z. B. weniger Belegung im Sommer."),
    ("Trend", "Ob die Belegung über längere Zeit eher steigt oder fällt."),
    ("Gebuchter Bestand", "Was für einen Monat schon fest gebucht ist. Die Vorhersage liegt nie darunter."),
]


def zeichnen(a, pg, kap: int) -> None:
    from . import rechenweg_kern as rw

    zs = monate(pg, kap)
    with a.inhalt:
        wurzel = ui.element("div").classes("m-ex m-rb")
    with wurzel:
        if not zs:
            leer("Für diese Auswahl gibt es keine Prognosemonate.")
            return
        idx = [i for i, _z_ in zs]
        if getattr(a, "aw_rw_monat", None) not in idx:
            a.aw_rw_monat = idx[0]
        ort = konfig.STANDORT_LABEL.get(a.aw_standort, a.aw_standort)
        with ui.element("section").classes("m-block"):
            with ui.element("div").classes("m-paktionen").style("align-items:center"):
                ui.html('<b class="m-fx-zeichen">ƒx</b>', sanitize=False)
                ui.label(f"So entsteht die Vorhersage · {ort}").classes("m-btitel")
                ui.label(("Brutto" if a.aw_brutto else "Netto") + f" · Datenstand {a.daten['stichtag']:%d.%m.%Y}"
                         ).classes("m-zweite")
                knopf("Zum Diagramm", lambda: a.setzen(aw_chart="trend", nur_seite=True), "leise", "show_chart",
                      "Zurück zu Trend & Prognose").style("margin-left:auto")
            ui.label("Wählen Sie einen Monat. Darunter steht Schritt für Schritt in einfachen Worten, wie die Zahl "
                     "zustande kommt – die genaue Mathematik lässt sich bei jedem Schritt aufklappen.").classes("m-zweite")
            with ui.element("div").classes("m-rb-monate"):
                for i, z in zs:
                    b = ui.element("button").classes("m-rb-monat" + (" an" if i == a.aw_rw_monat else ""))
                    with b:
                        ui.label(ak.monat_text(z.monat)).classes("m-name")
                        ui.label(f"rund {_z(z.erwartet)} ({_z(z.lo80)}–{_z(z.hi80)})").classes("m-zweite")
                    b.on("click", lambda i=i: a.setzen(aw_rw_monat=i, nur_seite=True))
        i = a.aw_rw_monat
        z, pz = dict(zs)[i], pg.zeilen[i]
        try:
            schritte = rw.rechenweg((a.daten or {}).get("ds"), a.aw_standort, z.monat, pz.vertraege,
                                    {"erwartet": z.erwartet, "lo80": z.lo80, "hi80": z.hi80, "lo95": z.lo95,
                                     "hi95": z.hi95})
        except Exception as exc:                          # noqa: BLE001 – lieber erklären als abstürzen
            schritte = []
            ui.label(f"Der Rechenweg ließ sich nicht nachrechnen: {exc}").classes("m-zweite")
        if not schritte:
            leer("Für diesen Monat liegt kein Rechenweg vor.")
            return
        ergebnis = next((s for s in reversed(schritte) if s.titel == "Ergebnis"), None)
        with ui.element("section").classes("m-block m-rb-kurz"):
            ui.label(f"Kurz gesagt – {ak.monat_text(z.monat)}").classes("m-rb-mk")
            ui.label(ergebnis.einfach if ergebnis and ergebnis.einfach else
                     f"Erwartet werden rund {_z(z.erwartet)} belegte Plätze, sehr wahrscheinlich zwischen "
                     f"{_z(z.lo80)} und {_z(z.hi80)}.").classes("m-rb-satz")
        ui.label(f"So entsteht die Zahl – in {len(schritte)} Schritten").classes("m-abschnitt")
        for n, s in enumerate(schritte, 1):
            with ui.element("section").classes("m-block m-rb-schritt"):
                with ui.element("div").classes("m-rb-kopf"):
                    ui.label(str(n)).classes("m-rb-nr")
                    with ui.element("div"):
                        ui.label(s.kurz or s.titel).classes("m-name")
                        if s.kurz and s.kurz != s.titel:
                            ui.label(s.titel).classes("m-zweite")
                if s.einfach:
                    ui.label(s.einfach).classes("m-rb-text")
                if s.formel or s.rechnung or s.details:
                    with ui.expansion("Für Fachleute: Formel und Rechnung", icon="functions").classes("m-rb-fach"):
                        _formel_block(s)
        with ui.expansion("Begriffe kurz erklärt", icon="menu_book").classes("m-block m-rb-fach"):
            for wort, erkl in GLOSSAR:
                with ui.element("div").classes("m-rb-gloss"):
                    ui.label(wort).classes("m-name")
                    ui.label(erkl).classes("m-zweite")
        with ui.expansion("Für Fachleute: alle Rechenwege im Vergleich und Rückblick", icon="query_stats") \
                .classes("m-rb-fach"):
            from .seite_prognose import _methodik

            _methodik(a, pg)
        with ui.element("div").classes("m-paktionen"):
            knopf("Teilnehmer je Maßnahme", lambda: a.oeffnen(
                "auswertung", ansicht="massnahmen", mn_ansicht="prognose",
                von=("Belegungs\u00adprognose", "auswertung", "prognose")), "leise", "groups",
                "Teilnehmer je Maßnahme – dort im Diagramm einen Monat anklicken: Rechenweg der Simulation")


CSS = """
.m-rb-monate { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.m-rb-monat { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; padding: 6px 10px;
  border-radius: var(--r, 8px); border: 1px solid var(--rand);
  background: transparent; color: inherit; cursor: pointer; text-align: left; }
.m-rb-monat:hover { border-color: var(--akzent); }
.m-rb-monat.an { border-color: var(--akzent); box-shadow: inset 0 0 0 1px var(--akzent); }
.m-rb-kurz { border-left: 4px solid var(--akzent); }
.m-rb-satz { font-size: 1.15rem; line-height: 1.55; white-space: normal; }
.m-rb-mk { font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; opacity: .7; margin: 10px 0 4px; }
.m-rb-schritt { margin-top: 10px; }
.m-rb-kopf { display: flex; gap: 12px; align-items: center; }
.m-rb-nr { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  background: var(--akzent); color: #fff; font-weight: 700; flex: none; }
.m-rb-text { margin: 8px 0 0 40px; line-height: 1.6; white-space: normal; max-width: 900px; }
.m-rb-fach { margin: 6px 0 0 30px; }
.m-rb-gl { font-family: "Cambria Math", "STIX Two Math", "Latin Modern Math", Cambria, Georgia, serif;
  font-size: 1.08rem; line-height: 1.7; padding: 3px 0 3px 14px; border-left: 2px solid var(--rand);
  font-variant-numeric: tabular-nums; white-space: normal; }
.m-rb-gl .op { color: var(--akzent); padding: 0 .18em; font-weight: 600;
  font-family: "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif; font-size: 1.05em; }
.m-rb-gl sup { font-size: .7em; }
.m-rb-erg { background: var(--s-akzent-bg, rgba(11,110,102,.12)); color: inherit; border-radius: 6px;
  padding: 1px 8px; font-weight: 700; }
.m-rb-det { margin: 8px 0 4px 16px; padding: 0; font-size: .85rem; opacity: .85; }
.m-rb-det li { white-space: normal; margin: 2px 0; }
.m-rb-gloss { display: grid; grid-template-columns: minmax(180px, 260px) 1fr; gap: 12px; padding: 6px 0;
  border-bottom: 1px solid var(--rand); }
.m-rb-gloss > * { white-space: normal; }
"""
