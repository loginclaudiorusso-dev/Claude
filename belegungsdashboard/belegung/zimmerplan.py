"""Zimmerplanung Internat Goslar: Stammdaten, Regeln und Zuteilungsvorschläge (ohne Qt).

Feste Regeln (werden nie verletzt):
* Gruppe → erlaubte Häuser/Etagen (EMR nur Haus 2 Etage 1–2, Gäste nur Haus 2 Etage 6,
  Mieter nur Haus 6, UWT nur 3.2/3.3/6, alle anderen nicht in Haus 6)
* Gästezimmer nur für Gäste
* Tiere nur in Zimmern mit Tier-Freigabe (Haus 3.1 EG/UG) – das geht der Gruppenregel vor,
  d. h. auch EMR mit Tier wohnt dort (bevorzugt EG)
* Zimmer mit Bad über den Flur (Haus 6) nur für Männer
* Doppelzimmer nur gleiches Geschlecht
* gesperrte/renovierte Zeiträume und ein Puffer nach jeder Abreise (Reinigung)

Wünsche (gewichtet):
* eine Anreise/Maßnahme zusammen auf einem Flur – Zimmer aber nicht direkt nebeneinander
* kurze Maßnahmen und Assessment bevorzugt Haus 2 Etage 5, RVL bevorzugt Haus 3.1
* Doppelzimmer bevorzugt für UWT, Tier-Zimmer für Personen mit Tier freihalten
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from . import anreiseliste, gebaeudeplan, protokoll, speicher, uwt
from .gebaeudeplan import Belegung

STAMM_DATEI = "zimmer_stammdaten.json"
ZUWEISUNGEN = "zimmer_zuweisungen.json"
PERSONEN_ANGABEN = "zimmer_personen.json"     # im Zimmerplan korrigiertes Geschlecht / Tier

GRUPPEN = ["EMR", "ASS", "RVL", "RVT", "Reha", "UWT", "Gast", "Mieter"]
GRUPPE_LABEL = {"EMR": "EMR", "ASS": "Assessment", "RVL": "RVL", "RVT": "RVT", "Reha": "Reha-Maßnahme",
                "UWT": "UWT", "Gast": "Gast", "Mieter": "Mieter"}
REHA_HAEUSER = [("2", {"1", "2", "3", "4", "5"}), ("3.1", None), ("3.2", None), ("3.3", None)]
ERLAUBT: dict[str, list[tuple[str, set | None]]] = {
    "EMR": [("2", {"1", "2"})],
    "Gast": [("2", {"6"})],
    "Mieter": [("6", None)],
    "UWT": [("3.2", None), ("3.3", None), ("6", None)],   # UWT immer Haus 3.2, 3.3 oder 6
    "RVL": REHA_HAEUSER,              # bevorzugt 3.1 (siehe zimmer_wert), sonst 3.2, 3.3 oder Haus 2
    "ASS": REHA_HAEUSER, "RVT": REHA_HAEUSER, "Reha": REHA_HAEUSER,
}
# angenommene Dauer in Wochen, wenn keine Abreise eingetragen ist
# angenommene Aufenthaltsdauer in Tagen, wenn keine Abreise eingetragen ist
STANDARD_TAGE = {"EMR": 3, "ASS": 28, "RVL": 91, "RVT": 91, "UWT": 14, "Gast": 7, "Mieter": 364, "Reha": 364}
STANDARD_TEXT = "EMR 3 Übernachtungen ab dem Vortag, Assessment 4 Wochen, RVL/RVT 13 Wochen, sonst 1 Jahr"
# EMR reisen einen Tag vor dem Datum der Anreiseliste an (Liste 05.10. → da ab 04.10., Abreise 07.10.)
EMR_VORTAG = 1
KURZ_WOCHEN = 8
GAESTEZIMMER = [f"GS-2-{n}" for n in range(601, 618)]


def gruppe_von(massnahme: str, standard: str = "Reha") -> str:
    m = (massnahme or "").upper()
    if "EMR" in m:
        return "EMR"
    if "UWT" in m:
        return "UWT"
    if "MIET" in m:
        return "Mieter"
    if re.search(r"\bGAST|GÄSTE|GAESTE", m):
        return "Gast"
    if re.search(r"\bRVL\b", m):
        return "RVL"
    if re.search(r"\bRVT\b", m):
        return "RVT"
    if re.search(r"\bASS\b|ASSESSMENT", m):
        return "ASS"
    return standard


# ---------------------------------------------------------------------------------------
# Geschlecht aus dem Vornamen schätzen (nur als Vorschlag – im Programm korrigierbar)
# ---------------------------------------------------------------------------------------

_WEIBLICH = set("""
ines doris iris agnes carmen karin kerstin katrin kathrin miriam ruth edith gudrun sigrid ingrid astrid birgit
gertrud elif ayse ayşe beatrix esther rachel isabel mareike liv jasmin yasmin chantal michelle nicole
annett anett jennifer madlen madeleine marlen kim lilli lilly lili mandy cindy sandy ivonne yvonne
heike elke silke anke frauke ilse else meike maike helga inga ulrike dörte doerte christin kristin
gloria safiatou suad mercedes nathalie natalie leonie sophie franziska fenja ann anne anna christin kristin
shannon lynn evelyn kathleen jacqueline ingeborg margot elisabeth judith gabriele carolin karolin marlene
dagmar hannelore rosemarie irmgard waltraud gisela ursel sabine susanne nadin jessika denise beatrice alice
""".split())
_MAENNLICH = set("""
uwe rene rené ole kalle mike luca luka nikita sascha jonas niklas nicklas klaus hans jens lars
mattia elia noah jona joshua jeremia dominique jean pascal jannik yannik janik maxime kai kay toni tony malte
hauke ingo udo arne bjarne kalle
benedikt nico niko mirko marko heiko eike haike timo hauke enno momme jannes ilja sasha emre musa
hamza mustafa idris yunus luis louis jörg joerg hoang-phuong carlo
""".split())


def vorname(name: str) -> str:
    """'Nachname, Vorname Zweitname' -> 'Vorname'; 'Vorname Nachname' -> 'Vorname'."""
    teil = name.split(",", 1)[1] if "," in name else name
    worte = teil.strip().split()
    return worte[0] if worte else ""


def geschlecht_raten(name: str) -> str:
    v = vorname(name).lower().strip(".-")
    if not v:
        return ""
    if v in _WEIBLICH:
        return "w"
    if v in _MAENNLICH:
        return "m"
    teile = v.split("-")
    if any(t in _WEIBLICH for t in teile) and not teile[0] in _MAENNLICH:
        return "w"
    erster = teile[0]
    if erster in _WEIBLICH:
        return "w"
    if erster in _MAENNLICH:
        return "m"
    return "w" if erster.endswith(("a", "e")) else "m"


# ---------------------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------------------

@dataclass
class Zimmer:
    id: str
    haus: str
    etage: str
    nr: str
    betten: int = 1
    flur: str = ""            # z. B. "West" / "Ost"
    nur_maenner: bool = False  # Bad über den Flur
    tiere: bool = False
    gaeste: bool = False
    aktiv: bool = True         # False = gehört nicht zum Internat (z. B. Jugendhilfe, Lager)
    notiz: str = ""

    @property
    def nummer(self) -> int:
        m = re.search(r"(\d+)$", self.nr)
        return int(m.group(1)) if m else 0

    @property
    def flur_schluessel(self) -> tuple[str, str, str]:
        return self.haus, self.etage, self.flur

    @property
    def kurz(self) -> str:
        return f"{self.haus}-{self.nr}"


def etage_text(etage: str) -> str:
    return {"E": "EG", "U": "UG"}.get(etage, f"{etage}. OG")


def flur_text(z: Zimmer) -> str:
    return f"Haus {z.haus} · {etage_text(z.etage)}"     # Flur (West/Ost) nur intern für die Planung


def _standard_flur(haus: str, etage: str, nummer: int) -> str:
    """Aus den Grundrissen: jeweils zwei Flure, getrennt durch das Treppenhaus."""
    n = nummer % 100
    if haus == "2":
        return "West" if n <= 6 or n >= 19 else "Ost"
    if haus == "3.1":
        return "West" if n <= 11 else "Ost"
    if haus == "3.2":
        return "West" if n <= 8 else "Ost"
    if haus == "3.3":
        return "West" if n <= 18 else "Ost"
    if haus == "6":
        return "Ost" if n <= 4 else "West"
    return ""


def standard_zimmer(plan_zimmer: list[gebaeudeplan.PlanZimmer]) -> list[Zimmer]:
    ergebnis = []
    for p in plan_zimmer:
        z = Zimmer(p.id, p.haus, p.etage, p.nr, p.betten)
        z.flur = _standard_flur(p.haus, p.etage, z.nummer)
        if p.haus == "6" and z.nummer % 100 in (1, 2, 5, 8, 9):
            z.nur_maenner = True   # Bad über den Flur (Grundriss Haus 6)
        if p.haus == "3.1" and p.etage in ("E", "U"):
            z.tiere = True
        ergebnis.append(z)
    vorhanden = {z.id for z in ergebnis}
    for zid in GAESTEZIMMER:
        if zid not in vorhanden:
            nr = zid.rsplit("-", 1)[1]
            ergebnis.append(Zimmer(zid, "2", "6", nr, 1, _standard_flur("2", "6", int(nr)), gaeste=True))
    return ergebnis


def mitgelieferte_zimmer() -> list[gebaeudeplan.PlanZimmer]:
    from .gebaeude_standard import ZIMMER

    return [gebaeudeplan.PlanZimmer(*z) for z in ZIMMER]


def stammdaten(plan: gebaeudeplan.Gebaeudeplan | None) -> list[Zimmer]:
    """Standard aus Plan + Grundrissen, überschrieben mit den in der App gepflegten Werten."""
    basis = standard_zimmer(plan.zimmer if plan else mitgelieferte_zimmer())
    aenderungen = speicher.lesen(STAMM_DATEI, {})
    for z in basis:
        for k, v in aenderungen.get(z.id, {}).items():
            if hasattr(z, k) and k not in ("id", "haus", "etage", "nr"):
                setattr(z, k, v)
    return sorted(basis, key=lambda z: (_haus_sort(z.haus), _etage_sort(z.etage), z.nummer))


def stammdaten_speichern(zimmer: list[Zimmer], plan: gebaeudeplan.Gebaeudeplan | None) -> None:
    """Nur Abweichungen vom Standard speichern – so wirken spätere Regeländerungen weiter."""
    standard = {z.id: z for z in standard_zimmer(plan.zimmer if plan else mitgelieferte_zimmer())}
    aenderungen = {}
    for z in zimmer:
        s = standard.get(z.id)
        if s is None:
            continue
        diff = {k: v for k, v in asdict(z).items() if k not in ("id", "haus", "etage", "nr") and getattr(s, k) != v}
        if diff:
            aenderungen[z.id] = diff
    speicher.schreiben(STAMM_DATEI, aenderungen)


def _haus_sort(h: str) -> float:
    try:
        return float(h)
    except ValueError:
        return 99


def _etage_sort(e: str) -> int:
    return {"U": -1, "E": 0}.get(e, int(e) if e.isdigit() else 99)


# ---------------------------------------------------------------------------------------
# Bedarf: wer braucht ein Zimmer?
# ---------------------------------------------------------------------------------------

@dataclass
class Bedarf:
    schluessel: str
    name: str
    massnahme: str
    gruppe: str
    von: date
    bis: date
    geschlecht: str = ""          # m | w | d | ""
    geschlecht_geschaetzt: bool = False
    tier: bool = False
    bis_angenommen: bool = False
    anreise_kennung: str = ""     # Gruppierung (Anreisetag + Gruppe/Klasse)
    bemerkung: str = ""
    zimmer_vorgabe: str = ""      # bereits bekanntes Zimmer (UWT-Liste)
    liste_anreise: date | None = None   # Anreisedatum laut Liste (EMR sind schon am Vortag da)
    abreise_liste: date | None = None   # eingetragene Abreise (None = angenommen)
    dz: str = ""                  # UWT: "" = keine DZ-Liste | "allein" | "<Klasse>:<Nr>" = DZ-Partner-Gruppe

    @property
    def wochen(self) -> float:
        return ((self.bis - self.von).days + 1) / 7

    @property
    def kurz(self) -> bool:
        return self.wochen <= KURZ_WOCHEN or self.gruppe in ("ASS", "EMR")


def bedarf_aus_personen(personen: list[anreiseliste.Person], wochen: dict | None = None) -> list[Bedarf]:
    tage = wochen or STANDARD_TAGE
    ergebnis = []
    for p in personen:
        if not p.internat:
            continue
        gruppe = gruppe_von(p.massnahme, "EMR" if p.gruppe == "EMR" else "Reha")
        von, bis = zeitraum(gruppe, p.anreise, p.abreise, tage)
        g = p.geschlecht or geschlecht_raten(p.name)
        ergebnis.append(Bedarf(p.schluessel, p.name, p.massnahme or p.gruppe, gruppe, von, bis, g,
                               not p.geschlecht, p.tier, p.abreise is None, f"{von.isoformat()}|{gruppe}",
                               p.bemerkung, liste_anreise=p.anreise, abreise_liste=p.abreise))
    return ergebnis


def zeitraum(gruppe: str, anreise: date, abreise: date | None, tage: dict | None = None) -> tuple[date, date]:
    """(Ankunft, Abreisetag) im Haus. EMR kommen am Vortag des Listendatums und bleiben drei Nächte."""
    tage = tage or STANDARD_TAGE
    if gruppe == "EMR":
        von = anreise - timedelta(days=EMR_VORTAG)
        return von, abreise or von + timedelta(days=tage.get("EMR", 3))
    return anreise, abreise or anreise + timedelta(days=tage.get(gruppe, 364) - 1)


def bedarf_aus_uwt(bloecke: list[dict], klassen: dict[str, list[dict]] | None = None) -> list[Bedarf]:
    """UWT-Blöcke → Personen. Namen kommen aus der Blockliste (PDF) oder der Klassenübersicht;
    ohne beides gibt es Platzhalter („Platz 1 …“). DZ-Partner aus der Klassenübersicht."""
    ergebnis = []
    for b in bloecke:
        von, bis = date.fromisoformat(b["anreise"]), date.fromisoformat(b["abreise"])
        kennung = f"{b['anreise']}|UWT {b['klasse']}"
        klasse = (klassen or {}).get(b["klasse"], [])
        nach_id = {k["tn_id"]: k for k in klasse}
        personen = b.get("personen") or klasse
        for p in personen:
            k = nach_id.get(str(p.get("tn_id", "")), {})
            vorgabe = p.get("geschlecht") or k.get("geschlecht")
            g = vorgabe or geschlecht_raten(p["name"])
            ergebnis.append(Bedarf(f"uwt:{b['klasse']}:{b['anreise']}:{p['tn_id']}", p["name"], f"UWT {b['klasse']}", "UWT",
                                   von, bis, g, not vorgabe, False, False, kennung, k.get("bemerkung", ""),
                                   p.get("zimmer", ""), dz=k.get("dz", "")))
        for i in range(len(personen), 0 if klasse and not b.get("personen") else int(b["anzahl"])):
            ergebnis.append(Bedarf(f"uwt:{b['klasse']}:{b['anreise']}:#{i + 1}", f"UWT {b['klasse']} – Platz {i + 1}",
                                   f"UWT {b['klasse']}", "UWT", von, bis, "", True, False, False, kennung))
    return ergebnis


def angaben_laden() -> dict[str, dict]:
    return speicher.lesen(PERSONEN_ANGABEN, {})


def angabe_setzen(schluessel: str, **werte) -> None:
    alle = angaben_laden()
    alle.setdefault(schluessel, {}).update(werte)
    speicher.schreiben(PERSONEN_ANGABEN, alle)


def angaben_anwenden(bedarf: list[Bedarf], angaben: dict[str, dict]) -> list[Bedarf]:
    for b in bedarf:
        a = angaben.get(b.schluessel, {})
        if a.get("geschlecht") is not None:
            b.geschlecht, b.geschlecht_geschaetzt = a["geschlecht"], False
        if a.get("tier") is not None:
            b.tier = bool(a["tier"])
        if a.get("gruppe") in GRUPPEN:
            b.gruppe = a["gruppe"]
            if b.liste_anreise is not None:
                b.von, b.bis = zeitraum(b.gruppe, b.liste_anreise, b.abreise_liste)
            if "|" in b.anreise_kennung and not b.anreise_kennung.split("|", 1)[1].startswith("UWT"):
                b.anreise_kennung = f"{b.von.isoformat()}|{b.gruppe}"
    return bedarf


# ---------------------------------------------------------------------------------------
# Belegungslage
# ---------------------------------------------------------------------------------------

@dataclass
class Lage:
    zimmer: dict[str, Zimmer]
    belegungen: dict[str, list[Belegung]]   # Zimmer-ID -> Belegungen (Plan + geplante Zuweisungen)
    puffer: int = 1                          # Tage nach einer Abreise, bevor neu belegt wird (1 = nicht am Abreisetag)
    abgleich: list["Abgleich"] = field(default_factory=list)   # Zuteilung ↔ Gebäudeplan
    dz: dict[str, str] = field(default_factory=dict)           # Person → DZ-Gruppe (UWT, siehe Bedarf.dz)

    def _relevant(self, zid: str, von: date, bis: date, ohne: set[str] | frozenset = frozenset()) -> list[Belegung]:
        p = max(self.puffer - 1, 0)
        return [b for b in self.belegungen.get(zid, []) if b.person not in ohne and b.ueberschneidet(von, bis, p)]

    def freie_betten(self, zid: str, von: date, bis: date, ohne: set[str] | frozenset = frozenset()) -> int:
        z = self.zimmer[zid]
        kollision = self._relevant(zid, von, bis, ohne)
        if any(b.art == "gesperrt" for b in kollision):
            return 0
        # maximale gleichzeitige Belegung im Zeitraum (Tageswechsel prüfen)
        punkte = sorted({max(b.von, von) for b in kollision} | {von})
        maximal = 0
        for t in punkte:
            maximal = max(maximal, sum(1 for b in kollision if b.art in ("belegt", "geplant")
                                       and b.von <= t <= b.bis + timedelta(days=max(self.puffer - 1, 0))))
        return max(z.betten - maximal, 0)

    def mitbewohner(self, zid: str, von: date, bis: date, ohne: set[str] | frozenset = frozenset()) -> list[Belegung]:
        return [b for b in self._relevant(zid, von, bis, ohne) if b.art in ("belegt", "geplant")]

    def status_am(self, zid: str, tag: date) -> tuple[str, list[Belegung]]:
        """frei | belegt | teilweise | geplant | gesperrt am Tag."""
        z = self.zimmer[zid]
        heute = [b for b in self.belegungen.get(zid, []) if b.von <= tag <= b.bis]
        if any(b.art == "gesperrt" for b in heute):
            return "gesperrt", heute
        personen = [b for b in heute if b.art in ("belegt", "geplant")]
        if not personen:
            return "frei", heute
        if len(personen) < z.betten:
            return "teilweise", heute
        return ("geplant" if all(b.art == "geplant" for b in personen) else "belegt"), heute

    def frei_bis(self, zid: str, ab: date) -> date | None:
        """Bis wann ein ab ``ab`` freies Zimmer frei bleibt (None = offen)."""
        kuenftig = [b.von for b in self.belegungen.get(zid, []) if b.von > ab and b.art != "freigabe"]
        return (min(kuenftig) - timedelta(days=self.puffer)) if kuenftig else None


PIVOT_NAME = "belegt laut Zimmer-Pivot"


@dataclass
class Abgleich:
    """Unterschied zwischen unserer Zuteilung und dem Gebäudeplan."""
    art: str            # "anders" = in anderem Zimmer gebucht | "fehlt" = angereist, aber nicht gebucht
    person: str
    name: str
    geplant: str        # Zimmer-ID unserer Zuteilung
    gebucht: str = ""   # Zimmer-ID laut Gebäudeplan
    von: date | None = None

    @property
    def text(self) -> str:
        kurz = lambda zid: zid.removeprefix("GS-")
        if self.art == "anders":
            return f"{self.name}: anders gebucht als geplant – {kurz(self.gebucht)} statt {kurz(self.geplant)}"
        return (f"{self.name}: angereist am {self.von:%d.%m.}? Im Gebäudeplan noch nicht gebucht "
                f"(geplant {kurz(self.geplant)})")


def _namenswoerter(name: str) -> frozenset[str]:
    return frozenset(w for w in re.split(r"[^\wäöüß]+", name.lower()) if len(w) > 1)


def lage_bauen(zimmer: list[Zimmer], plan: gebaeudeplan.Gebaeudeplan | None, zuweisungen: list[dict],
               puffer: int = 1, zimmer_pivot=None, heute: date | None = None) -> Lage:
    """Gebäudeplan + unsere Zuteilungen. Steht eine Person (Name, Zeitraum überschneidet sich) im
    Gebäudeplan – egal in welchem Zimmer –, gilt die Buchung dort; unsere Zuteilung entfällt."""
    heute = heute or date.today()
    belegungen: dict[str, list[Belegung]] = {z.id: [] for z in zimmer}
    gebucht: list[tuple[frozenset[str], Belegung]] = []
    for b in (plan.belegungen if plan else []):
        belegungen.setdefault(b.zimmer, []).append(b)
        if b.name and b.art == "belegt":
            gebucht.append((_namenswoerter(b.name), b))
    abgleich: list[Abgleich] = []
    toleranz = timedelta(days=3)     # An-/Abreise im Gebäudeplan kann ein paar Tage abweichen
    for zw in zuweisungen:
        von, bis = date.fromisoformat(zw["von"]), date.fromisoformat(zw["bis"])
        woerter = _namenswoerter(zw["name"])
        treffer = [b for w, b in gebucht if woerter and woerter <= w
                   and b.von <= bis + toleranz and von - toleranz <= b.bis]
        if treffer:
            if all(b.zimmer != zw["zimmer"] for b in treffer):
                abgleich.append(Abgleich("anders", zw["person"], zw["name"], zw["zimmer"], treffer[0].zimmer, von))
            continue   # steht im Gebäudeplan – das gilt
        if plan is not None and von <= heute <= bis:
            abgleich.append(Abgleich("fehlt", zw["person"], zw["name"], zw["zimmer"], "", von))
        b = Belegung(zw["zimmer"], von, bis, "geplant",
                     zw["name"], zw.get("massnahme", ""), zw.get("geschlecht", ""), zw["person"])
        belegungen.setdefault(b.zimmer, []).append(b)
    if zimmer_pivot is not None:
        from .zimmerpivot import ergaenzungen

        bekannt = {zid: [(b.von, b.bis) for b in bs if b.art in ("belegt", "geplant")] for zid, bs in belegungen.items()}
        freigaben = {zid: [(b.von, b.bis) for b in bs if b.art == "freigabe"] for zid, bs in belegungen.items()}
        for zid, laeufe in ergaenzungen(zimmer_pivot, bekannt, freigaben).items():
            if zid not in belegungen:
                continue
            for von, bis, n in laeufe:
                for _ in range(n):
                    belegungen[zid].append(Belegung(zid, von, bis, "belegt", PIVOT_NAME, "", "Zimmer-Pivot"))
    for z in zimmer:
        if not z.aktiv:
            belegungen[z.id] = [Belegung(z.id, date(2000, 1, 1), date(2099, 12, 31), "gesperrt", grund="nicht im Internat")]
    return Lage({z.id: z for z in zimmer}, belegungen, puffer, abgleich)


# ---------------------------------------------------------------------------------------
# Regeln
# ---------------------------------------------------------------------------------------

def nur_emr(z: Zimmer) -> bool:
    """Haus 2, 1. Etage, Zimmer 101–110: ausschließlich EMR."""
    return z.haus == "2" and z.etage == "1" and 101 <= z.nummer <= 110


def erlaubt(z: Zimmer, gruppe: str) -> bool:
    if z.gaeste != (gruppe == "Gast"):
        return False
    if nur_emr(z) and gruppe != "EMR":
        return False
    for haus, etagen in ERLAUBT.get(gruppe, REHA_HAEUSER):
        if z.haus == haus and (etagen is None or z.etage in etagen):
            return True
    return False


def belegung_gruppe(b: Belegung) -> str | None:
    """Personengruppe einer Belegung (aus der Maßnahme, z. B. „GS UWT CUA26“ → UWT, „Miete Goslar“ → Mieter).
    None für Sperrungen und Pivot-Ergänzungen (dort ist nicht bekannt, wer im Zimmer ist)."""
    if b.art not in ("belegt", "geplant") or b.name == PIVOT_NAME:
        return None
    return gruppe_von(b.massnahme, "Reha")


def gruppen_am(lage: Lage, zid: str, tag: date) -> set[str]:
    return {g for b in lage.belegungen.get(zid, []) if b.von <= tag <= b.bis and (g := belegung_gruppe(b))}


def passt(lage: Lage, z: Zimmer, b: Bedarf, ohne: set[str] | frozenset = frozenset()) -> str | None:
    """None, wenn das Zimmer für den Bedarf zulässig ist – sonst der Grund."""
    if not z.aktiv:
        return "nicht im Internat"
    # Tier geht vor Gruppenregel: wer mit Tier kommt (auch EMR), wohnt in einem Tier-Zimmer
    tier_ausnahme = b.tier and z.tiere and b.gruppe not in ("Gast", "Mieter")
    if not erlaubt(z, b.gruppe) and not tier_ausnahme:
        return f"{GRUPPE_LABEL[b.gruppe]} nicht in {flur_text(z)}"
    if b.tier and not z.tiere:
        return "Tier nur in Haus 3.1 EG/UG"
    if z.nur_maenner and b.geschlecht != "m":
        return "Bad über den Flur – nur Männer"
    if lage.freie_betten(z.id, b.von, b.bis, ohne) <= 0:
        return "im Zeitraum belegt oder gesperrt"
    if z.betten > 1:
        mit = lage.mitbewohner(z.id, b.von, b.bis, ohne)
        # Doppelzimmer teilen sich nur UWT-Teilnehmende derselben Klasse; alle anderen wohnen allein darin
        if mit and (b.gruppe != "UWT" or any(gruppe_von(m.massnahme, "") != "UWT" or m.massnahme.split()[-1:] != b.massnahme.split()[-1:]
                                              for m in mit)):
            return "Doppelzimmer – nur gemeinsam mit derselben UWT-Klasse"
        # mit DZ-Liste: nur die eingetragenen Partner zusammen, wer keinen hat, wohnt allein
        partner = bool(mit) and b.dz not in ("", "allein") and all(lage.dz.get(m.person, "") == b.dz for m in mit)
        if mit and not partner and (b.dz or any(lage.dz.get(m.person, "") for m in mit)):
            return ("Doppelzimmer – laut DZ-Liste allein" if b.dz == "allein"
                    else "Doppelzimmer – nur mit dem DZ-Partner laut Liste")
        for m in mit if not partner else []:      # DZ-Partner laut Liste: Geschlecht nicht raten
            g = geschlecht_raten(m.name) if m.art == "belegt" else m.grund
            if b.geschlecht and g and g != b.geschlecht:
                return "Doppelzimmer – anderes Geschlecht"
    return None


def zimmer_wert(z: Zimmer, b: Bedarf) -> float:
    """Wunsch-Punkte eines (zulässigen) Zimmers für eine Person."""
    w = 0.0
    if b.kurz and z.haus == "2" and z.etage == "5":
        w += 3
    elif not b.kurz and z.haus == "2" and z.etage == "5":
        w -= 1.5                     # Reserve für kurze Maßnahmen
    if b.gruppe == "RVL" and z.haus == "3.1":
        w += 1 if z.tiere else 4     # 3.1 bevorzugt – aber nicht auf Kosten der Tier-Zimmer
    if b.gruppe == "UWT":
        if b.dz == "allein":
            w += -1 if z.betten > 1 else 1   # laut DZ-Liste allein: Einzelzimmer, Doppelzimmer für Paare lassen
        else:
            w += 3 if z.betten > 1 else 0
        w += 1 if z.haus in ("3.2", "3.3") else 0
    elif z.betten > 1:
        w -= 2                       # Doppelzimmer für UWT freihalten
    if z.tiere and not b.tier:
        w -= 3                       # Tier-Zimmer freihalten – es gibt nur wenige
    if b.tier and z.etage == "E":
        w += 1                       # mit Tier bevorzugt Erdgeschoss
    if z.nur_maenner and b.gruppe != "UWT":
        w -= 0.5
    if b.gruppe in ("Reha", "RVT") and (z.haus.startswith("3") or (z.haus == "2" and z.etage in ("2", "3", "4"))):
        w += 1
    if b.gruppe != "EMR" and z.haus == "2" and z.etage in ("1", "2"):
        w -= 1                       # EMR kann nur hierhin – Platz freihalten
    if b.gruppe == "EMR" and nur_emr(z):
        w += 2                       # EMR zuerst in die reinen EMR-Zimmer 101–110 (dort darf sonst niemand hin)
    return w


def anschluss_wert(lage: Lage, z: Zimmer, b: Bedarf) -> float:
    """Bonus für nahtlose Folgebelegung: Zimmer, aus dem kurz vor der Anreise jemand auszieht (Auszugs- und
    Einzugsreinigung fallen zusammen) bzw. in das kurz nach der Abreise wieder jemand einzieht. Das hält
    lange freie Zimmer für lange Aufenthalte frei. Bewusst kleiner als die Reserven (Tier, Doppel, EMR)."""
    w = 0.0
    luecke = luecke_davor(lage, z, b)
    if luecke is not None:
        # wenn möglich ein ganzer Werktag zum Reinigen zwischen Aus- und Einzug (Auszug Mi → Anreise ab Fr;
        # Auszug Fr → Anreise erst ab Di, weil am Wochenende nicht gereinigt wird)
        ok = reinigungstag_dazwischen(b.von - timedelta(days=luecke), b.von)
        w += -1.0 if not ok else 1.5 if luecke <= 4 else 0.75 if luecke <= 10 else 0
    danach = luecke_danach(lage, z, b)
    if danach is not None:
        ok = reinigungstag_dazwischen(b.bis, b.bis + timedelta(days=danach))
        w += -1.0 if not ok else 0.75 if danach <= 4 else 0
    return w


REINIGUNGS_ABSTAND = 2   # Tage von Auszug bis Anreise, damit ein ganzer Tag zum Reinigen bleibt


def werktag(d: date) -> bool:
    """Gereinigt wird Montag bis Freitag – samstags und sonntags nicht."""
    return d.weekday() < 5


def reinigungstag_dazwischen(auszug: date, anreise: date) -> bool:
    """Bleibt zwischen Auszug und Anreise Zeit zum Reinigen? Ja, wenn ein ganzer Werktag dazwischen liegt
    (Auszug Mi → Anreise Fr) oder der Auszugstag ein Werktag ist und die Anreise nicht schon am nächsten Tag
    folgt (Auszug Fr → Anreise Mo: am Freitag nach dem Auszug). Nein z. B. bei Auszug Sa → Anreise Mo."""
    d = auszug + timedelta(days=1)
    while d < anreise:
        if werktag(d):
            return True
        d += timedelta(days=1)
    return werktag(auszug) and (anreise - auszug).days >= REINIGUNGS_ABSTAND


def _andere(lage: Lage, z: Zimmer, b: Bedarf) -> list[Belegung]:
    return [x for x in lage.belegungen.get(z.id, []) if x.art in ("belegt", "geplant") and x.person != b.schluessel]


def luecke_davor(lage: Lage, z: Zimmer, b: Bedarf) -> int | None:
    """Tage zwischen dem letzten Auszug im Zimmer und der Anreise (None = vorher niemand)."""
    vorher = [x.bis for x in _andere(lage, z, b) if x.bis < b.von]
    return (b.von - max(vorher)).days if vorher else None


def luecke_danach(lage: Lage, z: Zimmer, b: Bedarf) -> int | None:
    """Tage zwischen der Abreise und der nächsten Anreise im Zimmer (None = danach niemand)."""
    nachher = [x.von for x in _andere(lage, z, b) if x.von > b.bis]
    return (min(nachher) - b.bis).days if nachher else None


# ---------------------------------------------------------------------------------------
# Vorschlag
# ---------------------------------------------------------------------------------------

@dataclass
class Zuteilung:
    bedarf: Bedarf
    zimmer: Zimmer | None
    grund: str = ""
    warnungen: list[str] = field(default_factory=list)
    alternativen: list[Zimmer] = field(default_factory=list)
    ausnahmen: list[Zimmer] = field(default_factory=list)   # nur von Hand wählbar (freie Gästezimmer)


def _paar(b: Bedarf) -> bool:
    return b.dz not in ("", "allein")


def _als_belegung(b: Bedarf, z: Zimmer) -> Belegung:
    # Geschlecht im Feld "grund" mitführen, damit Doppelzimmer-Regeln es kennen
    return Belegung(z.id, b.von, b.bis, "geplant", b.name, b.massnahme, b.geschlecht, b.schluessel)


def vorschlagen(lage: Lage, bedarf: list[Bedarf], fest: dict[str, str] | None = None) -> list[Zuteilung]:
    """Teilt alle Personen einer oder mehrerer Anreisen zu.

    ``fest``: Person -> Zimmer-ID, vom Nutzer festgelegt (wird übernommen, sofern zulässig).
    Vorgehen je Anreise-Gruppe (gleicher Tag, gleiche Gruppe/Klasse): zuerst den Flur wählen,
    auf dem die ganze Gruppe zulässig Platz hat und der am besten passt; darin die Zimmer mit
    Lücken vergeben (Nachbarzimmer nur, wenn nötig). Wer nicht mehr passt, kommt auf den
    nächstbesten Flur.
    """
    fest = fest or {}
    ohne = frozenset(b.schluessel for b in bedarf)   # eigene bisherige Planungen neu vergeben
    belegungen = {k: [x for x in v if x.person not in ohne] for k, v in lage.belegungen.items()}
    arbeit = Lage(lage.zimmer, belegungen, lage.puffer, dz={**lage.dz, **{b.schluessel: b.dz for b in bedarf if b.dz}})
    ergebnis: dict[str, Zuteilung] = {}

    def belegen(b: Bedarf, z: Zimmer, grund: str) -> None:
        geteilt = z.betten > 1 and bool(arbeit.mitbewohner(z.id, b.von, b.bis))
        arbeit.belegungen.setdefault(z.id, []).append(_als_belegung(b, z))
        warn = []
        vorher, nachher = luecke_davor(arbeit, z, b), luecke_danach(arbeit, z, b)
        if vorher is not None and not reinigungstag_dazwischen(b.von - timedelta(days=vorher), b.von):
            warn.append(f"Kein Reinigungstag (Werktag): Vorgänger zieht am {b.von - timedelta(days=vorher):%d.%m.} aus")
        if nachher is not None and not reinigungstag_dazwischen(b.bis, b.bis + timedelta(days=nachher)):
            warn.append(f"Kein Reinigungstag (Werktag): Nachfolger kommt am {b.bis + timedelta(days=nachher):%d.%m.}")
        laut_liste = False
        if geteilt and _paar(b):
            mit = [m for m in arbeit.mitbewohner(z.id, b.von, b.bis) if m.person != b.schluessel]
            laut_liste = all(arbeit.dz.get(m.person) == b.dz for m in mit)
            grund = f"Doppelzimmer mit {', '.join(m.name for m in mit)} (DZ-Liste)"
        if laut_liste:
            pass                     # Paar laut DZ-Liste – Geschlecht nicht nachfragen
        elif not b.geschlecht and (geteilt or z.nur_maenner):
            warn.append("Geschlecht unbekannt – bitte prüfen")
        elif b.geschlecht_geschaetzt and (geteilt or z.nur_maenner):
            warn.append("Geschlecht aus dem Vornamen geschätzt – bitte prüfen")
        ergebnis[b.schluessel] = Zuteilung(b, z, grund, warn)

    # 1) Vorgaben: vom Nutzer festgelegt oder aus der UWT-Liste bekannt
    for b in bedarf:
        zid = fest.get(b.schluessel) or _zimmer_aus_kurz(b.zimmer_vorgabe, lage)
        if zid and zid in lage.zimmer:
            z = lage.zimmer[zid]
            grund = passt(arbeit, z, b)
            if grund is None or b.schluessel in fest:
                belegen(b, z, "festgelegt" if b.schluessel in fest else "laut UWT-Liste")
                if grund:
                    ergebnis[b.schluessel].warnungen.append(
                        "Ausnahme: Gästezimmer, von Hand gewählt" if z.gaeste and b.gruppe != "Gast"
                        and grund.startswith(GRUPPE_LABEL[b.gruppe]) else f"Regel verletzt: {grund}")

    # 2) Personen mit Tier zuerst – für sie gibt es nur wenige Zimmer (Haus 3.1 EG/UG)
    zimmer_liste = [z for z in lage.zimmer.values() if z.aktiv]
    for b in sorted((b for b in bedarf if b.tier and b.schluessel not in ergebnis), key=lambda b: b.von):
        kandidaten = [z for z in zimmer_liste if passt(arbeit, z, b) is None]
        if kandidaten:
            z = max(kandidaten, key=lambda z: zimmer_wert(z, b) + anschluss_wert(arbeit, z, b) - 0.001 * z.nummer)
            belegen(b, z, f"Tier-Zimmer {flur_text(z)}")

    # 3) Gruppenweise nach Flur
    offen = [b for b in bedarf if b.schluessel not in ergebnis]
    gruppen: dict[str, list[Bedarf]] = {}
    for b in sorted(offen, key=lambda b: (b.von, not b.tier, b.name)):
        gruppen.setdefault(b.anreise_kennung or b.schluessel, []).append(b)
    # schwierige Gruppen zuerst (wenig zulässige Zimmer)
    # Klassen mit DZ-Liste vor Klassen ohne – die Paare brauchen die Doppelzimmer
    reihenfolge = sorted(gruppen.values(), key=lambda g: (g[0].von, not any(_paar(b) for b in g),
                                                         len([z for z in zimmer_liste if erlaubt(z, g[0].gruppe)])))

    def paar_start(b: Bedarf) -> bool:
        """Erste Person eines DZ-Paares, deren Partner noch kein Zimmer hat."""
        return _paar(b) and not any(x.dz == b.dz for x in (zt.bedarf for zt in ergebnis.values())) and any(
            x.dz == b.dz and x is not b for x in bedarf)

    def doppel_frei(z: Zimmer, b: Bedarf) -> bool:
        return z.betten > 1 and arbeit.freie_betten(z.id, b.von, b.bis) >= 2 and passt(arbeit, z, b) is None

    for gruppe in reihenfolge:
        rest = list(gruppe)
        genutzte_flure: list[tuple] = []
        while rest:
            flure: dict[tuple, list[Zimmer]] = {}
            for z in zimmer_liste:
                if any(passt(arbeit, z, b) is None for b in rest):
                    flure.setdefault(z.flur_schluessel, []).append(z)
            if not flure:
                for b in rest:
                    ergebnis[b.schluessel] = Zuteilung(b, None, "kein zulässiges Zimmer frei",
                                                       [_warum_nicht(arbeit, zimmer_liste, b)])
                break
            n = len(rest)

            def flur_wert(item) -> float:
                schluessel, zs = item
                b0 = rest[0]
                if b0.gruppe == "UWT":
                    plaetze = sum(arbeit.freie_betten(z.id, b0.von, b0.bis) for z in zs)
                else:
                    plaetze = sum(1 for z in zs if passt(arbeit, z, b0) is None)
                beste = sorted((zimmer_wert(z, b0) + anschluss_wert(arbeit, z, b0) for z in zs
                                if passt(arbeit, z, b0) is None), reverse=True)[:n]
                wert = (sum(beste) / len(beste) if beste else 0) * 2   # wie gut passt der Flur (Ø der besten Zimmer)
                wert += 6 if plaetze >= n else 6 * plaetze / n
                wert += 2 if plaetze >= 2 * n - 1 else 0          # Platz für Lücken
                paare = sum(1 for b in rest if paar_start(b))
                if paare:                                          # Doppelzimmer für die DZ-Paare
                    wert += 4 * min(sum(1 for z in zs if doppel_frei(z, b0)), paare) / paare
                wert -= 0.02 * max(plaetze - 2 * n, 0)             # nicht unnötig große Flure anbrechen
                if genutzte_flure and schluessel[:2] == genutzte_flure[-1][:2]:
                    wert += 1                                      # Folge-Flur auf derselben Etage
                return wert

            schluessel, zs = max(flure.items(), key=flur_wert)
            genutzte_flure.append(schluessel)
            belegt_hier: list[int] = []
            vergeben = False
            for b in sorted(rest, key=lambda b: (not b.tier, b.geschlecht, b.dz)):
                eigene = list(zs)
                if _paar(b):   # Zimmer des Partners gehört dazu, auch auf einem anderen Flur
                    eigene += [x.zimmer for x in ergebnis.values() if x.bedarf.dz == b.dz and x.zimmer and x.zimmer not in eigene]
                kandidaten = [z for z in sorted(eigene, key=lambda z: z.nummer) if passt(arbeit, z, b) is None]
                if paar_start(b) and not any(z.betten > 1 for z in kandidaten) and any(
                        doppel_frei(z, b) for z in zimmer_liste):
                    continue   # Paar wartet auf einen Flur mit freiem Doppelzimmer
                if not kandidaten:
                    continue

                def wert(z: Zimmer) -> float:
                    w = zimmer_wert(z, b) + anschluss_wert(arbeit, z, b)   # frei gewordene Zimmer zuerst
                    if any(abs(z.nummer - n) == 1 for n in belegt_hier):
                        w -= 1.2                                   # nicht direkt nebeneinander
                    if z.betten > 1 and (mit := arbeit.mitbewohner(z.id, b.von, b.bis)):
                        w += 1.5                                   # angefangenes Doppelzimmer auffüllen
                        if b.dz and all(arbeit.dz.get(m.person) == b.dz for m in mit):
                            w += 8                                 # zum DZ-Partner laut Liste
                    elif z.betten > 1 and b.dz not in ("", "allein") and any(
                            x.dz == b.dz and x.schluessel not in ergebnis and x is not b for x in rest):
                        w += 2                                     # Doppelzimmer für das Paar anfangen
                    return w - 0.001 * z.nummer

                z = max(kandidaten, key=wert)
                belegen(b, z, f"{GRUPPE_LABEL[b.gruppe]} zusammen auf {flur_text(z)}")
                belegt_hier.append(z.nummer)
                vergeben = True
            rest = [b for b in rest if b.schluessel not in ergebnis]
            if not vergeben:
                for b in rest:
                    ergebnis[b.schluessel] = Zuteilung(b, None, "kein zulässiges Zimmer frei",
                                                       [_warum_nicht(arbeit, zimmer_liste, b)])
                break

    # DZ-Partner, die nicht zusammen untergekommen sind
    for zt in ergebnis.values():
        b = zt.bedarf
        if b.dz in ("", "allein") or zt.zimmer is None:
            continue
        getrennt = [x.bedarf.name for x in ergebnis.values() if x is not zt and x.bedarf.dz == b.dz
                    and x.zimmer is not None and x.zimmer.id != zt.zimmer.id]
        if getrennt:
            zt.warnungen.append(f"DZ-Partner {', '.join(getrennt)} in anderem Zimmer – kein gemeinsames Doppelzimmer frei")

    # 4) Alternativen je Person (ohne die eigene Zuteilung)
    for zt in ergebnis.values():
        b = zt.bedarf
        eigene = frozenset({b.schluessel})
        alt = [z for z in zimmer_liste if passt(arbeit, z, b, eigene) is None]
        # alle zulässigen Zimmer – angezeigt nach Haus und Nummer
        zt.alternativen = sorted(alt, key=lambda z: (_haus_sort(z.haus), z.nummer))
        if zt.zimmer and zt.zimmer not in zt.alternativen:
            zt.alternativen.insert(0, zt.zimmer)
        # Von Hand geht jedes Zimmer, das im Zeitraum ein freies Bett hat – auch gegen die Regeln
        # (Gästezimmer, anderes Haus …). Vorgeschlagen werden solche Zimmer nie.
        # Zimmer, in denen im Zeitraum schon jemand anderes wohnt, nicht (keine Fremden ins Doppelzimmer).
        zt.ausnahmen = sorted((z for z in zimmer_liste if z not in zt.alternativen
                               and arbeit.freie_betten(z.id, b.von, b.bis, eigene) > 0
                               and not arbeit.mitbewohner(z.id, b.von, b.bis, eigene)),
                              key=lambda z: (_haus_sort(z.haus), z.nummer))
    return [ergebnis[b.schluessel] for b in bedarf if b.schluessel in ergebnis]


def verschieben_pruefen(stand: "Planstand", person: str, nach: str) -> tuple[str | None, str | None, list[Bedarf]]:
    """Kann die geplante Zuweisung ins Zimmer ``nach``? Gibt (Fehler, Hinweis, DZ-Partner) zurück:
    Fehler = geht nicht (belegt, gesperrt, fremder Mitbewohner); Hinweis = geht, verletzt aber eine Regel;
    DZ-Partner = Partner laut DZ-Liste, die im selben Zimmer geplant sind (können mitziehen)."""
    b = next((x for x in stand.bedarf if x.schluessel == person), None)
    zw = stand.zugewiesen(person)
    z = stand.lage.zimmer.get(nach)
    if b is None or zw is None:
        return "Zu dieser Person gibt es keine gespeicherte Zuweisung.", None, []
    if z is None or not z.aktiv:
        return f"{nach.removeprefix('GS-')} gehört nicht zum Internat.", None, []
    partner = [x for x in stand.bedarf if _paar(b) and x.dz == b.dz and x is not b
               and (stand.zugewiesen(x.schluessel) or {}).get("zimmer") == zw["zimmer"]]
    ohne = frozenset({person})
    lage = stand.lage
    if lage.freie_betten(nach, b.von, b.bis, ohne) <= 0:
        return f"{z.kurz} ist vom {b.von:%d.%m.} bis {b.bis:%d.%m.%Y} belegt oder gesperrt.", None, partner
    grund = passt(lage, z, b, ohne)
    fremde = [m for m in lage.mitbewohner(nach, b.von, b.bis, ohne) if not (_paar(b) and lage.dz.get(m.person) == b.dz)]
    if fremde and grund:
        return (f"In {z.kurz} wohnt im Zeitraum schon {', '.join(m.name for m in fremde)} – "
                f"dorthin geht es nicht ({grund})."), None, partner
    return None, grund, partner


def ausnahme_grund(lage: Lage, z: Zimmer, b: Bedarf) -> str:
    """Kurzer Grund, warum ein Zimmer nur als Ausnahme (von Hand) in Frage kommt – für die Zimmerauswahl."""
    if z.gaeste and b.gruppe != "Gast":
        return "Gästezimmer"
    if nur_emr(z) and b.gruppe != "EMR":
        return "nur EMR"
    grund = passt(lage, z, b, frozenset({b.schluessel})) or ""
    if grund.startswith("Tier"):
        return "kein Tier-Zimmer"
    if "nur Männer" in grund:
        return "nur Männer"
    if grund.startswith("Doppelzimmer"):
        return "Doppelzimmer geteilt"
    if grund:
        return "andere Gruppe"
    return "frei"


def _zimmer_aus_kurz(text: str, lage: Lage) -> str | None:
    """'3.2-109/1' oder '6-703' -> 'GS-3.2-109'."""
    m = re.match(r"^\s*([\d.]+)-([A-Z]?\d+)", text or "")
    if not m:
        return None
    zid = f"GS-{m.group(1)}-{m.group(2)}"
    return zid if zid in lage.zimmer else None


def _erlaubt_text(gruppe: str) -> str:
    teile = []
    for haus, etagen in ERLAUBT.get(gruppe, REHA_HAEUSER):
        teile.append(f"Haus {haus}" + (f" Etage {', '.join(sorted(etagen, key=_etage_sort))}" if etagen else ""))
    return ", ".join(teile)


def _warum_nicht(lage: Lage, zimmer: list[Zimmer], b: Bedarf) -> str:
    """Verständlicher Grund, warum es für eine Person kein zulässiges Zimmer gibt."""
    zulaessig = [z for z in zimmer if z.aktiv and erlaubt(z, b.gruppe)]
    if b.tier and not any(z.tiere for z in zulaessig):
        return (f"Regeln widersprechen sich: Tier nur in Tier-Zimmern (Haus 3.1 EG/UG), "
                f"{GRUPPE_LABEL[b.gruppe]} aber nur {_erlaubt_text(b.gruppe)} – bitte Zimmer von Hand festlegen.")
    if b.tier:
        zulaessig = [z for z in zulaessig if z.tiere]
    if not b.geschlecht == "m":
        ohne_maenner = [z for z in zulaessig if not z.nur_maenner]
        if zulaessig and not ohne_maenner:
            return "Nur Zimmer mit Bad über den Flur zulässig – diese sind Männern vorbehalten."
        zulaessig = ohne_maenner
    belegt = sum(1 for z in zulaessig if lage.freie_betten(z.id, b.von, b.bis) <= 0)
    return (f"Alle {len(zulaessig)} zulässigen Zimmer ({_erlaubt_text(b.gruppe)}"
            + (", mit Tier" if b.tier else "") + f") sind vom {b.von:%d.%m.} bis {b.bis:%d.%m.%Y} belegt oder gesperrt"
            + ("" if belegt == len(zulaessig) else " bzw. passen nicht (Geschlecht im Doppelzimmer)") + ".")


# ---------------------------------------------------------------------------------------
# Zuweisungen speichern
# ---------------------------------------------------------------------------------------

def zuweisungen_laden() -> list[dict]:
    return list(speicher.lesen(ZUWEISUNGEN, {}).get("zuweisungen", []))


def zuweisungen_speichern(zuteilungen: list[Zuteilung], quelle: str = "Zuteilen") -> int:
    """Übernimmt Zuteilungen (ersetzt frühere Zuweisungen derselben Personen) und protokolliert Änderungen."""
    personen = {zt.bedarf.schluessel for zt in zuteilungen}
    alle = zuweisungen_laden()
    vorher = {z["person"]: z["zimmer"] for z in alle}
    bestand = [z for z in alle if z["person"] not in personen]
    log = []
    for zt in zuteilungen:
        alt, neu_z = vorher.get(zt.bedarf.schluessel, ""), zt.zimmer.id if zt.zimmer else ""
        if alt != neu_z:
            log.append({"aktion": "geplant" if not alt else ("entfernt" if not neu_z else "umgeplant"),
                        "name": zt.bedarf.name, "person": zt.bedarf.schluessel, "alt": alt, "neu": neu_z,
                        "von": zt.bedarf.von.isoformat(), "quelle": quelle})
    protokoll.eintragen(log)
    neu = [{"person": zt.bedarf.schluessel, "name": zt.bedarf.name, "massnahme": zt.bedarf.massnahme,
            "gruppe": zt.bedarf.gruppe, "geschlecht": zt.bedarf.geschlecht, "zimmer": zt.zimmer.id,
            "von": zt.bedarf.von.isoformat(), "bis": zt.bedarf.bis.isoformat()}
           for zt in zuteilungen if zt.zimmer is not None]
    speicher.schreiben(ZUWEISUNGEN, {"zuweisungen": bestand + neu})
    return len(neu)


def zuweisungen_abgleichen(zuw: list[dict], bedarf: list[Bedarf]) -> list[dict]:
    """Gespeicherte Zuweisungen übernehmen geänderte Zeiträume der Person (z. B. EMR-Vortag, neue Abreise)."""
    nach_person = {b.schluessel: b for b in bedarf}
    for z in zuw:
        b = nach_person.get(z["person"])
        if b is not None:
            z["von"], z["bis"], z["name"] = b.von.isoformat(), b.bis.isoformat(), b.name
    return zuw


def zuweisungen_entfernen(personen: set[str], quelle: str = "Zuteilen") -> None:
    alle = zuweisungen_laden()
    protokoll.eintragen([{"aktion": "entfernt", "name": z["name"], "person": z["person"], "alt": z["zimmer"], "neu": "",
                          "von": z["von"], "quelle": quelle} for z in alle if z["person"] in personen])
    speicher.schreiben(ZUWEISUNGEN, {"zuweisungen": [z for z in alle if z["person"] not in personen]})


def person_geloescht(schluessel: str) -> None:
    """Person wurde gelöscht – ihre Zimmerzuweisung gleich mit entfernen."""
    zuweisungen_entfernen({schluessel}, "Person gelöscht")


def person_umbenannt(alt: str | None, neu: str) -> None:
    """Schlüssel der Person hat sich geändert (z. B. TN-ID nachgetragen) – Zuweisung mitnehmen."""
    if not alt or alt == neu:
        return
    alle = zuweisungen_laden()
    if not any(z["person"] == alt for z in alle):
        return
    alle = [z for z in alle if z["person"] != neu]
    for z in alle:
        if z["person"] == alt:
            z["person"] = neu
    speicher.schreiben(ZUWEISUNGEN, {"zuweisungen": alle})


UWT_AUTO = f"{speicher.IMPORT_ORDNER}/uwt_auto_zugeteilt.json"


def uwt_vorschlaege(stand: "Planstand", heute: date | None = None, schon: set[str] | frozenset = frozenset()) -> list[Zuteilung]:
    """Zimmer für alle kommenden UWT-Teilnehmenden (mit Namen), die noch keins haben – Block für Block in
    zeitlicher Reihenfolge, damit spätere Blöcke die früheren sehen. ``schon``: früher automatisch
    zugeteilte Personen (wer dort von Hand entfernt wurde, bekommt nicht wieder eins)."""
    heute = heute or date.today()
    tage: dict[date, list[Bedarf]] = {}
    for b in stand.bedarf:
        if b.gruppe == "UWT" and b.von > heute and " – Platz " not in b.name:
            tage.setdefault(b.von, []).append(b)
    lage = stand.lage
    ergebnis: list[Zuteilung] = []
    for _tag, bs in sorted(tage.items()):
        offen = [b for b in bs if not stand.zugewiesen(b.schluessel) and b.schluessel not in schon]
        if not offen:
            continue
        fest = {b.schluessel: z["zimmer"] for b in bs if (z := stand.zugewiesen(b.schluessel))}
        mit = [b for b in bs if b.schluessel in fest] + offen
        for zt in vorschlagen(lage, mit, fest):
            if zt.zimmer is None or zt.bedarf.schluessel in fest:
                continue
            ergebnis.append(zt)
            lage.belegungen.setdefault(zt.zimmer.id, []).append(_als_belegung(zt.bedarf, zt.zimmer))
            if zt.bedarf.dz:
                lage.dz[zt.bedarf.schluessel] = zt.bedarf.dz
    return ergebnis


def uwt_automatisch_zuteilen(stand: "Planstand", heute: date | None = None) -> list[Zuteilung]:
    """Teilt kommende UWT zu und speichert es. Gibt die neuen Zuteilungen zurück."""
    roh = speicher.lesen(UWT_AUTO, {})
    schon = set(roh.get("personen", []))
    neu = uwt_vorschlaege(stand, heute, schon)
    if neu:
        zuweisungen_speichern(neu, "UWT automatisch")
        speicher.schreiben(UWT_AUTO, {"personen": sorted(schon | {zt.bedarf.schluessel for zt in neu})})
    return neu


def uwt_auto_sperren(personen: set[str]) -> None:
    """Diese Personen nicht wieder automatisch zuteilen (z. B. nachdem ihre Planung zurückgenommen wurde)."""
    roh = speicher.lesen(UWT_AUTO, {})
    speicher.schreiben(UWT_AUTO, {"personen": sorted(set(roh.get("personen", [])) | {p for p in personen if p.startswith("uwt:")})})


def planung_zuruecknehmen(personen: set[str]) -> int:
    """Entfernt die gespeicherten Zimmer dieser Personen. UWT wird danach nicht wieder automatisch zugeteilt."""
    vorher = zuweisungen_laden()
    zuweisungen_entfernen(personen, "zurückgenommen")
    uwt_auto_sperren(personen)
    return sum(1 for z in vorher if z["person"] in personen)


def uwt_neu_zuteilen(stand: "Planstand", heute: date | None = None) -> list[Zuteilung]:
    """Alle kommenden UWT-Planungen verwerfen und neu automatisch zuteilen (DZ-Paare zusammen)."""
    heute = heute or date.today()
    kommend = {b.schluessel for b in stand.bedarf if b.gruppe == "UWT" and b.von > heute}
    zuweisungen_entfernen(kommend, "UWT neu zuteilen")
    roh = speicher.lesen(UWT_AUTO, {})
    speicher.schreiben(UWT_AUTO, {"personen": sorted(set(roh.get("personen", [])) - kommend)})
    return uwt_automatisch_zuteilen(laden(), heute)


# ---------------------------------------------------------------------------------------
# Konflikte: geplantes Zimmer ist inzwischen laut Gebäudeplan belegt oder gesperrt
# ---------------------------------------------------------------------------------------

@dataclass
class Konflikt:
    person: str
    name: str
    zimmer: str
    von: date
    bis: date
    grund: str           # z. B. „gesperrt (Renoviert)“ oder „belegt: Meier, Anna (bis 20.10.)“

    @property
    def text(self) -> str:
        return f"{self.name} ({self.zimmer.removeprefix('GS-')}, {self.von:%d.%m.}–{self.bis:%d.%m.}): {self.grund}"


def konflikte(lage: Lage, heute: date | None = None) -> list[Konflikt]:
    """Unsere (noch nicht abgelaufenen) Planungen, deren Zimmer laut Gebäudeplan inzwischen anderweitig
    belegt oder gesperrt ist – also nach denselben Regeln wie beim Planen (inkl. Puffer) nicht mehr frei."""
    heute = heute or date.today()
    ergebnis = []
    for zid, bs in lage.belegungen.items():
        for b in bs:
            if b.art != "geplant" or b.bis < heute:
                continue
            ohne = frozenset({b.person})
            andere = lage._relevant(zid, b.von, b.bis, ohne)
            gesperrt = [x for x in andere if x.art == "gesperrt"]
            fremd = [x for x in andere if x.art == "belegt"]
            if gesperrt:
                grund = "gesperrt" + (f" ({gesperrt[0].grund})" if gesperrt[0].grund else "")
            elif fremd and lage.freie_betten(zid, b.von, b.bis, ohne) <= 0:
                namen = ", ".join(f"{x.name} (bis {x.bis:%d.%m.})" for x in fremd[:2])
                grund = f"belegt: {namen}"
            else:
                continue
            ergebnis.append(Konflikt(b.person, b.name, zid, b.von, b.bis, grund))
    return sorted(ergebnis, key=lambda k: (k.von, k.name))


def neu_planen(stand: "Planstand", personen: set[str]) -> tuple[list[Zuteilung], list[Bedarf]]:
    """Plant die Personen neu (DZ-Partner derselben Anreise mit) und speichert es.
    Gibt (neu zugeteilt, ohne Zimmer) zurück; wer kein Zimmer findet, verliert die alte Planung."""
    bekannt = {b.schluessel for b in stand.bedarf}
    if verwaist := {p for p in personen if p not in bekannt}:
        zuweisungen_entfernen(verwaist, "nicht mehr in der Liste")      # Person steht in keiner Liste mehr – Planung hinfällig
    betroffen = [b for b in stand.bedarf if b.schluessel in personen]
    paare = {(b.von, b.dz) for b in betroffen if _paar(b)}
    betroffen += [b for b in stand.bedarf if (b.von, b.dz) in paare and b.schluessel not in personen]
    if not betroffen:
        return [], []
    erg = vorschlagen(stand.lage, betroffen)
    neu = [zt for zt in erg if zt.zimmer is not None]
    ohne = [zt.bedarf for zt in erg if zt.zimmer is None]
    zuweisungen_speichern(neu, "Konflikt neu geplant")
    if ohne:
        zuweisungen_entfernen({b.schluessel for b in ohne}, "Konflikt – kein Zimmer frei")
    return neu, ohne


# ---------------------------------------------------------------------------------------
# Alles zusammen laden
# ---------------------------------------------------------------------------------------

@dataclass
class Planstand:
    plan: gebaeudeplan.Gebaeudeplan | None
    plan_meta: dict
    zimmer: list[Zimmer]
    lage: Lage
    zuweisungen: list[dict]
    bedarf: list[Bedarf]
    zimmer_pivot: object = None

    def anreisen(self, ab: date) -> list[tuple[str, date, str, list[Bedarf]]]:
        """Anreisetage ab einem Tag: (Kennung, Datum, Gruppen-Text, Personen).

        Alle Gruppen eines Tages werden gemeinsam geplant – sonst würden z. B. drei UWT-Klassen
        mit derselben Anreise jeweils dieselben freien Zimmer vorgeschlagen bekommen."""
        tage: dict[date, list[Bedarf]] = {}
        for b in self.bedarf:
            if b.von >= ab:
                tage.setdefault(b.von, []).append(b)
        ergebnis = []
        for tag, bs in sorted(tage.items()):
            gruppen: dict[str, int] = {}
            for b in bs:
                titel = b.anreise_kennung.split("|", 1)[1] if "|" in b.anreise_kennung else b.gruppe
                titel = GRUPPE_LABEL.get(titel, titel)
                if b.liste_anreise and b.liste_anreise != b.von:
                    titel += f" (Liste {b.liste_anreise:%d.%m.})"
                gruppen[titel] = gruppen.get(titel, 0) + 1
            text = ", ".join(f"{g} ({n})" if len(gruppen) > 1 else g for g, n in gruppen.items())
            ergebnis.append((tag.isoformat(), tag, text, sorted(bs, key=lambda b: (b.anreise_kennung, b.name))))
        return ergebnis

    def zugewiesen(self, person: str) -> dict | None:
        return next((z for z in self.zuweisungen if z["person"] == person), None)


def laden(puffer: int | None = None) -> Planstand:
    plan, meta = gebaeudeplan.laden()
    zimmer = stammdaten(plan)
    zuw = zuweisungen_laden()
    if puffer is None:
        puffer = int(speicher.einstellungen().get("zimmer_puffer", 1))
    from . import zimmerpivot

    personen, _ = anreiseliste.laden()
    bedarf = angaben_anwenden(bedarf_aus_personen(personen) + bedarf_aus_uwt(uwt.laden(), uwt.klassen_laden()),
                              angaben_laden())
    schluessel = {b.schluessel for b in bedarf}
    # Zuweisungen ohne Person (gelöscht, kein Internat mehr, UWT-Platzhalter ersetzt, Block entfernt)
    # blockieren kein Zimmer mehr
    zuw = [z for z in zuw if z["person"] in schluessel]
    zuw = zuweisungen_abgleichen(zuw, bedarf)
    zpivot = zimmerpivot.laden()
    lage = lage_bauen(zimmer, plan, zuw, puffer, zpivot)
    lage.dz = {b.schluessel: b.dz for b in bedarf if b.dz}
    return Planstand(plan, meta, zimmer, lage, zuw, bedarf, zpivot)


# ---------------------------------------------------------------------------------------
# Reinigungsliste: am Auszugstag wird das Zimmer gereinigt
# ---------------------------------------------------------------------------------------

LEERSTAND_TAGE = 28        # länger leer → vor der nächsten Anreise noch einmal vorbereiten


@dataclass
class Reinigung:
    """Eine Reinigung je Zimmer und Tag. Normalfall: Auszugsreinigung am Auszugstag – sie macht das Zimmer
    zugleich für die nächste Anreise fertig (``einzug`` = für wen, ``naechste_anreise`` = Frist).
    Ohne vorherigen Auszug (oder nach langem Leerstand) gibt es stattdessen „Vorbereiten“ vor der Anreise."""
    tag: date                                   # Reinigungstag
    zimmer: Zimmer
    auszug: list[Belegung] = field(default_factory=list)   # wer an dem Tag auszieht
    einzug: list[Belegung] = field(default_factory=list)   # für wen das Zimmer danach bereit sein muss
    bleibt: int = 0                             # Personen, die im Zimmer bleiben (Doppelzimmer)
    naechste_anreise: date | None = None        # nächste Anreise ins Zimmer (ab dem Reinigungstag) = Frist
    leer_seit: date | None = None               # Vorbereiten: letzter Auszug (None = keiner bekannt)

    @property
    def anreise(self) -> date | None:
        return min(b.von for b in self.einzug) if self.einzug else None

    @property
    def art(self) -> str:
        if self.auszug:
            return "Auszug" if self.bleibt == 0 else "Auszug (1 Bett, Mitbewohner bleibt)"
        return "Vorbereiten"

    @property
    def eilig(self) -> bool:
        """Anreise am selben oder nächsten Tag – Zimmer muss sofort fertig werden."""
        return self.naechste_anreise is not None and (self.naechste_anreise - self.tag).days <= 1

    @property
    def frist(self) -> date | None:
        """Sauber bis spätestens: letzter Werktag vor der nächsten Anreise (Sa/So wird nicht gereinigt) – aber nicht
        vor dem Auszug. Gibt es keinen Werktag dazwischen, der nächste Werktag ab dem Auszug (ggf. der Anreisetag);
        liegt auch der nach der Anreise (Auszug Sa → Anreise So), bleibt der Auszugstag (Sonderreinigung).
        None = danach kommt (noch) niemand."""
        anreise = self.naechste_anreise
        if anreise is None:
            return None
        d = anreise - timedelta(days=1)
        while not werktag(d):
            d -= timedelta(days=1)
        if d >= self.tag:
            return d
        d = self.tag
        while not werktag(d):
            d += timedelta(days=1)
        return d if d <= anreise else self.tag

    @property
    def knapp(self) -> bool:
        """Frist fällt auf den Auszugstag, den Anreisetag oder ein Wochenende – sofort bzw. besonders handeln."""
        f = self.frist
        anreise = self.naechste_anreise
        return f is not None and ((bool(self.auszug) and anreise <= self.tag + timedelta(days=1))
                                   or f >= anreise or not werktag(f))


def einzug_tag(anreise: date, letzter_auszug: date | None = None, am_anreisetag: bool = False) -> date:
    """Wann vor einer Anreise gereinigt wird: letzter Werktag vor der Anreise (Sonntag/Montag → Freitag),
    aber nie bevor der Vorgänger ausgezogen ist; ``am_anreisetag`` = immer am Anreisetag selbst."""
    if am_anreisetag:
        tag = anreise
    else:
        tag = anreise - timedelta(days=1)
        while tag.weekday() >= 5:
            tag -= timedelta(days=1)
    if letzter_auszug is not None and letzter_auszug > tag:
        tag = min(letzter_auszug, anreise)
    return tag


def reinigungen(lage: Lage, von: date, bis: date, pivot_ende: date | None = None, pivot_start: date | None = None,
                am_anreisetag: bool = False) -> list[Reinigung]:
    """Reinigungen zwischen von und bis – je Zimmer und Tag eine Zeile, sortiert nach Tag und Lage.

    * Auszug: am Auszugstag; macht das Zimmer zugleich für die nächste Anreise fertig (keine zweite Zeile).
    * Vorbereiten: nur, wenn vor einer Anreise kein Auszug bekannt ist oder das Zimmer länger als
      ``LEERSTAND_TAGE`` leer stand – am letzten Werktag vor der Anreise (bzw. am Anreisetag).
    Pivot-Ergänzungen am Rand des Pivot-Zeitraums sind keine echten An-/Auszüge."""
    ergebnis = []
    for zid, belegungen in lage.belegungen.items():
        z = lage.zimmer.get(zid)
        if z is None or not z.aktiv:
            continue
        personen = [b for b in belegungen if b.art in ("belegt", "geplant")]
        tage: dict[date, Reinigung] = {}

        def pivot_anschluss(b: Belegung, tag: date) -> bool:
            """Zimmer-Pivot führt die Belegung nahtlos weiter – kein echter Aus-/Einzug."""
            return any(x is not b and x.name == PIVOT_NAME and x.von == tag for x in personen)

        for b in personen:
            if (von <= b.bis <= bis and not (b.name == PIVOT_NAME and pivot_ende and b.bis >= pivot_ende)
                    and not pivot_anschluss(b, b.bis + timedelta(days=1))):
                tage.setdefault(b.bis, Reinigung(b.bis, z)).auszug.append(b)
            # Vorbereiten: nur ohne passende Auszugsreinigung davor
            if b.name == PIVOT_NAME and any(x.bis == b.von - timedelta(days=1) for x in personen if x is not b):
                continue                       # Pivot verlängert nur eine Belegung aus dem Gebäudeplan
            if not (von <= b.von <= bis + timedelta(days=10)) or (b.name == PIVOT_NAME and pivot_start
                                                                  and b.von <= pivot_start):
                continue
            vorher = [x.bis for x in personen if x is not b and x.bis <= b.von and x.von < b.von]
            letzter = max(vorher) if vorher else None
            if letzter is not None and (b.von - letzter).days <= LEERSTAND_TAGE:
                continue                       # die Auszugsreinigung hat das Zimmer schon fertig gemacht
            if any(x is not b and x.von < b.von <= x.bis for x in personen):
                continue                       # Mitbewohner wohnt schon drin – Bett wurde bei dessen Einzug gemacht
            tag = einzug_tag(b.von, letzter, am_anreisetag)
            if von <= tag <= bis:
                r = tage.setdefault(tag, Reinigung(tag, z))
                r.leer_seit = letzter
        for tag, r in tage.items():
            r.bleibt = sum(1 for b in personen if b not in r.auszug and b.von <= tag < b.bis)
            danach = [b for b in personen if b not in r.auszug and b.von >= tag]
            r.naechste_anreise = min((b.von for b in danach), default=None)
            r.einzug = [b for b in danach if b.von == r.naechste_anreise]
            ergebnis.append(r)
    return sorted(ergebnis, key=lambda r: (r.tag, _haus_sort(r.zimmer.haus), _etage_sort(r.zimmer.etage),
                                           r.zimmer.nummer))


# ---------------------------------------------------------------------------------------
# Zeitstrahl: Balken je Zimmer (Doppelzimmer und Überschneidungen in eigenen Spuren)
# ---------------------------------------------------------------------------------------

@dataclass
class Balken:
    von: date
    bis: date
    text: str
    art: str                 # belegt | geplant | pivot | gesperrt
    belegung: Belegung


def balken_text(b: Belegung) -> tuple[str, str]:
    if b.art == "gesperrt":
        return f"Gesperrt · {b.grund}" if b.grund else "Gesperrt", "gesperrt"
    if b.name == PIVOT_NAME:
        return "belegt (laut Zimmer-Pivot)", "pivot"
    text = b.name + (f" ({b.massnahme})" if b.massnahme else "")
    return text, ("geplant" if b.art == "geplant" else "belegt")


def zeitstrahl(lage: Lage, zimmer: list[Zimmer], von: date, bis: date) -> list[tuple[Zimmer, list[list[Balken]]]]:
    """Je Zimmer die Spuren mit Balken im Zeitraum. Freigaben werden nicht gezeichnet (Zimmer ist frei)."""
    ergebnis = []
    for z in zimmer:
        balken = []
        for b in sorted(lage.belegungen.get(z.id, []), key=lambda b: (b.art != "gesperrt", b.von)):
            if b.art == "freigabe" or b.bis < von or b.von > bis:
                continue
            text, art = balken_text(b)
            balken.append(Balken(max(b.von, von), min(b.bis, bis), text, art, b))
        spuren: list[list[Balken]] = []
        for bk in balken:
            for spur in spuren:
                if all(bk.von > x.bis or bk.bis < x.von for x in spur):
                    spur.append(bk)
                    break
            else:
                spuren.append([bk])
        while len(spuren) < max(z.betten, 1):
            spuren.append([])
        ergebnis.append((z, spuren))
    return ergebnis
