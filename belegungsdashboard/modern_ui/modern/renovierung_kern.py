"""Renovierung (Steuerung → Renovierung): Welche Etagen bzw. Zimmer – wann – was kostet es – wohin mit den Bewohnern?

Ein Flur ist die ganze Etage (Haus 2 und Haus 6). Nur Planung: Hier wird nichts gesperrt, niemand umgezogen und keine
Buchung verschoben. Gespeichert werden nur Annahmen und – nach Bestätigung – Vormerkungen
(``importe/modern_renovierung.json``, nur im Datenordner, nie im Programm).

0.44 – Grundsätze:

* **Bedarf getrennt nach Bau und Möbel, in Klassen A (jetzt) / B (1–3 Jahre) / C (später)** – aus Mängelarten
  (Boden, Wand, Schimmel, Geruch → Bau; Möbel, Matratze → Möbel; „Renovierung nötig“ → beides), Jahren seit der
  Renovierung und der Zustandsnote der Etage. In den letzten 5 Jahren renoviert = kein Bau (harte Regel), Möbel geht.
  Gewichte 100/10/1: erst alle A, dann B, dann C.
* **Baubudget = feste Grenze, die verfällt** → es soll möglichst voll in gedeckten Bedarf gehen; ein Rest ist ein
  Warnhinweis. **Möbel = Antrag**: INNternat rechnet den Möbelbedarf aus (für die Bau-Maßnahmen + „nur Möbel“ für
  Klasse-A-Zimmer); eine realistische Obergrenze ist optional.
* **Auswahl**: jede Etagenkombination im Baubudget, aufgefüllt mit Einzelzimmern nach Bedarf je Euro – die beste
  Gesamtlösung gewinnt. Etagen ohne machbaren Monat und Reserve-Etagen (Kernbestand) fallen vorher heraus.
* **Kosten mit Herkunft** (Angebot / Eingabe / Schätzung / Platzhalter), Puffer je Budget, Spanne statt Scheingenauigkeit.
  Einzelzimmer aus Einheitspreisen des Angebots × Zimmerfläche, sonst anteilig + Aufschlag (Schätzung).
* **Termine**: Etagen in den besten Monat (Ausweich → Warnschwelle → Umzüge); ohne Buchungen „nicht prüfbar“.
  Einzelzimmer gebündelt in Kampagnen je Haus, frühestens nach der Möbel-Lieferzeit.

1.29 aufgeteilt (nur verschoben): Kosten und Angebote → ``renovierung_kosten``, Strategien, Kampagnen und
Jahresplan → ``renovierung_planung``. Alle Namen bleiben hier erreichbar.

Rein, ohne NiceGUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

from belegung import speicher
from belegung import zimmerplan as zp


# 1.29: aufgeteilt – diese Namen liegen jetzt in renovierung_kosten.py (hier weiter erreichbar)
from .renovierung_kosten import (  # noqa: F401
    _BODEN,
    _BRUTTO,
    _GUELTIG,
    _HAUS,
    _HAUS_STANDARD,
    _POS,
    _STUECK,
    _SUMME,
    _TUER,
    _WAND,
    HERKUNFT_TEXT,
    KOSTEN_GEMEINSAM,
    STANDARD,
    UNSICHER,
    UST,
    Kosten,
    _zahl,
    angebot_auswerten,
    angebot_lesen,
    angebot_uebernehmen,
    angebote_alt,
    bau_je_einzelzimmer,
    einheitspreise,
    euro,
    euro2,
    gesamt_unsicherheit,
    gueltig_bis,
    herkunft,
    kosten,
    positionen,
    preisfaktor,
    spanne_text,
    tsd,
)

DATEI = f"{speicher.IMPORT_ORDNER}/modern_renovierung.json"
MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
KURZ_GRUPPEN = ("EMR", "ASS", "UWT", "Gast")
FRISCH_JAHRE = 5
BAU_MAENGEL = {"boden_kaputt", "boden_dreckig", "wand", "schimmel", "geruch"}
MOEBEL_MAENGEL = {"moebel", "matratze"}
KLASSEN_WERT = {"A": 100, "B": 10, "C": 1, None: 0}
ARTEN = {"etage": "ganze Etage", "zimmer": "Einzelzimmer komplett", "moebel": "nur Möbel tauschen"}


# ---- Ablage -------------------------------------------------------------------------------

def _roh() -> dict:
    return speicher.lesen(DATEI, {})


def parameter() -> dict:
    roh = _roh().get("parameter") or {}
    p = {**STANDARD, **{k: v for k, v in roh.items() if k in STANDARD}}
    if "moebel_obergrenze" not in roh and roh.get("budget_moebel") is not None:     # 0.42/0.43: Möbelbudget → Obergrenze
        p["moebel_obergrenze"] = roh["budget_moebel"]
    if "modus" not in roh:
        p["modus"] = "budget"
    kosten_ = {}
    for h in p["haeuser"]:
        alt = (roh.get("kosten") or {}).get(h) or {}
        if "bau_etage" not in alt:                 # Annahmen von 0.39/0.40 (Flur-Pauschale) nicht übernehmen
            alt = {}
        kosten_[h] = {**_HAUS_STANDARD, **STANDARD["kosten"].get(h, {}), **alt}
    p["kosten"] = kosten_
    p["herkunft"] = dict(p.get("herkunft") or {})
    if not p.get("preisstand"):
        p["preisstand"] = date.today().year
    return p


def parameter_speichern(p: dict) -> str:
    roh = _roh()
    roh["parameter"] = {k: p[k] for k in STANDARD if k in p}
    speicher.schreiben(DATEI, roh)
    return "Planungsannahmen gespeichert"


def herkunft_merken(alt: dict, neu: dict) -> dict:
    """Von Hand geänderte Kostenwerte als „Eingabe“ kennzeichnen."""
    h = dict(neu.get("herkunft") or alt.get("herkunft") or {})
    for haus, werte in (neu.get("kosten") or {}).items():
        for feld, wert in werte.items():
            if (alt.get("kosten", {}).get(haus) or {}).get(feld) != wert:
                h[f"{haus}.{feld}"] = "eingabe"
    return {**neu, "herkunft": h}


# ---- Vormerkungen ------------------------------------------------------------------------------------

def plan() -> list[dict]:
    """Vorgemerkte Renovierungen: {flur: "2|3|", start, ende (ISO), art (etage|zimmer|moebel), zimmer: [IDs], notiz}."""
    return [{"art": "etage", "zimmer": [], **e} for e in (_roh().get("plan") or [])]


def _gleich(e: dict, flur: str, art: str, zimmer: list, jahr: int) -> bool:
    return (e["flur"] == flur and e.get("art", "etage") == art and sorted(e.get("zimmer") or []) == sorted(zimmer or [])
            and e["start"][:4] == str(jahr))


def vormerken(flur: str, start: date, ende: date, notiz: str = "", art: str = "etage", zimmer: list | None = None) -> str:
    roh = _roh()
    eintraege = [e for e in roh.get("plan") or [] if not _gleich(e, flur, art, zimmer or [], start.year)]
    neu = {"flur": flur, "start": start.isoformat(), "ende": ende.isoformat(), "notiz": notiz}
    if art != "etage":
        neu.update(art=art, zimmer=list(zimmer or []))
    eintraege.append(neu)
    roh["plan"] = sorted(eintraege, key=lambda e: (e["start"], e["flur"]))
    speicher.schreiben(DATEI, roh)
    was = flur_text_schluessel(flur) if art == "etage" else f"{len(zimmer or [])} Zimmer ({ARTEN[art]})"
    return f"{was} vorgemerkt: {start:%d.%m.} – {ende:%d.%m.%Y} (unverbindlich)"


def entfernen(flur: str, start: str, art: str | None = None) -> str:
    roh = _roh()
    roh["plan"] = [e for e in roh.get("plan") or [] if not (e["flur"] == flur and e["start"] == start
                                                           and (art is None or e.get("art", "etage") == art))]
    speicher.schreiben(DATEI, roh)
    return f"{flur_text_schluessel(flur)}: Vormerkung entfernt"


# ---- Etagen und Bedarf (Klassen) -------------------------------------------------------------------

def schluessel(haus: str, etage: str, flur: str) -> str:
    return f"{haus}|{etage}|{flur}"


def flur_text_schluessel(k: str) -> str:
    haus, etage, flur = (k.split("|") + ["", "", ""])[:3]
    return f"Haus {haus} · {zp.etage_text(etage)}" + (f" {flur}" if flur else "")


def zustandsnoten() -> dict:
    """Etage → Note 1–5 aus einer Begehung (Steuerung → Kennzahlen → Werte eingeben)."""
    return {k: int(v) for k, v in (_roh().get("zustand") or {}).items() if v}


def zustandsnoten_speichern(noten: dict) -> str:
    roh = _roh()
    roh["zustand"] = {k: int(v) for k, v in noten.items() if v}
    speicher.schreiben(DATEI, roh)
    return f"Zustandsnoten für {len(roh['zustand'])} Etagen gespeichert"


@dataclass
class ZBedarf:
    """Bedarf eines Zimmers: Klasse A/B/C/None je Bau und Möbel, Gründe, Bau gesperrt (frisch renoviert)."""
    bau: str | None = None
    moebel: str | None = None
    gruende: list = field(default_factory=list)
    frisch: bool = False
    alter: float | None = None

    @property
    def wert_bau(self) -> int:
        return 0 if self.frisch else KLASSEN_WERT[self.bau]

    @property
    def wert_moebel(self) -> int:
        return KLASSEN_WERT[self.moebel]

    @property
    def a(self) -> bool:
        return (self.bau == "A" and not self.frisch) or self.moebel == "A"


def _max_klasse(*k):
    for x in ("A", "B", "C"):
        if x in k:
            return x
    return None


def zimmer_bedarf(z, maengel_: list, heute: date, note: int | None) -> ZBedarf:
    """Klassen je Zimmer. Bau: A = „Renovierung nötig“, Schimmel, Note 5, ≥ 20 Jahre; B = Note 4, ≥ 15 Jahre, Boden-/
    Wand-/Geruchsmangel; C = Note 3, ≥ 10 Jahre. Möbel: A = Möbel-/Matratzenmangel, „Renovierung nötig“; B = ≥ 15
    Jahre; C = ≥ 10 Jahre. In den letzten 5 Jahren renoviert: kein Bau."""
    from belegung import zimmerliste as zl

    zb = ZBedarf()
    bau, mob = [], []
    arten = {m.art for m in maengel_}
    if "renovierung" in arten:
        bau.append("A"), mob.append("A"), zb.gruende.append("Renovierung nötig")
    if "schimmel" in arten:
        bau.append("A"), zb.gruende.append("Schimmel")
    if arten & (BAU_MAENGEL - {"schimmel"}):
        bau.append("B"), zb.gruende.append("Boden/Wand/Geruch")
    if arten & MOEBEL_MAENGEL:
        mob.append("A"), zb.gruende.append("Möbel/Matratze")
    if note:
        bau.append({5: "A", 4: "B", 3: "C"}.get(note))
        if note >= 4:
            zb.gruende.append(f"Zustandsnote {note}")
    d = zl.reno_datum(z) if z.renoviert else None
    if d:
        j = (heute - d).days / 365.25
        zb.alter = round(j, 1)
        if j < FRISCH_JAHRE:
            zb.frisch = True
            zb.gruende.append(f"renoviert vor {max(j, 0):.0f} J. – kein Bau")
        else:
            bau.append("A" if j >= 20 else "B" if j >= 15 else "C" if j >= 10 else None)
            mob.append("B" if j >= 15 else "C" if j >= 10 else None)
            if j >= 15:
                zb.gruende.append(f"seit {j:.0f} J. nicht renoviert")
    zb.bau, zb.moebel = _max_klasse(*bau), _max_klasse(*mob)
    return zb


@dataclass
class Flur:
    schluessel: str
    haus: str
    etage: str
    flur: str
    zimmer: list = field(default_factory=list)     # zp.Zimmer
    bedarf: float = 0.0                            # Ø Wert je Zimmer (für die Reihenfolge)
    gruende: list = field(default_factory=list)    # (Wert, Text)
    luecken: list = field(default_factory=list)
    reno_bekannt: int = 0
    alter: float | None = None
    sonder: list = field(default_factory=list)
    kosten: Kosten | None = None
    bedarfe: dict = field(default_factory=dict)    # Zimmer-ID → ZBedarf
    zustand: int | None = None

    @property
    def text(self) -> str:
        return flur_text_schluessel(self.schluessel)

    @property
    def betten(self) -> int:
        return sum(z.betten for z in self.zimmer)

    @property
    def wert(self) -> float:
        return sum(b.wert_bau + b.wert_moebel for b in self.bedarfe.values())

    def klassen(self, art: str = "bau") -> dict:
        erg = {"A": 0, "B": 0, "C": 0}
        for b in self.bedarfe.values():
            k = b.bau if art == "bau" and not b.frisch else b.moebel if art == "moebel" else None
            if k:
                erg[k] += 1
        return erg

    @property
    def klassen_text(self) -> str:
        teile = []
        for art, name in (("bau", "Bau"), ("moebel", "Möbel")):
            k = self.klassen(art)
            if any(k.values()):
                teile.append(f"{name} " + " ".join(f"{x}{n}" for x, n in k.items() if n))
        return " · ".join(teile) or "kein Bedarf erfasst"

    @property
    def ampel(self) -> str:
        if any(b.a for b in self.bedarfe.values()):
            return "krit"
        return "warn" if any("B" in (b.bau, b.moebel) for b in self.bedarfe.values()) else "ok"

    @property
    def sonderzimmer(self) -> bool:
        """EMR-, Gäste- oder Kurzmaßnahmen-Etage – nie als Reserve vorschlagen."""
        return any(zp.nur_emr(z) or z.gaeste or zp.nur_kurz(z) for z in self.zimmer)


def flure(stand: zp.Planstand, heute: date | None = None, p: dict | None = None, offen: dict | None = None,
          noten: dict | None = None) -> list[Flur]:
    """Alle Etagen der gewählten Häuser mit Bedarf je Zimmer – höchster Bedarf zuerst."""
    from belegung import maengel as mg
    from belegung import zimmerliste as zl

    heute = heute or date.today()
    p = p or parameter()
    offen = mg.offen_je_zimmer() if offen is None else offen
    noten = zustandsnoten() if noten is None else noten
    je: dict[str, Flur] = {}
    for z in stand.zimmer:
        if not z.aktiv or z.haus not in p["haeuser"]:
            continue
        k = schluessel(z.haus, z.etage, "")
        je.setdefault(k, Flur(k, z.haus, z.etage, "")).zimmer.append(z)
    for f in je.values():
        n = len(f.zimmer)
        f.zustand = noten.get(f.schluessel)
        jahre, ohne_datum, unbew = [], 0, 0
        for z in f.zimmer:
            f.bedarfe[z.id] = b = zimmer_bedarf(z, offen.get(z.id, []), heute, f.zustand)
            if b.alter is not None:
                jahre.append(b.alter)
            if z.renoviert:
                f.reno_bekannt += 1
                if zl.reno_datum(z) is None:
                    ohne_datum += 1
            if z.id in stand.lage.unbewohnbar:
                unbew += 1
        for art, name in (("bau", "Bau"), ("moebel", "Möbel")):
            for kl, anz in f.klassen(art).items():
                if anz:
                    f.gruende.append((KLASSEN_WERT[kl] * anz, f"{anz} × {name} Klasse {kl}"))
        frisch = sum(1 for b in f.bedarfe.values() if b.frisch)
        if frisch:
            f.gruende.append((0, f"{frisch} Zimmer in den letzten {FRISCH_JAHRE} Jahren renoviert – dort kein Bau"))
        if unbew:
            f.gruende.append((0, f"{unbew} Zimmer derzeit unbewohnbar"))
        f.bedarf = round(f.wert / n, 1) if n else 0.0
        f.alter = round(sum(jahre) / len(jahre), 1) if jahre else None
        if f.reno_bekannt < n:
            f.luecken.append(f"{n - f.reno_bekannt} von {n} Zimmern ohne Renovierungsdatum – unbekannt, nicht „nie“")
        if ohne_datum:
            f.luecken.append(f"{ohne_datum} Zimmer „renoviert“ ohne Datum")
        if not f.zustand:
            f.luecken.append("keine Zustandsnote")
        if emr := sum(1 for z in f.zimmer if zp.nur_emr(z)):
            f.sonder.append(f"{emr} reine EMR-Zimmer")
        if any(zp.nur_kurz(z) for z in f.zimmer):
            f.sonder.append("Etage für Kurzmaßnahmen/Allergiker")
        if g := sum(1 for z in f.zimmer if z.gaeste):
            f.sonder.append(f"{g} Gästezimmer")
        if nm := sum(1 for z in f.zimmer if z.nur_maenner):
            f.sonder.append(f"{nm} „nur Männer“ (eigenes Bad über den Flur)")
        if dz := sum(1 for z in f.zimmer if z.betten > 1):
            f.sonder.append(f"{dz} Doppelzimmer")
        f.kosten = kosten(p, f.haus, n)
    return sorted(je.values(), key=lambda f: (-f.bedarf, f.haus, zp._etage_sort(f.etage), f.flur))


def a_zimmer(fl: list[Flur], ohne: set | None = None) -> int:
    """Zimmer mit Klasse A (Bau oder Möbel), ohne die in ``ohne``."""
    return sum(1 for f in fl for zid, b in f.bedarfe.items() if b.a and zid not in (ohne or set()))


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
    pruefbar: bool = True                           # liegt der Monat noch im Bereich bekannter Buchungen?

    @property
    def betroffen(self) -> int:
        return len(self.umzug) + len(self.umleiten)

    @property
    def stufe(self) -> str:
        if self.gesperrt:
            return "gesperrt"
        if not self.betroffen:
            return "frei" if self.pruefbar else "offen"
        return "eng" if self.ohne_ausweich else "ok"


def _gruppe(b) -> str:
    return zp.belegung_gruppe(b) or ""


def _geschlecht(b) -> str:
    from .belegung_felder import (
        geschlecht,  # 1.29: „grund“ trägt bei eigenen Planungen das Geschlecht
    )

    return geschlecht(b)


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
    fe = Fenster(start, ende, start - timedelta(days=int(p["vorlauf_tage"])), gesperrt=start.month in (p.get("gesperrt") or []),
                 pruefbar=start <= buchungshorizont(stand))
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


_HORIZONT: dict = {}


def buchungshorizont(stand: zp.Planstand) -> date:
    """Bis wann Buchungen bekannt sind (späteste bekannte Anreise) – danach sagt die Ausweichprüfung nichts."""
    if _HORIZONT.get("id") is not stand:
        tage = [b.von for b in getattr(stand, "bedarf", []) or []]
        tage += [b.von for v in stand.lage.belegungen.values() for b in v if b.art in ("belegt", "geplant") and b.name
                 and b.name != zp.PIVOT_NAME]
        _HORIZONT.update(id=stand, wert=max(tage) if tage else date.today())
    return _HORIZONT["wert"]


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


# ---- Ziel ------------------------------------------------------------------------------------------

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


def defekte_betten(stand: zp.Planstand, ohne: set | None = None) -> float:
    """1.14: Betten in Zimmern, die heute nicht bewohnbar sind (Mängel) – ``ohne``: Zimmer, die schon anders zählen."""
    ohne = ohne or set()
    return float(sum(z.betten for z in stand.zimmer
                     if z.aktiv and z.id in stand.lage.unbewohnbar and z.id not in ohne))


def engpass_markieren(fs: list[Fenster], f: Flur, kap: float | None, belegt: list | None = None,
                      warn_anteil: float = .95, defekt: float = 0.0) -> None:
    """Monat ist ein Engpass, wenn die obere Prognose die Warnschwelle der Kapazität erreicht – Kapazität minus diese
    Etage, minus Etagen, die im selben Monat schon im Bau sind (``belegt``: PlanZeilen), und (1.14) minus defekte
    Betten (``defekt``, Stand heute – sie fehlen auch während des Baus)."""
    if not kap:
        return
    for fe in fs:
        if not fe.prognose:
            continue
        weg = f.betten + defekt + gesperrte_betten(belegt or [], date(fe.start.year, fe.start.month, 1))
        fe.engpass = fe.prognose[2] >= (kap - weg) * warn_anteil


# ---- Maßnahmen, Varianten, Auswahl ----------------------------------------------------------------

@dataclass
class Massnahme:
    art: str                      # etage | zimmer | moebel
    flur: Flur
    zimmer: list                  # zp.Zimmer
    wert: float                   # gedeckter Bedarf (Klassenwerte)
    kosten: Kosten
    a_zimmer: int = 0             # davon Klasse-A-Zimmer

    @property
    def text(self) -> str:
        if self.art == "etage":
            return f"{self.flur.text} (ganze Etage)"
        return f"{', '.join(z.kurz for z in self.zimmer)} ({ARTEN[self.art]})"


@dataclass
class Variante:
    schluessel: str
    titel: str
    erklaerung: str
    massnahmen: list = field(default_factory=list)
    hinweis: str = ""
    rest_bau: float | None = None

    @property
    def zimmer(self) -> int:
        return sum(len(m.zimmer) for m in self.massnahmen)

    @property
    def wert(self) -> float:
        return sum(m.wert for m in self.massnahmen)

    @property
    def klassen(self) -> tuple[int, ...]:
        """1.14: (Bau A, B, C, Möbel A, B, C) – Varianten werden der Reihe nach verglichen: erst Bau-Bedarf A, dann B,
        dann C, danach Möbel. So schlagen viele kleine Fälle nie einen dringenden."""
        liste = [(m.flur, z, m.art) for m in self.massnahmen for z in m.zimmer]
        return klassen_zahl(liste, "bau") + klassen_zahl(liste, "moebel")

    @property
    def a_zimmer(self) -> int:
        return sum(m.a_zimmer for m in self.massnahmen)

    @property
    def kosten(self) -> Kosten:
        k = Kosten(0, 0, herkunft_bau="", herkunft_moebel="")
        for m in self.massnahmen:
            k = k.plus(m.kosten)
        return k

    @property
    def etagen(self) -> list:
        return [m.flur for m in self.massnahmen if m.art == "etage"]

    def sperr_zimmermonate(self, p: dict) -> float:
        s = 0.0
        for m in self.massnahmen:
            tage = (int((p["kosten"].get(m.flur.haus) or {}).get("dauer_tage") or 30) if m.art == "etage" else
                    int(p.get("zimmer_tage") or 14) if m.art == "zimmer" else int(p.get("moebel_tage") or 3))
            s += len(m.zimmer) * tage / 30
        return round(s, 1)


def _wert(b: ZBedarf, art: str) -> float:
    return (b.wert_bau if art != "moebel" else 0) + b.wert_moebel


def _klasse(b: ZBedarf, art: str) -> str | None:
    """Maßgebliche Klasse eines Zimmers: Bau (bei Etage/Zimmer), sonst Möbel; frisch renoviert = kein Bau."""
    if art != "moebel" and b.bau and not b.frisch:
        return b.bau
    return b.moebel


def _rang(b: ZBedarf, art: str) -> int:
    """1.14: feste Rangfolge A (3) vor B (2) vor C (1) – unabhängig davon, wie viele Zimmer einer Klasse es sind."""
    return {"A": 3, "B": 2, "C": 1}.get(_klasse(b, art) or "", 0)


def klassen_zahl(liste, teil: str = "bau") -> tuple[int, int, int]:
    """(Anzahl A, B, C) einer Auswahl [(Flur, Zimmer, Art)] – zum Vergleichen der Reihe nach (1.14).
    ``teil`` „bau“: Bau-Klasse der Bau-Maßnahmen (Etage/Zimmer, frisch renoviert zählt nicht); „moebel“: Möbel-Klasse
    aller Maßnahmen (auch Etage/Zimmer komplett tauschen die Möbel)."""
    n = {"A": 0, "B": 0, "C": 0}
    for t in liste:
        f, z = t[0], t[1]
        art = t[2] if len(t) > 2 else "etage"
        if art == "moebel" and teil != "moebel":
            continue                                      # „nur Möbel“ deckt keinen Bau-Bedarf; Etage/Zimmer komplett
                                                          # bringen dagegen auch neue Möbel mit

        b = f.bedarfe.get(z.id) or ZBedarf()
        k = b.moebel if teil == "moebel" else (None if b.frisch else b.bau)
        if k in n:
            n[k] += 1
    return n["A"], n["B"], n["C"]


def _massnahme(p, f: Flur, zimmer: list, art: str, jahr: int) -> Massnahme:
    bs = [f.bedarfe.get(z.id) or ZBedarf() for z in zimmer]
    k = kosten(p, f.haus, len(zimmer), jahr, art, len(f.zimmer))
    return Massnahme(art, f, list(zimmer), sum(_wert(b, art) for b in bs), k,
                     sum(1 for b in bs if (b.a if art != "moebel" else b.moebel == "A")))


def _gruppieren(p, liste: list, jahr: int) -> list[Massnahme]:
    """(Flur, Zimmer, Art) → Maßnahmen je Etage und Art."""
    je: dict[tuple, list] = {}
    for f, z, art in liste:
        je.setdefault((f.schluessel, art), [f, []])[1].append(z)
    return [_massnahme(p, f, zs, art, jahr) for (_s, art), (f, zs) in je.items()]


def _zimmer_kandidaten(fl: list[Flur], frei: set, p: dict, jahr: int, art: str) -> list[tuple]:
    """(Wert je €, Wert, Bau-€, Möbel-€, Flur, Zimmer) – nur Zimmer mit Bedarf in dieser Art."""
    erg = []
    cache: dict[tuple, Kosten] = {}
    for f in fl:
        for z in f.zimmer:
            if z.id not in frei:
                continue
            b = f.bedarfe.get(z.id) or ZBedarf()
            w = _wert(b, art)
            if art == "zimmer" and not b.wert_bau:
                continue                                  # ohne Bau-Bedarf kein „komplett“
            if w <= 0:
                continue
            k = cache.setdefault((f.haus, art, len(f.zimmer)), kosten(p, f.haus, 1, jahr, art, len(f.zimmer)))
            preis = k.instandhaltung if art == "zimmer" else k.investition
            erg.append(((_rang(b, art), w / max(preis, 1)), w, k.instandhaltung, k.investition, f, z))
    # 1.14: erst die Klasse (A vor B vor C), dann Bedarf je € – kein billiges C-Zimmer vor einem A-Zimmer
    return sorted(erg, key=lambda x: (-x[0][0], -x[0][1], -x[1], x[4].haus, x[5].id))


def _fuellen(kand: list, rest_b: float | None, rest_m: float | None, belegt: set, ziel: int | None = None):
    """Gierig nach Bedarf je €: (Auswahl[(Flur, Zimmer)], Rest Bau, Rest Möbel)."""
    wahl = []
    for _r, _w, kb, km, f, z in kand:
        if z.id in belegt or (ziel is not None and len(wahl) >= ziel):
            continue
        if (rest_b is not None and kb > rest_b + .5) or (rest_m is not None and km > rest_m + .5):
            continue
        rest_b = None if rest_b is None else rest_b - kb
        rest_m = None if rest_m is None else rest_m - km
        wahl.append((f, z))
        belegt = belegt | {z.id}
    return wahl, rest_b, rest_m


def _moebel_a(fl: list[Flur], belegt: set) -> list[tuple]:
    """Zimmer mit Möbel-Klasse A, die noch keine Maßnahme haben → „nur Möbel“ (Teil des Möbelantrags)."""
    return [(f, z, "moebel") for f in fl for z in f.zimmer if z.id not in belegt and (f.bedarfe.get(z.id) or ZBedarf()).moebel == "A"]


def optimieren(fl: list[Flur], p: dict, jahr: int, budget_bau: float | None, moebel_grenze: float | None,
               ziel: int | None = None, mit_etagen: bool = True, mit_zimmern: bool = True, vorrang: str = "") -> tuple[list, float | None]:
    """Beste Kombination aus ganzen Etagen und Einzelzimmern: jede Etagenkombination im Baubudget (bzw. bis zum
    Zimmerziel), Rest gierig mit Einzelzimmern nach Bedarf je €. Ziel: meister Bedarf (Vorrang-Haus zuerst), dann
    mehr Zimmer, dann weniger Geld (0.46: nie nur zum Ausschöpfen). Ergebnis: ([(Flur, Zimmer, Art)], Rest Bau)."""
    etagen = [(f, kosten(p, f.haus, len(f.zimmer), jahr)) for f in fl][:16] if mit_etagen else []
    alle = {z.id for f in fl for z in f.zimmer}
    kand = _zimmer_kandidaten(fl, alle, p, jahr, "zimmer") if mit_zimmern else []
    best, best_wert, best_rest = [], None, budget_bau
    if budget_bau is None and ziel is None and moebel_grenze is None:
        return [(f, z, "etage") for f, _k in etagen for z in f.zimmer], None      # keine Grenze: alle Etagen

    def kombis(i: int, gew: list, sb: float, sm: float, nz: int):
        """Alle Etagenkombinationen, die in Budget bzw. Ziel passen (Äste, die schon zu teuer sind, werden abgeschnitten)."""
        yield gew, sb, sm, nz
        for j in range(i, len(etagen)):
            f, k = etagen[j]
            sb2, sm2, nz2 = sb + k.instandhaltung, sm + k.investition, nz + len(f.zimmer)
            if budget_bau is not None and sb2 > budget_bau + .5:
                continue
            if moebel_grenze is not None and sm2 > moebel_grenze + .5:
                continue
            if ziel is not None and nz >= ziel:
                continue                                  # Ziel schon erreicht: keine weitere Etage
            yield from kombis(j + 1, gew + [(f, k)], sb2, sm2, nz2)

    for gew, sb, sm, nz in kombis(0, [], 0.0, 0.0, 0):
        belegt = {z.id for f, _k in gew for z in f.zimmer}
        rest_b = None if budget_bau is None else budget_bau - sb
        rest_m = None if moebel_grenze is None else moebel_grenze - sm
        einzel, rest_b, _rm = _fuellen(kand, rest_b, rest_m, belegt, None if ziel is None else max(0, ziel - nz))
        if budget_bau is None and ziel is None:
            einzel = []                                   # ohne Grenze und ohne Ziel: nur Etagen
        liste = [(f, z, "etage") for f, _k in gew for z in f.zimmer] + [(f, z, "zimmer") for f, z in einzel]
        w_v = sum(_wert(f.bedarfe.get(z.id) or ZBedarf(), "etage") for f, z, _a in liste if f.haus == vorrang)
        w = sum(_wert(f.bedarfe.get(z.id) or ZBedarf(), "etage") for f, z, _a in liste)
        genutzt = (budget_bau - rest_b) if budget_bau is not None and rest_b is not None else sb
        # 0.46: Zimmer ohne Bedarf zählen nicht (außer beim Zimmerziel) – bei gleichem Bedarf die günstigere Lösung,
        # nie eine Etage nur zum Ausschöpfen des Budgets
        n = len(liste) if ziel is not None else sum(1 for f, z, _a in liste if _wert(f.bedarfe.get(z.id) or ZBedarf(), "etage") > 0)
        wert = (w_v, klassen_zahl(liste), w, n, -genutzt)   # 1.14: A vor B vor C (Reihenfolge, nicht Summe)
        if best_wert is None or wert > best_wert:
            best, best_wert, best_rest = liste, wert, rest_b
    return best, best_rest


def _als_massnahmen(p, liste: list, jahr: int) -> list[Massnahme]:
    etagen: dict[str, Flur] = {}
    rest = []
    for f, z, art in liste:
        if art == "etage":
            etagen[f.schluessel] = f
        else:
            rest.append((f, z, art))
    return [_massnahme(p, f, f.zimmer, "etage", jahr) for f in etagen.values()] + _gruppieren(p, rest, jahr)


def machbare_etagen(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict) -> set[str]:
    """Etagen mit mindestens einem Monat, in dem gebaut werden kann (nicht gesperrt, Vorlauf reicht, Ausweich für
    alle). Ohne Buchungen gilt ein Monat als machbar (nicht prüfbar)."""
    erg = set()
    for f in fl:
        for m in range(1, 13):
            fe = fenster(stand, f, date(jahr, m, 1), p)
            if not fe.gesperrt and fe.stopp_ab >= heute and not fe.ohne_ausweich:
                erg.add(f.schluessel)
                break
    return erg


def varianten(fl: list[Flur], p: dict, jahr: int, ziel: int | None = None, schon: set | None = None,
              machbar: set | None = None, reserve: set | None = None, budget_faktor: float = 1.0) -> tuple[list[Variante], str]:
    """Varianten des Jahres. Budget-Modus: Baubudget fest (Obergrenze – Rest bleibt frei, wenn kein Bedarf passt), Möbel als Antrag (optionale
    Obergrenze). Ziel-Modus: Zimmerziel. ``schon``: im Jahr vorgemerkte Zimmer; ``machbar``: Etagen mit machbarem
    Monat; ``reserve``: Reserve-Etagen (Kernbestand) – fallen heraus. Empfehlung = rechnerisch beste Variante."""
    budget = p.get("modus") != "ziel"
    bb = p.get("budget_bau") if budget else None
    bb = None if bb is None else bb * budget_faktor
    mg = p.get("moebel_obergrenze") if budget else None
    ziel = None if budget else int(ziel if ziel is not None else p.get("ziel_zimmer") or 0)
    schon, reserve = schon or set(), reserve or set()
    fl_ok = [f for f in fl if f.schluessel not in reserve]
    fl_etage = [f for f in fl_ok if not any(z.id in schon for z in f.zimmer)
                and (machbar is None or f.schluessel in machbar) and (not budget or f.wert > 0)]
    frei = {z.id for f in fl_ok for z in f.zimmer} - schon
    fl_z = [Flur(f.schluessel, f.haus, f.etage, f.flur, [z for z in f.zimmer if z.id in frei], bedarfe=f.bedarfe)
            for f in fl_ok]
    vorrang = p.get("haus_vorrang") or ""

    def mit_moebel_a(liste):
        belegt = {z.id for _f, z, _a in liste}
        return liste + _moebel_a(fl_z, belegt)

    a_liste, a_rest = optimieren(fl_etage, p, jahr, bb, mg, ziel, True, False, vorrang)
    b_liste, b_rest = optimieren(fl_etage, p, jahr, bb, mg, ziel, True, True, vorrang)
    b_liste = b_liste if b_liste else []
    # Einzelzimmer dürfen auch auf Etagen liegen, die selbst nicht machbar sind (kein Belegungsstopp nötig)
    if fl_z:
        extra, b_rest2, _m = _fuellen(_zimmer_kandidaten(fl_z, frei, p, jahr, "zimmer"),
                                      b_rest, None, {z.id for _f, z, _a in b_liste},
                                      None if ziel is None else max(0, ziel - len(b_liste)))
        if budget and bb is not None:
            b_liste += [(f, z, "zimmer") for f, z in extra]
            b_rest = b_rest2
    c_liste, c_rest = optimieren(fl_z, p, jahr, bb, mg, ziel, False, True, vorrang)
    d_kand = _zimmer_kandidaten(fl_z, frei, p, jahr, "moebel")
    d_wahl, _rb, _rm = _fuellen(d_kand, None, mg, set(), ziel if ziel is not None else None)
    a = Variante("etagen", "Nur ganze Etagen", "Ganze Etagen nach Bedarf – so, wie die Angebote gelten. Belegungsstopp "
                 "und Ausweich für die ganze Etage.", _als_massnahmen(p, a_liste, jahr), rest_bau=a_rest)
    b = Variante("kombi", "Beste Kombination", "Jede mögliche Etagenkombination im Baubudget, der Rest in die "
                 "bedürftigsten Einzelzimmer (Bedarf je €); dazu „nur Möbel“ für Zimmer mit Möbel-Klasse A.",
                 _als_massnahmen(p, mit_moebel_a(b_liste), jahr), rest_bau=b_rest)
    c = Variante("zimmer", "Nur Einzelzimmer", "Keine ganze Etage, sondern die bedürftigsten Zimmer einzeln – kein "
                 "Belegungsstopp für ganze Flure, dafür Termine je Zimmer (gebündelt in Kampagnen).",
                 _als_massnahmen(p, mit_moebel_a(c_liste), jahr), rest_bau=c_rest)
    d = Variante("moebel", "Nur Möbel tauschen", "Nur neue Möbel für Zimmer mit Möbel-Bedarf – braucht kein Baubudget. "
                 "Wände und Böden bleiben, wie sie sind.", _als_massnahmen(p, [(f, z, "moebel") for f, z in d_wahl], jahr),
                 rest_bau=bb)
    vs = [a, b, c, d]
    if not any(b_.wert_bau + b_.wert_moebel for f in fl for b_ in f.bedarfe.values()):
        for v in (b, c, d):
            v.hinweis = "Für einzelne Zimmer ist kein Bedarf erfasst (Mängel, Renovierungsdaten, Zustandsnote)."
    if budget and not any(f.wert > 0 for f in fl_ok):
        a.hinweis = "Für keine Etage ist Bedarf erfasst – Renovierungsdaten, Mängel oder Zustandsnoten pflegen."
    elif budget and bb is not None and not a.massnahmen:
        a.hinweis = "Mit diesem Baubudget passt keine ganze Etage mit Bedarf."
    if budget:                                            # 1.14: offener A-Bedarf wird sichtbar, nie still verschoben
        a_offen = {z.id for f in fl_ok for z in f.zimmer
                   if z.id not in schon and (f.bedarfe.get(z.id) or ZBedarf()).bau == "A"
                   and not (f.bedarfe.get(z.id) or ZBedarf()).frisch}
        for v in (a, b, c):
            drin = {z.id for m in v.massnahmen if m.art != "moebel" for z in m.zimmer}
            rest_a = len(a_offen - drin)
            if rest_a and v.massnahmen:
                txt = ((f"{rest_a} Zimmer mit A-Bedarf passen" if rest_a > 1 else "1 Zimmer mit A-Bedarf passt")
                       + " nicht mehr ins Baubudget und rutscht ins nächste Jahr".replace("rutscht", "rutschen" if rest_a > 1 else "rutscht")
                       + (" – C-Bedarf ist nur dabei, weil für A und B kein passender Rest mehr da war." if v.klassen[2] else "."))
                v.hinweis = (v.hinweis + " " if v.hinweis else "") + txt
    kandidaten = [v for v in vs[:3] if v.massnahmen]
    empf = max(kandidaten, key=lambda v: (v.klassen, v.wert, v.zimmer, -(v.rest_bau or 0))).schluessel if kandidaten else (
        "moebel" if d.massnahmen else "")
    return vs, empf


def robustheit(fl: list[Flur], p: dict, jahr: int, empf: str, **kw) -> str:
    """Bleibt die Empfehlung, wenn alle Kosten 15 % höher bzw. niedriger sind? (= Budget ÷ 1,15 bzw. ÷ 0,85)"""
    vs, e = varianten(fl, p, jahr, budget_faktor=1, **kw)
    basis = {(m.art, m.flur.schluessel, len(m.zimmer)) for v in vs if v.schluessel == e for m in v.massnahmen}
    saetze = []
    for faktor, text in ((1 / 1.15, "15 % teurer"), (1 / 0.85, "15 % günstiger")):
        vs2, e2 = varianten(fl, p, jahr, budget_faktor=faktor, **kw)
        v2 = next((v for v in vs2 if v.schluessel == e2), None)
        andere = {(m.art, m.flur.schluessel, len(m.zimmer)) for m in (v2.massnahmen if v2 else [])}
        if e2 != e:
            saetze.append(f"wenn alles {text} ist, wäre „{v2.titel if v2 else '–'}“ vorn")
        elif {x for x in andere if x[0] == "etage"} != {x for x in basis if x[0] == "etage"}:
            saetze.append(f"wenn alles {text} ist, ändern sich die Etagen")
    if p.get("modus") == "ziel" or p.get("budget_bau") is None:
        return "Ohne Baubudget hängt die Auswahl nicht an den Preisen."
    return "Empfehlung stabil bei Kosten ±15 %." if not saetze else "Achtung: " + "; ".join(saetze) + "."


def moebelantrag(v: Variante | None) -> dict:
    """Was beantragt werden muss: Möbel für die Bau-Maßnahmen + „nur Möbel“ – mit Spanne."""
    if not v:
        return {"summe": 0.0, "bau_mass": 0.0, "nur_moebel": 0.0, "von": 0.0, "bis": 0.0}
    bm = sum(m.kosten.investition for m in v.massnahmen if m.art != "moebel")
    nm = sum(m.kosten.investition for m in v.massnahmen if m.art == "moebel")
    von = sum(m.kosten.spanne_von("moebel")[0] for m in v.massnahmen)
    bis = sum(m.kosten.spanne_von("moebel")[1] for m in v.massnahmen)
    return {"summe": bm + nm, "bau_mass": bm, "nur_moebel": nm, "von": von, "bis": bis}


def guenstigste(fl: list[Flur], p: dict, jahr: int) -> tuple[Flur, Kosten] | None:
    erg = [(f, kosten(p, f.haus, len(f.zimmer), jahr)) for f in fl]
    return min(erg, key=lambda x: x[1].instandhaltung) if erg else None


# ---- Mit Rückgängig (für die Oberfläche) ---------------------------------------------------------

def vormerken_schritt(flur: str, start: date, ende: date) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Renovierung vorgemerkt: {flur_text_schluessel(flur)}", lambda: erg.append(vormerken(flur, start, ende)), [DATEI])
    return erg[0]


def vormerken_mehrere_schritt(eintraege: list) -> str:
    """Mehrere Vorschläge auf einmal übernehmen – ein Schritt, ein Rückgängig. Einträge: (Flur, Start, Ende) oder
    (Flur, Start, Ende, Art, [Zimmer-IDs])."""
    from .kern import _schritt

    def tun():
        for e in eintraege:
            flur, start, ende, *rest = e
            vormerken(flur, start, ende, "", *(rest[:1] or ["etage"]), *(rest[1:2] or [None]))
    _schritt(f"Renovierung: {len(eintraege)} Vorschläge übernommen", tun, [DATEI])
    return f"{len(eintraege)} Maßnahme{'n' if len(eintraege) != 1 else ''} vorgemerkt (unverbindlich)"


def zustand_schritt(noten: dict) -> str:
    from .kern import _schritt

    erg = []
    _schritt("Zustandsnoten der Etagen", lambda: erg.append(zustandsnoten_speichern(noten)), [DATEI])
    return erg[0]


def entfernen_schritt(flur: str, start: str, art: str | None = None) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Vormerkung entfernt: {flur_text_schluessel(flur)}", lambda: erg.append(entfernen(flur, start, art)), [DATEI])
    return erg[0]


def entfernen_mehrere_schritt(eintraege: list[tuple[str, str, str]]) -> str:
    """(Flur, Start ISO, Art) – z. B. alle Einzelzimmer einer Gruppe, ein Rückgängig."""
    from .kern import _schritt

    def tun():
        for flur, start, art in eintraege:
            entfernen(flur, start, art)
    _schritt(f"Renovierung: {len(eintraege)} Vormerkungen entfernt", tun, [DATEI])
    return f"{len(eintraege)} Vormerkung{'en' if len(eintraege) != 1 else ''} entfernt"


def parameter_schritt(p: dict) -> str:
    from .kern import _schritt

    erg = []
    p = herkunft_merken(parameter(), p)
    _schritt("Renovierung: Planungsannahmen", lambda: erg.append(parameter_speichern(p)), [DATEI])
    return erg[0]

def gesperrte_betten(zeilen: list[PlanZeile], monat: date) -> float:
    """Betten, die im Monat (anteilig nach Tagen) wegen Bauarbeiten fehlen – für die Kapazitätslinie."""
    m1 = date(monat.year + (monat.month == 12), monat.month % 12 + 1, 1) - timedelta(days=1)
    tage = (m1 - monat).days + 1
    summe = 0.0
    for z in zeilen:
        for von, bis, betten in ([(t[2], t[3], t[4]) for t in z.teile] if z.teile else [(z.start, z.ende, z.betten)]):
            a, b = max(von, monat), min(bis, m1)
            if a <= b:
                summe += betten * ((b - a).days + 1) / tage
    return round(summe, 1)


if TYPE_CHECKING:                                   # nur für Typangaben (kein Kreis-Import zur Laufzeit)
    from .renovierung_planung import PlanZeile


# 1.29: aufgeteilt – diese Namen liegen jetzt in renovierung_planung.py (baut hierauf auf); sie bleiben hier
# erreichbar, werden aber erst beim ersten Zugriff geladen (sonst Kreis-Import).
_IN_RENOVIERUNG_PLANUNG = frozenset({"PlanZeile", "Strategie", "Vorschlag", "_altern", "_frei_ab", "excel", "excel_speichern",
                                     "jahresplan", "jahresuebersicht", "kampagnen", "strategien", "vorschlaege",
                                     "vorschlaege_variante"})


def __getattr__(name: str):
    if name in _IN_RENOVIERUNG_PLANUNG:
        from . import renovierung_planung

        return getattr(renovierung_planung, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
