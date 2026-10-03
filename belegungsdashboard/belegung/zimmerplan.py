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

from . import anreiseliste, gebaeudeplan, speicher, uwt
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
    "UWT": [("3.2", None), ("3.3", None), ("6", None)],
    "RVL": REHA_HAEUSER,              # bevorzugt 3.1 (siehe zimmer_wert), sonst 3.2, 3.3 oder Haus 2
    "ASS": REHA_HAEUSER, "RVT": REHA_HAEUSER, "Reha": REHA_HAEUSER,
}
# angenommene Dauer in Wochen, wenn keine Abreise eingetragen ist
STANDARD_WOCHEN = {"EMR": 4, "ASS": 4, "RVL": 13, "RVT": 13, "UWT": 2, "Gast": 1, "Mieter": 52, "Reha": 52}
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
    return f"Haus {z.haus} · {etage_text(z.etage)}" + (f" · {z.flur}" if z.flur else "")


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


def stammdaten(plan: gebaeudeplan.Gebaeudeplan | None) -> list[Zimmer]:
    """Standard aus Plan + Grundrissen, überschrieben mit den in der App gepflegten Werten."""
    basis = standard_zimmer(plan.zimmer if plan else [])
    aenderungen = speicher.lesen(STAMM_DATEI, {})
    for z in basis:
        for k, v in aenderungen.get(z.id, {}).items():
            if hasattr(z, k) and k not in ("id", "haus", "etage", "nr"):
                setattr(z, k, v)
    return sorted(basis, key=lambda z: (_haus_sort(z.haus), _etage_sort(z.etage), z.flur, z.nummer))


def stammdaten_speichern(zimmer: list[Zimmer], plan: gebaeudeplan.Gebaeudeplan | None) -> None:
    """Nur Abweichungen vom Standard speichern – so wirken spätere Regeländerungen weiter."""
    standard = {z.id: z for z in standard_zimmer(plan.zimmer if plan else [])}
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

    @property
    def wochen(self) -> float:
        return ((self.bis - self.von).days + 1) / 7

    @property
    def kurz(self) -> bool:
        return self.wochen <= KURZ_WOCHEN or self.gruppe in ("ASS", "EMR")


def bedarf_aus_personen(personen: list[anreiseliste.Person], wochen: dict | None = None) -> list[Bedarf]:
    wochen = wochen or STANDARD_WOCHEN
    ergebnis = []
    for p in personen:
        if not p.internat:
            continue
        gruppe = gruppe_von(p.massnahme, "EMR" if p.gruppe == "EMR" else "Reha")
        bis, angenommen = p.abreise, False
        if bis is None:
            bis, angenommen = p.anreise + timedelta(weeks=wochen.get(gruppe, 52)) - timedelta(days=1), True
        g = p.geschlecht or geschlecht_raten(p.name)
        ergebnis.append(Bedarf(p.schluessel, p.name, p.massnahme or p.gruppe, gruppe, p.anreise, bis, g,
                               not p.geschlecht, p.tier, angenommen, f"{p.anreise.isoformat()}|{gruppe}",
                               p.bemerkung))
    return ergebnis


def bedarf_aus_uwt(bloecke: list[dict]) -> list[Bedarf]:
    ergebnis = []
    for b in bloecke:
        von, bis = date.fromisoformat(b["anreise"]), date.fromisoformat(b["abreise"])
        kennung = f"{b['anreise']}|UWT {b['klasse']}"
        personen = b.get("personen", [])
        for p in personen:
            g = p.get("geschlecht") or geschlecht_raten(p["name"])
            ergebnis.append(Bedarf(f"uwt:{b['klasse']}:{b['anreise']}:{p['tn_id']}", p["name"], f"UWT {b['klasse']}", "UWT",
                                   von, bis, g, not p.get("geschlecht"), False, False, kennung, "", p.get("zimmer", "")))
        for i in range(len(personen), int(b["anzahl"])):
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
    return bedarf


# ---------------------------------------------------------------------------------------
# Belegungslage
# ---------------------------------------------------------------------------------------

@dataclass
class Lage:
    zimmer: dict[str, Zimmer]
    belegungen: dict[str, list[Belegung]]   # Zimmer-ID -> Belegungen (Plan + geplante Zuweisungen)
    puffer: int = 1                          # Tage nach einer Abreise, bevor neu belegt wird (1 = nicht am Abreisetag)

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
            maximal = max(maximal, sum(1 for b in kollision if b.von <= t <= b.bis + timedelta(days=max(self.puffer - 1, 0))))
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
        kuenftig = [b.von for b in self.belegungen.get(zid, []) if b.von > ab]
        return (min(kuenftig) - timedelta(days=self.puffer)) if kuenftig else None


def lage_bauen(zimmer: list[Zimmer], plan: gebaeudeplan.Gebaeudeplan | None, zuweisungen: list[dict],
               puffer: int = 1) -> Lage:
    belegungen: dict[str, list[Belegung]] = {z.id: [] for z in zimmer}
    namen_im_plan = set()
    for b in (plan.belegungen if plan else []):
        belegungen.setdefault(b.zimmer, []).append(b)
        if b.name:
            namen_im_plan.add((b.name.lower(), b.zimmer))
    for zw in zuweisungen:
        if (zw["name"].lower(), zw["zimmer"]) in namen_im_plan:
            continue   # steht inzwischen im Gebäudeplan
        b = Belegung(zw["zimmer"], date.fromisoformat(zw["von"]), date.fromisoformat(zw["bis"]), "geplant",
                     zw["name"], zw.get("massnahme", ""), "", zw["person"])
        belegungen.setdefault(b.zimmer, []).append(b)
    for z in zimmer:
        if not z.aktiv:
            belegungen[z.id] = [Belegung(z.id, date(2000, 1, 1), date(2099, 12, 31), "gesperrt", grund="nicht im Internat")]
    return Lage({z.id: z for z in zimmer}, belegungen, puffer)


# ---------------------------------------------------------------------------------------
# Regeln
# ---------------------------------------------------------------------------------------

def erlaubt(z: Zimmer, gruppe: str) -> bool:
    if z.gaeste != (gruppe == "Gast"):
        return False
    for haus, etagen in ERLAUBT.get(gruppe, REHA_HAEUSER):
        if z.haus == haus and (etagen is None or z.etage in etagen):
            return True
    return False


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
        for m in mit:
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
    return w


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
    arbeit = Lage(lage.zimmer, belegungen, lage.puffer)
    ergebnis: dict[str, Zuteilung] = {}

    def belegen(b: Bedarf, z: Zimmer, grund: str) -> None:
        geteilt = z.betten > 1 and bool(arbeit.mitbewohner(z.id, b.von, b.bis))
        arbeit.belegungen.setdefault(z.id, []).append(_als_belegung(b, z))
        warn = []
        if not b.geschlecht and (geteilt or z.nur_maenner):
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
                    ergebnis[b.schluessel].warnungen.append(f"Regel verletzt: {grund}")

    # 2) Personen mit Tier zuerst – für sie gibt es nur wenige Zimmer (Haus 3.1 EG/UG)
    zimmer_liste = [z for z in lage.zimmer.values() if z.aktiv]
    for b in sorted((b for b in bedarf if b.tier and b.schluessel not in ergebnis), key=lambda b: b.von):
        kandidaten = [z for z in zimmer_liste if passt(arbeit, z, b) is None]
        if kandidaten:
            z = max(kandidaten, key=lambda z: zimmer_wert(z, b) - 0.001 * z.nummer)
            belegen(b, z, f"Tier-Zimmer {flur_text(z)}")

    # 3) Gruppenweise nach Flur
    offen = [b for b in bedarf if b.schluessel not in ergebnis]
    gruppen: dict[str, list[Bedarf]] = {}
    for b in sorted(offen, key=lambda b: (b.von, not b.tier, b.name)):
        gruppen.setdefault(b.anreise_kennung or b.schluessel, []).append(b)
    # schwierige Gruppen zuerst (wenig zulässige Zimmer)
    reihenfolge = sorted(gruppen.values(), key=lambda g: (g[0].von, len([z for z in zimmer_liste if erlaubt(z, g[0].gruppe)])))
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
                beste = sorted((zimmer_wert(z, b0) for z in zs if passt(arbeit, z, b0) is None), reverse=True)[:n]
                wert = (sum(beste) / len(beste) if beste else 0) * 2   # wie gut passt der Flur (Ø der besten Zimmer)
                wert += 6 if plaetze >= n else 6 * plaetze / n
                wert += 2 if plaetze >= 2 * n - 1 else 0          # Platz für Lücken
                wert -= 0.02 * max(plaetze - 2 * n, 0)             # nicht unnötig große Flure anbrechen
                if genutzte_flure and schluessel[:2] == genutzte_flure[-1][:2]:
                    wert += 1                                      # Folge-Flur auf derselben Etage
                return wert

            schluessel, zs = max(flure.items(), key=flur_wert)
            genutzte_flure.append(schluessel)
            belegt_hier: list[int] = []
            vergeben = False
            for b in sorted(rest, key=lambda b: (not b.tier, b.geschlecht)):
                kandidaten = [z for z in sorted(zs, key=lambda z: z.nummer) if passt(arbeit, z, b) is None]
                if not kandidaten:
                    continue

                def wert(z: Zimmer) -> float:
                    w = zimmer_wert(z, b)
                    if any(abs(z.nummer - n) == 1 for n in belegt_hier):
                        w -= 1.2                                   # nicht direkt nebeneinander
                    if z.betten > 1 and arbeit.mitbewohner(z.id, b.von, b.bis):
                        w += 1.5                                   # angefangenes Doppelzimmer auffüllen
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

    # 4) Alternativen je Person (ohne die eigene Zuteilung)
    for zt in ergebnis.values():
        b = zt.bedarf
        eigene = frozenset({b.schluessel})
        alt = [z for z in zimmer_liste if passt(arbeit, z, b, eigene) is None]
        zt.alternativen = sorted(alt, key=lambda z: (-(zimmer_wert(z, b)), _haus_sort(z.haus), _etage_sort(z.etage), z.flur, z.nummer))[:60]
        if zt.zimmer and zt.zimmer not in zt.alternativen:
            zt.alternativen.insert(0, zt.zimmer)
    return [ergebnis[b.schluessel] for b in bedarf if b.schluessel in ergebnis]


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


def zuweisungen_speichern(zuteilungen: list[Zuteilung]) -> int:
    """Übernimmt Zuteilungen (ersetzt frühere Zuweisungen derselben Personen)."""
    personen = {zt.bedarf.schluessel for zt in zuteilungen}
    bestand = [z for z in zuweisungen_laden() if z["person"] not in personen]
    neu = [{"person": zt.bedarf.schluessel, "name": zt.bedarf.name, "massnahme": zt.bedarf.massnahme,
            "gruppe": zt.bedarf.gruppe, "geschlecht": zt.bedarf.geschlecht, "zimmer": zt.zimmer.id,
            "von": zt.bedarf.von.isoformat(), "bis": zt.bedarf.bis.isoformat()}
           for zt in zuteilungen if zt.zimmer is not None]
    speicher.schreiben(ZUWEISUNGEN, {"zuweisungen": bestand + neu})
    return len(neu)


def zuweisungen_entfernen(personen: set[str]) -> None:
    speicher.schreiben(ZUWEISUNGEN, {"zuweisungen": [z for z in zuweisungen_laden() if z["person"] not in personen]})


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
                gruppen[GRUPPE_LABEL.get(titel, titel)] = gruppen.get(GRUPPE_LABEL.get(titel, titel), 0) + 1
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
    lage = lage_bauen(zimmer, plan, zuw, puffer)
    personen, _ = anreiseliste.laden()
    bedarf = angaben_anwenden(bedarf_aus_personen(personen) + bedarf_aus_uwt(uwt.laden()), angaben_laden())
    return Planstand(plan, meta, zimmer, lage, zuw, bedarf)
