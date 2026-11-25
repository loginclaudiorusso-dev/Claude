"""1.29: Renovierung – Strategien über mehrere Jahre, Kampagnen-Termine für Einzelzimmer und Jahresplan.

Baut auf renovierung_kern auf (Flure, Varianten, Kosten …). Aus renovierung_kern.py ausgelagert (nur verschoben, keine
Funktionsänderung); dort weiter erreichbar."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import zimmerplan as zp

from .renovierung_kern import (  # baut auf renovierung_kern auf
    ARTEN,
    Auswahl,
    Fenster,
    Flur,
    Variante,
    ZBedarf,
    a_zimmer,
    bestand,
    bester_monat,
    defekte_betten,
    engpass_markieren,
    flur_text_schluessel,
    flure,
    monatsfenster,
    parameter,
    plan,
    schluessel,
    varianten,
    ziel_auswahl,
    zustandsnoten,
)
from .renovierung_kosten import (  # noqa: E402,F401
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

# ---- Strategien über mehrere Jahre (mit Alterung) ------------------------------------------------------

@dataclass
class Strategie:
    schluessel: str
    titel: str
    erklaerung: str
    jahre: list = field(default_factory=list)       # {jahr, text, zimmer, bau, moebel, summe, sperr, a_offen}
    bestand: int = 0
    a_start: int = 0
    zimmer_ids: set = field(default_factory=set)
    zusatz: str = ""

    @property
    def zimmer(self) -> int:
        return len(self.zimmer_ids)

    def summe(self, feld: str) -> float:
        return sum(j[feld] for j in self.jahre)

    @property
    def anteil(self) -> float:
        return 100 * self.zimmer / self.bestand if self.bestand else 0.0

    @property
    def je_jahr(self) -> float:
        return self.zimmer / len(self.jahre) if self.jahre else 0.0

    @property
    def zyklus(self) -> float | None:
        return round(self.bestand / self.je_jahr, 1) if self.je_jahr else None

    @property
    def a_ende(self) -> int:
        return self.jahre[-1]["a_offen"] if self.jahre else self.a_start

    @property
    def deutung(self) -> str:
        n = len(self.jahre)
        teile = [f"Klasse-A-Zimmer: heute {self.a_start}, nach {n} Jahren {self.a_ende}."]
        if self.zimmer:
            teile.append(f"{self.zimmer} von {self.bestand} Zimmern ({self.anteil:.0f} %) erneuert für "
                         f"{tsd(self.summe('summe'))} (Bau {tsd(self.summe('bau'))}, Möbel {tsd(self.summe('moebel'))}).")
            if self.zyklus:
                teile.append(f"Bei diesem Tempo ist jedes Zimmer etwa alle {self.zyklus:g} Jahre dran.")
        else:
            teile.append("Es wird nichts erneuert.")
        if self.zusatz:
            teile.append(self.zusatz)
        return " ".join(teile)


def _altern(fl: list[Flur], heute: date, p: dict, offen: dict, noten: dict) -> list[Flur]:
    """Bedarf neu einstufen, wie er in ``heute`` wäre (Zimmer werden älter, offene Mängel bleiben)."""
    from types import SimpleNamespace

    stand = SimpleNamespace(zimmer=[z for f in fl for z in f.zimmer], lage=SimpleNamespace(unbewohnbar=set()))
    return flure(stand, heute, p, offen, noten)


def strategien(fl: list[Flur], p: dict, start_jahr: int, heute: date, jahre: int = 5, reserve: set | None = None,
               kern_text: str = "") -> list[Strategie]:
    """Nichtstun · Empfohlen · Kürzung −20 % · Beschleunigt (+50 %) · Kernbestand. Jahr für Jahr: Bedarf altert,
    erneuerte Zimmer zählen als frisch (kein Bau-Bedarf mehr, kein A)."""
    from belegung import maengel as mg

    offen = mg.offen_je_zimmer()
    noten = zustandsnoten()
    bestand_ = bestand(fl)
    a0 = a_zimmer(fl)

    def lauf(schl, titel, erkl, faktor: float | None, res: set | None = None, zusatz: str = "") -> Strategie:
        s = Strategie(schl, titel, erkl, bestand=bestand_ - sum(len(f.zimmer) for f in fl if f.schluessel in (res or set())),
                      a_start=a0, zusatz=zusatz)
        for _i, j in enumerate(range(start_jahr, start_jahr + jahre)):
            stichtag = date(j, 1, 1) if j > heute.year else heute
            fl_j = _altern(fl, stichtag, p, offen, noten)
            for f in fl_j:                                   # erneuerte Zimmer: frisch
                for zid in list(f.bedarfe):
                    if zid in s.zimmer_ids:
                        f.bedarfe[zid] = ZBedarf(frisch=True)
            massnahmen = []
            if faktor is not None:
                pj = dict(p)
                if pj.get("modus") == "ziel":
                    pj["ziel_zimmer"] = round(int(p.get("ziel_zimmer") or 0) * faktor)
                vs, e = varianten(fl_j, pj, j, schon=set(s.zimmer_ids), reserve=res, budget_faktor=faktor)
                massnahmen = next((v.massnahmen for v in vs if v.schluessel == e), [])
            neu_ids = {z.id for m in massnahmen for z in m.zimmer} - s.zimmer_ids
            s.zimmer_ids |= neu_ids
            k = Kosten(0, j, herkunft_bau="", herkunft_moebel="")
            for m in massnahmen:
                k = k.plus(m.kosten)
            a_offen = sum(1 for f in fl_j for zid, b in f.bedarfe.items() if b.a and zid not in s.zimmer_ids)
            s.jahre.append({"jahr": j, "text": "; ".join(m.text for m in massnahmen) or "nichts", "zimmer": len(neu_ids),
                            "bau": k.instandhaltung, "moebel": k.investition, "summe": k.summe,
                            "sperr": Variante("", "", "", massnahmen).sperr_zimmermonate(p), "a_offen": a_offen})
        return s

    erg = [lauf("nichts", "Nichtstun", "Keine Renovierung – zeigt, wie der Bedarf mit dem Alter der Zimmer wächst.", None),
           lauf("empfohlen", "Empfohlen", "Jedes Jahr die rechnerisch beste Variante mit dem eingestellten Budget bzw. Ziel.", 1.0),
           lauf("kuerzung", "Kürzung −20 %", "Wie „Empfohlen“, aber mit 20 % weniger Budget bzw. Zimmerziel.", .8),
           lauf("schneller", "Beschleunigt +50 %", "Wie „Empfohlen“, aber mit 50 % mehr Budget bzw. Zimmerziel.", 1.5)]
    if reserve:
        erg.append(lauf("kern", "Kernbestand", "Wie „Empfohlen“, aber Reserve-Etagen werden nicht renoviert, nur in "
                        "Betrieb gehalten.", 1.0, reserve, kern_text))
    return erg


# ---- Termine für Einzelzimmer: Kampagnen ----------------------------------------------------------------

def _frei_ab(stand: zp.Planstand, z, d: date, tage: int) -> bool:
    return stand.lage.freie_betten(z.id, d, d + timedelta(days=tage - 1)) >= z.betten


def kampagnen(stand: zp.Planstand, zimmer: list, ab: date, bis: date, tage: int, gesperrt: list,
              hoechstens: int = 2) -> tuple[list[tuple], list]:
    """Einzelzimmer gebündelt: je Kampagne der Wochenbeginn, an dem die meisten Zimmer gleichzeitig leer sind.
    Höchstens ``hoechstens`` Kampagnen; was übrig bleibt, einzeln im ersten Leerstand. → ([(Zimmer, von, bis)], ohne)."""
    offen = list(zimmer)
    erg = []
    starts = []
    d = ab + timedelta(days=(7 - ab.weekday()) % 7)
    while d + timedelta(days=tage - 1) <= bis:
        if d.month not in gesperrt:
            starts.append(d)
        d += timedelta(days=7)
    for _k in range(hoechstens):
        if not offen or not starts:
            break
        best = max(starts, key=lambda s: (sum(1 for z in offen if _frei_ab(stand, z, s, tage)), -s.toordinal()))
        drin = [z for z in offen if _frei_ab(stand, z, best, tage)]
        if not drin:
            break
        erg += [(z, best, best + timedelta(days=tage - 1)) for z in drin]
        offen = [z for z in offen if z not in drin]
    ohne = []
    for z in offen:
        d = ab
        while d + timedelta(days=tage - 1) <= bis and not (d.month not in gesperrt and _frei_ab(stand, z, d, tage)):
            d += timedelta(days=1)
        if d + timedelta(days=tage - 1) <= bis:
            erg.append((z, d, d + timedelta(days=tage - 1)))
        else:
            ohne.append(z)
    return erg, ohne


@dataclass
class Vorschlag:
    flur: Flur
    fenster: Fenster | None
    art: str = "etage"
    teile: list = field(default_factory=list)       # Einzelzimmer: (Zimmer, von, bis)
    ohne_fenster: list = field(default_factory=list)


def vorschlaege_variante(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict, prognose: dict | None,
                         v: Variante | None, kap: float | None = None) -> list[Vorschlag]:
    """Etagen: bester Monat. Einzelzimmer: Kampagnen je Haus und Art, frühestens nach Bestellung + Möbel-Lieferzeit."""
    if v is None:
        return []
    etagen = [m.flur for m in v.massnahmen if m.art == "etage"]
    erg = vorschlaege(stand, fl, jahr, heute, p, prognose, Auswahl("", etagen, 0, Kosten(0, jahr)), kap) if etagen else []
    ab = max(date(jahr, 1, 1), heute + timedelta(days=int(p.get("lieferzeit_tage") or 28) + 14))
    je_haus: dict[tuple, list] = {}
    for m in v.massnahmen:
        if m.art != "etage":
            je_haus.setdefault((m.flur.haus, m.art), []).append(m)
    for (_haus, art), ms in je_haus.items():
        tage = int(p.get("zimmer_tage") or 14) if art == "zimmer" else int(p.get("moebel_tage") or 3)
        alle = [z for m in ms for z in m.zimmer]
        teile, ohne = kampagnen(stand, alle, ab, date(jahr, 12, 31), tage, p.get("gesperrt") or [])
        nach_flur = {z.id: m.flur for m in ms for z in m.zimmer}
        for m in ms:
            vs = Vorschlag(m.flur, None, art, [t for t in teile if nach_flur[t[0].id] is m.flur],
                           [z for z in ohne if nach_flur[z.id] is m.flur])
            erg.append(vs)
    return erg


def vorschlaege(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict | None = None,
                prognose: dict | None = None, auswahl: Auswahl | None = None, kap: float | None = None) -> list[Vorschlag]:
    """Für die Etagen der Ziel-Auswahl (ohne schon vorgemerkte) je den besten Monat – keine zwei Baustellen im
    selben Monat (die Ausweichzimmer würden doppelt gezählt)."""
    p = p or parameter()
    schon = {e["flur"] for e in plan() if e["start"][:4] == str(jahr) and e["art"] == "etage"}
    belegt_monate = {date.fromisoformat(e["start"]).month for e in plan() if e["start"][:4] == str(jahr) and e["art"] == "etage"}
    auswahl = auswahl or (ziel_auswahl(fl, p, jahr) or [None])[-1]
    erg = []
    bau = jahresplan(stand, jahr, None, p) if kap else []          # schon vorgemerkte Baustellen senken die Kapazität
    for f in (auswahl.flure if auswahl else []):
        if f.schluessel in schon:
            continue
        fs = [x for x in monatsfenster(stand, f, jahr, p, prognose) if x.start.month not in belegt_monate]
        engpass_markieren(fs, f, kap, bau, defekt=defekte_betten(stand, {z.id for z in f.zimmer}))
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
    art: str = "etage"
    teile: list = field(default_factory=list)      # Einzelzimmer: (Zimmer-ID, kurz, von, bis, Betten)
    pruefbar: bool = True

    @property
    def titel(self) -> str:
        return self.text if self.art == "etage" else f"{self.text} – {self.zimmer} Zi. {ARTEN[self.art]}"


def jahresplan(stand: zp.Planstand, jahr: int, vorschl: list[Vorschlag] | None = None,
               p: dict | None = None) -> list[PlanZeile]:
    """Zeilen für das Gantt: vorgemerkte Etagen (fest) und Vorschläge (gestrichelt)."""
    p = p or parameter()
    nach_schl: dict[str, list] = {}
    for z in stand.zimmer:
        nach_schl.setdefault(schluessel(z.haus, z.etage, ""), []).append(z)
    erg = []
    nach_id = {z.id: z for z in stand.zimmer}
    gruppen: dict[tuple, list] = {}
    for e in plan():
        s, en = date.fromisoformat(e["start"]), date.fromisoformat(e["ende"])
        if not (s.year <= jahr <= en.year):
            continue
        zs = nach_schl.get(e["flur"], [])
        if e["art"] != "etage":
            gruppen.setdefault((e["flur"], e["art"], "vorgemerkt"), []).extend(
                (zid, nach_id[zid].kurz, s, en, nach_id[zid].betten) for zid in e["zimmer"] if zid in nach_id)
            continue
        erg.append(PlanZeile(e["flur"], flur_text_schluessel(e["flur"]), len(zs), sum(z.betten for z in zs), s, en,
                             s - timedelta(days=int(p["vorlauf_tage"])), "vorgemerkt",
                             kosten(p, e["flur"].split("|")[0], len(zs), s.year)))
    for v in vorschl or []:
        if v.art != "etage":
            if v.teile:
                gruppen.setdefault((v.flur.schluessel, v.art, "vorschlag"), []).extend(
                    (z.id, z.kurz, a, b, z.betten) for z, a, b in v.teile)
            continue
        if v.fenster is None:
            continue
        fe, f = v.fenster, v.flur
        erg.append(PlanZeile(f.schluessel, f.text, len(f.zimmer), f.betten, fe.start, fe.ende, fe.stopp_ab, "vorschlag",
                             kosten(p, f.haus, len(f.zimmer), jahr), fe.gleichwertig, len(fe.ohne_ausweich),
                             fe.engpass, pruefbar=fe.pruefbar))
    for (schl, art, status), teile in gruppen.items():
        n = len(teile)
        start, ende = min(t[2] for t in teile), max(t[3] for t in teile)
        erg.append(PlanZeile(schl, flur_text_schluessel(schl), n, sum(t[4] for t in teile), start, ende, start, status,
                             kosten(p, schl.split("|")[0], n, start.year, art, len(nach_schl.get(schl, [])) or n),
                             art=art, teile=sorted(teile, key=lambda t: t[2])))
    return sorted(erg, key=lambda z: (z.art != "etage", z.start, z.text))


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
    kopf = ["Maßnahme", "Status", "Belegungsstopp ab", "Bau von", "Bau bis", "Zimmer", "Betten", "Bau + Neben (€)",
            "Möbel + Aufbau (€)", "Gesamt (€)", "netto (€)"]
    ws.append(kopf)
    for c in ws[4]:
        c.font = Font(bold=True)
    for z in zeilen:
        ws.append([z.titel + (": " + ", ".join(t[1] for t in z.teile) if z.teile else ""), z.status,
                   z.stopp_ab if z.art == "etage" else None, z.start, z.ende, z.zimmer, z.betten, round(z.kosten.instandhaltung),
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


def excel_speichern(stand: zp.Planstand, jahr: int) -> tuple[str, object]:

    from . import export_ziel as ez

    name = f"Renovierungsplan_{jahr}.xlsx"
    pfad = ez.speichern(name, lambda p: excel(stand, jahr, p), "Exporte")
    return f"Renovierungsplan gespeichert{ez.hinweis(pfad, name, 'Exporte')}", pfad
