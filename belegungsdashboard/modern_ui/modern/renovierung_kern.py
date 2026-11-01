"""Flurweise Renovierung: Welcher Flur als Nächstes – und wann im Jahr? (Zimmer → Renovierung)

Ein Flur ist hier die ganze Etage (Haus 2 und Haus 6 – Ost und West lassen sich baulich nicht trennen).

Nur Planung: Hier wird nichts gesperrt, niemand umgezogen und keine Buchung verschoben. Gespeichert werden nur die
Planungsannahmen (Kosten, Budget, Dauer …) und – nach Bestätigung – vorgemerkte Renovierungen in einer eigenen Datei
(``importe/modern_renovierung.json``). Bewertet werden ausschließlich vorhandene Daten:

* **Bedarf** (Zustand) – offene Mängel nach Stufe und Alter, Mängel „Renovierung nötig“, kürzlich renovierte Zimmer
  (senken den Bedarf). Fehlt ein Renovierungsdatum, wird das als **Lücke** gezeigt, nicht geschätzt – „kein Eintrag“
  heißt nicht „nie renoviert“.
* **Machbarkeit** (je Monat) – wer im Bauzeitraum laut Gebäudeplan bzw. Planung im Flur wohnt (Umzug nötig) oder
  anreist (umleiten), ab wann ein Belegungsstopp nötig ist, ob im selben Haus genug frei ist, welche Sonderzimmer
  (EMR, Gäste, „nur Männer“) wegfallen und welche Mietverträge betroffen sind. Nur bekannte Buchungen – keine
  Vorhersage für einzelne Flure.
* **Kosten** – nur aus den eingegebenen Annahmen (je Haus: Pauschale je Flur + je Zimmer von–bis).

Rein, ohne NiceGUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import speicher
from belegung import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/modern_renovierung.json"
MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

# Planungsannahmen – alle in der Oberfläche änderbar; Kosten nur, was angegeben wurde
STANDARD = {
    "haeuser": ["2", "6"],
    "kosten": {"2": {"flur": 100000, "zimmer_min": 0, "zimmer_max": 0},       # Haus 2: rund 100.000 € je Etage inkl. Zimmer
               "6": {"flur": 10000, "zimmer_min": 3000, "zimmer_max": 4000}},  # Haus 6: Flur ~10.000 € + 3.000–4.000 € je Zimmer (9 Zimmer ≈ 40.000 €)
    "budget": 100000,             # je Jahr
    "dauer_tage": 30,
    "vorlauf_tage": 56,           # Belegungsstopp vor Baubeginn (kurze Aufenthalte sind dann von selbst weg)
    "gesperrt": [],               # Monate (1–12), in denen nicht renoviert werden soll
}
KURZ_GRUPPEN = ("EMR", "ASS", "UWT", "Gast")
KURZ_TAGE = 56
FRISCH_JAHRE = 5                  # in den letzten 5 Jahren renoviert → senkt den Bedarf
ALT_TAGE = 90                     # Mangel seit mehr als 90 Tagen offen → zählt mehr


# ---- Ablage -------------------------------------------------------------------------------

def _roh() -> dict:
    return speicher.lesen(DATEI, {})


def parameter() -> dict:
    p = {**STANDARD, **(_roh().get("parameter") or {})}
    p["kosten"] = {h: {**STANDARD["kosten"].get(h, {"flur": 0, "zimmer_min": 0, "zimmer_max": 0}), **(p["kosten"].get(h) or {})}
                   for h in p["haeuser"]}
    return p


def parameter_speichern(p: dict) -> str:
    roh = _roh()
    roh["parameter"] = {k: p[k] for k in STANDARD if k in p}
    speicher.schreiben(DATEI, roh)
    return "Planungsannahmen gespeichert"


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
    sonder: list = field(default_factory=list)     # z. B. „EMR-Zimmer (10)“
    kosten: tuple = (0, 0)                         # (von, bis) in €

    @property
    def text(self) -> str:
        return flur_text_schluessel(self.schluessel)

    @property
    def betten(self) -> int:
        return sum(z.betten for z in self.zimmer)


def _kosten(p: dict, haus: str, n: int) -> tuple[int, int]:
    k = p["kosten"].get(haus) or {}
    return (int(k.get("flur", 0) + n * k.get("zimmer_min", 0)), int(k.get("flur", 0) + n * k.get("zimmer_max", 0)))


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
        frisch, ohne_datum, unbew = 0, 0, 0
        for z in f.zimmer:
            for m in offen.get(z.id, []):
                st = m.stufe
                if m.art == "renovierung":
                    punkte["reno"] = punkte.get("reno", 0) + 4
                    texte["reno"] = texte.get("reno", 0) + 1
                else:
                    punkte[f"s{st}"] = punkte.get(f"s{st}", 0) + st
                    texte[f"s{st}"] = texte.get(f"s{st}", 0) + 1
                if (heute - m.seit).days > ALT_TAGE:
                    punkte["alt"] = punkte.get("alt", 0) + 1
                    texte["alt"] = texte.get("alt", 0) + 1
            if z.id in stand.lage.unbewohnbar:
                unbew += 1
            if z.renoviert:
                f.reno_bekannt += 1
                d = zl.reno_datum(z)
                if d is None:
                    ohne_datum += 1
                elif (heute - d).days < 365 * FRISCH_JAHRE:
                    frisch += 1
        if frisch:
            punkte["frisch"] = -3 * frisch
        namen = {"s3": "Mängel, die unbewohnbar machen (je 3 P.)", "s2": "dringende Mängel (je 2 P.)",
                 "s1": "leichte Mängel (je 1 P.)", "reno": "Mangel „Renovierung nötig“ (je 4 P.)",
                 "alt": f"davon länger als {ALT_TAGE} Tage offen (je +1 P.)"}
        f.gruende = [(punkte[k], f"{texte[k]} {namen[k]}") for k in ("reno", "s3", "s2", "s1", "alt") if k in punkte]
        if frisch:
            f.gruende.append((punkte["frisch"], f"{frisch} Zimmer in den letzten {FRISCH_JAHRE} Jahren renoviert (je −3 P.)"))
        if unbew:
            f.gruende.append((0, f"{unbew} Zimmer derzeit unbewohnbar"))
        f.bedarf = round(10 * sum(punkte.values()) / n, 1) if n else 0.0
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
        f.kosten = _kosten(p, f.haus, n)
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
    gesperrt: bool = False

    @property
    def betroffen(self) -> int:
        return len(self.umzug) + len(self.umleiten)

    @property
    def stufe(self) -> str:
        if self.gesperrt:
            return "gesperrt"
        if not self.betroffen:
            return "frei"
        return "ok" if self.betroffen <= self.frei_im_haus else "eng"


def _gruppe(b) -> str:
    return zp.belegung_gruppe(b) or ""


def fenster(stand: zp.Planstand, f: Flur, start: date, p: dict | None = None) -> Fenster:
    p = p or parameter()
    ende = start + timedelta(days=int(p["dauer_tage"]) - 1)
    fe = Fenster(start, ende, start - timedelta(days=int(p["vorlauf_tage"])), gesperrt=start.month in (p.get("gesperrt") or []))
    ids = {z.id for z in f.zimmer}
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
    fe.frei_im_haus = sum(1 for z in stand.zimmer if z.aktiv and z.haus == f.haus and z.id not in ids
                          and z.id not in stand.lage.unbewohnbar and stand.lage.freie_betten(z.id, start, ende) > 0)
    return fe


def monatsfenster(stand: zp.Planstand, f: Flur, jahr: int, p: dict | None = None) -> list[Fenster]:
    """Je Monat des Jahres ein Bauzeitraum ab dem Monatsersten (Dauer laut Annahme)."""
    p = p or parameter()
    return [fenster(stand, f, date(jahr, m, 1), p) for m in range(1, 13)]


def bester_monat(fs: list[Fenster], heute: date) -> Fenster | None:
    moeglich = [x for x in fs if not x.gesperrt and x.stopp_ab >= heute]
    return min(moeglich, key=lambda x: (x.betroffen > x.frei_im_haus, x.betroffen, x.mieter, x.start)) if moeglich else None


# ---- Budget-Pakete und Jahresübersicht ---------------------------------------------------------

@dataclass
class Paket:
    titel: str
    flure: list
    kosten: tuple
    zimmer: int
    betten: int
    bedarf: float


def pakete(fl: list[Flur], p: dict | None = None) -> list[Paket]:
    """Was passt ins Jahresbudget? Je Haus die bedürftigsten Flure, solange die Kosten (obere Schätzung) reichen."""
    p = p or parameter()
    budget = p.get("budget") or 0
    erg = []
    for haus in p["haeuser"]:
        gew, summe = [], (0, 0)
        for f in [x for x in fl if x.haus == haus]:
            if budget and summe[1] + f.kosten[1] > budget:
                continue
            gew.append(f)
            summe = (summe[0] + f.kosten[0], summe[1] + f.kosten[1])
            if not budget and len(gew) >= 1:
                break
        if gew:
            erg.append(Paket(f"Haus {haus}: {len(gew)} Flur{'e' if len(gew) > 1 else ''}", gew, summe,
                             sum(len(f.zimmer) for f in gew), sum(f.betten for f in gew), round(sum(f.bedarf for f in gew), 1)))
    return sorted(erg, key=lambda x: -x.bedarf)


def jahresuebersicht(stand: zp.Planstand, jahr: int, p: dict | None = None) -> list[dict]:
    """Je Monat: vorgemerkte Flure, Zimmer, Betten, Kosten (nur aus den Annahmen)."""
    p = p or parameter()
    nach_schl = {}
    for z in stand.zimmer:
        nach_schl.setdefault(schluessel(z.haus, z.etage, ""), []).append(z)
    monate = [{"monat": m, "flure": [], "zimmer": 0, "betten": 0, "kosten": (0, 0)} for m in range(1, 13)]
    for e in plan():
        s, en = date.fromisoformat(e["start"]), date.fromisoformat(e["ende"])
        zs = nach_schl.get(e["flur"], [])
        k = _kosten(p, e["flur"].split("|")[0], len(zs))
        erster = True
        for mo in monate:
            m0 = date(jahr, mo["monat"], 1)
            m1 = (date(jahr + (mo["monat"] == 12), mo["monat"] % 12 + 1, 1) - timedelta(days=1))
            if s <= m1 and en >= m0:
                mo["flure"].append(flur_text_schluessel(e["flur"]))
                mo["zimmer"] += len(zs)
                mo["betten"] += sum(z.betten for z in zs)
                if erster and s.year == jahr:            # Kosten im Startmonat zählen
                    mo["kosten"] = (mo["kosten"][0] + k[0], mo["kosten"][1] + k[1])
                    erster = False
    return monate


def excel(stand: zp.Planstand, jahr: int, pfad) -> int:
    import openpyxl
    from openpyxl.styles import Font

    p = parameter()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Plan {jahr}"
    ws.append([f"Renovierungsplan {jahr} (unverbindlich) – Kosten nur aus den Annahmen"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([])
    ws.append(["Monat", "Flure", "Zimmer", "Betten", "Kosten von (€)", "Kosten bis (€)"])
    for c in ws[3]:
        c.font = Font(bold=True)
    summe = [0, 0, 0, 0]
    for mo in jahresuebersicht(stand, jahr, p):
        ws.append([MONATE[mo["monat"] - 1], ", ".join(mo["flure"]), mo["zimmer"], mo["betten"], mo["kosten"][0], mo["kosten"][1]])
        summe = [summe[0] + mo["zimmer"], summe[1] + mo["betten"], summe[2] + mo["kosten"][0], summe[3] + mo["kosten"][1]]
    ws.append(["Jahr", "", *summe])
    ws.append([])
    ws.append(["Budget je Jahr (Annahme)", p.get("budget") or "–"])
    ws.append(["Flure vorgemerkt", ", ".join(flur_text_schluessel(e["flur"]) + f" ({e['start']} – {e['ende']})" for e in plan()
                                             if e["start"][:4] == str(jahr))])
    for spalte, breite in zip("ABCDEF", (14, 60, 10, 10, 16, 16)):
        ws.column_dimensions[spalte].width = breite
    pfad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pfad)
    return len(plan())


# ---- Mit Rückgängig (für die Oberfläche) ---------------------------------------------------------

def vormerken_schritt(flur: str, start: date, ende: date) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Renovierung vorgemerkt: {flur_text_schluessel(flur)}", lambda: erg.append(vormerken(flur, start, ende)), [DATEI])
    return erg[0]


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
