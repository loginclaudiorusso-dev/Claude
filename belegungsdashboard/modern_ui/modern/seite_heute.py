"""Startseite „Heute“: links alles, was zu tun ist (Aufgaben-Karten mit 1-Klick-Lösung), rechts der Tag auf einen
Blick – Zimmer, Anreisen der nächsten Tage, Abreisen, Reinigung, Neuigkeiten."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import json

from nicegui import run, ui

from .kern import WT, kurz
from .ui_bausteine import attr, kennzahlen, knopf, leer, segmente


@dataclass
class Tag:
    zimmer: dict
    anreisen: list = field(default_factory=list)        # (Kennung, Text, Personen, mit Zimmer)
    abreisen: list = field(default_factory=list)        # (Tag-Text, Name, Zimmer)
    reinigung: tuple = (0, 0)                            # (eilig, offen heute)
    neuigkeiten: list = field(default_factory=list)     # (Zeit-Text, Text, Art)
    np: object = None                                    # kern.NachPlanung
    willkommen: bool = False                             # „Erste Schritte“ zeigen (bis „Verstanden“)
    woche: list = field(default_factory=list)            # Tageszentrale: je Tag (Datum, Anreisen, mit Zimmer, bereit, Abreisen)
    nicht_nutzbar: int = 0                               # unbewohnbare Zimmer
    mit_maengeln: int = 0                                # Zimmer mit offenen Mängeln


def tag_daten(stand, heute: date) -> Tag:
    from belegung import cockpit, neuigkeiten

    t = Tag(cockpit.zimmer_heute(stand, heute))
    for a in cockpit.anreisen(stand, heute, 7):
        t.anreisen.append((a.tag.isoformat(), f"{WT[a.tag.weekday()]} {a.tag:%d.%m.} · {a.text}", a.personen, a.mit_zimmer))
    for a in cockpit.abreisen(stand, heute, 1):
        t.abreisen.append(("heute" if a.tag == heute else "morgen", a.name, kurz(a.zimmer)))
    dringend, offen = cockpit.reinigung_heute(stand, heute)
    t.reinigung = (len(dringend), len(offen))
    t.nicht_nutzbar = len(stand.lage.unbewohnbar)
    try:
        from belegung import maengel

        t.mit_maengeln = len(maengel.offen_je_zimmer())
    except Exception:                          # noqa: BLE001
        t.mit_maengeln = 0
    t.woche = _woche(stand, heute)
    grenze = datetime.now() - timedelta(hours=48)
    for n in neuigkeiten.laden()[:30]:
        if n.zeit >= grenze:
            t.neuigkeiten.append((f"{n.zeit:%d.%m. %H:%M}", n.text, n.art))
    t.neuigkeiten = t.neuigkeiten[:8]
    return t


def _woche(stand, heute: date) -> list[dict]:
    """Die nächsten 7 Tage: Anreisen (mit Zimmer, bezugsfertig) und Abreisen je Tag – aus den vorhandenen Regeln."""
    from belegung import cockpit

    from . import kern

    an: dict[date, list] = {}
    for a in cockpit.anreisen(stand, heute, 7):
        an.setdefault(a.tag, []).append(a)
    ab: dict[date, int] = {}
    for x in cockpit.abreisen(stand, heute, 6):
        ab[x.tag] = ab.get(x.tag, 0) + 1
    erg = []
    for i in range(7):
        tag = heute + timedelta(days=i)
        gruppen = an.get(tag, [])
        n, mit = sum(a.personen for a in gruppen), sum(a.mit_zimmer for a in gruppen)
        bereit = None
        if n:
            try:
                b = kern.bereitschaft(stand, kern.zeilen(stand, tag.isoformat(), heute), tag)
                bereit = (b.bereit, b.n)
            except Exception:                  # noqa: BLE001 – Zusatzinfo
                bereit = None
        if n or ab.get(tag):
            erg.append({"tag": tag, "an": n, "mit": mit, "bereit": bereit, "ab": ab.get(tag, 0),
                        "gruppen": ", ".join(dict.fromkeys(a.text for a in gruppen))})
    return erg


STUFE = {"ok": "ok", "knapp": "warn", "kritisch": "krit"}


def daten(a) -> None:
    from .kern import nach_planung

    a.daten = tag_daten(a.stand, a.heute)
    from .kern import willkommen_zeigen

    a.daten.willkommen = willkommen_zeigen()
    try:
        a.daten.np = nach_planung(a.stand, a.heute, 12)
    except Exception:                          # noqa: BLE001 – Anzeige darf Heute nie blockieren
        a.daten.np = None


MONATE_LANG = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
               "Dezember"]
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def briefing(t: Tag, karten: list, heute: date) -> list[str]:
    """Morgen-Briefing in wenigen Sätzen (zum Vorlesen): Anreisen, Zimmer, Aufgaben – nur Zahlen und Aufgabentitel,
    keine Personennamen."""
    sz = [f"Guten Morgen. Das Briefing für {WOCHENTAGE[heute.weekday()]}, den {heute.day}. {MONATE_LANG[heute.month - 1]}."]
    heute_an = [x for x in t.anreisen if x[0] == heute.isoformat()]
    morgen_an = [x for x in t.anreisen if x[0] == (heute + timedelta(days=1)).isoformat()]
    if heute_an:
        n, mit = sum(x[2] for x in heute_an), sum(x[3] for x in heute_an)
        sz.append(f"Heute reisen {n} Personen an" + (f", {n - mit} davon haben noch kein Zimmer." if n > mit else
                                                       ", alle haben ein Zimmer."))
    elif morgen_an:
        n, mit = sum(x[2] for x in morgen_an), sum(x[3] for x in morgen_an)
        sz.append(f"Heute keine Anreisen. Morgen kommen {n} Personen" + (f", {n - mit} davon noch ohne Zimmer." if n > mit else
                                                                         ", alle mit Zimmer."))
    else:
        sz.append("Heute und morgen sind keine Anreisen geplant.")
    z = t.zimmer
    sz.append(f"{z['frei']} Zimmer sind heute frei" + (f", {z['ohne_zimmer']} Personen der nächsten Wochen warten noch auf ein "
                                                       "Zimmer." if z.get("ohne_zimmer") else "."))
    dringend = [k for k in karten if k.stufe == "dringend"]
    if dringend:
        sz.append(f"{len(dringend)} dringende Aufgabe{'n' if len(dringend) != 1 else ''}. Zuerst: {dringend[0].titel}.")
    else:
        sz.append("Keine dringenden Aufgaben – " + (f"{len(karten)} weitere stehen an." if karten else "alles erledigt."))
    sz.append("Ende des Briefings.")
    return sz


BRIEFING_JS = """<script>
window.mBriefing = (knopf, saetze) => {   // Sprachausgabe im Browser/Windows (Web Speech) – es verlässt nichts den Rechner
  const box = knopf.closest('.m-feed-kopf') || document; const text = box.querySelector('.m-briefing-text');
  if (text) text.classList.add('offen');
  const s = window.speechSynthesis;
  if (!s || typeof SpeechSynthesisUtterance === 'undefined') { knopf.classList.add('stumm'); return; }
  if (s.speaking || s.pending) { s.cancel(); knopf.classList.remove('spricht'); return; }
  const de = s.getVoices().find(v => (v.lang || '').toLowerCase().startsWith('de'));
  saetze.forEach((satz, i) => {
    const u = new SpeechSynthesisUtterance(satz); u.lang = 'de-DE'; if (de) u.voice = de; u.rate = 1.0;
    if (text) u.onstart = () => text.querySelectorAll('li').forEach((li, j) => li.classList.toggle('jetzt', j === i));
    if (i === saetze.length - 1) u.onend = u.onerror = () => { knopf.classList.remove('spricht');
      if (text) text.querySelectorAll('li').forEach(li => li.classList.remove('jetzt')); };
    s.speak(u);
  });
  knopf.classList.add('spricht');
};
</script>"""


def zeichnen(a) -> None:
    if ansicht(a) == "zentrale":
        _umschalter(a)
        with a.inhalt:
            if a.daten.willkommen:
                _willkommen(a)
            _zentrale(a, a.daten)
        return
    if a.design.get("layout", "original") != "original":
        return _feed(a)                       # neue Layouts: Newsfeed mit Briefing; Original bleibt 1:1
    t: Tag = a.daten
    z = t.zimmer
    with a.leiste:
        wt = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][a.heute.weekday()]
        werte = [("frei", z["frei"], "frei heute", "ok"), ("belegt", z["belegt"], "belegt", "blau"),
                 ("gesperrt", z["gesperrt"], "gesperrt", "neutral"),
                 ("ohne", z["ohne_zimmer"], "Anreisen ohne Zimmer", "krit" if z["ohne_zimmer"] else "ok")]
        np_ = t.np
        if np_ and np_.tiefst:
            text, frei, stufe = np_.tiefst
            werte.append(("np", frei, f"frei nach Planung · {text.split(' · ')[0]}", STUFE[stufe]))
        werte.append(("maengel", sum(1 for _ in _defekte(a)), "Zimmer mit Mängeln", "warn"))
        if a.neu:
            werte.append(("neu", len(a.neu), "neue Personen (7 Tage)", "blau"))

        def sprung(k):
            if k == "ohne":
                return a.oeffnen("anreisen", ansicht="zuteilen", filter="ohne")
            if k == "np":
                return a.oeffnen("auswertung", ansicht="zimmer")
            if k == "maengel":
                return a.oeffnen("zimmer", ansicht="maengel")
            if k == "neu":
                return a.oeffnen("anreisen", ansicht="personen", ps_filter="neu")
            return a.oeffnen("zimmer", ansicht="uebersicht", zu_tag=a.heute, zu_filter=k)

        kennzahlen(werte, None, sprung, {"ohne": "Anreisen der nächsten 8 Wochen ohne Zimmer – Klick: zuteilen",
                                         "np": "Mindestens so viele Zimmer bleiben frei, wenn alle bekannten Anreisen ein Zimmer "
                                               "hätten – Klick: alle Wochen",
                                         "maengel": "Klick: defekte Zimmer",
                                         "neu": "Neu in den Listen – Klick: Liste der neuen Personen", "frei": "Klick: Zimmer-Übersicht",
                                         "belegt": "Klick: Zimmer-Übersicht", "gesperrt": "Klick: Zimmer-Übersicht"})
        ui.label(f"{wt}, {a.heute:%d.%m.%Y}").classes("m-kpi").style("margin-left:auto")
    _umschalter(a)
    with a.inhalt:
        if t.willkommen:
            _willkommen(a)
        if postfach_an(a):
            _postfach(a, t)
            return
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
                _tagesblock(a, t)

def _tagesblock(a, t: "Tag") -> None:
    """Der Tag auf einen Blick: Anreisen 7 Tage, frei nach Planung, Abreisen, Reinigung, Neuigkeiten."""
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
    if t.np:
        _nach_planung_block(a, t.np)
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

def _nach_planung_block(a, np_) -> None:
    """Freie Zimmer der nächsten 5 Wochen nach Planung – gesamt, EMR, Doppelzimmer, mit Ampel."""
    with ui.element("div").classes("m-block"):
        ui.label("Frei nach Planung – nächste 5 Wochen").classes("m-btitel")
        ui.label(f"Ganz freie Zimmer, wenn auch die {np_.offen} Anreisen ohne Zimmer probeweise zugeteilt sind"
                 + (f" ({np_.ohne_platz} fänden keins)" if np_.ohne_platz else "") + ".").classes("m-ptext")
        with ui.element("div").classes("m-np"):
            for t in ("Woche", "jetzt", "nach Planung", "EMR", "Doppel"):
                ui.label(t).classes("m-zweite")
            for text, jetzt, frei, emr, doppel, stufe, je in np_.wochen[:5]:
                ui.label(text).classes("m-ptext")
                ui.label(str(jetzt)).classes("m-mono")
                ui.label(str(frei)).classes(f"m-pille {STUFE[je['gesamt']]}")
                ui.label(str(emr)).classes(f"m-pille {STUFE[je['emr']]}")
                ui.label(str(doppel)).classes(f"m-pille {STUFE[je['doppel']]}")
        knopf("Alle 12 Wochen", lambda: a.oeffnen("auswertung", ansicht="zimmer"), "leise", "insights")


def _defekte(a):
    from belegung import maengel as mg

    aktiv = {z.id for z in a.stand.zimmer if z.aktiv}
    return [zid for zid in mg.offen_je_zimmer() if zid in aktiv]


SCHRITTE = [
    ("today", "Hier beginnt der Tag", "Links stehen die Aufgaben – der farbige Knopf löst sie mit einem Klick, „Später“ verschiebt "
                                      "auf morgen. Rot umrandet = dringend."),
    ("ads_click", "Zahlen sind Knöpfe", "Die Kacheln oben (frei, belegt, ohne Zimmer …) führen direkt zu den Zimmern oder filtern."),
    ("meeting_room", "Zimmer zuteilen", "Unter „Anreisen“ das Zimmer in der Zeile wählen – grün ist der passende Vorschlag. "
                                        "Gespeichert wird sofort."),
    ("undo", "Nichts kann schiefgehen", "Jede Änderung lässt sich mit „Rückgängig“ (unten im Hinweis) oder Strg+Z zurücknehmen."),
    ("search", "Alles finden", "Strg+K sucht Personen, Zimmer und Seiten."),
]


def _willkommen(a) -> None:
    from .kern import willkommen_weg

    box = ui.element("section").classes("m-willkommen")
    with box:
        with ui.element("div").classes("m-w-kopf"):
            ui.icon("waving_hand").classes("m-w-gruss")
            with ui.element("div"):
                ui.label("Willkommen – so funktioniert die neue Oberfläche").classes("m-btitel")
                ui.label("Fünf Dinge, dann kennen Sie alles Wichtige.").classes("m-ptext")

            async def weg():
                await run.io_bound(willkommen_weg)
                box.delete()

            knopf("Verstanden", weg, "primaer", "check").style("margin-left:auto")
        with ui.element("div").classes("m-w-schritte"):
            for i, (icon, titel, text) in enumerate(SCHRITTE, 1):
                with ui.element("div").classes("m-w-schritt"):
                    with ui.element("span").classes("m-w-nr"):
                        ui.icon(icon)
                    ui.label(f"{i}. {titel}").classes("m-name")
                    ui.label(text).classes("m-ptext")


# =======================================================================================
# Newsfeed (alle Layouts außer „Original“): nur das Wesentliche, chronologisch – jetzt · heute · morgen
# =======================================================================================

def feed_eintraege(t: Tag, karten: list, heute: date) -> dict:
    """Gruppiert, was heute zählt: dringende Aufgaben, Anreisen/Abreisen heute und morgen, eilige Reinigung, Warnungen."""
    tag_iso, morgen_iso = heute.isoformat(), (heute + timedelta(days=1)).isoformat()
    return {
        "jetzt": [k for k in karten if k.stufe == "dringend"],
        "heute_an": [x for x in t.anreisen if x[0] == tag_iso],
        "morgen_an": [x for x in t.anreisen if x[0] == morgen_iso],
        "heute_ab": [x for x in t.abreisen if x[0] == "heute"],
        "morgen_ab": [x for x in t.abreisen if x[0] == "morgen"],
        "reinigung": t.reinigung[0],
        "warnungen": [x for x in t.neuigkeiten if x[2] in ("warnung", "fehler")][:3],
        "weitere": [k for k in karten if k.stufe != "dringend"],
    }


def _feed(a) -> None:
    t: Tag = a.daten
    z = t.zimmer
    f = feed_eintraege(t, a.karten, a.heute)
    saetze = briefing(t, a.karten, a.heute)
    with a.werkzeuge:
        b = ui.element("button").classes("m-briefing")
        attr(b, title="Morgen-Briefing vorlesen (ca. 30 Sekunden) – noch einmal klicken beendet",
             aria_label="Briefing abspielen")
        with b:
            with ui.element("span").classes("m-welle"):
                for _ in range(4):
                    ui.element("i")
            ui.label("Briefing abspielen")
        b.on("click", js_handler=f"(e) => mBriefing(e.currentTarget, {json.dumps(saetze)})")
    with a.leiste:
        werte = [("frei", z["frei"], "Zimmer frei heute", "ok"),
                 ("ohne", z["ohne_zimmer"], "Anreisen ohne Zimmer", "krit" if z["ohne_zimmer"] else "ok"),
                 ("dringend", len(f["jetzt"]), "dringende Aufgaben", "krit" if f["jetzt"] else "ok")]
        kennzahlen(werte, None, lambda k: (a.center_umschalten(True) if k == "dringend" else
                                            a.oeffnen("anreisen", ansicht="zuteilen", filter="ohne") if k == "ohne" else
                                            a.oeffnen("zimmer", ansicht="uebersicht", zu_tag=a.heute, zu_filter="frei")),
                   {"frei": "Klick: Zimmer-Übersicht", "ohne": "Klick: zuteilen", "dringend": "Klick: alle Aufgaben"})
        ui.label(f"{WOCHENTAGE[a.heute.weekday()]}, {a.heute:%d.%m.%Y}").classes("m-kpi").style("margin-left:auto")
    _umschalter(a)
    with a.inhalt:
        if t.willkommen:
            _willkommen(a)
        if postfach_an(a):
            _postfach(a, t)
            return
        with ui.element("div").classes("m-feed"):
            with ui.element("div").classes("m-feed-kopf"):
                with ui.element("ol").classes("m-briefing-text"):        # Mitschrift – erscheint beim Abspielen
                    for satz in saetze:
                        with ui.element("li"):
                            ui.label(satz)
            _abschnitt("Jetzt", "bolt", "krit")
            if f["jetzt"]:
                for k in f["jetzt"]:
                    with ui.element("div").classes("m-feed-eintrag"):
                        a._karte(k)
            else:
                _eintrag("check_circle", "Keine dringenden Aufgaben", "Alles Wichtige ist erledigt.", "ok")
            for w_zeit, w_text, w_art in f["warnungen"]:
                _eintrag("warning", w_text, f"Hinweis · {w_zeit}", "warn")
            _abschnitt(f"Heute · {WOCHENTAGE[a.heute.weekday()]}", "today", "")
            _tag(a, f["heute_an"], f["heute_ab"], "heute")
            if f["reinigung"]:
                _eintrag("cleaning_services", f"{f['reinigung']} Zimmer vor Einzug noch reinigen", "Reinigung · heute", "krit",
                         lambda: a.oeffnen("reinigung", rg_zeitraum="heute"))
            _abschnitt("Morgen", "event", "")
            _tag(a, f["morgen_an"], f["morgen_ab"], "morgen")
            if f["weitere"]:
                with ui.element("div").classes("m-feed-mehr"):
                    knopf(f"{len(f['weitere'])} weitere Aufgaben (als Nächstes, zur Info)", lambda: a.center_umschalten(True),
                          "leise", "inbox")


def _abschnitt(titel: str, icon: str, art: str) -> None:
    with ui.element("div").classes(f"m-feed-abschnitt {art}"):
        ui.icon(icon)
        ui.label(titel)


def _eintrag(icon: str, titel: str, unter: str, art: str = "", klick=None) -> None:
    e = ui.element("button" if klick else "div").classes(f"m-feed-eintrag m-feed-zeile {art}")
    with e:
        with ui.element("span").classes(f"m-feed-symbol {art}"):
            ui.icon(icon)
        with ui.element("div").classes("m-feed-txt"):
            ui.label(titel).classes("m-name")
            ui.label(unter).classes("m-zweite")
        if klick:
            ui.icon("chevron_right").classes("m-feed-pfeil")
    if klick:
        e.on("click", klick)


def _tag(a, anreisen: list, abreisen: list, wann: str) -> None:
    if not anreisen and not abreisen:
        _eintrag("event_available", f"{'Heute' if wann == 'heute' else 'Morgen'} keine Anreisen und Abreisen", "", "neutral")
        return
    for kennung, text, n, mit in anreisen:
        offen = n - mit
        _eintrag("flight_land", f"Anreise: {text.split(' · ', 1)[-1]}",
                 f"{n} Personen · " + (f"{offen} ohne Zimmer – zuteilen" if offen else "alle mit Zimmer"),
                 "krit" if offen else "ok", lambda k=kennung: a.oeffnen("anreisen", kennung=k))
    if abreisen:
        namen = ", ".join(f"{n} ({z})" for _w, n, z in abreisen[:4]) + (f" und {len(abreisen) - 4} weitere" if len(abreisen) > 4 else "")
        _eintrag("flight_takeoff", f"{len(abreisen)} Abreise{'n' if len(abreisen) != 1 else ''}", namen, "neutral",
                 lambda: a.oeffnen("anreisen", ansicht="abreisen"))



# ---------------------------------------------------------------------------------------
# Postfach (wie Outlook): links die Aufgaben als Zeilen, rechts alle Fälle der gewählten Aufgabe
# ---------------------------------------------------------------------------------------

UEBERBLICK = "ueberblick"
STUFEN_PF = (("dringend", "Dringend"), ("bald", "Als Nächstes"), ("info", "Zur Info"))


ANSICHTEN = {"zentrale": "Tageszentrale", "postfach": "Postfach", "uebersicht": "Übersicht"}


def ansicht(a) -> str:
    return getattr(a, "heute_ansicht", "zentrale")


def postfach_an(a) -> bool:
    return ansicht(a) == "postfach"


def _umschalter(a) -> None:
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht(a), lambda v: a.setzen(heute_ansicht=v, laden=False))


def auswahl(a) -> str:
    """Gewählte Aufgabe – bleibt nach dem Erledigen eines Falls stehen; ist die Aufgabe ganz erledigt, rückt die
    nächste nach (wie im Posteingang)."""
    ids = [k.id for k in a.karten]
    alt = getattr(a, "pf_auswahl", None)
    if alt in ids or alt == UEBERBLICK:
        return alt
    reihe = getattr(a, "pf_reihe", [])
    if alt in reihe:                                  # erledigt → die nächste in der alten Reihenfolge
        for kid in reihe[reihe.index(alt) + 1:] + list(reversed(reihe[:reihe.index(alt)])):
            if kid in ids:
                return kid
    return ids[0] if ids else UEBERBLICK


def _postfach(a, t: Tag) -> None:
    a.pf_auswahl = auswahl(a)
    a.pf_reihe = [k.id for k in a.karten]
    with ui.element("div").classes("m-pf"):
        liste = ui.element("nav").classes("m-pf-liste")
        attr(liste, aria_label="Aufgaben")
        detail = ui.element("section").classes("m-pf-detail")

    def zeigen(kid: str) -> None:
        a.pf_auswahl = kid
        fuellen()

    def schritt(richtung: int) -> None:
        reihe = [UEBERBLICK] + [k.id for k in a.karten]
        i = reihe.index(a.pf_auswahl) if a.pf_auswahl in reihe else 0
        zeigen(reihe[max(0, min(len(reihe) - 1, i + richtung))])

    a.pf_schritt = schritt

    def fuellen() -> None:
        liste.clear()
        detail.clear()
        with liste:
            z = ui.element("button").classes("m-pf-zeile ueberblick" + (" an" if a.pf_auswahl == UEBERBLICK else ""))
            with z:
                ui.icon("today").classes("m-pf-symbol")
                with ui.element("div").classes("m-pf-text"):
                    ui.label("Überblick heute").classes("m-pf-titel")
                    ui.label(f"{len(t.anreisen)} Anreisetage · {len(t.abreisen)} Abreisen · Reinigung").classes("m-pf-unter")
            z.on("click", lambda: zeigen(UEBERBLICK))
            if not a.karten:
                ui.label("Keine Aufgaben – alles erledigt.").classes("m-pf-leer")
            for stufe, titel in STUFEN_PF:
                ks = [k for k in a.karten if k.stufe == stufe]
                if not ks:
                    continue
                ui.label(f"{titel} ({len(ks)})").classes("m-pf-gruppe")
                for k in ks:
                    z = ui.element("button").classes(f"m-pf-zeile {k.stufe}" + (" an" if a.pf_auswahl == k.id else ""))
                    attr(z, title=k.titel)
                    with z:
                        ui.icon(_symbol(k.id)).classes(f"m-pf-symbol {k.stufe}")
                        with ui.element("div").classes("m-pf-text"):
                            ui.label(k.titel).classes("m-pf-titel")
                            ui.label(k.detail).classes("m-pf-unter")
                    z.on("click", lambda k=k: zeigen(k.id))
        with detail:
            if a.pf_auswahl == UEBERBLICK:
                ui.label("Überblick heute").classes("m-pf-dtitel")
                with ui.element("div").classes("m-pf-ueberblick"):
                    _tagesblock(a, t)
                return
            k = next(k for k in a.karten if k.id == a.pf_auswahl)
            with ui.element("div").classes("m-pf-dkopf"):
                ui.icon(_symbol(k.id)).classes(f"m-pf-symbol {k.stufe}")
                with ui.element("div").classes("m-pf-text"):
                    ui.label(k.titel).classes("m-pf-dtitel")
                    ui.label({"dringend": "Dringend", "bald": "Als Nächstes", "info": "Zur Info"}[k.stufe]).classes(
                        "m-kstufe " + {"dringend": "krit", "bald": "warn", "info": "ok"}[k.stufe])
                knopf("", lambda k=k: a._spaeter(k), "leise", "snooze", "Später – bis morgen ausblenden")
            if not a.pf_hat_liste(k):                   # keine Fall-Liste: Text und die Knöpfe der Aufgabe
                ui.label(k.detail).classes("m-ptext")
                with ui.element("div").classes("m-paktionen"):
                    if k.aktion:
                        knopf(k.aktion.text, lambda k=k: a._karte_loesen(k), "primaer")
                    if k.zweite:
                        knopf(k.zweite.text, lambda k=k: a._zeigen(k.zweite.zeigen), "")
                    if k.hinweis:
                        ui.label(k.hinweis).classes("m-zweite")
            koerper = ui.element("div").classes("m-pf-faelle")
            ui.timer(0.01, lambda k=k: a.pf_detail(k, koerper), once=True)

    fuellen()


def _symbol(kid: str) -> str:
    from .kern import symbol

    return symbol(kid)



# ---------------------------------------------------------------------------------------
# Tageszentrale: der Tag auf einer Seite – priorisiert, mit direkter Aktion
# ---------------------------------------------------------------------------------------

KATEGORIE = {"anreise": "Anreise", "reinigung": "Reinigung", "strittig": "Gebäudeplan", "unbewohnbar": "Zimmer",
             "konflikte": "Zimmer", "fm": "FM-Auftrag", "allergie": "Allergiker", "eintragen": "Belegungssystem",
             "mail": "Mail", "termin": "Termin", "maengel": "Mängel", "facility": "Facility", "abreisen": "Abreise",
             "umzug": "Umzug", "mieterende": "Mieter", "engpass": "Engpass", "gebaeudeplan": "Gebäudeplan"}
STUFE_TEXT = {"dringend": "dringend", "bald": "als Nächstes", "info": "zur Info"}
STUFE_ICON = {"dringend": "priority_high", "bald": "schedule", "info": "info"}


def _kategorie(kid: str) -> str:
    return KATEGORIE.get(kid.split(":")[0].split("_")[0], "Aufgabe")


def _zentrale(a, t: Tag) -> None:
    jetzt = [k for k in a.karten if k.stufe == "dringend"]
    naechste = [k for k in a.karten if k.stufe in ("dringend", "bald")]
    info = [k for k in a.karten if k.stufe == "info"]
    heute_an = next((w for w in t.woche if w["tag"] == a.heute), None)
    with ui.element("div").classes("m-tz"):
        with ui.element("header").classes("m-tz-kopf"):
            ui.label(f"{WOCHENTAGE[a.heute.weekday()]} · {a.heute.day}. {MONATE_LANG[a.heute.month - 1]} {a.heute.year}").classes(
                "m-tz-datum")
            ui.label("Der Tag im Griff.").classes("m-tz-titel")
            ui.label(f"{len(jetzt)} Punkt{'e brauchen' if len(jetzt) != 1 else ' braucht'} heute deine Aufmerksamkeit, "
                     f"{len(naechste) - len(jetzt)} weitere stehen an." if jetzt else
                     "Nichts Dringendes – " + (f"{len(naechste)} Punkte stehen als Nächstes an." if naechste else
                                               "alles erledigt.")).classes("m-tz-sub")
        _zahlen(a, t, len(jetzt), heute_an)
        with ui.element("div").classes("m-tz-raster"):
            with ui.element("section").classes("m-tz-links"):
                with ui.element("div").classes("m-tz-ab"):
                    ui.label("Als Nächstes")
                    ui.label(f"nach Dringlichkeit sortiert · {len(naechste)} offen").classes("m-tz-meta")
                if not naechste:
                    with ui.element("div").classes("m-tz-leer"):
                        ui.icon("check_circle")
                        ui.label("Keine dringenden oder anstehenden Aufgaben.")
                for i, k in enumerate(naechste[:7], 1):
                    _punkt(a, i, k)
                rest = len(naechste) - 7
                with ui.element("div").classes("m-paktionen"):
                    if rest > 0:
                        knopf(f"Alle {len(naechste)} im Postfach", lambda: a.setzen(heute_ansicht="postfach", laden=False),
                              "leise", "inbox")
                    if info:
                        knopf(f"{len(info)} Hinweis{'e' if len(info) != 1 else ''} zur Info",
                              lambda: a.setzen(heute_ansicht="postfach", pf_auswahl=info[0].id, laden=False), "leise", "info")
            with ui.element("aside").classes("m-tz-rechts"):
                outlook_block(a)
                _woche_block(a, t)
        _frei_block(a, t)


def _zahlen(a, t: Tag, n_jetzt: int, heute_an) -> None:
    eilig, offen = t.reinigung
    np_ = t.np
    werte = [
        ("jetzt", n_jetzt, "Jetzt klären", "dringende Punkte" if n_jetzt else "nichts Dringendes",
         "krit" if n_jetzt else "ok", "priority_high" if n_jetzt else "check_circle",
         lambda: a.setzen(heute_ansicht="postfach", laden=False)),
        ("an", heute_an["an"] if heute_an else 0, "Anreisen heute",
         (f"{heute_an['an'] - heute_an['mit']} noch ohne Zimmer" if heute_an["an"] > heute_an["mit"] else "alle mit Zimmer")
         if heute_an else "keine Anreisen", "krit" if heute_an and heute_an["an"] > heute_an["mit"] else "blau", "flight_land",
         lambda: a.oeffnen("anreisen", ansicht="zuteilen", kennung=a.heute.isoformat()) if heute_an else a.oeffnen("anreisen")),
        ("rein", eilig, "Reinigung vor Einzug", f"offen · {offen} weitere heute", "warn" if eilig else "ok", "cleaning_services",
         lambda: a.oeffnen("reinigung", rg_zeitraum="heute")),
        ("zimmer", t.nicht_nutzbar, "Zimmer nicht nutzbar", f"{t.mit_maengeln} Zimmer mit Mängeln",
         "krit" if t.nicht_nutzbar else "ok", "report" if t.nicht_nutzbar else "verified",
         lambda: a.oeffnen("zimmer", ansicht="maengel")),
    ]
    if np_ and np_.tiefst:
        text, frei, stufe = np_.tiefst
        werte.append(("np", frei, "Frei nach Planung", f"Tiefstand {text.split(' · ')[0]}", STUFE[stufe],
                      {"ok": "event_available", "warn": "warning", "krit": "error"}[STUFE[stufe]],
                      lambda: a.oeffnen("auswertung", ansicht="zimmer")))
    with ui.element("div").classes("m-tz-zahlen"):
        for _k, zahl, titel, unter, stufe, icon, klick in werte:
            b = ui.element("button").classes(f"m-tz-zahl-k {stufe}")
            attr(b, title=f"{titel}: {zahl} – {unter}")
            with b:
                ui.label(f"{zahl:02d}" if isinstance(zahl, int) and 0 <= zahl < 100 else str(zahl)).classes("m-tz-zahl")
                with ui.element("div").classes("m-tz-zahl-t"):
                    with ui.element("div").classes("m-tz-zahl-l"):
                        ui.icon(icon)
                        ui.label(titel)
                    ui.label(unter).classes("m-tz-zahl-u")
            b.on("click", klick)


def _punkt(a, i: int, k) -> None:
    liste = a.pf_hat_liste(k)
    with ui.element("article").classes(f"m-tz-punkt {k.stufe}"):
        ui.label(f"{i:02d}").classes("m-tz-nr")
        with ui.element("div").classes("m-tz-ptext"):
            with ui.element("div").classes("m-tz-kat"):
                ui.icon(STUFE_ICON[k.stufe])
                ui.label(f"{_kategorie(k.id)} · {STUFE_TEXT[k.stufe]}")
            ui.label(k.titel).classes("m-tz-ptitel")
            if k.detail:
                attr(ui.label(k.detail).classes("m-tz-pdetail"), title=k.detail)
        with ui.element("div").classes("m-tz-paktion"):
            if k.aktion:
                knopf(k.aktion.text, lambda k=k: a._karte_loesen(k), "primaer")
            if liste:
                knopf("Fälle ansehen", lambda k=k: a.setzen(heute_ansicht="postfach", pf_auswahl=k.id, laden=False),
                      "" if k.aktion else "primaer")
            elif k.zweite:
                knopf(k.zweite.text, lambda k=k: a._zeigen(k.zweite.zeigen), "" if k.aktion else "primaer")
            elif k.hinweis and not k.aktion:
                ui.label(k.hinweis).classes("m-zweite")
            knopf("", lambda k=k: a._spaeter(k), "leise", "snooze", "Später – bis morgen ausblenden")


def _woche_block(a, t: Tag) -> None:
    with ui.element("section").classes("m-tz-block"):
        with ui.element("div").classes("m-tz-ab"):
            ui.label("Die nächsten 7 Tage")
            knopf("Alle Anreisen", lambda: a.oeffnen("anreisen"), "leise")
        if not t.woche:
            ui.label("Keine An- oder Abreisen in den nächsten 7 Tagen.").classes("m-ptext")
        for w in t.woche:
            tag = w["tag"]
            wann = "Heute" if tag == a.heute else "Morgen" if tag == a.heute + timedelta(days=1) else f"{WT[tag.weekday()]} {tag:%d.%m.}"
            z = ui.element("button").classes("m-tz-tag")
            with z:
                ui.label(wann).classes("m-tz-wann" + (" heute" if tag == a.heute else ""))
                with ui.element("div").classes("m-tz-tagtext"):
                    if w["an"]:
                        ohne = w["an"] - w["mit"]
                        ui.label(f"{w['an']} Anreise{'n' if w['an'] != 1 else ''}"
                                 + (f" · {w['gruppen']}" if w["gruppen"] else "")).classes("m-name")
                        teile = [f"{ohne} ohne Zimmer" if ohne else "alle mit Zimmer"]
                        if w["bereit"]:
                            teile.append(f"{w['bereit'][0]} von {w['bereit'][1]} bezugsfertig")
                        ui.label(" · ".join(teile)).classes("m-zweite" + (" m-krit" if ohne else ""))
                    if w["ab"]:
                        ui.label(f"{w['ab']} Abreise{'n' if w['ab'] != 1 else ''}").classes("m-zweite")
            z.on("click", lambda tag=tag, w=w: a.oeffnen("anreisen", ansicht="zuteilen", kennung=tag.isoformat())
                 if w["an"] else a.oeffnen("anreisen", ansicht="abreisen"))


def _frei_block(a, t: Tag) -> None:
    np_ = t.np
    if not np_ or not np_.wochen:
        return
    wochen = np_.wochen[:5]
    groesst = max([w[1] for w in wochen] + [1])
    engpass = next((w for w in wochen if w[6].get("emr") != "ok" or w[6].get("doppel") != "ok"), None)
    with ui.element("section").classes("m-tz-frei"):
        with ui.element("div").classes("m-tz-ab"):
            ui.label("Freie Zimmer nach Planung")
            ui.label("5-Wochen-Blick" + (f" · Engpass zuerst in {engpass[0].split(' · ')[0]}" if engpass else " · kein Engpass")).classes(
                "m-tz-meta")
            knopf("Alle 12 Wochen", lambda: a.oeffnen("auswertung", ansicht="zimmer"), "leise")
        with ui.element("div").classes("m-tz-wochen"):
            for text, jetzt, frei, emr, doppel, stufe, je in wochen:
                st = STUFE[stufe]
                with ui.element("div").classes(f"m-tz-woche {st}"):
                    with ui.element("div").classes("m-tz-wkopf"):
                        ui.label(text.split(" · ")[0]).classes("m-zweite")
                        with ui.element("span").classes("m-tz-wfrei"):
                            if st != "ok":
                                ui.icon("warning" if st == "warn" else "error")
                            ui.label(f"{frei} frei")
                    with ui.element("div").classes("m-tz-balken"):
                        ui.element("i").style(f"width:{max(2, min(100, round(100 * frei / groesst)))}%")
                    ui.label(f"EMR {emr}{' (knapp)' if je.get('emr') != 'ok' else ''} · DZ {doppel}"
                             f"{' (knapp)' if je.get('doppel') != 'ok' else ''}").classes(
                        "m-tz-wunter" + (" m-warn" if je.get("emr") != "ok" or je.get("doppel") != "ok" else ""))


def outlook_block(a) -> None:
    """Platzhalter – wird mit der Outlook-Vorschau gefüllt (siehe outlook_kern)."""
    from . import outlook_kern

    outlook_kern.block(a)
