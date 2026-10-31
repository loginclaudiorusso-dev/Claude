"""Seite „Einstellungen“: Allgemein (Zimmerplanung, Erinnerungen, Engpass-Grenzen, KI), Zimmer-Stammdaten und
Sicherung & Verlauf. Gespeichert wird in denselben Einstellungen wie im Hauptprogramm."""

from __future__ import annotations

from datetime import datetime

from nicegui import run, ui

from belegung import datensicherung, eintragen, protokoll, speicher
from belegung import termine as tm
from belegung import zimmerplan as zp

from . import seiten_kern as sk
from .kern import _schritt
from .ui_bausteine import attr, knopf, leer, segmente
from .standort_kern import kurz as zkurz

ANSICHTEN = {"allgemein": "Allgemein", "stammdaten": "Zimmer-Stammdaten", "sicherung": "Sicherung & Verlauf"}
ZAHLEN = {   # Einstellung → (Text, Standard, min, max)
    "zimmer_puffer": ("Tage zwischen Abreise und nächster Belegung (1 = nicht am Abreisetag)", 1, 0, 7),
    "facility_monate": ("Facility-Check nach einem Aufenthalt ab … Monaten (Elektrik, Fenster)", 6, 1, 36),
    "anreise_standard_wochen": ("Anreisen ohne Abreise: angenommene Dauer in Wochen (0 = nur Termin)", 0, 0, 104),
}
ERINNERUNG = {"notiz_tage": "Notiz zur Anreise … Tage vorher", "abreise_tage": "Abreise-Erinnerung … Tage vorher",
              "abreise_tage_emr": "Abreise-Erinnerung EMR … Tage vorher"}


def daten(a) -> None:
    ansicht = a.ansicht_von("einstellungen", "allgemein")
    if ansicht == "allgemein":
        e = speicher.einstellungen()
        a.daten = {"zahlen": {k: int(e.get(k, s) or s) for k, (_t, s, _a, _b) in ZAHLEN.items()},
                   "bool": sk.einstellungen(), "termine": tm.einstellungen(), "grenzen": eintragen.grenzen(),
                   "ki": e.get("ki", {})}
    elif ansicht == "stammdaten":
        a.daten = {"zimmer": [z for z in a.stand.zimmer]}
    else:
        a.daten = {"sicherungen": datensicherung.liste(), "verlauf": protokoll.laden(150)}


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("einstellungen", "allgemein")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("einstellungen", ansicht=v))
    {"allgemein": _allgemein, "stammdaten": _stammdaten, "sicherung": _sicherung}[ansicht](a)


# ---- Allgemein --------------------------------------------------------------------------

def zahl_setzen(k: str, wert: int) -> str:
    text, _s, mi, ma = ZAHLEN[k]
    if not mi <= wert <= ma:
        raise ValueError(f"Bitte {mi} bis {ma}.")
    _schritt(text, lambda: speicher.einstellung_setzen(k, int(wert)), [speicher.EINSTELLUNGEN])
    return "Gespeichert"


def termin_setzen(k: str, wert: int) -> str:
    if not 0 <= wert <= 60:
        raise ValueError("Bitte 0 bis 60 Tage.")
    _schritt(ERINNERUNG[k], lambda: tm.einstellung_setzen(**{k: int(wert)}), [speicher.EINSTELLUNGEN])
    return "Gespeichert"


def grenzen_setzen(werte: dict) -> str:
    _schritt("Engpass-Grenzen", lambda: eintragen.grenzen_speichern(werte), [speicher.EINSTELLUNGEN])
    return "Grenzen gespeichert"


def ki_setzen(backend: str, modell: str, effort: str, lokal_url: str, lokal_modell: str, schluessel: str | None) -> str:
    from belegung.assistent import llm

    e = llm.Einstellungen.aus_dict(speicher.einstellungen().get("ki", {}))
    e.backend, e.claude_modell, e.claude_effort, e.lokal_url, e.lokal_modell = backend, modell, effort, lokal_url, lokal_modell
    _schritt("KI-Einstellungen", lambda: speicher.einstellung_setzen("ki", e.__dict__), [speicher.EINSTELLUNGEN])
    if schluessel:
        if not llm.schluessel_speichern(schluessel.strip()):
            raise ValueError("Der API-Schlüssel konnte nicht sicher gespeichert werden (Windows-Anmeldeinformationen).")
        return "KI-Einstellungen und Schlüssel gespeichert (sicher in der Windows-Anmeldeinformationsverwaltung)"
    return "KI-Einstellungen gespeichert"


def _zahlfeld(a, text: str, wert: int, speichern) -> None:
    with ui.element("div").classes("m-einst"):
        ui.label(text).classes("m-ptext")
        n = ui.number(value=wert, step=1, format="%d").classes("m-feld klein").props("dense outlined dark")
        n.on("blur", lambda: speichern(int(n.value or 0)) if int(n.value or 0) != wert else None)


def meldungen_setzen(an: bool) -> str:
    from . import melder

    melder.setzen(an)
    return "Windows-Meldungen an" if an else "Windows-Meldungen aus (Fälliges steht weiter unter Heute)"


def autostart_setzen(an: bool) -> str:
    from pathlib import Path

    from . import melder

    return melder.autostart_setzen(an, Path(__file__).resolve().parent.parent)


async def _schalten(a, aktion, wert: bool) -> None:
    """Einstellung ohne Rückgängig-Schritt (betrifft nicht die Planungsdaten)."""
    from nicegui import run

    try:
        a.toast(await run.io_bound(aktion, wert), rueck=False)
    except Exception as exc:                   # noqa: BLE001
        a.toast(f"Nicht geändert: {exc}", fehler=True, rueck=False)


def _windows(a) -> None:
    """Meldungen unten rechts (Termine, Reinigung vor Anreise, Facility-Checks) und „Mit Windows starten“."""
    from . import melder

    with ui.element("div").classes("m-schalter"):
        ui.switch("Windows-Meldungen: fällige Termine, offene Reinigung vor Anreise, Facility-Checks",
                  value=melder.an(), on_change=lambda e: _schalten(a, meldungen_setzen, e.value)
                  ).props("dense color=indigo-4")
    with ui.element("div").classes("m-schalter"):
        sw = ui.switch("Mit Windows starten (minimiert) – meldet Fälliges, ohne dass man das Programm öffnet",
                       value=melder.autostart_aktiv(), on_change=lambda e: _schalten(a, autostart_setzen, e.value)
                       ).props("dense color=indigo-4")
        if not melder.autostart_moeglich():
            sw.props("disable")
            ui.label("Nur unter Windows.").classes("m-zweite")
    ui.label(f"Geprüft wird beim Start und alle {melder.TAKT_MINUTEN} Minuten, jede Meldung einmal – auch wenn das "
             "Hauptprogramm gleichzeitig läuft.").classes("m-zweite")
    _briefing(a)
    _outlook_vorschau(a)


def _outlook_vorschau(a) -> None:
    """Ordner für die Outlook-Vorschau auf „Heute“ (nur lesen)."""
    from . import outlook_kern as ok

    ui.label("Outlook-Vorschau auf „Heute“").classes("m-btitel").style("margin-top:14px")
    ui.label("Zeigt die neuesten Mails eines Ordners (Betreff, Zeit, ungelesen) – nur lesen, es wird nichts gesendet, "
             "verschoben oder gelöscht. Postfach-Name wie in Outlook links, z. B. „Internatsdienst“ (dessen Posteingang) "
             "oder „Internatsdienst/Posteingang/Anreisen“. Leer = aus. Nur mit dem klassischen Outlook.").classes("m-ptext")
    with ui.element("div").classes("m-schalter"):
        feld = ui.input("Outlook-Ordner", value=ok.ordner()).classes("m-feld").props("dense outlined dark")

        async def speichern() -> None:
            a.toast(await run.io_bound(ok.einstellen, feld.value or ""), rueck=False)

        async def testen() -> None:
            await run.io_bound(ok.einstellen, feld.value or "")
            mails, fehler = await run.io_bound(ok.vorschau, True)
            a.toast(fehler or f"Verbindung klappt: {len(mails)} Mails gelesen", rueck=False, fehler=bool(fehler))
        knopf("Speichern", speichern, "", "check")
        knopf("Testen", testen, "leise", "bolt")


def _briefing(a) -> None:
    """Tagesbriefing: einmal am Tag die wichtigsten Punkte als Outlook-Termin oder E-Mail an mich (ohne Namen)."""
    from . import briefing_kern as bk

    ui.label("Tagesbriefing per Outlook").classes("m-btitel").style("margin-top:14px")
    ui.label("Einmal am Tag ab der Uhrzeit: Dringendes, Anreisen (bezugsfertig?), Abreisen, Reinigung, Allergiker – "
             "ohne Personennamen.").classes("m-ptext")
    with ui.element("div").classes("m-schalter"):
        weg = ui.select(bk.KANAELE, value=bk.kanal(), label="Weg").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        zeit = ui.input("Uhrzeit", value=f"{bk.uhrzeit():%H:%M}").classes("m-feld").props("dense outlined dark type=time")

        async def speichern() -> None:
            try:
                a.toast(await run.io_bound(bk.einstellen, weg.value, zeit.value), rueck=False)
            except Exception as exc:           # noqa: BLE001
                a.toast(f"Nicht geändert: {exc}", fehler=True, rueck=False)
        weg.on_value_change(speichern)
        zeit.on("change", speichern)
    vorschau = ui.element("pre").classes("m-briefing")
    vorschau.set_visibility(False)

    async def zeigen() -> None:
        b = await run.io_bound(lambda: bk.erstellen(zp.laden(), a.heute))
        vorschau.clear()
        with vorschau:
            ui.html(f"<b>{_esc(b.betreff)}</b>\n\n{_esc(b.text)}", sanitize=False)
        vorschau.set_visibility(True)

    async def testen() -> None:
        art = weg.value if weg.value != "aus" else "mail"
        try:
            a.toast(await run.io_bound(lambda: bk.senden(zp.laden(), art=art, test=True)), rueck=False)
        except Exception as exc:               # noqa: BLE001
            a.toast(str(exc), fehler=True, rueck=False)
    with ui.element("div").classes("m-schalter"):
        knopf("Vorschau", zeigen, "", "visibility")
        knopf("Jetzt testen", testen, "", "send", titel="Schickt das Briefing sofort (zählt nicht als heutiges)")
        st = bk.status()
        if st:
            ui.label(f"Zuletzt {st['datum'][8:10]}.{st['datum'][5:7]}. {st.get('zeit', '')} – "
                     + ("geschickt" if st.get("ok") else f"nicht geschickt: {st.get('fehler', '')}")).classes("m-zweite")


def _esc(t: str) -> str:
    import html

    return html.escape(t)


def _allgemein(a) -> None:
    d = a.daten
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            _darstellung(a)
            with ui.element("section").classes("m-block"):
                ui.label("Zimmerplanung").classes("m-btitel")
                for k, (text, _s, _mi, _ma) in ZAHLEN.items():
                    _zahlfeld(a, text, d["zahlen"][k], lambda w, k=k: a.aendern(zahl_setzen, k, w))
                with ui.element("div").classes("m-einst"):
                    ui.label(sk.EINSTELLUNGEN["reinigung_anreisetag"][0]).classes("m-ptext")
                    ui.switch(value=d["bool"]["reinigung_anreisetag"], on_change=lambda e: a.aendern(
                        sk.einstellung_setzen, "reinigung_anreisetag", e.value)).props("dense color=indigo-4")
            with ui.element("section").classes("m-block"):
                ui.label("Erinnerungen").classes("m-btitel")
                for k, text in ERINNERUNG.items():
                    _zahlfeld(a, text, d["termine"][k], lambda w, k=k: a.aendern(termin_setzen, k, w))
                _windows(a)
                ui.label("Engpass-Grenzen (Auswertung, Heute)").classes("m-btitel").style("margin-top:14px")
                felder = {}
                with ui.element("div").classes("m-kap"):
                    ui.label("")
                    ui.label("knapp unter").classes("m-zweite")
                    ui.label("kritisch unter").classes("m-zweite")
                    for art, (k_, kr) in d["grenzen"].items():
                        ui.label(eintragen.ENGPASS_NAMEN[art]).classes("m-name")
                        felder[(art, 0)] = ui.number(value=k_, min=0, step=1, format="%d").classes("m-feld").props("dense outlined dark")
                        felder[(art, 1)] = ui.number(value=kr, min=0, step=1, format="%d").classes("m-feld").props("dense outlined dark")
                knopf("Grenzen speichern", lambda: a.aendern(grenzen_setzen, {
                    art: (int(felder[(art, 0)].value or 0), int(felder[(art, 1)].value or 0)) for art in d["grenzen"]}), "", "check")
            with ui.element("section").classes("m-block"):
                ui.label("KI für freie Fragen (Assistenz)").classes("m-btitel")
                ui.label("Zahlen kommen immer aus den Daten. Eine KI beantwortet nur, was die Datenantworten nicht "
                         "verstehen. Der Schlüssel liegt sicher in der Windows-Anmeldeinformationsverwaltung.").classes("m-ptext")
                ki = d["ki"]
                backend = ui.select({"aus": "aus (nur Datenantworten, offline)", "claude": "Claude (Anthropic)",
                                     "lokal": "lokales Modell (z. B. Ollama)"}, value=ki.get("backend", "aus"), label="KI").classes(
                    "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
                from belegung.assistent import llm

                modell = ui.input("Claude-Modell", value=ki.get("claude_modell", llm.CLAUDE_STANDARDMODELL)).classes("m-feld").props(
                    "dense outlined dark")
                effort = ui.select({"low": "schnell", "medium": "ausgewogen", "high": "gründlich"}, value=ki.get("claude_effort", "medium"),
                                   label="Denktiefe").classes("m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
                schl = ui.input("API-Schlüssel (leer = unverändert)", password=True).classes("m-feld").props("dense outlined dark")
                url = ui.input("Lokales Modell: Adresse", value=ki.get("lokal_url", "http://localhost:11434/v1")).classes(
                    "m-feld").props("dense outlined dark")
                lmod = ui.input("Lokales Modell: Name", value=ki.get("lokal_modell", "qwen2.5:7b-instruct")).classes("m-feld").props(
                    "dense outlined dark")
                with ui.element("div").classes("m-paktionen"):
                    knopf("KI-Einstellungen speichern", lambda: a.aendern(ki_setzen, backend.value, modell.value or llm.CLAUDE_STANDARDMODELL,
                                                                          effort.value, url.value or "", lmod.value or "",
                                                                          schl.value or None), "", "check")
                    knopf("Verbindung testen", lambda: _ki_testen(a), "leise", "bolt")


# ---- Stammdaten -------------------------------------------------------------------------

FELDER = {"betten": "Betten", "flur": "Flur", "nur_maenner": "Bad über den Flur (nur Männer)", "tiere": "Tier-Zimmer",
          "gaeste": "Gästezimmer", "aktiv": "gehört zum Internat", "notiz": "Hinweis", "renoviert": "Renoviert (Datum/„ja“)",
          "boden": "Boden"}


def stammdaten_setzen(zid: str, werte: dict) -> str:
    def aktion():
        st = zp.laden()
        for z in st.zimmer:
            if z.id == zid:
                for k, v in werte.items():
                    setattr(z, k, v)
        zp.stammdaten_speichern(st.zimmer, st.plan)
    _schritt(f"Stammdaten {zkurz(zid)}", aktion, [zp.STAMM_DATEI])
    return f"Zimmer {zkurz(zid)} gespeichert"


def _stammdaten(a) -> None:
    sp = "80px minmax(110px, .8fr) 60px 70px minmax(160px, 1.2fr) minmax(120px, 1fr) 70px"
    with a.inhalt:
        ui.label("Eigenschaften der Zimmer – gelten für die Zuteil-Regeln. Klick auf ein Zimmer zum Ändern.").classes(
            "m-ptext").style("padding: 14px 20px 4px")
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Zimmer", "Lage", "Betten", "Flur", "Merkmale", "Hinweis", ""):
                ui.label(t)
        for z in a.daten["zimmer"]:
            merk = ", ".join(t for k, t in (("tiere", "Tier"), ("nur_maenner", "Bad über Flur"), ("gaeste", "Gäste")) if getattr(z, k))
            r = ui.element("div").classes("m-raster m-zeile m-klick" + ("" if z.aktiv else " fertig")).style(f"grid-template-columns:{sp}")
            with r:
                ui.label(z.kurz).classes("m-name")
                ui.label(zp.flur_text(z)).classes("m-zweite")
                ui.label(str(z.betten)).classes("m-mono")
                ui.label(z.flur or "–").classes("m-zweite")
                ui.label(merk or "–").classes("m-zweite")
                attr(ui.label(z.notiz).classes("m-zweite"), title=z.notiz)
                ui.label("" if z.aktiv else "inaktiv").classes("m-zweite")
            r.on("click", lambda z=z: _stamm_panel(a, z))


def _stamm_panel(a, z) -> None:
    def bauen():
        betten = ui.number("Betten", value=z.betten, min=1, max=4, step=1, format="%d").classes("m-feld").props("dense outlined dark")
        flur = ui.input("Flur", value=z.flur).classes("m-feld").props("dense outlined dark")
        schalter = {k: ui.switch(FELDER[k], value=getattr(z, k)).props("dense color=indigo-4")
                    for k in ("aktiv", "tiere", "nur_maenner", "gaeste")}
        notiz = ui.input("Hinweis", value=z.notiz).classes("m-feld").props("dense outlined dark")
        reno = ui.input(FELDER["renoviert"], value=z.renoviert).classes("m-feld").props("dense outlined dark")
        boden = ui.input("Boden", value=z.boden).classes("m-feld").props("dense outlined dark")

        async def speichern():
            werte = {"betten": int(betten.value or 1), "flur": flur.value or "", "notiz": notiz.value or "",
                     "renoviert": reno.value or "", "boden": boden.value or "", **{k: bool(s.value) for k, s in schalter.items()}}
            if await a.aendern(stammdaten_setzen, z.id, werte):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Stammdaten · {z.kurz}", bauen)


# ---- Sicherung & Verlauf ----------------------------------------------------------------

def _sicherung(a) -> None:
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block"):
                ui.label("Datensicherung").classes("m-btitel")
                ui.label("Beim Start sichert das Hauptprogramm die Arbeitsdaten automatisch. Hier sichern Sie zusätzlich von "
                         "Hand oder stellen einen Stand wieder her (der aktuelle Stand wird vorher gesichert).").classes("m-ptext")

                async def sichern():
                    s = await run.io_bound(datensicherung.sichern, "manuell (neue Oberfläche)")
                    await a.laden()
                    a.toast(f"Gesichert: {s.text}" if s else "Nichts zu sichern.", rueck=False)

                knopf("Jetzt sichern", sichern, "primaer", "backup")
                for s in a.daten["sicherungen"][:20]:
                    with ui.element("div").classes("m-notiz"):
                        ui.label(s.text).classes("m-ptext").style("color:var(--text)")
                        ui.label(str(s.pfad.name)).classes("m-zweite")
                        knopf("", lambda s=s: _wieder(a, s), "leise", "restore", "Diesen Stand wiederherstellen")
            with ui.element("section").classes("m-block"):
                ui.label("Verlauf – wer hat wann was geändert").classes("m-btitel")
                if not a.daten["verlauf"]:
                    ui.label("Noch keine Änderungen.").classes("m-ptext")
                for e in a.daten["verlauf"]:
                    zeit = e.get("zeit", "")
                    try:
                        zeit = f"{datetime.fromisoformat(zeit):%d.%m. %H:%M}"
                    except (TypeError, ValueError):
                        pass
                    with ui.element("div").classes("m-liste-zeile"):
                        ui.label(zeit).classes("m-zweite").style("width:84px")
                        attr(ui.label(f"{e.get('aktion', '')}: {e.get('name', '')}"
                                      + (f" · {zkurz(str(e.get('alt', '')))} → {zkurz(str(e.get('neu', '')))}"
                                         if e.get("alt") or e.get("neu") else "")).classes("m-name"), title=e.get("quelle", ""))
                        ui.label(e.get("wer", "")).classes("m-zweite")


def _wieder(a, s) -> None:
    def bauen():
        ui.label(f"Stand vom {s.text} wiederherstellen? Der aktuelle Stand wird vorher gesichert – Sie können also "
                 "zurück.").classes("m-ptext")

        async def los():
            n = await run.io_bound(datensicherung.wiederherstellen, s)
            a.panel_zu()
            await a.laden()
            a.toast("Wiederhergestellt" + (f" – vorher gesichert: {n.text}" if n else ""), rueck=False)

        with ui.element("div").classes("m-paktionen"):
            knopf("Wiederherstellen", los, "primaer", "restore")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Wiederherstellen", bauen)


def ki_testen() -> str:
    """Eine kurze Frage an die eingestellte KI – wie „Verbindung testen“ im bisherigen Programm."""
    from datetime import date

    from belegung.assistent.llm import Einstellungen, backend_erstellen

    from . import auswertung_kern as ak

    ds, fehler = ak.datenstand()
    if ds is None:
        raise ValueError(fehler or "Erst Daten laden.")
    backend = backend_erstellen(Einstellungen.aus_dict(speicher.einstellungen().get("ki", {})))
    if backend is None:
        raise ValueError("Die KI ist ausgeschaltet – oben „Claude“ oder „lokales Modell“ wählen und speichern.")
    return backend.antworte("Wie hoch ist die Belegung insgesamt heute? Antworte in einem Satz.", [], ds, date.today())


async def _ki_testen(a) -> None:
    a.toast("Teste die Verbindung …", rueck=False)
    try:
        text = await run.io_bound(ki_testen)
    except Exception as exc:                  # noqa: BLE001
        a.toast(f"Test fehlgeschlagen: {exc}", fehler=True)
        return
    a.toast(f"Verbindung klappt: {text[:160]}", rueck=False)


def _darstellung(a) -> None:
    """Darstellung: Standard ist „Original“; Layouts und Farben stehen unter „Weitere Darstellungen“ (wie in der
    schwebenden Werkzeugleiste unten rechts)."""
    from . import themes

    d = a.design
    original = d["layout"] == "original"
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Darstellung").classes("m-btitel")
        ui.label("Standard ist „Original“ – für den Alltag reicht das. Unter „Weitere Darstellungen“ gibt es andere "
                 "Layouts (Aufbau) und Farben (Theme) zum Ausprobieren; sie wirken sofort und bleiben gespeichert.").classes(
                     "m-ptext")
        if not original:
            with ui.element("div").classes("m-paktionen"):
                knopf("Zurück zum Original", lambda: a.design_setzen(**{**themes.STANDARD, "notiz": d["notiz"]}),
                      "primaer", "restart_alt")
        mehr = ui.element("details").classes("m-mehr")
        if not original:
            attr(mehr, open="")                # in einer weiteren Darstellung: gleich aufgeklappt
        with mehr:
            with ui.element("summary"):
                ui.icon("chevron_right").classes("m-mehr-pfeil")
                ui.label("Weitere Darstellungen – Layouts und Farben")
            ui.label("Layout (Aufbau)").classes("m-ktitel")
            with ui.element("div").classes("m-designs"):
                for k, (name, text, icon) in themes.LAYOUTS.items():
                    b = ui.element("button").classes("m-design" + (" an" if k == d["layout"] else ""))
                    attr(b, aria_pressed=str(k == d["layout"]).lower())
                    with b:
                        with ui.element("div").classes("m-name").style("display:flex; gap:8px; align-items:center"):
                            ui.icon(icon)
                            ui.label(name + (" (Standard)" if k == "original" else ""))
                        ui.label(text).classes("m-zweite").style("white-space:normal")
                    b.on("click", lambda k=k: a.design_setzen(layout=k))
            ui.label("Farben (Theme)" + (" – wechselt auch das Layout zu Classic Grid" if original else "")).classes("m-ktitel")
            with ui.element("div").classes("m-designs"):
                for k, (name, text, _m) in themes.THEMES.items():
                    an = not original and k == d["theme"]
                    b = ui.element("button").classes(f"m-design d-{k}" + (" an" if an else ""))
                    attr(b, aria_pressed=str(an).lower())
                    with b:
                        with ui.element("div").classes("m-design-muster"):
                            for _i in range(3):
                                ui.element("i")
                        ui.label(name).classes("m-name")
                        ui.label(text).classes("m-zweite").style("white-space:normal")
                    b.on("click", lambda k=k: a.design_setzen(theme=k))
            if not original:
                with ui.element("div").classes("m-paktionen"):
                    if len(themes.modi(d["theme"])) > 1:
                        segmente({"hell": "Hell", "dunkel": "Dunkel"}, d["modus"], lambda m: a.design_setzen(modus=m))
                    segmente({"normal": "Normale Dichte", "kompakt": "Kompakt"}, d["dichte"], lambda x: a.design_setzen(dichte=x))
                    if d["layout"] == "grid":
                        segmente({False: "Seitenleiste", True: "Schmale Leiste"}, d["schmal"], lambda x: a.design_setzen(schmal=x))
