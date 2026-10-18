"""Assistenz: normale Eingaben verstehen und umsetzen – ohne erst die Zimmerkarte zu öffnen.

Beispiele (eine Zeile = ein Auftrag, mehrere Zeilen auf einmal gehen auch)::

    6-403 Fliegen beseitigen bis 1.11.26     → Frist im Kalender, Mangel „Ungeziefer“ (Zimmer wird nicht zugeteilt),
                                                Notiz am Zimmer
    3.1-E02 Rollo defekt                      → Mangel „Fenster/Rollo“ (leicht), Notiz am Zimmer
    2-115 Heizung erledigt                    → offenen Mangel „Heizung“ als behoben markieren, Frist erledigt
    Freitag 10 Uhr Teambesprechung            → Termin im Kalender
    morgen Schlüssel 2-204 an FM übergeben    → Termin im Kalender + Notiz am Zimmer

Erkannt wird mit festen Regeln (ohne Internet): Zimmer (wie im Zimmerplan, z. B. 6-403, 3.1-E02), Datum
(„bis 1.11.26“ = Frist, „am 3.11.“ / „morgen“ / „Freitag“ / „in 3 Tagen“ / „nächste Woche“ = Termin), Uhrzeit
(„10 Uhr“, „10:30“), Mangelart aus Stichwörtern und „erledigt/behoben“. Vor dem Ausführen wird alles angezeigt und
lässt sich abwählen; jede Ausführung kann rückgängig gemacht werden. Rein, ohne Qt.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from . import maengel, speicher, termine
from . import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/assistenz.json"
FRIST_VORLAUF = 2           # Erinnerung an eine Frist so viele Tage vorher
TERMIN_VORLAUF = 1

WOCHENTAGE = {"montag": 0, "mo": 0, "dienstag": 1, "di": 1, "mittwoch": 2, "mi": 2, "donnerstag": 3, "do": 3,
              "freitag": 4, "fr": 4, "samstag": 5, "sa": 5, "sonntag": 6, "so": 6}

# Stichwörter → Mängel-Art (spezielle vor allgemeinen; Wortanfänge, Groß/klein egal)
MANGEL_WOERTER: list[tuple[str, tuple[str, ...]]] = [
    ("ungeziefer", ("fliege", "ungeziefer", "maus", "mäuse", "ratte", "schabe", "kakerlake", "wanze", "bettwanze",
                    "ameise", "motte", "silberfisch", "floh", "flöhe", "wespe")),
    ("schimmel", ("schimmel", "feucht", "stockfleck")),
    ("rauchmelder", ("rauchmelder", "feuermelder", "brandmelder")),
    ("abfluss", ("abfluss", "verstopf", "siphon")),
    ("wasser", ("wasserhahn", "hahn", "tropft", "undicht", "leck", "wasserschaden")),
    ("heizung", ("heizung", "heizkörper", "thermostat")),
    ("bad", ("dusche", "wc", "toilette", "klo", "bad", "waschbecken", "spülung", "brause", "silikon")),
    ("elektrik", ("licht", "lampe", "steckdose", "strom", "sicherung", "kühlschrank", "küleg", "leuchte")),
    ("tuer", ("tür", "schloss", "schlüssel", "zylinder")),
    ("geruch", ("geruch", "riecht", "stinkt", "rauch", "muffig")),
    ("matratze", ("matratze",)),
    ("fenster", ("fenster", "rollo", "plissee", "jalousie", "gardine", "vorhang", "store")),
    ("boden_dreckig", ("fleck", "dreckig", "verschmutz", "schmutz")),
    ("boden_kaputt", ("teppich", "boden", "filz", "pvc", "vinyl")),
    ("wand", ("wand", "tapete", "streichen", "putz", "loch", "löcher")),
    ("moebel", ("möbel", "schrank", "stuhl", "tisch", "bett", "regal", "nachttisch", "kommode", "spiegel")),
    ("grundreinigung", ("grundreinigung", "reinigung", "reinigen", "putzen", "säubern")),
    ("renovierung", ("renovier", "reno")),
]
# Ein Mangel entsteht nur mit einem Schadens- oder Reparaturwort („Schlüssel übergeben“ ist kein Mangel) –
# außer bei Arten, die schon selbst ein Mangel sind
SCHADEN = re.compile(r"\b(defekt|kaputt|beschädigt|fehlt|fehlen|tropft|verstopft|undicht|lose|locker|klemmt|hakt|"
                     r"schwergängig|piept|zerrissen|gerissen|riss|alt|dreckig|fleck|stinkt|riecht|beseitig|reparier|"
                     r"erneuer|tausch|austausch|wechseln|streichen|prüfen|reinig|säuber|geht nicht|funktioniert nicht|"
                     r"kalt|nass|schimmel|loch|löcher)", re.I)
MANGEL_VON_SICH_AUS = {"ungeziefer", "schimmel", "grundreinigung", "renovierung", "abfluss", "geruch"}
ERLEDIGT = re.compile(r"\b(erledigt|behoben|beseitigt|repariert|fertig|gemacht|getauscht|ausgetauscht|ok)\b", re.I)
_ZIMMER = re.compile(r"(?<![\w.])(?:GS-)?(2|3\.1|3\.2|3\.3|6)\s*-\s*([A-Za-z]?\d{2,4})(?![\w])")
_DATUM = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})?(?![\d])")
_UHR = re.compile(r"\b(?:um\s+)?(\d{1,2})(?::(\d{2}))?\s*uhr\b|\b(\d{1,2}):(\d{2})\b", re.I)


@dataclass
class Aktion:
    art: str                    # termin | notiz | mangel | sperren | behoben
    text: str                   # Anzeige in der Vorschau
    an: bool = True
    daten: dict = field(default_factory=dict)


@dataclass
class Verstanden:
    eingabe: str
    zimmer: list[str] = field(default_factory=list)       # Zimmer-IDs
    datum: date | None = None
    frist: bool = False                                    # „bis …“
    uhrzeit: str = ""
    aufgabe: str = ""                                      # Text ohne Zimmer und Datum
    mangel: str = ""                                       # Mängel-Art aus Stichwörtern
    erledigt: bool = False
    hinweise: list[str] = field(default_factory=list)
    aktionen: list[Aktion] = field(default_factory=list)


# ---------------------------------------------------------------------------------------
# Verstehen
# ---------------------------------------------------------------------------------------

def _datum(text: str, heute: date) -> tuple[date | None, bool, str]:
    """(Datum, ist Frist, Text ohne die Datumsangabe)."""
    t = text
    frist = False
    d: date | None = None

    def weg(m: re.Match) -> None:
        nonlocal t, frist
        davor = t[:m.start()].rstrip()
        if re.search(r"\b(bis|spätestens|bis zum|bis spätestens)$", davor, re.I):
            frist = True
            davor = re.sub(r"\s*\b(bis zum|bis spätestens|spätestens|bis)$", "", davor, flags=re.I)
        elif re.search(r"\b(am|ab|zum|für)$", davor, re.I):
            davor = re.sub(r"\s*\b(am|ab|zum|für)$", "", davor, flags=re.I)
        t = (davor + " " + t[m.end():]).strip()

    if (m := _DATUM.search(t)):
        tag, monat, jahr = int(m.group(1)), int(m.group(2)), m.group(3)
        try:
            if jahr:
                d = date(int(jahr) + (2000 if len(jahr) == 2 else 0), monat, tag)
            else:
                d = date(heute.year, monat, tag)
                if d < heute - timedelta(days=30):            # „3.1.“ im Dezember = nächstes Jahr
                    d = d.replace(year=heute.year + 1)
        except ValueError:
            d = None
        if d is not None:
            weg(m)
            return d, frist, t
    relativ = [(r"\bübermorgen\b", 2), (r"\bmorgen\b", 1), (r"\bheute\b", 0)]
    for muster, tage in relativ:
        if (m := re.search(muster, t, re.I)):
            weg(m)
            return heute + timedelta(days=tage), frist, t
    if (m := re.search(r"\bin\s+(\d+)\s+(tag|tagen|woche|wochen)\b", t, re.I)):
        n = int(m.group(1)) * (7 if m.group(2).lower().startswith("woche") else 1)
        weg(m)
        return heute + timedelta(days=n), frist, t
    if (m := re.search(r"\b(nächste|kommende)\s+woche\b", t, re.I)):
        weg(m)
        return heute + timedelta(days=7 - heute.weekday()), frist, t
    if (m := re.search(r"\b(ende des monats|monatsende|ende monat)\b", t, re.I)):
        weg(m)
        naechster = (heute.replace(day=28) + timedelta(days=4)).replace(day=1)
        return naechster - timedelta(days=1), frist, t
    for m in re.finditer(r"\b(nächsten\s+|kommenden\s+)?(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|"
                         r"mo|di|mi|do|fr|sa|so)\b\.?", t, re.I):
        wort = m.group(2).lower()
        if len(wort) == 2 and not re.search(r"\b(bis|am|ab)\s*$", t[:m.start()], re.I):
            continue                                       # „so“, „do“ … nur nach „bis/am/ab“ als Wochentag
        ziel = WOCHENTAGE[wort]
        tage = (ziel - heute.weekday()) % 7
        if m.group(1) and tage == 0:
            tage = 7
        weg(m)
        return heute + timedelta(days=tage), frist, t
    return None, False, t


def _zimmer(text: str, bekannt: set[str]) -> tuple[list[str], str, list[str]]:
    from .zkl import zimmer_id

    ids, hinweise = [], []
    t = text
    for m in list(_ZIMMER.finditer(text)):
        zid = zimmer_id(f"{m.group(1)}-{m.group(2)}", bekannt)
        if zid in bekannt:
            ids.append(zid)
            t = t.replace(m.group(0), " ")
        else:
            hinweise.append(f"Zimmer „{m.group(0)}“ gibt es im Zimmerplan nicht.")
    # „Zimmer 403“ ohne Haus: nur, wenn die Nummer eindeutig ist
    for m in re.finditer(r"\bzimmer\s+([A-Za-z]?\d{2,4})\b", t, re.I):
        passend = [z for z in bekannt if z.rsplit("-", 1)[-1].upper() == m.group(1).upper()]
        if len(passend) == 1:
            ids.append(passend[0])
            t = t.replace(m.group(0), " ")
        elif passend:
            hinweise.append(f"„{m.group(0)}“ gibt es in mehreren Häusern – bitte mit Haus schreiben, z. B. 6-{m.group(1)}.")
    return list(dict.fromkeys(ids)), re.sub(r"\s{2,}", " ", t).strip(" ,;:-"), hinweise


def mangel_art(text: str) -> str:
    klein = text.lower()
    for art, woerter in MANGEL_WOERTER:
        if any(re.search(rf"\b{re.escape(w)}", klein) for w in woerter):
            return art
    return ""


def verstehen(eingabe: str, bekannt: set[str], heute: date | None = None) -> Verstanden:
    heute = heute or date.today()
    v = Verstanden(eingabe.strip())
    v.zimmer, rest, v.hinweise = _zimmer(v.eingabe, bekannt)
    v.datum, v.frist, rest = _datum(rest, heute)
    if (m := _UHR.search(rest)):
        std, minute = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        if int(std) < 24:
            v.uhrzeit = f"{int(std):02d}:{minute or '00'}"
            rest = (rest[:m.start()] + rest[m.end():]).strip()
    v.erledigt = bool(ERLEDIGT.search(rest))
    v.aufgabe = re.sub(r"\s{2,}", " ", rest).strip(" ,;:-")
    v.aufgabe = v.aufgabe[:1].upper() + v.aufgabe[1:]
    v.mangel = mangel_art(v.aufgabe) if v.zimmer else ""
    if v.mangel and v.mangel not in MANGEL_VON_SICH_AUS and not SCHADEN.search(v.aufgabe) and not v.erledigt:
        v.mangel = ""                                      # z. B. „Schlüssel an FM übergeben“: Aufgabe, kein Mangel
    if v.datum is not None and v.datum < heute and not v.erledigt:
        v.hinweise.append(f"Das Datum {v.datum:%d.%m.%Y} liegt in der Vergangenheit.")
    v.aktionen = _aktionen(v)
    if not v.aktionen:
        v.hinweise.append("Nichts erkannt, was sich eintragen lässt – bitte Zimmer (z. B. 6-403) und/oder ein Datum "
                          "(z. B. „bis 1.11.“, „morgen“) angeben.")
    return v


def _kurz(zid: str) -> str:
    return zid.removeprefix("GS-")


def _aktionen(v: Verstanden) -> list[Aktion]:
    akt: list[Aktion] = []
    zimmer_text = ", ".join(_kurz(z) for z in v.zimmer)
    titel = f"{zimmer_text}: {v.aufgabe}" if v.zimmer else v.aufgabe
    if v.uhrzeit:
        titel = f"{v.uhrzeit} Uhr – {titel}"
    if v.erledigt:
        for z in v.zimmer:
            offen = [m for m in maengel.offen(z) if not v.mangel or m.art == v.mangel]
            for m in offen:
                akt.append(Aktion("behoben", f"Mangel „{m.text}“ in {_kurz(z)} als behoben markieren",
                                  daten={"zimmer": z, "art": m.art}))
        for t in _offene_fristen(v.zimmer, v.mangel):
            akt.append(Aktion("termin_erledigt", f"Kalender: „{t.titel}“ ({t.datum:%d.%m.}) erledigt", daten={"id": t.id}))
        if v.zimmer:
            akt.append(Aktion("notiz", f"Notiz am Zimmer {zimmer_text}: „{v.aufgabe}“",
                              daten={"zimmer": v.zimmer, "text": v.aufgabe}))
        return akt
    if v.datum is not None:
        art = "Frist" if v.frist else "Termin"
        vorlauf = FRIST_VORLAUF if v.frist else TERMIN_VORLAUF
        akt.append(Aktion("termin", f"Kalender: {art} am {v.datum:%d.%m.%Y} – „{titel}“ (Erinnerung {vorlauf} "
                                    f"Tag{'e' if vorlauf > 1 else ''} vorher)",
                          daten={"datum": v.datum.isoformat(), "titel": (f"Frist: {titel}" if v.frist else titel),
                                 "vorlauf": vorlauf, "text": v.eingabe}))
    for z in v.zimmer:
        if v.mangel:
            name = maengel.NAMEN.get(v.mangel, v.mangel)
            schon = any(m.art == v.mangel for m in maengel.offen(z))
            notiz = v.aufgabe + (f" – bis {v.datum:%d.%m.%Y}" if v.datum and v.frist else "")
            if not schon:
                akt.append(Aktion("mangel", f"Mangel in {_kurz(z)}: {name} – „{notiz}“",
                                  daten={"zimmer": z, "art": v.mangel, "notiz": notiz}))
            gesperrt = v.mangel in maengel.UNBEWOHNBAR_STANDARD
            akt.append(Aktion("sperren", f"{_kurz(z)} bis zur Erledigung nicht zuteilen (macht unbewohnbar)",
                              an=gesperrt, daten={"zimmer": z, "art": v.mangel}))
    if v.zimmer:
        notiz = v.aufgabe + (f" – {'bis' if v.frist else 'am'} {v.datum:%d.%m.%Y}" if v.datum else "")
        akt.append(Aktion("notiz", f"Notiz am Zimmer {zimmer_text}: „{notiz}“",
                          daten={"zimmer": v.zimmer, "text": notiz}))
    return akt


def _offene_fristen(zimmer: list[str], art: str) -> list[termine.Termin]:
    """Offene eigene Termine zu diesen Zimmern (Titel enthält die Zimmernummer) – passend zur Mängel-Art."""
    erg = []
    for t in termine.eigene():
        if t.erledigt:
            continue
        if any(re.search(rf"(?<![\w.]){re.escape(_kurz(z))}(?![\w])", t.titel) for z in zimmer):
            if not art or mangel_art(t.titel) == art:
                erg.append(t)
    return erg


# ---------------------------------------------------------------------------------------
# Ausführen und Rückgängig
# ---------------------------------------------------------------------------------------

def ausfuehren(liste: list[Verstanden], heute: date | None = None) -> dict:
    """Angehakte Aktionen ausführen. Gibt den Protokolleintrag zurück (mit allem, was für Rückgängig nötig ist)."""
    heute = heute or date.today()
    eintrag = {"id": uuid.uuid4().hex[:10], "zeit": datetime.now().isoformat(timespec="seconds"),
               "eingaben": [v.eingabe for v in liste], "erledigt": [], "rueck": []}
    for v in liste:
        for a in (a for a in v.aktionen if a.an):
            d = a.daten
            if a.art == "termin":
                t = termine.eigenen_speichern(termine.Termin("", date.fromisoformat(d["datum"]), d["titel"],
                                                             f"Assistenz: {d['text']}", vorlauf=d["vorlauf"]))
                eintrag["rueck"].append({"art": "termin", "id": t.id})
            elif a.art == "mangel":
                if maengel.setzen(d["zimmer"], d["art"], True, heute, d["notiz"]):
                    eintrag["rueck"].append({"art": "mangel", "zimmer": d["zimmer"], "mangel": d["art"]})
            elif a.art == "sperren":
                if maengel.sperren_setzen(d["zimmer"], d["art"], True):
                    eintrag["rueck"].append({"art": "sperren", "zimmer": d["zimmer"], "mangel": d["art"]})
            elif a.art == "behoben":
                if maengel.setzen(d["zimmer"], d["art"], False, heute):
                    eintrag["rueck"].append({"art": "behoben", "zimmer": d["zimmer"], "mangel": d["art"]})
            elif a.art == "termin_erledigt":
                t = next((t for t in termine.eigene() if t.id == d["id"]), None)
                if t is not None:
                    termine.erledigt_setzen(t, True)
                    eintrag["rueck"].append({"art": "termin_erledigt", "id": t.id})
            elif a.art == "notiz":
                for z in d["zimmer"]:
                    n = termine.notiz_speichern(termine.Notiz(zp.zimmer_schluessel(z), f"Zimmer {_kurz(z)}",
                                                              d["text"], heute))
                    eintrag["rueck"].append({"art": "notiz", "id": n.id})
            eintrag["erledigt"].append(a.text)
    alle = speicher.lesen(DATEI, {}).get("eintraege", [])
    speicher.schreiben(DATEI, {"eintraege": ([eintrag] + alle)[:200]})
    return eintrag


def verlauf() -> list[dict]:
    return speicher.lesen(DATEI, {}).get("eintraege", [])


def rueckgaengig(eintrag_id: str) -> int:
    """Alles aus einem Eintrag zurücknehmen (in umgekehrter Reihenfolge). Gibt die Zahl der Schritte zurück."""
    alle = verlauf()
    e = next((x for x in alle if x["id"] == eintrag_id), None)
    if e is None or e.get("zurueck"):
        return 0
    n = 0
    for r in reversed(e.get("rueck", [])):
        if r["art"] == "termin":
            termine.eigenen_loeschen(r["id"])
        elif r["art"] == "notiz":
            termine.notiz_loeschen(r["id"])
        elif r["art"] == "mangel":
            _mangel_entfernen(r["zimmer"], r["mangel"])
        elif r["art"] == "sperren":
            maengel.sperren_setzen(r["zimmer"], r["mangel"], False)
        elif r["art"] == "behoben":
            _behoben_zuruecknehmen(r["zimmer"], r["mangel"])
        elif r["art"] == "termin_erledigt":
            t = next((t for t in termine.eigene() if t.id == r["id"]), None)
            if t is not None:
                termine.erledigt_setzen(t, False)
        n += 1
    e["zurueck"] = datetime.now().isoformat(timespec="seconds")
    speicher.schreiben(DATEI, {"eintraege": alle})
    return n


def _mangel_entfernen(zimmer: str, art: str) -> None:
    """Den zuletzt gemeldeten offenen Mangel dieser Art ganz entfernen (war ein Versehen, kein „behoben“)."""
    alle = maengel.laden()
    offen = [m for m in alle if m.zimmer == zimmer and m.art == art and m.behoben is None]
    if offen:
        alle.remove(offen[-1])
        speicher.schreiben(maengel.DATEI, {"maengel": [m.zu_dict() for m in alle]})


def _behoben_zuruecknehmen(zimmer: str, art: str) -> None:
    alle = maengel.laden()
    behoben = sorted((m for m in alle if m.zimmer == zimmer and m.art == art and m.behoben is not None),
                     key=lambda m: m.behoben)
    if behoben:
        behoben[-1].behoben = None
        speicher.schreiben(maengel.DATEI, {"maengel": [m.zu_dict() for m in alle]})
