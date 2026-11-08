"""Bestandsmodell der Maßnahmen-Belegung – Schritt 1: Aufenthalte und Prüfbericht (0.76). Rein, ohne NiceGUI.

Grundlage ist der Maßnahmen-Pivot (Excel aus dem Hauptsystem): eine Zeile je Person, darunter je eine Zeile je Kurs,
Spalten = Tage, Zelle 1 = anwesend. Für die spätere Prognose (Verbleibskurven, Übergänge, Simulation) braucht es die
**Aufenthalte je Person und Kurs** – Schritt 1 bildet sie und prüft die Daten, bevor irgendetwas geschätzt wird.

**Datenschutz:** Namen werden nie gespeichert. Jede Person bekommt beim Einlesen eine fortlaufende Nummer (bei jedem
Einlesen neu vergeben); gespeichert werden je Aufenthalt nur Nummer, Kurs, Eintritt, Austritt und Zähler. Gründe für
Abbrüche oder Gesundheitsdaten kommen im Pivot nicht vor und werden nicht erfasst.

**Personen- und Kurszeilen:** Eine Zeile mit Kursmuster („GS EMR ASS 261109“) ist eine Kurszeile. Andere Zeilen ohne
Werte sind Personen. Eine Zeile ohne Kursmuster, aber mit Werten, ist entweder ein alter Kurs mit Langnamen
(„Zerspanungsmechaniker/-in …“) oder – wenn direkt danach Kurszeilen folgen – eine Person mit Teilsumme.
"""

from __future__ import annotations

import re
import statistics as stt
from dataclasses import dataclass, field
from datetime import date, timedelta

_KURS = re.compile(r"^[A-Z]{2}\s+\S")

# Parameter (Standardwerte aus dem Prompt; später unter Einstellungen änderbar)
LUECKE_TAGE = 30              # größere Lücke = Unterbrechung
LAUFEND_TAGE = 3              # Austritt so nah am letzten Ist-Tag = läuft noch (zensiert)
AUFFAELLIG = {"Hauptmaßnahme": 913, "Assessment": 92}     # > 30 Monate bzw. > 3 Monate
GRUPPEN = ("Assessment", "Vorbereitung", "Hauptmaßnahme", "IBTZ", "Sonstige", "Ignoriert")   # Ignoriert: zählt nirgends

# Zuordnungstabelle – Startwerte. „offen“ = laut Prompt noch zu klären (Dauer bzw. Art nicht gesichert).
ZUORDNUNG_STANDARD = [
    # 0.77: Solldauer „aus Anmeldung“ = gemessen je Kursfamilie aus den Daten der Zimmerbelegung (Anreiselisten mit
    # eingetragener Abreise, Gebäudeplan) – so werden 4- und 6-wöchige Assessments, RVT usw. von selbst unterschieden.
    {"muster": "EMR", "art": "EMR-Assessment", "gruppe": "Assessment", "soll_tage": None, "soll_quelle": "anmeldung"},
    {"muster": "ASPQ", "art": "Assessment ASPQ", "gruppe": "Assessment", "soll_tage": None, "soll_quelle": "anmeldung"},
    {"muster": "ASS", "art": "Assessment", "gruppe": "Assessment", "soll_tage": 42, "soll_quelle": "anmeldung"},
    {"muster": "RVL", "art": "Reha-Vorbereitungslehrgang", "gruppe": "Vorbereitung", "soll_tage": 91, "soll_quelle": "anmeldung"},
    {"muster": "RVT", "art": "RVT", "gruppe": "Vorbereitung", "soll_tage": 91, "soll_quelle": "anmeldung"},
    {"muster": "IBTZ", "art": "IBTZ", "gruppe": "IBTZ", "soll_tage": None},
    {"muster": "VW", "art": "Hauptmaßnahme VW", "gruppe": "Hauptmaßnahme", "soll_tage": 730, "soll_quelle": "anmeldung",
     "max_plaetze": 24},                     # nur VW erreicht seine Kursgröße (24 Plätze)
    {"muster": "CNC", "art": "Hauptmaßnahme CNC", "gruppe": "Hauptmaßnahme", "soll_tage": 730},
    {"muster": "M-GA", "art": "Hauptmaßnahme M-GA", "gruppe": "Hauptmaßnahme", "soll_tage": 730},
    {"muster": "BFS", "art": "Hauptmaßnahme BFS", "gruppe": "Hauptmaßnahme", "soll_tage": 730},
    {"muster": "JobTrain", "art": "JobTrain", "gruppe": "Ignoriert", "soll_tage": None},      # für uns ohne Belang
    {"muster": "Bauhelfer", "art": "Bauhelfer", "gruppe": "Ignoriert", "soll_tage": None},
]


# ---- Kursbezeichnung lesen ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class KursInfo:
    standort: str | None
    start: date | None
    genau: bool            # True = JJMMTT, False = JJMM (1. des Monats)


def kurs_info(name: str) -> KursInfo:
    """„GS EMR ASS 261109“ → (GS, 09.11.2026, genau) · „GS CNC 2001“ → (GS, 01.01.2020, Monat) · „GS JobTrain 20“ →
    kein Start (zweistellig, Bedeutung unklar) · Langnamen ohne Code → (None, None)."""
    teile = name.split()
    standort = teile[0] if teile and re.fullmatch(r"[A-Z]{2}", teile[0]) else None
    letzte = teile[-1] if len(teile) > 1 else ""
    if re.fullmatch(r"\d{6}", letzte):
        try:
            return KursInfo(standort, date(2000 + int(letzte[:2]), int(letzte[2:4]), int(letzte[4:])), True)
        except ValueError:
            return KursInfo(standort, None, False)
    if re.fullmatch(r"\d{4}", letzte):
        j, m = int(letzte[:2]), int(letzte[2:])
        if 1 <= m <= 12:
            return KursInfo(standort, date(2000 + j, m, 1), False)
    return KursInfo(standort, None, False)


def passt(muster: str, name: str) -> bool:
    """„re:…“ = regulärer Ausdruck; sonst Kürzel (ganzes Wort, Groß/klein egal) oder – ab 5 Zeichen – Teiltext."""
    m = (muster or "").strip()
    if not m:
        return False
    if m.lower().startswith("re:"):
        try:
            return re.search(m[3:], name) is not None
        except re.error:
            return False
    if any(t.lower() == m.lower() for t in name.split()):
        return True
    return len(m) >= 5 and m.lower() in name.lower()


def zuordnen(name: str, tabelle: list[dict]) -> dict | None:
    """Erster passender Eintrag der Tabelle (Reihenfolge zählt); Standort-Spalte schränkt ein, wenn gefüllt."""
    info = kurs_info(name)
    for e in tabelle:
        if e.get("standort") and info.standort and e["standort"] != info.standort:
            continue
        if passt(e.get("muster", ""), name):
            return e
    return None


def _ganz(x) -> int | None:
    try:
        return int(x) if x not in (None, "") and int(x) > 0 else None
    except (TypeError, ValueError):
        return None


def familie(kurs: str) -> str:
    """„GS ASS PS 260909“ → „GS ASS PS“ – Kurs ohne Start-/Nummernteil."""
    return " ".join(x for x in kurs.split() if not re.search(r"\d", x)) or kurs


# ---- Solldauer aus den Daten der Zimmerbelegung (0.77) -----------------------------------------------------

@dataclass
class Messung:
    familie: str
    n: int
    median: float
    p10: float
    p90: float
    quelle: str            # Anmeldung | Gebäudeplan


def anmeldedauern(eintraege) -> dict[str, Messung]:
    """``eintraege``: (Maßnahme, von, bis, Quelle) aus Anreiselisten (nur mit eingetragener Abreise) und Gebäudeplan.
    Je Kursfamilie die Dauer in Kalendertagen (von bis bis, beide Tage gezählt). Anmeldungen haben Vorrang; der
    Gebäudeplan zählt nur für Familien, die in den Anmeldungen seltener als 3-mal vorkommen."""
    roh: dict[tuple[str, str], list[int]] = {}
    for massnahme, von, bis, quelle in eintraege:
        if not massnahme or not von or not bis or bis < von:
            continue
        fam = familie(massnahme.upper().strip())
        roh.setdefault((fam, quelle), []).append((bis - von).days + 1)
    erg: dict[str, Messung] = {}
    for quelle in ("Gebäudeplan", "Anmeldung"):
        for (fam, q), werte in roh.items():
            if q != quelle or (quelle == "Anmeldung" and len(werte) < 3 and fam in erg):
                continue
            erg[fam] = Messung(fam, len(werte), stt.median(werte), _quantil(werte, .1), _quantil(werte, .9), quelle)
    return erg


def soll_tage(kurs: str, e: dict | None, gemessen: dict[str, Messung]) -> tuple[int | None, str]:
    """Solldauer eines Kurses und woher sie kommt."""
    if e is None:
        return None, ""
    if e.get("soll_quelle") == "anmeldung" and (m := gemessen.get(familie(kurs.upper()))) and m.n >= 3:
        return round(m.median), f"{m.quelle}, n = {m.n}"
    return e.get("soll_tage"), "Tabelle" if e.get("soll_tage") else ""


def tabelle_bereinigen(roh) -> list[dict]:
    erg = []
    for e in roh if isinstance(roh, list) else []:
        if not isinstance(e, dict) or not str(e.get("muster", "")).strip():
            continue
        try:
            soll = int(e["soll_tage"]) if e.get("soll_tage") not in (None, "") else None
        except (TypeError, ValueError):
            soll = None
        erg.append({"muster": str(e["muster"]).strip(), "art": str(e.get("art") or e["muster"]).strip(),
                    "gruppe": e.get("gruppe") if e.get("gruppe") in GRUPPEN else "Sonstige", "soll_tage": soll,
                    "standort": str(e.get("standort") or "").strip().upper(), "offen": str(e.get("offen") or "").strip(),
                    "soll_quelle": "anmeldung" if e.get("soll_quelle") == "anmeldung" else "",
                    "max_plaetze": _ganz(e.get("max_plaetze"))})
    return erg


# ---- Aufenthalte beim Einlesen sammeln --------------------------------------------------------------------

@dataclass
class Aufenthalt:
    person: int            # fortlaufende Nummer – kein Name
    kurs: str
    ein: date
    aus: date
    anwesend: int          # Tage mit 1
    wochenende: int        # davon Sa/So
    luecke: int            # größte Lücke in Tagen
    halbjahr: bool = False  # hat Werte in Spalten ohne Tagesdatum (nicht tagesgenau)

    @property
    def kalendertage(self) -> int:
        return (self.aus - self.ein).days + 1

    def als_liste(self) -> list:
        return [self.person, self.kurs, self.ein.isoformat(), self.aus.isoformat(), self.anwesend, self.wochenende,
                self.luecke, int(self.halbjahr)]

    @classmethod
    def aus_liste(cls, x: list) -> "Aufenthalt":
        return cls(int(x[0]), str(x[1]), date.fromisoformat(x[2]), date.fromisoformat(x[3]), int(x[4]), int(x[5]),
                   int(x[6]), bool(x[7]) if len(x) > 7 else False)


class Sammler:
    """Wird beim Einlesen Zeile für Zeile gefüttert: (Beschriftung, Tagesindizes mit Wert, Werte ohne Tagesdatum)."""

    def __init__(self, von: date, stichtag: date | None = None) -> None:
        self.von = von
        self.grenze = (stichtag - von).days if stichtag else None     # Tagesindex des Stichtags (Import-Tag)
        self.kuenftig_tage = 0
        self.kuenftig_personen: set[int] = set()
        self.person = 0
        self.aufenthalte: list[Aufenthalt] = []
        self.offen = None                       # Zeile ohne Kursmuster mit Werten – Entscheidung erst mit der nächsten
        self.teilsummen = 0                     # Personenzeilen mit Teilsumme
        self.langnamen = 0
        self.nur_halbjahr = 0                   # Kurszeilen ganz ohne Tageswerte, aber mit Halbjahreswerten
        self.ohne_person = 0

    def _kurs(self, text: str, tage: list[int], hj: bool) -> None:
        if not tage:
            if hj:
                self.nur_halbjahr += 1
            return
        if self.person == 0:
            self.ohne_person += 1
            self.person = 1
        if self.grenze is not None and tage[-1] > self.grenze:          # geplante künftige Tage im Pivot
            self.kuenftig_tage += sum(1 for k in tage if k > self.grenze)
            self.kuenftig_personen.add(self.person)
        luecke = max((b - a - 1 for a, b in zip(tage, tage[1:])), default=0)
        we = sum(1 for k in tage if (self.von + timedelta(days=k)).weekday() >= 5)
        self.aufenthalte.append(Aufenthalt(self.person, text, self.von + timedelta(days=tage[0]),
                                           self.von + timedelta(days=tage[-1]), len(tage), we, luecke, hj))

    def _offen_klaeren(self, naechste_ist_kurs: bool) -> None:
        if self.offen is None:
            return
        text, tage, hj = self.offen
        self.offen = None
        if naechste_ist_kurs:                   # Teilsumme einer Person – darunter folgen ihre Kurse
            self.person += 1
            self.teilsummen += 1
        else:                                   # alter Kurs mit Langnamen
            self.langnamen += 1
            self._kurs(text, tage, hj)

    def zeile(self, text: str, tage: list[int], hj: bool) -> None:
        kurs = bool(_KURS.match(text))
        self._offen_klaeren(kurs)
        if kurs:
            self._kurs(text, tage, hj)
        elif tage or hj:
            self.offen = (text, tage, hj)
        else:
            self.person += 1

    def ende(self) -> None:
        self._offen_klaeren(False)


# ---- Prüfbericht -----------------------------------------------------------------------------------------

@dataclass
class ArtZeile:
    art: str
    gruppe: str
    soll_tage: int | None
    offen: str
    n: int
    laufend: int
    median: float | None       # Kalendertage, nur abgeschlossene
    p10: float | None
    p90: float | None
    unterbrochen: int
    soll_text: str = ""            # z. B. „28 Tage (Anmeldung, n = 40)“ oder „28–42 Tage je Kurs“


@dataclass
class Bericht:
    personen: int
    kurse: int
    aufenthalte: int
    von: date | None
    bis: date | None
    letzter_ist: date
    tagesgenau_ab: date | None
    halbjahr_spalten: int
    halbjahr_aufenthalte: int
    teilsummen: int
    langnamen: int
    nicht_zugeordnet: list          # (Kurs, Personen, von, bis)
    ohne_start: list                # (Kurs, Personen)
    offene_regeln: list             # (Muster, Hinweis, Kurse)
    wochenende_anteil: float | None
    wochenende_basis: int
    anwesend_quote: float | None    # Anwesenheitstage ÷ Kalendertage, regulär beendete Hauptmaßnahmen
    anwesend_basis: int
    wochenende_text: str
    arten: list[ArtZeile]
    auffaellig: list                # (Text, Anzahl, Beispiele)
    kuenftig_spalten: int
    kuenftig_personentage: int
    kuenftig_personen: int
    hinweise: list = field(default_factory=list)
    gemessen: list = field(default_factory=list)      # Messung je Kursfamilie aus der Zimmerbelegung (genutzt)
    ignoriert: tuple = (0, 0)                         # (Kurse, Aufenthalte) der Gruppe „Ignoriert“


def _quantil(werte: list[float], q: float) -> float | None:
    if not werte:
        return None
    w = sorted(werte)
    pos = (len(w) - 1) * q
    a = int(pos)
    b = min(a + 1, len(w) - 1)
    return w[a] + (w[b] - w[a]) * (pos - a)


def bericht(aufenthalte: list[Aufenthalt], meta: dict, tabelle: list[dict], stichtag: date,
            gemessen: dict[str, Messung] | None = None) -> Bericht:
    """Prüfbericht Schritt 1 – noch keine Prognose. ``gemessen``: Solldauern aus der Zimmerbelegung je Kursfamilie."""
    gemessen = gemessen or {}
    letzter = min(stichtag, date.fromisoformat(meta["bis"])) if meta.get("bis") else stichtag
    kurse: dict[str, list[Aufenthalt]] = {}
    for x in aufenthalte:
        kurse.setdefault(x.kurs, []).append(x)
    zuordnung = {k: zuordnen(k, tabelle) for k in kurse}
    nicht = sorted(((k, len({x.person for x in xs}), min(x.ein for x in xs), max(x.aus for x in xs))
                    for k, xs in kurse.items() if zuordnung[k] is None), key=lambda t: -t[1])
    ohne_start = sorted(((k, len(xs)) for k, xs in kurse.items() if kurs_info(k).start is None), key=lambda t: -t[1])
    offene = []
    for e in tabelle:
        if e.get("offen"):
            n = sum(1 for k in kurse if zuordnung[k] is e)
            offene.append((e["muster"], e["offen"], n))

    def kursstart(k: str, xs: list[Aufenthalt]) -> date:
        return kurs_info(k).start or min(x.ein for x in xs)

    def laeuft(x: Aufenthalt) -> bool:
        return x.aus >= letzter - timedelta(days=LAUFEND_TAGE)

    # Dauern je Maßnahmeart
    je_art: dict[str, list[Aufenthalt]] = {}
    for k, xs in kurse.items():
        e = zuordnung[k]
        if e is not None and e["gruppe"] != "Ignoriert":
            je_art.setdefault(e["art"], []).extend(xs)
    eintrag = {e["art"]: e for e in tabelle}
    arten = []
    for art, xs in sorted(je_art.items(), key=lambda t: (GRUPPEN.index(eintrag[t[0]]["gruppe"]), t[0])):
        e = eintrag[art]
        fertig_ = [x.kalendertage for x in xs if not laeuft(x) and not x.halbjahr]
        sollen = {soll_tage(k, e, gemessen) for k in {x.kurs for x in xs}}
        werte = sorted({s for s, _q in sollen if s})
        quellen = sorted({q for s, q in sollen if s and q != "Tabelle"})
        if not werte:
            text = ""
        elif len(werte) == 1:
            text = f"{werte[0]} Tage" + (f" ({quellen[0]})" if len(quellen) == 1 else " (aus Anmeldung)" if quellen else "")
        else:
            text = f"{werte[0]}–{werte[-1]} Tage je Kurs" + (" (aus Anmeldung)" if quellen else "")
        arten.append(ArtZeile(art, e["gruppe"], werte[0] if len(werte) == 1 else None, e["offen"], len(xs),
                              sum(1 for x in xs if laeuft(x)), stt.median(fertig_) if fertig_ else None,
                              _quantil(fertig_, .1), _quantil(fertig_, .9), sum(1 for x in xs if x.luecke > LUECKE_TAGE), text))

    # Wochenend-Prüfung: Hauptmaßnahmen ab 4 Wochen (sonst alle ab 4 Wochen)
    def gruppe(x: Aufenthalt) -> str | None:
        e = zuordnung.get(x.kurs)
        return e["gruppe"] if e else None
    basis = [x for x in aufenthalte if gruppe(x) == "Hauptmaßnahme" and x.kalendertage >= 28 and not x.halbjahr] or \
        [x for x in aufenthalte if x.kalendertage >= 28 and not x.halbjahr]
    anw = sum(x.anwesend for x in basis)
    we_anteil = (sum(x.wochenende for x in basis) / anw) if anw else None
    regulaer = []
    for x in aufenthalte:
        e = zuordnung.get(x.kurs)
        soll, _q = soll_tage(x.kurs, e, gemessen)
        if e and e["gruppe"] == "Hauptmaßnahme" and soll and not laeuft(x) and not x.halbjahr:
            soll_ende = kursstart(x.kurs, kurse[x.kurs]) + timedelta(days=soll)
            if abs((x.aus - soll_ende).days) <= 30:
                regulaer.append(x.anwesend / x.kalendertage)
    quote = stt.median(regulaer) if regulaer else None
    if we_anteil is None:
        we_text = "Nicht prüfbar – keine Aufenthalte ab 4 Wochen."
    elif we_anteil >= .2:
        we_text = (f"Wochenenden werden mitgezählt ({we_anteil:.0%} der Anwesenheitstage sind Sa/So; bei 7 Tagen pro Woche "
                   "wären es 29 %).")
    elif we_anteil <= .05:
        we_text = f"Wochenenden werden nicht gezählt ({we_anteil:.0%} der Anwesenheitstage sind Sa/So)."
    else:
        we_text = f"Uneinheitlich: {we_anteil:.0%} der Anwesenheitstage sind Sa/So – teils gezählt, teils nicht."
    we_text += " Dauern werden deshalb immer aus Kalendertagen gerechnet."

    # Auffällige Fälle
    auff = []
    for gr, grenze in AUFFAELLIG.items():
        faelle = [x for x in aufenthalte if gruppe(x) == gr and x.kalendertage > grenze]
        auff.append((f"{gr} länger als {round(grenze / 30.44)} Monate", len(faelle),
                     [f"Nr. {x.person} · {x.kurs} · {x.kalendertage} Tage" for x in sorted(faelle, key=lambda x: -x.kalendertage)[:8]]))
    unterbr = [x for x in aufenthalte if x.luecke > LUECKE_TAGE]
    auff.append((f"Unterbrechung länger als {LUECKE_TAGE} Tage (bleibt ein Aufenthalt mit Lücke)", len(unterbr),
                 [f"Nr. {x.person} · {x.kurs} · Lücke {x.luecke} Tage" for x in sorted(unterbr, key=lambda x: -x.luecke)[:8]]))
    frueh = [x for x in aufenthalte if kurs_info(x.kurs).start and x.ein < kurs_info(x.kurs).start - timedelta(days=31)]
    auff.append(("Eintritt mehr als einen Monat vor dem Kursstart laut Kursname", len(frueh),
                 [f"Nr. {x.person} · {x.kurs} · Eintritt {x.ein:%d.%m.%Y}" for x in frueh[:8]]))

    hinweise = []
    if meta.get("ohne_person"):
        hinweise.append("Kurszeilen vor der ersten Personenzeile – Zuordnung zu Personen unsicher.")
    if meta.get("teilsummen"):
        hinweise.append(f"{meta['teilsummen']} Personenzeilen tragen Teilsummen – als Personen erkannt.")
    return Bericht(
        personen=len({x.person for x in aufenthalte}), kurse=len(kurse), aufenthalte=len(aufenthalte),
        von=min((x.ein for x in aufenthalte), default=None), bis=max((x.aus for x in aufenthalte), default=None),
        letzter_ist=letzter, tagesgenau_ab=date.fromisoformat(meta["von"]) if meta.get("von") else None,
        halbjahr_spalten=int(meta.get("halbjahr_spalten", 0)), halbjahr_aufenthalte=sum(1 for x in aufenthalte if x.halbjahr),
        teilsummen=int(meta.get("teilsummen", 0)), langnamen=int(meta.get("langnamen", 0)), nicht_zugeordnet=nicht,
        ohne_start=ohne_start, offene_regeln=offene, wochenende_anteil=we_anteil, wochenende_basis=len(basis),
        anwesend_quote=quote, anwesend_basis=len(regulaer), wochenende_text=we_text, arten=arten, auffaellig=auff,
        kuenftig_spalten=int(meta.get("kuenftig_spalten", 0)), kuenftig_personentage=int(meta.get("kuenftig_tage", 0)),
        kuenftig_personen=int(meta.get("kuenftig_personen", 0)), hinweise=hinweise,
        gemessen=sorted((m for f, m in gemessen.items() if any(familie(k.upper()) == f for k in kurse)
                         or zuordnen(f, tabelle) is not None), key=lambda m: m.familie),
        ignoriert=(sum(1 for k in kurse if zuordnung[k] and zuordnung[k]["gruppe"] == "Ignoriert"),
                   sum(len(xs) for k, xs in kurse.items() if zuordnung[k] and zuordnung[k]["gruppe"] == "Ignoriert")))



# ---- Speichern (in der Maßnahmen-Datei) -------------------------------------------------------------------

def laden(roh: dict | None = None) -> tuple[list[Aufenthalt], dict]:
    from . import massnahmen_kern as mk

    b = (roh if roh is not None else mk._roh()).get("bestand") or {}
    return [Aufenthalt.aus_liste(x) for x in b.get("aufenthalte") or []], dict(b.get("meta") or {})


def tabelle(roh: dict | None = None) -> list[dict]:
    from . import massnahmen_kern as mk

    eigen = (roh if roh is not None else mk._roh()).get("zuordnung_arten")
    return tabelle_bereinigen(eigen if eigen is not None else ZUORDNUNG_STANDARD)


def tabelle_schritt(neu: list[dict] | None) -> str:
    """Zuordnungstabelle speichern (None = Startwerte) – mit Rückgängig."""
    from . import massnahmen_kern as mk
    from .kern import _schritt

    def tun():
        roh = mk._roh()
        if neu is None:
            roh.pop("zuordnung_arten", None)
        else:
            roh["zuordnung_arten"] = tabelle_bereinigen(neu)
        mk._schreiben(roh)
    _schritt("Maßnahmearten zugeordnet", tun, [mk.DATEI])
    return "Zuordnung gespeichert" if neu is not None else "Zuordnung auf Startwerte zurückgesetzt"
