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


def _allgemein(a) -> None:
    d = a.daten
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
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
                knopf("KI-Einstellungen speichern", lambda: a.aendern(ki_setzen, backend.value, modell.value or llm.CLAUDE_STANDARDMODELL,
                                                                      effort.value, url.value or "", lmod.value or "",
                                                                      schl.value or None), "", "check")


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
    _schritt(f"Stammdaten {zid.removeprefix('GS-')}", aktion, [zp.STAMM_DATEI])
    return f"Zimmer {zid.removeprefix('GS-')} gespeichert"


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
                                      + (f" · {str(e.get('alt', '')).removeprefix('GS-')} → {str(e.get('neu', '')).removeprefix('GS-')}"
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
