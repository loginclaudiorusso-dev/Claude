"""Flurweise Renovierung: Welche Etage als Nächstes – wann – was kostet es – wohin mit den Bewohnern?
(Steuerung → Renovierung; seit 0.41 nicht mehr unter Zimmer.)

Ein Flur ist hier die ganze Etage (Haus 2 und Haus 6 – Ost und West lassen sich baulich nicht trennen).

Nur Planung: Hier wird nichts gesperrt, niemand umgezogen und keine Buchung verschoben. Gespeichert werden nur die
Planungsannahmen und – nach Bestätigung – vorgemerkte Renovierungen in einer eigenen Datei
(``importe/modern_renovierung.json``, liegt nur im Datenordner, nie im Programm). Bewertet werden vorhandene Daten:

* **Bedarf** (Zustand) – Jahre seit der letzten Renovierung (wo bekannt), Mängel „Renovierung nötig“, offene Mängel nach
  Stufe (schwächer gewichtet: sie messen auch, wie schnell repariert wird). Fehlt ein Renovierungsdatum, steht es als
  **Lücke** da, nicht geschätzt.
* **Machbarkeit** (je Monat) – wer im Bauzeitraum im Flur wohnt (Umzug) oder anreist (umleiten), ab wann ein
  Belegungsstopp nötig ist und ob für **jede** betroffene Person ein passendes freies Zimmer in **allen** Häusern da ist
  (Gruppe, „nur Männer“, Gäste-/EMR-/Doppelzimmer – wie beim Zuteilen). Nur bekannte Buchungen.
* **Kosten** – aus den Angeboten bzw. Annahmen je Haus: Bau (Maler/Boden) je Etage, Möbel und Aufbau je Zimmer,
  Nebenkosten und Puffer in %, Preissteigerung je Jahr, nicht abziehbare Umsatzsteuer über die Vorsteuerquote.
  Möbel/Aufbau (Investition) und Bau (Instandhaltung) werden getrennt ausgewiesen.
* **Ziel** – „Zimmer je Jahr“ statt Budget; daraus folgen Etagen (ganze Etagen, zwei Rundungsvorschläge), Kosten und der
  Renovierungszyklus („jedes Zimmer etwa alle N Jahre“).

Rein, ohne NiceGUI.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import speicher
from belegung import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/modern_renovierung.json"
MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
UST = 0.19

# Planungsannahmen – alle in der Oberfläche änderbar. Keine Angebotswerte im Programm: Die echten Preise kommen über
# „Angebot einlesen“ bzw. die Eingabe und liegen nur im Datenordner.
STANDARD = {
    "haeuser": ["2", "6"],
    "kosten": {"2": {"bau_etage": 100000, "moebel_zimmer": 0, "aufbau_zimmer": 500, "dauer_tage": 30},
               "6": {"bau_etage": 30000, "moebel_zimmer": 0, "aufbau_zimmer": 500, "dauer_tage": 30}},
    "modus": "ziel",              # ziel = nach Zimmerziel | budget = nach verfügbarem Budget
    "ziel_zimmer": 9,             # Zimmer je Jahr
    "budget_bau": None,           # Budget je Jahr für Bau + Nebenkosten (Instandhaltung) – None = nicht angegeben
    "budget_moebel": None,        # Budget je Jahr für Möbel + Aufbau – eigene Kostenstelle, None = nicht angegeben
    "neben_pct": 0,               # Elektro, Sanitär, Brandschutz, Entsorgung, Bauleitung – in % vom Bau
    "puffer_pct": 10,             # Unvorhergesehenes, in % von allem
    "vorsteuer_pct": 0,           # 0 = Umsatzsteuer ist voll Kosten (brutto), 100 = voll abziehbar (netto)
    "preis_pct": 3,               # Preissteigerung je Jahr ab Preisstand
    "preisstand": 0,              # Jahr der Preise (0 = laufendes Jahr)
    "vorlauf_tage": 56,           # Belegungsstopp vor Baubeginn
    "gesperrt": [],               # Monate (1–12), in denen nicht renoviert werden soll
    "angebote": [],               # eingelesene Angebote: {haus, art (bau|moebel), netto, zimmer, datum, datei}
}
KURZ_GRUPPEN = ("EMR", "ASS", "UWT", "Gast")
KURZ_TAGE = 56
FRISCH_JAHRE = 5                  # in den letzten 5 Jahren renoviert → senkt den Bedarf
ALT_JAHRE = 15                    # älter als 15 Jahre → Bedarf
ALT_TAGE = 90                     # Mangel seit mehr als 90 Tagen offen → +0,5


# ---- Ablage -------------------------------------------------------------------------------

def _roh() -> dict:
    return speicher.lesen(DATEI, {})


def parameter() -> dict:
    roh = _roh().get("parameter") or {}
    p = {**STANDARD, **roh}
    kosten = {}
    for h in p["haeuser"]:
        alt = (roh.get("kosten") or {}).get(h) or {}
        if "bau_etage" not in alt:                 # Annahmen von 0.39/0.40 (Flur-Pauschale + je Zimmer) nicht übernehmen
            alt = {}
        kosten[h] = {**STANDARD["kosten"].get(h, {"bau_etage": 0, "moebel_zimmer": 0, "aufbau_zimmer": 0, "dauer_tage": 30}),
                     **alt}
    p["kosten"] = kosten
    if not p.get("preisstand"):
        p["preisstand"] = date.today().year
    return p


def parameter_speichern(p: dict) -> str:
    roh = _roh()
    roh["parameter"] = {k: p[k] for k in STANDARD if k in p}
    speicher.schreiben(DATEI, roh)
    return "Planungsannahmen gespeichert"


# ---- Kosten -------------------------------------------------------------------------------------

@dataclass
class Kosten:
    zimmer: int
    jahr: int
    bau: float = 0.0              # Maler/Boden je Etage (netto, mit Preissteigerung)
    neben: float = 0.0            # Nebenkosten (netto)
    moebel: float = 0.0           # Möbel (netto)
    aufbau: float = 0.0           # Aufbau (netto)
    puffer: float = 0.0           # Puffer (netto)
    ust: float = 0.0              # nicht abziehbare Umsatzsteuer
    luecken: list = field(default_factory=list)

    @property
    def netto(self) -> float:
        return self.bau + self.neben + self.moebel + self.aufbau + self.puffer

    @property
    def summe(self) -> float:
        """Was es das Haus kostet: netto + nicht abziehbare Umsatzsteuer."""
        return self.netto + self.ust

    def _anteil(self, teil: float) -> float:
        basis = self.bau + self.neben + self.moebel + self.aufbau
        return self.summe * teil / basis if basis else 0.0

    @property
    def instandhaltung(self) -> float:
        """Bau + Nebenkosten (anteilig Puffer und Steuer) – Aufwand."""
        return self._anteil(self.bau + self.neben)

    @property
    def investition(self) -> float:
        """Möbel + Aufbau (anteilig Puffer und Steuer) – ob aktiviert wird, entscheidet die Buchhaltung."""
        return self._anteil(self.moebel + self.aufbau)

    @property
    def je_zimmer(self) -> float:
        return self.summe / self.zimmer if self.zimmer else 0.0

    def plus(self, o: "Kosten") -> "Kosten":
        return Kosten(self.zimmer + o.zimmer, max(self.jahr, o.jahr), self.bau + o.bau, self.neben + o.neben,
                      self.moebel + o.moebel, self.aufbau + o.aufbau, self.puffer + o.puffer, self.ust + o.ust,
                      sorted(set(self.luecken) | set(o.luecken)))


def preisfaktor(p: dict, jahr: int) -> float:
    return (1 + float(p.get("preis_pct") or 0) / 100) ** max(0, jahr - int(p.get("preisstand") or jahr))


def kosten(p: dict, haus: str, zimmer: int, jahr: int | None = None) -> Kosten:
    """Kosten einer Etage mit ``zimmer`` Zimmern im Jahr ``jahr`` (Preisstand + Steigerung)."""
    jahr = jahr or int(p.get("preisstand") or date.today().year)
    k = p["kosten"].get(haus) or {}
    f = preisfaktor(p, jahr)
    erg = Kosten(zimmer, jahr, float(k.get("bau_etage") or 0) * f)
    erg.neben = erg.bau * float(p.get("neben_pct") or 0) / 100
    erg.moebel = float(k.get("moebel_zimmer") or 0) * zimmer * f
    erg.aufbau = float(k.get("aufbau_zimmer") or 0) * zimmer * f
    erg.puffer = (erg.bau + erg.neben + erg.moebel + erg.aufbau) * float(p.get("puffer_pct") or 0) / 100
    erg.ust = (erg.bau + erg.neben + erg.moebel + erg.aufbau + erg.puffer) * UST * (1 - float(p.get("vorsteuer_pct") or 0) / 100)
    if not k.get("bau_etage"):
        erg.luecken.append(f"Haus {haus}: Baukosten je Etage fehlen")
    if not k.get("moebel_zimmer"):
        erg.luecken.append(f"Haus {haus}: Möbelpreis je Zimmer fehlt")
    return erg


def euro(x: float) -> str:
    return f"{x:,.0f} €".replace(",", ".")


# ---- Angebot einlesen ------------------------------------------------------------------------------

_SUMME = re.compile(r"(?:Nettosumme|Summe\s+netto|Netto(?:betrag|summe)?|Warenwert\s+o\.?\s*MwSt\.?|Zwischensumme)"
                    r"[^\d\n]{0,30}?(\d{1,3}(?:\.\d{3})*,\d{2})", re.I)
_BRUTTO = re.compile(r"(?:Bruttosumme|Gesamtbetrag|Summe\s+brutto)[^\d\n]{0,30}?(\d{1,3}(?:\.\d{3})*,\d{2})", re.I)
_STUECK = re.compile(r"^\s*(\d{1,3})\s+St(?:ü|ue|u)?ck\b", re.I | re.M)
_HAUS = re.compile(r"(?:Geb(?:ä|ae)ude|Haus)\s*(\d+(?:\.\d)?)", re.I)


def _zahl(t: str) -> float:
    return float(t.replace(".", "").replace(",", "."))


def angebot_auswerten(text: str) -> dict:
    """Aus dem Text eines Angebots: Nettosumme, Art (Bau oder Möbel), Haus, bei Möbeln die Zimmerzahl (häufigste
    Stückzahl). Nur Vorschlag – die Oberfläche zeigt es vor dem Speichern zur Bestätigung."""
    netto = [_zahl(m) for m in _SUMME.findall(text)]
    brutto = [_zahl(m) for m in _BRUTTO.findall(text)]
    if not netto and brutto:
        netto = [round(brutto[-1] / (1 + UST), 2)]
    moebel = bool(re.search(r"Warenwert|Bettgestell|Matratze|Schreibtisch|Kleiderschrank|Möbel", text, re.I))
    stueck = [int(x) for x in _STUECK.findall(text)]
    zimmer = max(set(stueck), key=stueck.count) if stueck else 0
    haus = _HAUS.search(text)
    return {"netto": netto[-1] if netto else 0.0, "art": "moebel" if moebel else "bau",
            "haus": haus.group(1) if haus else "", "zimmer": zimmer if moebel else 0}


def angebot_lesen(pfad) -> dict:
    from .pdf_anreise_kern import text_lesen

    return angebot_auswerten(text_lesen(pfad))


def angebot_uebernehmen(p: dict, ang: dict) -> dict:
    """Ein bestätigtes Angebot in die Annahmen übernehmen (Bau je Etage bzw. Möbel je Zimmer)."""
    neu = {**p, "kosten": {h: dict(v) for h, v in p["kosten"].items()}, "angebote": list(p.get("angebote") or [])}
    h = str(ang.get("haus") or "")
    if h not in neu["kosten"]:
        raise ValueError(f"Haus „{h}“ wird nicht geplant (Häuser: {', '.join(neu['haeuser'])}).")
    if ang["art"] == "moebel":
        n = int(ang.get("zimmer") or 0)
        if n <= 0:
            raise ValueError("Für ein Möbel-Angebot bitte angeben, für wie viele Zimmer es gilt.")
        neu["kosten"][h]["moebel_zimmer"] = round(float(ang["netto"]) / n, 2)
    else:
        neu["kosten"][h]["bau_etage"] = round(float(ang["netto"]), 2)
    neu["angebote"] = [x for x in neu["angebote"] if not (x.get("haus") == h and x.get("art") == ang["art"])]
    neu["angebote"].append({k: ang.get(k) for k in ("haus", "art", "netto", "zimmer", "datum", "datei")})
    if ang.get("datum"):
        neu["preisstand"] = int(str(ang["datum"])[:4])
    return neu


def plan() -> list[dict]:
    """Vorgemerkte Renovierungen: {flur: "2|3|Ost", start: ISO, ende: ISO, notiz}. Unverbindlich."""
    return list(_roh().get("plan") or [])


def vormerken(flur: str, start: date, ende: date, notiz: str = "") -> str:
    roh = _roh()
    eintraege = [e for e in roh.get("plan") or [] if not (e["flur"] == flur and e["start"][:4] == str(start.year))]
    eintraege.append({"flur": flur, "start": start.isoformat(), "ende": ende.isoformat(), "notiz": notiz})
    roh["plan"] = sorted(eintraege, key=lambda e: (e["start"], e["flur"]))
    speicher.schreiben(DATEI, roh)
    return f"{flur_text_schluessel(flur)} vorgemerkt: {start:%d.%m.} – {ende:%d.%m.%Y} (unverbindlich)"


def entfernen(flur: str, start: str) -> str:
    roh = _roh()
    roh["plan"] = [e for e in roh.get("plan") or [] if not (e["flur"] == flur and e["start"] == start)]
    speicher.schreiben(DATEI, roh)
    return f"{flur_text_schluessel(flur)}: Vormerkung entfernt"


# ---- Flure und Bedarf -----------------------------------------------------------------------

def schluessel(haus: str, etage: str, flur: str) -> str:
    return f"{haus}|{etage}|{flur}"


def flur_text_schluessel(k: str) -> str:
    haus, etage, flur = (k.split("|") + ["", "", ""])[:3]
    return f"Haus {haus} · {zp.etage_text(etage)}" + (f" {flur}" if flur else "")


@dataclass
class Flur:
    schluessel: str
    haus: str
    etage: str
    flur: str
    zimmer: list = field(default_factory=list)     # zp.Zimmer
    bedarf: float = 0.0                            # Punkte je Zimmer (vergleichbar zwischen großen und kleinen Fluren)
    gruende: list = field(default_factory=list)    # (Punkte, Text) – nachvollziehbar
    luecken: list = field(default_factory=list)    # fehlende Daten
    reno_bekannt: int = 0                          # Zimmer mit Renovierungsvermerk
    alter: float | None = None                     # Ø Jahre seit Renovierung (nur bekannte)
    sonder: list = field(default_factory=list)     # z. B. „EMR-Zimmer (10)“
    kosten: Kosten | None = None

    @property
    def text(self) -> str:
        return flur_text_schluessel(self.schluessel)

    @property
    def betten(self) -> int:
        return sum(z.betten for z in self.zimmer)

    @property
    def ampel(self) -> str:
        return "krit" if self.bedarf >= 10 else "warn" if self.bedarf >= 4 else "ok"


def flure(stand: zp.Planstand, heute: date | None = None, p: dict | None = None) -> list[Flur]:
    """Alle Flure der gewählten Häuser mit nachvollziehbarem Bedarf – höchster Bedarf zuerst."""
    from belegung import maengel as mg
    from belegung import zimmerliste as zl

    heute = heute or date.today()
    p = p or parameter()
    offen = mg.offen_je_zimmer()
    je: dict[str, Flur] = {}
    for z in stand.zimmer:
        if not z.aktiv or z.haus not in p["haeuser"]:
            continue
        k = schluessel(z.haus, z.etage, "")            # ein Flur = die ganze Etage (Ost/West gehören baulich zusammen)
        je.setdefault(k, Flur(k, z.haus, z.etage, "")).zimmer.append(z)
    for f in je.values():
        n = len(f.zimmer)
        punkte: dict[str, float] = {}
        texte: dict[str, int] = {}
        frisch, alt, ohne_datum, unbew, jahre = 0, 0, 0, 0, []
        for z in f.zimmer:
            for m in offen.get(z.id, []):
                if m.art == "renovierung":
                    punkte["reno"] = punkte.get("reno", 0) + 4
                    texte["reno"] = texte.get("reno", 0) + 1
                else:                                  # 0.41: schwächer – Mängel messen auch das Reparaturtempo
                    punkte[f"s{m.stufe}"] = punkte.get(f"s{m.stufe}", 0) + m.stufe / 2
                    texte[f"s{m.stufe}"] = texte.get(f"s{m.stufe}", 0) + 1
                if (heute - m.seit).days > ALT_TAGE:
                    punkte["lang"] = punkte.get("lang", 0) + .5
                    texte["lang"] = texte.get("lang", 0) + 1
            if z.id in stand.lage.unbewohnbar:
                unbew += 1
            if z.renoviert:
                f.reno_bekannt += 1
                d = zl.reno_datum(z)
                if d is None:
                    ohne_datum += 1
                    continue
                j = (heute - d).days / 365.25
                jahre.append(j)
                if j < FRISCH_JAHRE:
                    frisch += 1
                elif j >= ALT_JAHRE:
                    alt += 1
        if frisch:
            punkte["frisch"] = -3 * frisch
        if alt:
            punkte["alt"] = 2 * alt
        namen = {"reno": "Mangel „Renovierung nötig“ (je 4 P.)", "alt": f"Zimmer seit über {ALT_JAHRE} Jahren nicht renoviert (je 2 P.)",
                 "s3": "Mängel, die unbewohnbar machen (je 1,5 P.)", "s2": "dringende Mängel (je 1 P.)",
                 "s1": "leichte Mängel (je 0,5 P.)", "lang": f"davon länger als {ALT_TAGE} Tage offen (je +0,5 P.)"}
        f.gruende = [(punkte[k], f"{texte.get(k, alt if k == 'alt' else 0)} {namen[k]}") for k in ("reno", "alt", "s3", "s2", "s1", "lang")
                     if k in punkte]
        if frisch:
            f.gruende.append((punkte["frisch"], f"{frisch} Zimmer in den letzten {FRISCH_JAHRE} Jahren renoviert (je −3 P.)"))
        if unbew:
            f.gruende.append((0, f"{unbew} Zimmer derzeit unbewohnbar"))
        f.bedarf = round(10 * sum(punkte.values()) / n, 1) if n else 0.0
        f.alter = round(sum(jahre) / len(jahre), 1) if jahre else None
        if f.reno_bekannt < n:
            f.luecken.append(f"{n - f.reno_bekannt} von {n} Zimmern ohne Renovierungsvermerk – unbekannt, nicht „nie“")
        if ohne_datum:
            f.luecken.append(f"{ohne_datum} Zimmer „renoviert“ ohne Datum")
        emr = sum(1 for z in f.zimmer if zp.nur_emr(z))
        if emr:
            f.sonder.append(f"{emr} reine EMR-Zimmer")
        if any(zp.nur_kurz(z) for z in f.zimmer):
            f.sonder.append("Etage für Kurzmaßnahmen/Allergiker")
        if g := sum(1 for z in f.zimmer if z.gaeste):
            f.sonder.append(f"{g} Gästezimmer")
        if nm := sum(1 for z in f.zimmer if z.nur_maenner):
            f.sonder.append(f"{nm} „nur Männer“ (Bad über den Flur)")
        if dz := sum(1 for z in f.zimmer if z.betten > 1):
            f.sonder.append(f"{dz} Doppelzimmer")
        f.kosten = kosten(p, f.haus, n)
    return sorted(je.values(), key=lambda f: (-f.bedarf, f.haus, zp._etage_sort(f.etage), f.flur))


# ---- Machbarkeit je Zeitfenster ---------------------------------------------------------------

@dataclass
class Fenster:
    start: date
    ende: date
    stopp_ab: date                                  # ab hier keine Neubelegung mehr (Vorlauf)
    umzug: list = field(default_factory=list)       # (Name, Zimmer kurz, bis, Gruppe) – wohnt im Bauzeitraum
    umleiten: list = field(default_factory=list)    # (Name, Zimmer kurz, Anreise, Gruppe) – reist im Bauzeitraum an
    nach_stopp: list = field(default_factory=list)  # zwischen Stopp und Start neu – sollte dann woanders hin
    mieter: int = 0
    frei_im_haus: int = 0                           # Zimmer im selben Haus (außerhalb des Flurs) im ganzen Zeitraum frei
    frei_gesamt: int = 0                            # passende Zimmer in allen Häusern im ganzen Zeitraum frei
    ohne_ausweich: list = field(default_factory=list)   # (Name, Gruppe, Grund) – kein passendes freies Zimmer
    ausweich: dict = field(default_factory=dict)    # Haus → Anzahl der Ausweichzimmer
    gesperrt: bool = False
    prognose: tuple | None = None                   # (erwartet, lo80, hi80) Standort – nur Orientierung
    engpass: bool = False                           # obere Prognose erreicht die Warnschwelle der (verringerten) Kapazität
    gleichwertig: bool = False                      # Unterschied zu anderen Monaten kleiner als die Unsicherheit

    @property
    def betroffen(self) -> int:
        return len(self.umzug) + len(self.umleiten)

    @property
    def stufe(self) -> str:
        if self.gesperrt:
            return "gesperrt"
        if not self.betroffen:
            return "frei"
        return "eng" if self.ohne_ausweich else "ok"


def _gruppe(b) -> str:
    return zp.belegung_gruppe(b) or ""


def _geschlecht(b) -> str:
    return (b.grund if b.person else "") or zp.geschlecht_raten(b.name)


def _ausweichen(stand: zp.Planstand, fe: Fenster, personen: list, ohne: set[str]) -> None:
    """Für jede betroffene Person ein passendes, im ganzen Bauzeitraum freies Zimmer außerhalb der Baustelle(n) –
    wie beim Zuteilen: Gruppe erlaubt, „nur Männer“, Gäste-/EMR-/Doppelzimmer. Engste Personen zuerst."""
    frei = [z for z in stand.zimmer if z.aktiv and z.id not in ohne and z.id not in stand.lage.unbewohnbar
            and stand.lage.freie_betten(z.id, fe.start, fe.ende) > 0]
    fe.frei_gesamt = len(frei)

    def passend(gruppe: str, g: str):
        return [z for z in frei if zp.erlaubt(z, gruppe or "Reha") and (not z.nur_maenner or g == "m")]
    vergeben: set[str] = set()
    for name, gruppe, g in sorted(personen, key=lambda x: len(passend(x[1], x[2]))):
        z = next((z for z in passend(gruppe, g) if z.id not in vergeben), None)
        if z is None:
            grund = "kein passendes Zimmer frei" + (" (nur Frauen-taugliche fehlen)" if g == "w" else "")
            fe.ohne_ausweich.append((name, gruppe or "–", grund))
            continue
        vergeben.add(z.id)
        fe.ausweich[z.haus] = fe.ausweich.get(z.haus, 0) + 1


def fenster(stand: zp.Planstand, f: Flur, start: date, p: dict | None = None, ohne: set[str] | None = None) -> Fenster:
    """``ohne`` = Zimmer, die gleichzeitig anderweitig gesperrt sind (weitere Baustellen) – zählen nicht als Ausweich."""
    p = p or parameter()
    dauer = int((p["kosten"].get(f.haus) or {}).get("dauer_tage") or p.get("dauer_tage") or 30)
    ende = start + timedelta(days=dauer - 1)
    fe = Fenster(start, ende, start - timedelta(days=int(p["vorlauf_tage"])), gesperrt=start.month in (p.get("gesperrt") or []))
    ids = {z.id for z in f.zimmer}
    personen = []
    for z in f.zimmer:
        for b in stand.lage.belegungen.get(z.id, []):
            if b.art not in ("belegt", "geplant") or not b.name or b.name == zp.PIVOT_NAME:
                continue
            if b.bis < start or b.von > ende:
                if fe.stopp_ab <= b.von < start:
                    fe.nach_stopp.append((zp.anzeige_name(b.name), z.kurz, b.von, _gruppe(b)))
                continue
            g = _gruppe(b)
            if g == "Mieter":
                fe.mieter += 1
            if b.von < start:
                fe.umzug.append((zp.anzeige_name(b.name), z.kurz, b.bis, g))
            else:
                fe.umleiten.append((zp.anzeige_name(b.name), z.kurz, b.von, g))
            personen.append((zp.anzeige_name(b.name), g, _geschlecht(b)))
    fe.frei_im_haus = sum(1 for z in stand.zimmer if z.aktiv and z.haus == f.haus and z.id not in ids
                          and z.id not in stand.lage.unbewohnbar and stand.lage.freie_betten(z.id, start, ende) > 0)
    _ausweichen(stand, fe, personen, ids | (ohne or set()))
    return fe


def monatsfenster(stand: zp.Planstand, f: Flur, jahr: int, p: dict | None = None,
                  prognose: dict | None = None) -> list[Fenster]:
    """Je Monat des Jahres ein Bauzeitraum ab dem Monatsersten. ``prognose``: {(Jahr, Monat): (erwartet, lo80, hi80)} –
    nur zur Orientierung, wo Buchungen noch nichts sagen."""
    p = p or parameter()
    fs = [fenster(stand, f, date(jahr, m, 1), p) for m in range(1, 13)]
    if prognose:
        for fe in fs:
            fe.prognose = prognose.get((jahr, fe.start.month))
    return fs


def bester_monat(fs: list[Fenster], heute: date) -> Fenster | None:
    """Erst die Machbarkeit (Ausweich für alle, wenig Betroffene, wenig Mieter). Sind mehrere Monate nach Buchungen
    gleich gut, entscheidet die Prognose – aber nur, wenn ihr Abstand größer ist als die halbe 80-%-Spanne; sonst
    heißen die Monate „gleichwertig“ und es gilt der früheste."""
    moeglich = [x for x in fs if not x.gesperrt and x.stopp_ab >= heute]
    if not moeglich:
        return None
    rang = lambda x: (bool(x.ohne_ausweich), x.engpass, x.betroffen, x.mieter)
    top = [x for x in moeglich if rang(x) == min(rang(y) for y in moeglich)]
    mit = [x for x in top if x.prognose]
    if len(mit) >= 2:
        best = min(mit, key=lambda x: x.prognose[0])
        rest = sorted(x.prognose[0] for x in mit if x is not best)
        mitte = rest[len(rest) // 2]
        spanne = (best.prognose[2] - best.prognose[1]) / 2
        if mitte - best.prognose[0] > spanne:
            return best
        for x in top:
            x.gleichwertig = True
    elif len(top) > 1:
        for x in top:
            x.gleichwertig = True
    return min(top, key=lambda x: x.start)


# ---- Ziel, Vorschläge, Szenarien -------------------------------------------------------------------

@dataclass
class Auswahl:
    titel: str
    flure: list
    zimmer: int
    kosten: Kosten

    @property
    def text(self) -> str:
        return ", ".join(f.text for f in self.flure)


def _auswahl(titel: str, fl: list[Flur], p: dict, jahr: int) -> Auswahl:
    k = Kosten(0, jahr)
    for f in fl:
        k = k.plus(kosten(p, f.haus, len(f.zimmer), jahr))
    return Auswahl(titel, fl, sum(len(f.zimmer) for f in fl), k)


def ziel_auswahl(fl: list[Flur], p: dict, jahr: int, ziel: int | None = None) -> list[Auswahl]:
    """Ganze Etagen nach Bedarf, bis das Zimmerziel erreicht ist. Zwei Vorschläge, wenn das Ziel nicht aufgeht:
    knapp darunter und knapp darüber – jeweils mit Kosten."""
    ziel = int(ziel if ziel is not None else p.get("ziel_zimmer") or 0)
    if ziel <= 0 or not fl:
        return []
    gew, n = [], 0
    for f in fl:
        if n >= ziel:
            break
        gew.append(f)
        n += len(f.zimmer)
    erg = []
    if n > ziel and len(gew) > 1:
        unter = gew[:-1]
        erg.append(_auswahl(f"{sum(len(f.zimmer) for f in unter)} Zimmer (knapp unter dem Ziel)", unter, p, jahr))
    erg.append(_auswahl(f"{n} Zimmer" + (" (Ziel genau)" if n == ziel else " (knapp über dem Ziel)" if n > ziel else
                                         " (alle geplanten Etagen)"), gew, p, jahr))
    return erg


def bestand(fl: list[Flur]) -> int:
    return sum(len(f.zimmer) for f in fl)


def zyklus(fl: list[Flur], zimmer_je_jahr: float) -> float | None:
    """Jedes Zimmer etwa alle N Jahre (Bestand der geplanten Häuser ÷ Zimmer je Jahr)."""
    return round(bestand(fl) / zimmer_je_jahr, 1) if zimmer_je_jahr > 0 else None


@dataclass
class Szenario:
    titel: str
    etagen: int
    zimmer: int
    kosten: Kosten
    sperr_zimmermonate: float
    jahre_bis_durch: int
    zyklus: float | None


def szenarien(fl: list[Flur], p: dict, jahr: int, etagen=(1, 2, 3)) -> list[Szenario]:
    """Vergleich: n Etagen je Jahr (nach Bedarf) – Kosten je Jahr, Zimmer, Sperr-Zimmermonate, Jahre bis alle
    Etagen einmal dran waren, Zyklus."""
    erg = []
    for n in etagen:
        gew = fl[:n]
        if not gew:
            continue
        aw = _auswahl("", gew, p, jahr)
        sperr = sum(len(f.zimmer) * int((p["kosten"].get(f.haus) or {}).get("dauer_tage") or 30) / 30 for f in gew)
        titel = {1: "Konservativ", 2: "Normal", 3: "Beschleunigt"}.get(n, f"{n} Etagen")
        erg.append(Szenario(f"{titel}: {n} Etage{'n' if n > 1 else ''} je Jahr", n, aw.zimmer, aw.kosten, round(sperr, 1),
                            math.ceil(len(fl) / n), zyklus(fl, aw.zimmer)))
    return erg


def budget_auswahl(fl: list[Flur], p: dict, jahr: int, budget_bau: float | None = None,
                   budget_moebel: float | None = None) -> Auswahl | None:
    """Welche Etagen passen in die beiden Budgets (Bau und Möbel getrennt)? Gesucht wird die Kombination mit dem
    meisten Bedarf (Punkte × Zimmer), bei Gleichstand mit den meisten Zimmern, dann die günstigere. ``None`` als
    Budget = keine Grenze. Ergebnis ``None``, wenn keine Etage hineinpasst."""
    bb = p.get("budget_bau") if budget_bau is None else budget_bau
    bm = p.get("budget_moebel") if budget_moebel is None else budget_moebel
    kand = [(f, kosten(p, f.haus, len(f.zimmer), jahr)) for f in fl][:16]          # 2^16 Kombinationen – schnell genug
    bau = [k.instandhaltung for _f, k in kand]
    mob = [k.investition for _f, k in kand]
    punkte = [max(0.0, f.bedarf) * len(f.zimmer) for f, _k in kand]
    zimmer = [len(f.zimmer) for f, _k in kand]
    best, best_wert = 0, None
    for maske in range(1, 1 << len(kand)):
        sb = sm = sp = sz = 0.0
        for i in range(len(kand)):
            if maske >> i & 1:
                sb += bau[i]
                sm += mob[i]
                sp += punkte[i]
                sz += zimmer[i]
        if (bb is not None and sb > bb + .5) or (bm is not None and sm > bm + .5):
            continue
        wert = (round(sp, 3), sz, -(sb + sm))
        if best_wert is None or wert > best_wert:
            best, best_wert = maske, wert
    if not best:
        return None
    gew = [kand[i][0] for i in range(len(kand)) if best >> i & 1]
    gew.sort(key=lambda f: fl.index(f))
    aw = _auswahl("", gew, p, jahr)
    aw.titel = f"{aw.zimmer} Zimmer im Budget"
    return aw


def guenstigste(fl: list[Flur], p: dict, jahr: int) -> tuple[Flur, Kosten] | None:
    erg = [(f, kosten(p, f.haus, len(f.zimmer), jahr)) for f in fl]
    return min(erg, key=lambda x: x[1].summe) if erg else None


def engpass_markieren(fs: list[Fenster], f: Flur, kap: float | None, belegt: list | None = None,
                      warn_anteil: float = .95) -> None:
    """Monat ist ein Engpass, wenn die obere Prognose die Warnschwelle der Kapazität erreicht – Kapazität minus diese
    Etage und minus Etagen, die im selben Monat schon im Bau sind (``belegt``: PlanZeilen)."""
    if not kap:
        return
    for fe in fs:
        if not fe.prognose:
            continue
        weg = f.betten + gesperrte_betten(belegt or [], date(fe.start.year, fe.start.month, 1))
        fe.engpass = fe.prognose[2] >= (kap - weg) * warn_anteil


@dataclass
class Vorschlag:
    flur: Flur
    fenster: Fenster | None


def vorschlaege(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict | None = None,
                prognose: dict | None = None, auswahl: Auswahl | None = None, kap: float | None = None) -> list[Vorschlag]:
    """Für die Etagen der Ziel-Auswahl (ohne schon vorgemerkte) je den besten Monat – keine zwei Baustellen im
    selben Monat (die Ausweichzimmer würden doppelt gezählt)."""
    p = p or parameter()
    schon = {e["flur"] for e in plan() if e["start"][:4] == str(jahr)}
    belegt_monate = {date.fromisoformat(e["start"]).month for e in plan() if e["start"][:4] == str(jahr)}
    auswahl = auswahl or (ziel_auswahl(fl, p, jahr) or [None])[-1]
    erg = []
    bau = jahresplan(stand, jahr, None, p) if kap else []          # schon vorgemerkte Baustellen senken die Kapazität
    for f in (auswahl.flure if auswahl else []):
        if f.schluessel in schon:
            continue
        fs = [x for x in monatsfenster(stand, f, jahr, p, prognose) if x.start.month not in belegt_monate]
        engpass_markieren(fs, f, kap, bau)
        best = bester_monat(fs, heute)
        if best:
            belegt_monate.add(best.start.month)
            bau.append(PlanZeile(f.schluessel, f.text, len(f.zimmer), f.betten, best.start, best.ende, best.stopp_ab,
                                 "vorschlag", Kosten(len(f.zimmer), jahr)))
        erg.append(Vorschlag(f, best))
    return erg


# ---- Jahresplan (Gantt) und Kapazität ---------------------------------------------------------------

@dataclass
class PlanZeile:
    flur: str                     # Schlüssel
    text: str
    zimmer: int
    betten: int
    start: date
    ende: date
    stopp_ab: date
    status: str                   # vorgemerkt | vorschlag
    kosten: Kosten
    gleichwertig: bool = False
    ohne_ausweich: int = 0
    engpass: bool = False


def jahresplan(stand: zp.Planstand, jahr: int, vorschl: list[Vorschlag] | None = None,
               p: dict | None = None) -> list[PlanZeile]:
    """Zeilen für das Gantt: vorgemerkte Etagen (fest) und Vorschläge (gestrichelt)."""
    p = p or parameter()
    nach_schl: dict[str, list] = {}
    for z in stand.zimmer:
        nach_schl.setdefault(schluessel(z.haus, z.etage, ""), []).append(z)
    erg = []
    for e in plan():
        s, en = date.fromisoformat(e["start"]), date.fromisoformat(e["ende"])
        if not (s.year <= jahr <= en.year):
            continue
        zs = nach_schl.get(e["flur"], [])
        erg.append(PlanZeile(e["flur"], flur_text_schluessel(e["flur"]), len(zs), sum(z.betten for z in zs), s, en,
                             s - timedelta(days=int(p["vorlauf_tage"])), "vorgemerkt",
                             kosten(p, e["flur"].split("|")[0], len(zs), s.year)))
    for v in vorschl or []:
        if v.fenster is None:
            continue
        fe, f = v.fenster, v.flur
        erg.append(PlanZeile(f.schluessel, f.text, len(f.zimmer), f.betten, fe.start, fe.ende, fe.stopp_ab, "vorschlag",
                             kosten(p, f.haus, len(f.zimmer), jahr), fe.gleichwertig, len(fe.ohne_ausweich),
                             fe.engpass))
    return sorted(erg, key=lambda z: (z.start, z.text))


def jahresuebersicht(stand: zp.Planstand, jahr: int, p: dict | None = None) -> list[dict]:
    """Je Monat: vorgemerkte Flure, Zimmer, Betten, Kosten (im Startmonat)."""
    p = p or parameter()
    monate = [{"monat": m, "flure": [], "zimmer": 0, "betten": 0, "kosten": 0.0} for m in range(1, 13)]
    for z in jahresplan(stand, jahr, None, p):
        for mo in monate:
            m0 = date(jahr, mo["monat"], 1)
            m1 = date(jahr + (mo["monat"] == 12), mo["monat"] % 12 + 1, 1) - timedelta(days=1)
            if z.start <= m1 and z.ende >= m0:
                mo["flure"].append(z.text)
                mo["zimmer"] += z.zimmer
                mo["betten"] += z.betten
                if z.start.year == jahr and z.start.month == mo["monat"]:
                    mo["kosten"] += z.kosten.summe
    return monate


def gesperrte_betten(zeilen: list[PlanZeile], monat: date) -> float:
    """Betten, die im Monat (anteilig nach Tagen) wegen Bauarbeiten fehlen – für die Kapazitätslinie."""
    m1 = date(monat.year + (monat.month == 12), monat.month % 12 + 1, 1) - timedelta(days=1)
    tage = (m1 - monat).days + 1
    summe = 0.0
    for z in zeilen:
        a, b = max(z.start, monat), min(z.ende, m1)
        if a <= b:
            summe += z.betten * ((b - a).days + 1) / tage
    return round(summe, 1)


def excel(stand: zp.Planstand, jahr: int, pfad, zeilen: list[PlanZeile] | None = None) -> int:
    import openpyxl
    from openpyxl.styles import Font

    p = parameter()
    zeilen = zeilen if zeilen is not None else jahresplan(stand, jahr, None, p)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Plan {jahr}"
    ws.append([f"Renovierungsplan {jahr} (unverbindlich)"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Kosten: Preisstand {p['preisstand']}, +{p['preis_pct']} % je Jahr, Nebenkosten {p['neben_pct']} %, "
               f"Puffer {p['puffer_pct']} %, Vorsteuerquote {p['vorsteuer_pct']} %"])
    ws.append([])
    kopf = ["Etage", "Status", "Belegungsstopp ab", "Bau von", "Bau bis", "Zimmer", "Betten", "Bau + Neben (€)",
            "Möbel + Aufbau (€)", "Gesamt (€)", "netto (€)"]
    ws.append(kopf)
    for c in ws[4]:
        c.font = Font(bold=True)
    for z in zeilen:
        ws.append([z.text, z.status, z.stopp_ab, z.start, z.ende, z.zimmer, z.betten, round(z.kosten.instandhaltung),
                   round(z.kosten.investition), round(z.kosten.summe), round(z.kosten.netto)])
        for sp in (3, 4, 5):
            ws.cell(ws.max_row, sp).number_format = "DD.MM.YYYY"
    ws.append(["Summe", "", "", "", "", sum(z.zimmer for z in zeilen), sum(z.betten for z in zeilen),
               round(sum(z.kosten.instandhaltung for z in zeilen)), round(sum(z.kosten.investition for z in zeilen)),
               round(sum(z.kosten.summe for z in zeilen)), round(sum(z.kosten.netto for z in zeilen))])
    for spalte, breite in zip("ABCDEFGHIJK", (22, 12, 16, 12, 12, 8, 8, 16, 18, 14, 14)):
        ws.column_dimensions[spalte].width = breite
    pfad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pfad)
    return len(zeilen)


# ---- Mit Rückgängig (für die Oberfläche) ---------------------------------------------------------

def vormerken_schritt(flur: str, start: date, ende: date) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Renovierung vorgemerkt: {flur_text_schluessel(flur)}", lambda: erg.append(vormerken(flur, start, ende)), [DATEI])
    return erg[0]


def vormerken_mehrere_schritt(eintraege: list[tuple[str, date, date]]) -> str:
    """Mehrere Vorschläge auf einmal übernehmen – ein Schritt, ein Rückgängig."""
    from .kern import _schritt

    def tun():
        for flur, start, ende in eintraege:
            vormerken(flur, start, ende)
    _schritt(f"Renovierung: {len(eintraege)} Vorschläge übernommen", tun, [DATEI])
    return f"{len(eintraege)} Etage{'n' if len(eintraege) != 1 else ''} vorgemerkt (unverbindlich)"


def entfernen_schritt(flur: str, start: str) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Vormerkung entfernt: {flur_text_schluessel(flur)}", lambda: erg.append(entfernen(flur, start)), [DATEI])
    return erg[0]


def parameter_schritt(p: dict) -> str:
    from .kern import _schritt

    erg = []
    _schritt("Renovierung: Planungsannahmen", lambda: erg.append(parameter_speichern(p)), [DATEI])
    return erg[0]


def excel_speichern(stand: zp.Planstand, jahr: int) -> tuple[str, object]:
    from pathlib import Path

    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Exporte"))
    pfad = ziel / f"Renovierungsplan_{jahr}.xlsx"
    excel(stand, jahr, pfad)
    return "Renovierungsplan gespeichert", pfad
