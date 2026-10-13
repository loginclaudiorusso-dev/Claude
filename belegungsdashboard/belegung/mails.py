"""Posteingang: Mails zu Anmeldungen, Gästehaus-Reservierungen, Stornos, Abbrüchen und Hinweisen.

1. ``erkennen``  – Art, Name, TN-Nummer, Zeitraum und Details aus Betreff und Text lesen.
2. ``zuordnen`` – passende Person bzw. Buchung finden (TN-Nummer vor Name, Zeitraum entscheidet).
3. ``vorschlag`` – Schritte vorschlagen (Person anlegen, Zimmer reservieren, Planung entfernen, Abreise setzen,
   Notiz/Wiedervorlage, Aufgabe fürs Belegungssystem); die Nutzerin bestätigt in der Oberfläche.
4. ``umsetzen`` – bestätigte Schritte ausführen und im Posteingang ablegen (Abbrüche mit Prüfliste).

Rein, ohne Qt. Die Mails liegen nur lokal in ``importe/posteingang.json``.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta

from . import anreiseliste, speicher
from . import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/posteingang.json"
ARTEN = {"gast": "Gästehaus", "anmeldung": "Anmeldung", "storno": "Storno", "abbruch": "Abbruch",
         "hinweis": "Hinweis", "unklar": "Unklar"}
PRUEFLISTE_ABBRUCH = ["Abreise im Belegungssystem geändert", "Zimmer geräumt und abgenommen", "Schlüssel zurück",
                      "Endreinigung veranlasst"]
PRUEFLISTE_STORNO = ["Im Belegungssystem storniert"]


@dataclass
class Erkannt:
    art: str = "unklar"
    name: str = ""                 # „Nachname, Vorname“ (oder nur Nachname)
    tn_id: str = ""
    von: date | None = None
    bis: date | None = None
    geschlecht: str = ""
    massnahme: str = ""
    einzelzimmer: bool | None = None
    fruehstueck: bool = False
    grund: str = ""                # Abbruch: Grund
    wiederaufnahme: str = ""       # „möglich“ | „nicht geplant“ | ""
    zimmer_geraeumt: bool = False
    bestaetigung: bool = False     # um Bestätigung gebeten
    kostenuebernahme: bool = False  # Kostenübernahme folgt
    zusammenfassung: str = ""      # kurzer Text für die Notiz
    unsicher: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------------------
# Erkennen
# ---------------------------------------------------------------------------------------

_SCHLUSS = re.compile(r"^\s*(mit\s+)?(freundlichen|freundliche|viele|beste|liebe|herzliche)\s+gr(ü|ue)(ß|ss)e|"
                      r"^\s*(schönes|schoenes)\s+wochenende|^\s*vielen\s+dank|^\s*(i\.\s*a\.|im\s+auftrag)\b|"
                      r"^\s*gruß|^\s*lg\b", re.I | re.M)
_KEIN_NAME = {"damen", "herren", "zimmer", "einzelzimmer", "doppelzimmer", "kostenträger", "kostentraeger",
              "maßnahme", "massnahme", "internat", "verwaltungsschule", "reservierung", "bestätigung", "frühstück"}
_GROSS = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"


def _koerper(text: str) -> str:
    """Nur der eigentliche Text – Grußformel und Unterschrift (mit fremden Namen) abschneiden."""
    m = _SCHLUSS.search(text or "")
    return text[:m.start()] if m else (text or "")


def _jahr(tag: int, monat: int, jahr: int | None, heute: date) -> date | None:
    try:
        if jahr is not None:
            return date(jahr + 2000 if jahr < 100 else jahr, monat, tag)
        d = date(heute.year, monat, tag)
    except ValueError:
        return None
    if d < heute - timedelta(days=120):        # ohne Jahr: der nächste passende Termin (bis 4 Monate zurück)
        d = date(heute.year + 1, monat, tag)
    return d


_BEREICH = re.compile(r"(?<![\d.])(\d{1,2})\.?\s*(?:[–\-]|bis)\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?(?!\d)")
_DATUM = re.compile(r"(?<![\d.])(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?(?![\d.]*\d)")


def daten(text: str, heute: date) -> list[tuple[int, date]]:
    """Alle Datumsangaben (Position, Datum) – „14. – 15.10.“ ergibt zwei Daten, Jahr wird ergänzt."""
    erg: list[tuple[int, date]] = []
    belegt: list[tuple[int, int]] = []
    for m in _BEREICH.finditer(text):
        monat, jahr = int(m.group(3)), int(m.group(4)) if m.group(4) else None
        bis = _jahr(int(m.group(2)), monat, jahr, heute)
        von = _jahr(int(m.group(1)), monat, bis.year if bis else jahr, heute)
        if von and bis and von <= bis:
            erg += [(m.start(), von), (m.start() + 1, bis)]
            belegt.append(m.span())
    for m in _DATUM.finditer(text):
        if any(a <= m.start() < b for a, b in belegt):
            continue
        d = _jahr(int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None, heute)
        if d:
            erg.append((m.start(), d))
    # zweites Datum ohne Jahr nach einem mit Jahr: „vom 27.01. bis 29.01.2027“ → gleiches Jahr
    erg.sort()
    for i in range(len(erg) - 1):
        (p1, d1), d2 = erg[i], erg[i + 1][1]
        if d2 - d1 > timedelta(days=200) and d1.replace(year=d2.year) <= d2:
            erg[i] = (p1, d1.replace(year=d2.year))
    return erg


def _datum_nach(text: str, muster: str, heute: date) -> date | None:
    m = re.search(muster, text, re.I)
    if not m:
        return None
    rest = [d for p, d in daten(text[m.start():m.start() + 120], heute)]
    return rest[0] if rest else None


def _name(text: str, betreff: str) -> tuple[str, str]:
    """(„Nachname, Vorname“, Geschlecht) – aus TN-Zeile, „Nachname, Vorname“-Zeile, Herr/Frau oder Betreff."""
    titel = lambda w: w if not w.isupper() else w.capitalize()     # „MUSTERMANN“ → „Mustermann“
    m = re.search(rf"\bTN\s+({_GROSS}),\s*({_GROSS})", text)
    if m:
        return f"{titel(m.group(1))}, {titel(m.group(2))}", ""
    for m in re.finditer(rf"^\s*({_GROSS}),\s*({_GROSS})\s*$", text, re.M):
        if m.group(1).lower() not in _KEIN_NAME:
            return f"{titel(m.group(1))}, {titel(m.group(2))}", ""
    for m in re.finditer(rf"\b(Herrn?|Frau)\s+({_GROSS})(?:\s+({_GROSS}))?", text):
        g = "w" if m.group(1) == "Frau" else "m"
        w1, w2 = m.group(2), m.group(3)
        if w1.lower() in _KEIN_NAME:
            continue
        if w2 and w2.lower() not in _KEIN_NAME and not re.match(r"(IK|RVL|RVT|EMR|ASS|UWT)$", w2):
            return f"{titel(w2)}, {titel(w1)}", g
        return titel(w1), g
    m = re.search(rf"(?:Zimmer|für|von|TN)\s+({_GROSS})\s+({_GROSS})\s*$", betreff.strip())
    if m and m.group(2).lower() not in _KEIN_NAME:
        return f"{titel(m.group(2))}, {titel(m.group(1))}", ""
    return "", ""


def erkennen(betreff: str, text: str, heute: date | None = None) -> Erkannt:
    heute = heute or date.today()
    betreff = re.sub(r"^\s*((AW|WG|RE|FW|Fwd?)\s*:\s*)+", "", betreff or "", flags=re.I)
    koerper = _koerper(text)
    alles = f"{betreff}\n{koerper}"
    klein = alles.lower()
    e = Erkannt()
    # Art – Storno vor Abbruch vor Gästehaus vor Anmeldung
    if re.search(r"storn|absage|sagt\s+ab|nicht\s+an(reisen|treten)", klein):
        e.art = "storno"
    elif re.search(r"abbruch|abgebrochen|brechen\b.*\bab\b|vorzeitig\s+beendet|maßnahme\s+beendet|letzte\s+tag", klein):
        e.art = "abbruch"
    elif re.search(r"gästehaus|gaestehaus|gästezimmer|übernachtung|\büN\b|frühstück|reservierung", alles, re.I):
        e.art = "gast"
    elif re.search(r"anmeldung|melden\s+\w+(\s+\w+)?\s+an\b|bitten\s+um\s+(ein(en)?|das)\s+(zimmer|internatsplatz)|"
                   r"(reservieren|buchen)\s+sie\s+bitte", klein):
        e.art = "anmeldung"
    m = re.search(r"(?<!\d)(\d{6})(?!\d)", alles)
    e.tn_id = m.group(1) if m else ""
    e.name, e.geschlecht = _name(koerper, betreff)
    if not e.name:
        e.name, e.geschlecht = _name(betreff, betreff)
    alle = [d for _p, d in daten(alles, heute)]
    if e.art in ("gast", "anmeldung", "storno"):
        e.von = alle[0] if alle else None
        e.bis = alle[1] if len(alle) > 1 else None
        n = re.search(r"\((\d+)\s*ÜN\)|(\d+)\s*(?:Übernachtungen|Nächte)", alles, re.I)
        if e.von and not e.bis and n:
            e.bis = e.von + timedelta(days=int(n.group(1) or n.group(2)))
        if e.art == "storno" and e.von and not e.bis:
            e.bis = e.von
    elif e.art == "abbruch":
        e.bis = (_datum_nach(alles, r"letzte[rn]?\s+tag|ende\s*:|beendet\s+zum|abgebrochen\s+zum|abbruch\s+zum", heute)
                 or (alle[0] if alle else None))
    else:
        e.von = _datum_nach(alles, r"anreise", heute) or (alle[0] if alle else None)
    if e.art == "hinweis" or (e.art == "unklar" and (e.name or e.tn_id)):
        e.art = "hinweis"
    # Details
    if e.art == "gast":
        e.massnahme = "Gast Gästehaus"
        e.einzelzimmer = True if re.search(r"einzelzimmer", klein) else (False if "doppelzimmer" in klein else None)
        e.fruehstueck = "frühstück" in klein or "fruehstueck" in klein
    m = re.search(r"\b(IK|RVL|RVT|EMR|ASS|UWT|GS)\s*([A-Z]{0,4}\s?\d{2,4})\b", alles)
    if m and not e.massnahme:
        e.massnahme = f"{m.group(1)} {m.group(2)}".strip()
    e.bestaetigung = bool(re.search(r"bestätigung|bestaetigung|bitte\s+bestätigen", klein))
    e.kostenuebernahme = bool(re.search(r"kostenübernahme|kostenuebernahme|kostenzusage", klein))
    if e.art == "abbruch":
        g = re.search(r"(gesundheitlich\w*|persönlich\w*|disziplinarisch\w*|fehlzeiten|arbeitsaufnahme|eigenen\s+wunsch)",
                      klein)
        e.grund = {"gesundheitlich": "gesundheitliche Gründe"}.get(g.group(1)[:14], g.group(1)) if g else ""
        if re.search(r"keine\s+wiederaufnahme", klein):
            e.wiederaufnahme = "nicht geplant"
        elif re.search(r"wiederaufnahme\s+(ist\s+)?möglich", klein):
            e.wiederaufnahme = "möglich"
        e.zimmer_geraeumt = bool(re.search(r"zimmer.{0,40}(geräumt|leer|übergeben)", klein))
    # Zusammenfassung (für die Notiz an der Person)
    teile = []
    if e.art == "gast":
        teile.append(("Einzelzimmer" if e.einzelzimmer else "Doppelzimmer" if e.einzelzimmer is False else "Zimmer")
                     + (" mit Frühstück" if e.fruehstueck else "") + " im Gästehaus")
    if e.art == "abbruch":
        teile.append(f"Abbruch, letzter Tag {e.bis:%d.%m.%Y}" if e.bis else "Abbruch")
        teile += [x for x in (e.grund, f"Wiederaufnahme {e.wiederaufnahme}" if e.wiederaufnahme else "",
                              "Zimmer laut Mail geräumt" if e.zimmer_geraeumt else "") if x]
    if e.art == "storno":
        teile.append("Storno" + (f" {e.von:%d.%m.}–{e.bis:%d.%m.%Y}" if e.von and e.bis else ""))
    if e.art == "hinweis":
        absatz = re.split(r"\n\s*\n", koerper.strip())[0] if koerper.strip() else betreff
        absatz = re.sub(r"\s+", " ", absatz)
        absatz = re.sub(r"^(hallo|liebe|lieber|sehr geehrte)[^,]*,\s*", "", absatz, flags=re.I)
        teile.append(absatz if len(absatz) <= 240 else absatz[:237].rsplit(" ", 1)[0] + " …")
    if e.bestaetigung:
        teile.append("Bestätigung erbeten")
    if e.kostenuebernahme:
        teile.append("Kostenübernahme folgt")
    e.zusammenfassung = " · ".join(teile)
    # Was unsicher ist, sagen wir offen
    if not e.name and not e.tn_id:
        e.unsicher.append("Keine Person erkannt – bitte Namen eintragen.")
    if e.art in ("gast", "anmeldung") and not (e.von and e.bis):
        e.unsicher.append("Zeitraum unvollständig – bitte Anreise und Abreise prüfen.")
    if e.art == "abbruch" and not e.bis:
        e.unsicher.append("Kein Enddatum erkannt – bitte letzten Tag eintragen.")
    if e.art == "unklar":
        e.unsicher.append("Art der Mail nicht erkannt – bitte auswählen.")
    return e


# ---------------------------------------------------------------------------------------
# Zuordnen
# ---------------------------------------------------------------------------------------

@dataclass
class Treffer:
    schluessel: str                # Personen-Schlüssel (Anreiseliste/UWT) oder „gp:…“ (nur Gebäudeplan)
    name: str
    quelle: str                    # „Anreiseliste“ | „Gebäudeplan“ | „UWT“
    von: date
    bis: date
    zimmer: str = ""               # gebucht bzw. geplant
    art: str = ""                  # „belegt“ (Gebäudeplan) | „geplant“ | „ohne Zimmer“
    person: anreiseliste.Person | None = None
    punkte: float = 0.0

    @property
    def text(self) -> str:
        z = self.zimmer.removeprefix("GS-") if self.zimmer else "ohne Zimmer"
        return f"{self.name} · {self.von:%d.%m.}–{self.bis:%d.%m.%Y} · {z} · {self.quelle}"


def zuordnen(e: Erkannt, stand: zp.Planstand, personen: list[anreiseliste.Person]) -> list[Treffer]:
    """Mögliche Personen/Buchungen – beste zuerst. TN-Nummer zählt mehr als der Name."""
    woerter = zp._namenswoerter(e.name)
    nachname = zp._namenswoerter(e.name.split(",")[0]) if e.name else frozenset()
    von, bis = e.von or e.bis, e.bis or e.von

    def bewerten(name: str, tn: str, a: date, b: date) -> float:
        p = 0.0
        if e.tn_id and tn and e.tn_id == tn:
            p += 10
        w = zp._namenswoerter(name)
        if nachname and nachname <= w:
            p += 4 + (2 if woerter <= w else 0)
        if p and von and bis:
            if a <= bis + timedelta(days=3) and von - timedelta(days=3) <= b:
                p += 3
            else:
                p -= min(abs((a - von).days), 400) / 100
        return p

    erg: dict[str, Treffer] = {}
    nach_schluessel = {p.schluessel: p for p in personen}
    for b in stand.bedarf:
        p = nach_schluessel.get(b.schluessel)
        punkte = bewerten(b.name, p.tn_id if p else "", b.von, b.bis)
        if punkte >= 4:
            zw = stand.zugewiesen(b.schluessel)
            erg[b.schluessel] = Treffer(b.schluessel, b.name, "UWT" if b.gruppe == "UWT" else "Anreiseliste", b.von,
                                        b.bis, zw["zimmer"] if zw else "", "geplant" if zw else "ohne Zimmer", p, punkte)
    for zid, bs in stand.lage.belegungen.items():
        for bel in bs:
            if bel.art != "belegt" or not bel.name or bel.name == zp.PIVOT_NAME:
                continue
            punkte = bewerten(bel.name, "", bel.von, bel.bis)
            if punkte < 4:
                continue
            bw = zp.bewohner_aus(stand, bel)
            vorhanden = erg.get(bw.schluessel)
            if vorhanden is not None:            # Person steht im Gebäudeplan: Buchung dort gilt
                vorhanden.zimmer, vorhanden.art, vorhanden.quelle = zid, "belegt", "Gebäudeplan"
                vorhanden.punkte = max(vorhanden.punkte, punkte)
                continue
            erg[bw.schluessel] = Treffer(bw.schluessel, bel.name, "Gebäudeplan", bel.von, bel.bis, zid, "belegt",
                                         None, punkte)
    for p in personen:                         # ohne Internat bzw. nicht im Zimmerplan
        if p.schluessel not in erg:
            punkte = bewerten(p.name, p.tn_id, p.anreise, p.abreise or p.anreise)
            if punkte >= 4:
                erg[p.schluessel] = Treffer(p.schluessel, p.name, "Anreiseliste", p.anreise, p.abreise or p.anreise,
                                            "", "ohne Zimmer", p, punkte)
    return sorted(erg.values(), key=lambda t: (-t.punkte, t.von))


# ---------------------------------------------------------------------------------------
# Vorschlag und Umsetzen
# ---------------------------------------------------------------------------------------

@dataclass
class Schritt:
    art: str                       # person_anlegen | zimmer | planung_entfernen | person_entfernen | abreise |
    #                                notiz | aufgabe
    text: str
    an: bool = True
    daten: dict = field(default_factory=dict)


def neue_person(e: Erkannt) -> anreiseliste.Person | None:
    if not e.name or not e.von:
        return None
    gast = e.art == "gast"
    return anreiseliste.Person(name=e.name, massnahme=e.massnahme or ("Gast Gästehaus" if gast else ""),
                               anreise=e.von, internat=True, gruppe="Reha", tn_id=e.tn_id, abreise=e.bis,
                               geschlecht=e.geschlecht, bemerkung=e.zusammenfassung[:200],
                               abreise_quelle="hand" if e.bis else "")


def vorschlag(e: Erkannt, treffer: Treffer | None, stand: zp.Planstand, heute: date | None = None) -> list[Schritt]:
    heute = heute or date.today()
    s: list[Schritt] = []
    wer = treffer.name if treffer else e.name
    if e.art in ("gast", "anmeldung"):
        if treffer is None or treffer.person is None:
            p = neue_person(e)
            if p is not None:
                s.append(Schritt("person_anlegen", f"Person anlegen: {p.name} – {p.massnahme or 'Anmeldung'}, "
                                                   f"{p.anreise:%d.%m.%Y} – {p.abreise:%d.%m.%Y}" if p.abreise else
                                                   f"Person anlegen: {p.name}, Anreise {p.anreise:%d.%m.%Y}",
                                 daten={"person": p.zu_dict()}))
                b = zp.bedarf_aus_personen([p])
                if b:
                    zt = zp.vorschlagen(stand.lage, b)[0]
                    if zt.zimmer is not None:
                        s.append(Schritt("zimmer", f"Zimmer reservieren: {zt.zimmer.kurz} ({zt.grund})",
                                         daten={"zimmer": zt.zimmer.id, "person": p.schluessel}))
                    else:
                        s.append(Schritt("zimmer", f"Kein passendes Zimmer frei – {zt.warnungen[0] if zt.warnungen else ''}",
                                         an=False, daten={"zimmer": "", "person": p.schluessel}))
        elif treffer.art == "ohne Zimmer":
            b = next((x for x in stand.bedarf if x.schluessel == treffer.schluessel), None)
            zt = zp.vorschlagen(stand.lage, [b])[0] if b else None
            if zt and zt.zimmer:
                s.append(Schritt("zimmer", f"Zimmer reservieren für {treffer.name}: {zt.zimmer.kurz}",
                                 daten={"zimmer": zt.zimmer.id, "person": treffer.schluessel}))
        if e.bestaetigung:
            s.append(Schritt("notiz", f"Wiedervorlage heute: Bestätigung an den Absender senden ({wer})",
                             daten={"text": "Bestätigung an den Absender senden", "wv": heute.isoformat()}))
        if e.kostenuebernahme:
            s.append(Schritt("notiz", f"Wiedervorlage in 7 Tagen: Kostenübernahme eingegangen? ({wer})",
                             daten={"text": "Kostenübernahme eingegangen?", "wv": (heute + timedelta(days=7)).isoformat()}))
    elif e.art == "storno":
        if treffer is None:
            s.append(Schritt("aufgabe", "Keine passende Buchung gefunden – bitte Person auswählen oder im "
                                        "Belegungssystem prüfen.", an=False))
        else:
            if treffer.art == "geplant":
                s.append(Schritt("planung_entfernen", f"Zimmerplanung entfernen – {treffer.zimmer.removeprefix('GS-')} "
                                                      "wird frei", daten={"person": treffer.schluessel}))
            if treffer.person is not None:
                manuell = treffer.person.liste == anreiseliste.MANUELL
                s.append(Schritt("person_entfernen",
                                 "Person aus den Anreisen entfernen" if manuell else
                                 "Person als „ohne Internat“ markieren (Storno laut Mail)",
                                 daten={"person": treffer.schluessel, "loeschen": manuell}))
            if treffer.art == "belegt":
                s.append(Schritt("aufgabe", f"Aufgabe (Wiedervorlage heute): im Belegungssystem stornieren – {treffer.name}, "
                                            f"{treffer.zimmer.removeprefix('GS-')}, {treffer.von:%d.%m.}–{treffer.bis:%d.%m.%Y}",
                                 daten={"person": treffer.schluessel}))
    elif e.art == "abbruch":
        if treffer is None:
            s.append(Schritt("aufgabe", "Keine passende Person gefunden – bitte auswählen.", an=False))
        else:
            if e.bis and treffer.person is not None:
                s.append(Schritt("abreise", f"Abreise auf {e.bis:%d.%m.%Y} setzen (letzter Tag laut Mail)",
                                 daten={"person": treffer.schluessel, "abreise": e.bis.isoformat()}))
            if e.bis and treffer.zimmer:
                s.append(Schritt("aufgabe", f"Aufgabe (Wiedervorlage heute): im Belegungssystem Abreise auf {e.bis:%d.%m.%Y} ändern "
                                            f"({treffer.zimmer.removeprefix('GS-')})", daten={"person": treffer.schluessel}))
    if treffer is not None or e.art in ("gast", "anmeldung", "hinweis"):
        wv = None
        if e.art == "hinweis" and e.von and e.von > heute:
            wv = max(heute, e.von - timedelta(days=2))
        if e.zusammenfassung:
            s.append(Schritt("notiz", f"Notiz an {wer}: „{e.zusammenfassung}“"
                                      + (f" – Wiedervorlage {wv:%d.%m.}" if wv else ""),
                             daten={"text": e.zusammenfassung, "wv": wv.isoformat() if wv else None,
                                    "person": treffer.schluessel if treffer else None}))
    return s


@dataclass
class Eingang:
    id: str
    eingang: str                   # ISO-Zeitpunkt
    betreff: str
    absender: str
    text: str
    art: str
    name: str
    tn_id: str
    von: str | None
    bis: str | None
    person: str = ""               # zugeordneter Personen-Schlüssel
    status: str = "offen"          # offen | erledigt | zu prüfen | verworfen
    erledigt: list[str] = field(default_factory=list)       # umgesetzte Schritte
    pruefliste: dict[str, bool] = field(default_factory=dict)

    @property
    def offen_zu_pruefen(self) -> list[str]:
        return [k for k, v in self.pruefliste.items() if not v]


def eingaenge() -> list[Eingang]:
    roh = speicher.lesen(DATEI, {}).get("eingaenge", [])
    erg = []
    for d in roh:
        try:
            erg.append(Eingang(**{k: d.get(k) for k in Eingang.__dataclass_fields__ if k in d}))
        except TypeError:
            continue
    return sorted(erg, key=lambda x: x.eingang, reverse=True)


def eingang_speichern(x: Eingang) -> None:
    roh = speicher.lesen(DATEI, {})
    liste = [d for d in roh.get("eingaenge", []) if d.get("id") != x.id] + [asdict(x)]
    speicher.schreiben(DATEI, {"eingaenge": liste})


def eingang_entfernen(eid: str) -> None:
    roh = speicher.lesen(DATEI, {})
    speicher.schreiben(DATEI, {"eingaenge": [d for d in roh.get("eingaenge", []) if d.get("id") != eid]})


def offen_anzahl() -> int:
    """Offene und zu prüfende Eingänge (für Seitenleiste und Startseite)."""
    return sum(1 for x in eingaenge() if x.status in ("offen", "zu prüfen"))


def eingang_pruefen(x: Eingang, punkt: str, an: bool) -> Eingang:
    x.pruefliste[punkt] = an
    if x.status in ("zu prüfen", "erledigt") and x.pruefliste:
        x.status = "erledigt" if all(x.pruefliste.values()) else "zu prüfen"
    eingang_speichern(x)
    return x


def umsetzen(e: Erkannt, schritte: list[Schritt], stand: zp.Planstand, betreff: str = "", text: str = "",
             absender: str = "", treffer: Treffer | None = None, jetzt: datetime | None = None) -> Eingang:
    """Führt die angehakten Schritte aus und legt die Mail im Posteingang ab."""
    from . import termine

    jetzt = jetzt or datetime.now()
    erledigt: list[str] = []
    person = treffer.schluessel if treffer else ""
    for s in (x for x in schritte if x.an):
        if s.art == "person_anlegen":
            p = anreiseliste.Person.aus_dict(s.daten["person"])
            anreiseliste.person_speichern(p)
            person = p.schluessel
        elif s.art == "zimmer" and s.daten.get("zimmer"):
            neu = zp.laden()                        # mit der gerade angelegten Person
            zp.zuweisung_setzen(neu, s.daten["person"], s.daten["zimmer"], "Posteingang")
        elif s.art == "planung_entfernen":
            zp.zuweisungen_entfernen({s.daten["person"]}, "Storno (Posteingang)")
        elif s.art == "person_entfernen":
            personen, _ = anreiseliste.laden()
            p = next((x for x in personen if x.schluessel == s.daten["person"]), None)
            if p is not None:
                if s.daten.get("loeschen"):
                    anreiseliste.person_loeschen(p.schluessel)
                    zp.person_geloescht(p.schluessel)
                else:
                    anreiseliste.person_speichern(replace(p, internat=False,
                                                          bemerkung=(p.bemerkung + " · Storno laut Mail").strip(" ·")))
        elif s.art == "abreise":
            personen, _ = anreiseliste.laden()
            p = next((x for x in personen if x.schluessel == s.daten["person"]), None)
            if p is not None:
                anreiseliste.person_speichern(replace(p, abreise=date.fromisoformat(s.daten["abreise"]),
                                                      abreise_quelle="hand", erledigt=False))
        elif s.art == "notiz":
            ziel = s.daten.get("person") or person
            if ziel:
                wv = s.daten.get("wv")
                termine.notiz_speichern(termine.Notiz(ziel, (treffer.name if treffer else e.name), s.daten["text"],
                                                      jetzt.date(), date.fromisoformat(wv) if wv else None))
        elif s.art == "aufgabe" and (s.daten.get("person") or person):
            termine.notiz_speichern(termine.Notiz(s.daten.get("person") or person, treffer.name if treffer else e.name,
                                                  s.text, jetzt.date(), jetzt.date()))
        erledigt.append(s.text)
    pruef = {}
    if e.art == "abbruch":
        pruef = {k: False for k in PRUEFLISTE_ABBRUCH}
    elif e.art == "storno" and treffer is not None and treffer.art == "belegt":
        pruef = {k: False for k in PRUEFLISTE_STORNO}
    x = Eingang(uuid.uuid4().hex[:10], jetzt.isoformat(timespec="seconds"), betreff, absender, text, e.art,
                treffer.name if treffer else e.name, e.tn_id, e.von.isoformat() if e.von else None,
                e.bis.isoformat() if e.bis else None, person, "zu prüfen" if pruef else "erledigt", erledigt, pruef)
    eingang_speichern(x)
    return x


def ablegen(e: Erkannt, betreff: str, text: str, absender: str = "", status: str = "offen",
            jetzt: datetime | None = None) -> Eingang:
    """Ohne Aktion im Posteingang ablegen (später bearbeiten) bzw. verwerfen."""
    jetzt = jetzt or datetime.now()
    x = Eingang(uuid.uuid4().hex[:10], jetzt.isoformat(timespec="seconds"), betreff, absender, text, e.art, e.name,
                e.tn_id, e.von.isoformat() if e.von else None, e.bis.isoformat() if e.bis else None, status=status)
    eingang_speichern(x)
    return x


def outlook_auswahl() -> list[tuple[str, str, str]]:
    """In Outlook markierte Mails als (Betreff, Absender, Text). Nur Windows mit klassischem Outlook."""
    import win32com.client                       # noqa: PLC0415 – nur unter Windows vorhanden

    ol = win32com.client.Dispatch("Outlook.Application")
    auswahl = ol.ActiveExplorer().Selection
    erg = []
    for i in range(1, auswahl.Count + 1):
        m = auswahl.Item(i)
        if getattr(m, "Class", 0) == 43:            # olMail
            erg.append((str(m.Subject or ""), str(m.SenderName or ""), str(m.Body or "")))
    return erg


def eml_lesen(pfad) -> tuple[str, str, str]:
    """.eml-Datei → (Betreff, Absender, Text)."""
    from email import policy
    from email.parser import BytesParser

    with open(pfad, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    teil = msg.get_body(preferencelist=("plain", "html"))
    text = teil.get_content() if teil is not None else ""
    if teil is not None and teil.get_content_type() == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)
    return str(msg.get("subject", "")), str(msg.get("from", "")), text
