"""Startseite „Heute“: links alles, was zu tun ist (Aufgaben-Karten mit 1-Klick-Lösung), rechts der Tag auf einen
Blick – Zimmer, Anreisen der nächsten Tage, Abreisen, Reinigung, Neuigkeiten."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


from nicegui import run, ui

from .kern import WT, kurz
from .ui_bausteine import attr, knopf


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
    nicht_nutzbar: int = 0                               # 0.70: Zustand „nicht nutzbar“ (gesperrt oder unbewohnbar)
    unbewohnbar: int = 0                                 # davon wegen eines Mangels (das ist der Alarm)
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
    from .kern import kennzahlen

    t.nicht_nutzbar = kennzahlen(stand, heute)["nicht_nutzbar"]
    t.unbewohnbar = sum(1 for zid in stand.lage.unbewohnbar if zid in stand.lage.zimmer
                        and stand.lage.status_am(zid, heute)[0] in ("frei", "teilweise"))
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
        if n and i <= 3:                       # bezugsfertig nur für die nächsten 3 Tage (teure Prüfung, dort zählt es)
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
    """0.64 entschlackt: eine Ansicht (Tageszentrale). Das Postfach öffnet sich nur noch als Vertiefung („Fälle
    ansehen“, „Alle im Postfach“) und hat einen Weg zurück; die frühere Übersicht/der Newsfeed entfallen."""
    _umschalter(a)
    with a.inhalt:
        if a.daten.willkommen:
            _willkommen(a)
        if postfach_an(a):
            _postfach(a, a.daten)
        else:
            _zentrale(a, a.daten)

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
        knopf("Reinigungsliste öffnen", lambda: a.oeffnen("reinigung", rg_zeitraum="heute", rg_zimmer=""), "", "cleaning_services")
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
    ("today", "Aufgaben", "Links stehen die Aufgaben – der farbige Knopf löst sie mit einem Klick, „Später“ verschiebt "
                                      "auf morgen. Rot umrandet = dringend."),
    ("ads_click", "Kennzahlen", "Die Kacheln oben (frei, belegt, ohne Zimmer …) führen direkt zu den Zimmern oder filtern."),
    ("meeting_room", "Zimmer zuteilen", "Unter „Anreisen“ das Zimmer in der Zeile wählen – grün ist der passende Vorschlag. "
                                        "Gespeichert wird sofort."),
    ("undo", "Rückgängig", "Jede Änderung lässt sich mit „Rückgängig“ (unten im Hinweis) oder Strg+Z zurücknehmen."),
    ("search", "Suche", "Strg+K sucht Personen, Zimmer und Seiten."),
]


def _willkommen(a) -> None:
    from .kern import willkommen_weg

    if a.design.get("layout") == "office":            # 0.69: im Menüband nur eine schmale, schließbare Leiste
        leiste = ui.element("div").classes("m-w-leiste")
        with leiste:
            ui.icon("waving_hand")
            ui.label("Neu hier? Die wichtigsten Schritte in zwei Minuten – jederzeit auch mit F1.")

            async def weg_():
                await run.io_bound(willkommen_weg)
                leiste.delete()

            def zeigen():
                from . import hilfe_ui

                hilfe_ui.oeffnen(a, "start")
            knopf("Erste Schritte ansehen", zeigen, "leise", "school")
            knopf("", weg_, "leise", "close", "Nicht mehr zeigen")
        return
    box = ui.element("section").classes("m-willkommen")
    with box:
        with ui.element("div").classes("m-w-kopf"):
            ui.icon("waving_hand").classes("m-w-gruss")
            with ui.element("div"):
                ui.label("Erste Schritte in der neuen Oberfläche").classes("m-btitel")
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


UEBERBLICK = "ueberblick"
STUFEN_PF = (("dringend", "Dringend"), ("bald", "Als Nächstes"), ("info", "Zur Info"))

ANSICHTEN = {"zentrale": "Tageszentrale", "postfach": "Postfach"}    # 0.64: „Übersicht“ entfällt


def ansicht(a) -> str:
    v = getattr(a, "heute_ansicht", "zentrale")
    return v if v in ANSICHTEN else "zentrale"            # gemerkte „uebersicht“ → Tageszentrale


def postfach_an(a) -> bool:
    return ansicht(a) == "postfach"


def _umschalter(a) -> None:
    """0.64: kein Umschalter mehr – im Postfach nur der Weg zurück, in der Tageszentrale der Sprung ins Postfach."""
    with a.werkzeuge:
        if postfach_an(a):          # m-kopf-doppelt: im Menüband stehen „Tagesübersicht“ und „Aufgaben“ schon oben
            knopf("Tageszentrale", lambda: a.setzen(heute_ansicht="zentrale", laden=False), "leise", "arrow_back",
                  "Zurück zur Tageszentrale").classes("m-kopf-doppelt")
        elif a.karten:
            knopf(f"Alle Aufgaben ({len(a.karten)})", lambda: a.setzen(heute_ansicht="postfach", laden=False), "leise",
                  "inbox", "Alle Aufgaben mit ihren Fällen im Postfach bearbeiten").classes("m-kopf-doppelt")


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
                knopf("", lambda k=k: a._spaeter(k), "leise", "snooze", "Später – bis morgen ausblenden (Taste S)")
            tasten = {"s": lambda k=k: a._spaeter(k)}
            if k.aktion:
                tasten["l"] = lambda k=k: a._karte_loesen(k)
            a.tasten = (lambda kid=k.id: a.seite == "heute" and postfach_an(a) and getattr(a, "pf_auswahl", None) == kid,
                        tasten)
            ui.label("Tasten: ↑ ↓ Aufgabe wählen" + (" · L lösen" if k.aktion else "") + " · S später").classes(
                "m-tasten-hinweis")
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


def untertitel(dringend: int, weitere: int) -> str:
    """Sachliche Zeile unter „Tagesübersicht“ (0.65)."""
    if dringend:
        return (f"{dringend} dringende Aufgabe{'n' if dringend != 1 else ''}"
                + (f", {weitere} weitere offen." if weitere else "."))
    return f"Keine dringenden Aufgaben – {weitere} weitere offen." if weitere else "Keine offenen Aufgaben."


def _zentrale(a, t: Tag) -> None:
    jetzt = [k for k in a.karten if k.stufe == "dringend"]
    naechste = [k for k in a.karten if k.stufe in ("dringend", "bald")]
    info = [k for k in a.karten if k.stufe == "info"]
    heute_an = next((w for w in t.woche if w["tag"] == a.heute), None)
    with ui.element("div").classes("m-tz"):
        with ui.element("header").classes("m-tz-kopf"):
            ui.label(f"{WOCHENTAGE[a.heute.weekday()]} · {a.heute.day}. {MONATE_LANG[a.heute.month - 1]} {a.heute.year}").classes(
                "m-tz-datum")
            ui.label("Tagesübersicht").classes("m-tz-titel")
            ui.label(untertitel(len(jetzt), len(naechste) - len(jetzt))).classes("m-tz-sub")
        _zahlen(a, t, len(jetzt), heute_an)
        with ui.element("div").classes("m-tz-raster"):
            with ui.element("section").classes("m-tz-links"):
                with ui.element("div").classes("m-tz-ab"):
                    ui.label("Offene Aufgaben")
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
                if a.design.get("layout") == "office":     # 0.74: freie Zimmer kompakt rechts oben – über dem Falz
                    _frei_block(a, t)
                    _woche_block(a, t)
                    outlook_block(a)
                else:
                    outlook_block(a)
                    _woche_block(a, t)
        if a.design.get("layout") != "office":
            _frei_block(a, t)


def _zahlen(a, t: Tag, n_jetzt: int, heute_an) -> None:
    eilig, offen = t.reinigung
    np_ = t.np
    werte = [
        ("jetzt", n_jetzt, "Dringend", "Aufgaben mit Frist" if n_jetzt else "keine dringenden Aufgaben",
         "krit" if n_jetzt else "ok", "priority_high" if n_jetzt else "check_circle",
         lambda: a.setzen(heute_ansicht="postfach", laden=False)),
        ("an", heute_an["an"] if heute_an else 0, "Anreisen heute",
         (f"{heute_an['an'] - heute_an['mit']} noch ohne Zimmer" if heute_an["an"] > heute_an["mit"] else "alle mit Zimmer")
         if heute_an else "keine Anreisen", "krit" if heute_an and heute_an["an"] > heute_an["mit"] else "blau", "flight_land",
         lambda: a.oeffnen("anreisen", ansicht="zuteilen", kennung=a.heute.isoformat()) if heute_an else a.oeffnen("anreisen")),
        ("rein", eilig, "Reinigung vor Einzug", f"offen · {offen} weitere heute", "warn" if eilig else "ok", "cleaning_services",
         lambda: a.oeffnen("reinigung", rg_zeitraum="heute", rg_zimmer="")),
        ("zimmer", t.nicht_nutzbar, "Zimmer nicht nutzbar",
         (f"davon {t.unbewohnbar} wegen Mangel · " if t.unbewohnbar else "gesperrt laut Gebäudeplan · " if t.nicht_nutzbar
          else "") + f"{t.mit_maengeln} mit Mängeln",
         "krit" if t.unbewohnbar else "ok", "report" if t.unbewohnbar else "verified",   # Sperren sind geplant – kein Alarm
         lambda: a.oeffnen("zimmer", ansicht="uebersicht", zu_tag=a.heute, zu_filter=frozenset({"nicht_nutzbar"}))),
    ]
    if np_ and np_.tiefst:
        text, frei, stufe = np_.tiefst
        werte.append(("np", frei, "Frei nach Planung", f"Tiefstand {text.split(' · ')[0]}", STUFE[stufe],
                      {"ok": "event_available", "warn": "warning", "krit": "error"}[STUFE[stufe]],
                      lambda: a.oeffnen("auswertung", ansicht="zimmer")))
    with ui.element("div").classes("m-tz-zahlen"):
        for _k, zahl, titel, unter, stufe, icon, klick in werte:
            b = ui.element("button").classes(f"m-tz-zahl-k {stufe}" + (" null" if not zahl else ""))
            attr(b, title=f"{titel}: {zahl} – {unter}")
            with b:
                ui.label(str(zahl)).classes("m-tz-zahl")          # 0.54: ohne führende Null („0“ statt „00“)
                with ui.element("div").classes("m-tz-zahl-t"):
                    with ui.element("div").classes("m-tz-zahl-l"):
                        ui.icon(icon)
                        ui.label(titel)
                    ui.label(unter).classes("m-tz-zahl-u")
            b.on("click", klick)


def _punkt(a, i: int, k) -> None:
    liste = a.pf_hat_liste(k)
    with ui.element("article").classes(f"m-tz-punkt {k.stufe}"):
        ui.label(str(i)).classes("m-tz-nr")
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
