"""Maßnahmen-Prognose (0.50): Teilnehmende je Kurs und Tag aus dem Maßnahmen-Pivot, Internatsanteil aus den
Anreiselisten, Prognose = gebuchter Bestand + erwartete neue Kurse. Rein, ohne NiceGUI.

**Datenschutz**: Der Pivot enthält Namen. Eingelesen werden nur die Maßnahme-Zeilen (Kurs, z. B. „GS VW 2506“) mit der
Teilnehmerzahl je Tag – Namen werden weder gespeichert noch protokolliert. Aus den Anreiselisten (Word/PDF) bleibt je Kurs
nur: Teilnehmende, davon Pendler (P), davon mit Kostenzusage (K).

**Modell**
* **Ist** bis zum Stichtag, danach **gebucht** (laut Pivot, bis zum geplanten Ende).
* **Erwartete neue Kurse**: Jede Maßnahmenart startet in festem Rhythmus (meist Januar/Juni). Für jeden Kurs der letzten
  drei Jahre wird derselbe Kurs ein, zwei bzw. drei Jahre später mit demselben Verlauf angenommen; Mittelwert der Jahre,
  Spanne = kleinstes bzw. größtes Jahr (kam er nur in einem Teil der Jahre vor, zählt er anteilig). Ist der Kurs schon gebucht (gleiche Art, Start ±45 Tage), zählt er nicht doppelt.
* **Geplante Plätze** (eigene Eingabe je Art und Monat) ersetzen die Schätzung für diesen Start.
* **Internat** = Teilnehmende × Internatsanteil der Art (aus den Anreiselisten; sonst Anteil über alle, sonst 100 %).
* **Lücken** im Pivot (z. B. ein fehlender Monat) werden je Kurs mit dem letzten bekannten Wert überbrückt.
"""

from __future__ import annotations

import re
import statistics as stt
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from belegung import speicher

DATEI = f"{speicher.IMPORT_ORDNER}/modern_massnahmen.json"
GRUPPEN = {"lang": "Hauptmaßnahmen", "vorbereitung": "RVL / RVT", "ibtz": "IBTZ", "uebrige": "Übrige (Assessment, EMR, Info …)",
           "ohne": "ohne Zimmer"}
_KURS = re.compile(r"^[A-Z]{2}\s+\S")
_TAG = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
LANG_TAGE = 300                    # Teilnahmedauer (Median) ab der eine Art als Hauptmaßnahme gilt
VORJAHRE = 3                       # erwartete Kurse: Mittel aus bis zu drei Vorjahren


# ---- Speichern ------------------------------------------------------------------------------------------

def _roh() -> dict:
    return speicher.lesen(DATEI, {})


def _schreiben(roh: dict) -> None:
    speicher.schreiben(DATEI, roh)


def _rle(werte: list[int]) -> list[list[int]]:
    erg: list[list[int]] = []
    for w in werte:
        if erg and erg[-1][0] == w:
            erg[-1][1] += 1
        else:
            erg.append([w, 1])
    return erg


def _unrle(rle: list) -> list[int]:
    return [w for w, n in rle for _ in range(n)]


def familie(kurs: str) -> str:
    """„GS VW 2506“ → „GS VW“ (Teile mit Ziffern fallen weg)."""
    return " ".join(x for x in kurs.split() if not re.search(r"\d", x)) or kurs


# ---- Pivot einlesen -------------------------------------------------------------------------------------

@dataclass
class PivotErgebnis:
    von: date
    bis: date
    kurse: dict                    # Kurs → {"von": ISO, "werte": RLE, "dauer": Median-Tage je Person}
    personen: int
    luecken: list                  # [(von, bis)] überbrückt

    @property
    def text(self) -> str:
        t = f"{len(self.kurse)} Kurse, {self.personen} Teilnahmen, {self.von:%d.%m.%Y} – {self.bis:%d.%m.%Y}"
        if self.luecken:
            t += " · überbrückt: " + ", ".join(f"{a:%d.%m.%y}–{b:%d.%m.%y}" for a, b in self.luecken)
        return t


def pivot_aus_zeilen(zeilen) -> PivotErgebnis:
    """Zeilen (Tupel) des Pivots: Kopfzeile mit „Zeilenbeschriftungen“ und Tagesdaten, darunter Personen und ihre
    Maßnahme-Zeilen. Namen werden übersprungen."""
    it = iter(zeilen)
    kopf = None
    for z in it:
        if z and isinstance(z[0], str) and z[0].strip().lower() == "zeilenbeschriftungen":
            kopf = z
            break
    if kopf is None:
        raise ValueError("Kein Maßnahmen-Pivot erkannt (Zeile „Zeilenbeschriftungen“ mit Tagesdaten fehlt).")
    spalten = [(i, datetime.strptime(v.strip(), "%d.%m.%Y").date()) for i, v in enumerate(kopf)
               if isinstance(v, str) and _TAG.match(v.strip())]
    spalten += [(i, v.date() if isinstance(v, datetime) else v) for i, v in enumerate(kopf)
                if isinstance(v, (datetime, date)) and i]
    spalten.sort(key=lambda x: x[1])
    if not spalten:
        raise ValueError("Im Maßnahmen-Pivot fehlen die Tagesspalten.")
    tage = [d for _i, d in spalten]
    von, bis = tage[0], tage[-1]
    n = (bis - von).days + 1
    pos = [(i, (d - von).days) for i, d in spalten]
    summen: dict[str, list[float]] = {}
    dauer: dict[str, list[int]] = {}
    personen = 0
    for z in it:
        if not z or not isinstance(z[0], str):
            continue
        t = z[0].strip()
        if t.lower().startswith("gesamt"):
            break
        if not _KURS.match(t):
            continue                                   # Personenzeile – nichts davon wird gelesen
        reihe = summen.setdefault(t, [0.0] * n)
        erste = letzte = None
        for i, k in pos:
            w = z[i] if i < len(z) else None
            if w:
                reihe[k] += float(w)
                erste = k if erste is None else erste
                letzte = k
        if erste is not None:
            personen += 1
            dauer.setdefault(t, []).append(letzte - erste + 1)
    # Lücken (Tage ohne Spalte) je Kurs mit dem letzten bekannten Wert füllen
    bekannt = set(k for _i, k in pos)
    luecken, start = [], None
    for k in range(n):
        if k not in bekannt and start is None:
            start = k
        if k in bekannt and start is not None:
            luecken.append((von + timedelta(days=start), von + timedelta(days=k - 1)))
            start = None
    for reihe in summen.values():
        for k in range(1, n):
            if k not in bekannt:
                reihe[k] = reihe[k - 1]
    kurse = {}
    for kurs, reihe in summen.items():
        nz = [k for k, w in enumerate(reihe) if w]
        if not nz:
            continue
        a, e = nz[0], nz[-1]
        kurse[kurs] = {"von": (von + timedelta(days=a)).isoformat(), "werte": _rle([round(w) for w in reihe[a:e + 1]]),
                       "dauer": int(stt.median(dauer.get(kurs) or [e - a + 1]))}
    return PivotErgebnis(von, bis, kurse, personen, luecken)


def pivot_lesen(pfad) -> PivotErgebnis:
    import openpyxl

    wb = openpyxl.load_workbook(pfad, read_only=True, data_only=True)
    try:
        return pivot_aus_zeilen(wb.worksheets[0].iter_rows(values_only=True))
    finally:
        wb.close()


def pivot_uebernehmen(erg: PivotErgebnis, datei: str) -> str:
    roh = _roh()
    roh["pivot"] = {"datei": datei, "importiert_am": datetime.now().isoformat(timespec="seconds"),
                    "von": erg.von.isoformat(), "bis": erg.bis.isoformat(), "kurse": erg.kurse, "personen": erg.personen,
                    "luecken": [[a.isoformat(), b.isoformat()] for a, b in erg.luecken]}
    _schreiben(roh)
    return f"Maßnahmen-Pivot übernommen: {erg.text}"


def pivot_schritt(erg: PivotErgebnis, datei: str) -> str:
    from .kern import _schritt

    out = []
    _schritt("Maßnahmen-Pivot eingelesen", lambda: out.append(pivot_uebernehmen(erg, datei)), [DATEI])
    return out[0]


# ---- Anreiselisten (Word/PDF) → Pendler/Internat je Kurs ----------------------------------------------

def listen_aus_text(text: str) -> dict[str, dict]:
    """Je Kurs: Teilnehmende, Pendler (P), Kostenzusage (K). Nur Zähler – keine Namen."""
    from . import pdf_anreise_kern as pk

    erg: dict[str, dict] = {}
    kurs = None
    for zeile in text.splitlines():
        if m := pk._MASSNAHME.match(zeile):
            kurs = re.sub(r"\s+", " ", m.group(1)).strip()
            continue
        m = pk._PERSON.match(zeile)
        if not m or kurs is None:
            continue
        kz = pk.kennzeichen(m.group(4).split())
        z = erg.setdefault(kurs, {"tn": 0, "pendler": 0, "zusage": 0})
        z["tn"] += 1
        z["pendler"] += "P" in kz
        z["zusage"] += "K" in kz
    return erg


def listen_lesen(pfad) -> dict[str, dict]:
    from . import pdf_anreise_kern as pk

    erg = listen_aus_text(pk.text_lesen(pfad))
    if not erg:
        raise ValueError("Keine Kurse mit Teilnehmenden erkannt – ist das die Liste „Teilnehmer Beginn“ (Word oder PDF)?")
    return erg


def listen_uebernehmen(kurse: dict[str, dict], datei: str) -> str:
    roh = _roh()
    alt = roh.get("listen") or {"kurse": {}, "dateien": []}
    alt["kurse"].update(kurse)                         # gleicher Kurs aus einer neueren Liste ersetzt den alten Stand
    alt["dateien"] = [d for d in alt.get("dateien", []) if d.get("datei") != datei] + [
        {"datei": datei, "kurse": len(kurse), "importiert_am": datetime.now().isoformat(timespec="seconds")}]
    roh["listen"] = alt
    _schreiben(roh)
    tn = sum(k["tn"] for k in kurse.values())
    pe = sum(k["pendler"] for k in kurse.values())
    return f"{len(kurse)} Kurse, {tn} Teilnehmende, davon {pe} Pendler ({round(100 * pe / tn) if tn else 0} %)"


def listen_schritt(kurse: dict[str, dict], datei: str) -> str:
    from .kern import _schritt

    out = []
    _schritt("Anreiselisten für die Maßnahmen-Prognose", lambda: out.append(listen_uebernehmen(kurse, datei)), [DATEI])
    return out[0]


# ---- Zuordnung und eigene Plätze ------------------------------------------------------------------------

def standard_gruppe(fam: str, dauer: int) -> str:
    f = fam.upper()
    if "VIRTUELL" in f:
        return "ohne"
    if re.search(r"\b(RVL|RVT)\b", f):
        return "vorbereitung"
    if re.search(r"\bIBTZ\b", f):
        return "ibtz"
    return "lang" if dauer >= LANG_TAGE else "uebrige"


def gruppen(daten: dict | None = None) -> dict[str, str]:
    """Art → Gruppe (eigene Zuordnung › Vorschlag aus der Dauer)."""
    roh = daten if daten is not None else _roh()
    eigen = roh.get("gruppen") or {}
    dauer: dict[str, list[int]] = {}
    for k, v in ((roh.get("pivot") or {}).get("kurse") or {}).items():
        dauer.setdefault(familie(k), []).append(int(v.get("dauer") or 0))
    return {f: eigen.get(f) or standard_gruppe(f, int(stt.median(d))) for f, d in dauer.items()}


def zuordnung_schritt(fam: str, gruppe: str) -> str:
    from .kern import _schritt

    def aktion():
        roh = _roh()
        roh.setdefault("gruppen", {})[fam] = gruppe
        _schreiben(roh)
    _schritt(f"Maßnahmen-Gruppe: {fam}", aktion, [DATEI])
    return f"{fam} → {GRUPPEN.get(gruppe, gruppe)}"


def plaetze_schritt(fam: str, monat: str, plaetze: int | None) -> str:
    """Geplante Plätze je Art und Startmonat (JJJJ-MM); None = Eintrag entfernen."""
    from .kern import _schritt

    def aktion():
        roh = _roh()
        liste = [p for p in roh.get("plaetze") or [] if not (p["familie"] == fam and p["monat"] == monat)]
        if plaetze:
            liste.append({"familie": fam, "monat": monat, "plaetze": int(plaetze)})
        roh["plaetze"] = sorted(liste, key=lambda p: (p["monat"], p["familie"]))
        _schreiben(roh)
    _schritt(f"Geplante Plätze {fam} {monat}", aktion, [DATEI])
    return f"{fam} {monat}: {plaetze} Plätze" if plaetze else f"{fam} {monat}: Eintrag entfernt"


# ---- Rechnen --------------------------------------------------------------------------------------------

@dataclass
class Kurs:
    name: str
    familie: str
    start: date
    werte: list[int]               # ab Start, je Tag

    @property
    def ende(self) -> date:
        return self.start + timedelta(days=len(self.werte) - 1)

    @property
    def spitze(self) -> int:
        return max(self.werte) if self.werte else 0

    def am(self, t: date) -> int:
        k = (t - self.start).days
        return self.werte[k] if 0 <= k < len(self.werte) else 0


def kurse(daten: dict | None = None) -> list[Kurs]:
    roh = daten if daten is not None else _roh()
    return [Kurs(k, familie(k), date.fromisoformat(v["von"]), _unrle(v["werte"]))
            for k, v in ((roh.get("pivot") or {}).get("kurse") or {}).items()]


def internat_anteile(daten: dict | None = None) -> tuple[dict[str, float], float | None]:
    """Art → Anteil Internat (1 − Pendler/Teilnehmende) aus den Anreiselisten; dazu der Anteil über alle."""
    roh = daten if daten is not None else _roh()
    je: dict[str, list[int]] = {}
    for k, z in ((roh.get("listen") or {}).get("kurse") or {}).items():
        a = je.setdefault(familie(k), [0, 0])
        a[0] += int(z.get("tn") or 0)
        a[1] += int(z.get("pendler") or 0)
    alle_tn = sum(a for a, _p in je.values())
    gesamt = 1 - sum(p for _a, p in je.values()) / alle_tn if alle_tn else None
    return {f: 1 - p / a for f, (a, p) in je.items() if a >= 5}, gesamt


def _monate(von: date, anzahl: int) -> list[date]:
    erg, j, m = [], von.year, von.month
    for _ in range(anzahl):
        erg.append(date(j, m, 1))
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)
    return erg


def _monatsmittel(fn, monat: date) -> float:
    ende = date(monat.year + (monat.month == 12), monat.month % 12 + 1, 1)
    tage = [monat + timedelta(days=i) for i in range((ende - monat).days)]
    return sum(fn(t) for t in tage) / len(tage)


def _jahr_verschoben(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:                                 # 29.02.
        return d.replace(year=d.year + n, day=28)


@dataclass
class Neu:
    """Ein erwarteter neuer Kurs: Start, Verlauf je Tag (Mittel), kleiner/größer (Spanne), Herkunft."""
    familie: str
    start: date
    mittel: list[float]
    klein: list[float]
    gross: list[float]
    herkunft: str = "Vorjahre"     # Vorjahre | geplant

    def am(self, t: date, welche: str = "mittel") -> float:
        k = (t - self.start).days
        w = getattr(self, welche)
        return w[k] if 0 <= k < len(w) else 0.0

    @property
    def spitze(self) -> float:
        return max(self.mittel) if self.mittel else 0.0


def erwartete_kurse(ks: list[Kurs], stichtag: date, bis: date, plaetze: list | None = None,
                    daten_ab: date | None = None, familien: set | None = None) -> list[Neu]:
    """Kurse der letzten zwei Jahre ein bzw. zwei Jahre später wiederholen (Mittel aus beiden Jahren); schon gebuchte
    Kurse (gleiche Art, Start ±45 Tage) ersetzen die Schätzung. Kurse, die am Datenbeginn schon liefen, zählen nicht
    (ihr Start ist unbekannt)."""
    daten_ab = daten_ab or min((k.start for k in ks), default=stichtag)
    gebucht = [k for k in ks if k.start > stichtag]
    erg: list[Neu] = []
    for fam in sorted({k.familie for k in ks} if familien is None else familien):
        # je Jahr (1 = Vorjahr, 2 = vor zwei Jahren) die Kurse der Art, verschoben in die Zukunft
        quellen: dict[int, list[Kurs]] = {j: [] for j in range(1, VORJAHRE + 1)}
        for k in ks:
            if k.familie != fam or k.start <= daten_ab + timedelta(days=30) or k.start > stichtag:
                continue
            for j in quellen:
                if _jahr_verschoben(stichtag, -j) < k.start <= _jahr_verschoben(stichtag, -j + 1):
                    quellen[j].append(k)
        jahre_da = [j for j in quellen if _jahr_verschoben(stichtag, -j) >= daten_ab + timedelta(days=30)] or [1]
        for y in range(0, 6):                             # Zukunftsjahr 0, 1, 2 … relativ zum Stichtag
            kand = []
            for j, liste in quellen.items():
                for k in liste:
                    s = _jahr_verschoben(k.start, j + y)
                    if stichtag < s <= bis:
                        kand.append((s, j, k))
            kand.sort(key=lambda x: x[0])
            benutzt: set[int] = set()
            for i, (s, j, k) in enumerate(kand):
                if i in benutzt:
                    continue
                benutzt.add(i)
                quelle, js = [k], {j}
                for i2, (s2, j2, k2) in enumerate(kand):         # je weiteres Vorjahr höchstens ein Partner (±45 Tage)
                    if i2 not in benutzt and j2 not in js and abs((s2 - s).days) <= 45:
                        benutzt.add(i2)
                        quelle.append(k2)
                        js.add(j2)
                if any(e.familie == fam and abs((e.start - s).days) <= 45 for e in erg):
                    continue
                if any(g.familie == fam and abs((g.start - s).days) <= 45 for g in gebucht):
                    continue                              # schon gebucht – zählt im Bestand
                laenge = max(len(q.werte) for q in quelle)
                reihen = [[float(q.werte[t]) if t < len(q.werte) else 0.0 for t in range(laenge)] for q in quelle]
                mittel = [sum(r[t] for r in reihen) / len(reihen) for t in range(laenge)]
                gross = [max(r[t] for r in reihen) for t in range(laenge)]
                if len(reihen) >= 2:
                    klein = [min(r[t] for r in reihen) for t in range(laenge)]
                else:
                    klein = [w / 2 for w in reihen[0]]
                # kam der Kurs nur in einem Teil der Vorjahre vor, ist er unsicher: Mittel anteilig, unten bis halb
                anteil = len(reihen) / len(jahre_da)
                if anteil < 1:
                    mittel = [w * max(anteil, .5) for w in mittel]
                    klein = [min(a, b / 2) for a, b in zip(klein, gross)]
                erg.append(Neu(fam, s, mittel, klein, gross))
    for p in plaetze or []:                               # eigene Planung ersetzt die Schätzung dieses Starts
        fam, monat, n = p["familie"], date.fromisoformat(p["monat"] + "-01"), int(p["plaetze"])
        if not (stichtag < monat + timedelta(days=27) and monat <= bis):
            continue
        treffer = [e for e in erg if e.familie == fam and abs((e.start - monat).days) <= 45]
        vorlage = treffer[0] if treffer else next((e for e in erg if e.familie == fam), None)
        if vorlage is None:
            hist = [k for k in ks if k.familie == fam and k.spitze]
            if not hist:
                continue
            k = max(hist, key=lambda x: x.start)
            vorlage = Neu(fam, monat, [float(w) for w in k.werte], [float(w) for w in k.werte], [float(w) for w in k.werte])
        f = n / vorlage.spitze if vorlage.spitze else 1.0
        for t in treffer:
            erg.remove(t)
        erg.append(Neu(fam, max(monat, stichtag + timedelta(days=1)), [w * f for w in vorlage.mittel],
                       [w * f for w in vorlage.mittel], [w * f for w in vorlage.mittel], "geplant"))
    return sorted(erg, key=lambda e: (e.start, e.familie))


@dataclass
class MZeile:
    monat: date
    art: str                       # ist | prognose
    je_gruppe: dict                # Gruppe → Teilnehmende (Ist bzw. gebucht + erwartet)
    gebucht: float
    erwartet: float
    klein: float
    gross: float

    @property
    def summe(self) -> float:
        return sum(self.je_gruppe.values())


@dataclass
class Prognose:
    zeilen: list[MZeile]
    neu: list[Neu]
    stichtag: date
    internat: bool
    anteil_quelle: str
    gruppen: dict
    familien: list = field(default_factory=list)   # Tabelle je Art (Hauptmaßnahmen, Vorbereitung, IBTZ)


def prognose(daten: dict | None, stichtag: date, zurueck: int = 12, vor: int = 24, internat: bool = False) -> Prognose | None:
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    if not ks:
        return None
    gr = gruppen(roh)
    anteile, gesamt = internat_anteile(roh)
    faktor = (lambda fam: anteile.get(fam, gesamt if gesamt is not None else 1.0)) if internat else (lambda fam: 1.0)
    quelle = ("aus den Anreiselisten" if anteile else "Anteil über alle Listen" if gesamt is not None
              else "keine Anreiselisten – 100 % angenommen") if internat else ""
    zeigen = [f for f in gr if gr[f] != "ohne"]
    daten_ab = date.fromisoformat((roh.get("pivot") or {}).get("von") or min(k.start for k in ks).isoformat())
    akt = date(stichtag.year, stichtag.month, 1)
    erster = akt
    for _ in range(zurueck):
        erster = date(erster.year - (erster.month == 1), (erster.month - 2) % 12 + 1, 1)
    monate = _monate(erster, zurueck + vor + 1)
    neu = erwartete_kurse(ks, stichtag, monate[-1] + timedelta(days=31), roh.get("plaetze"), daten_ab, set(zeigen))
    zeilen = []
    for m in monate:
        prog = m >= akt
        je: dict[str, float] = {}
        geb = erw = kl = gr_ = 0.0
        for k in ks:
            if gr.get(k.familie) == "ohne":
                continue
            w = _monatsmittel(lambda t, k=k: k.am(t), m) * faktor(k.familie)
            if w:
                je[gr[k.familie]] = je.get(gr[k.familie], 0.0) + w
                if prog:
                    geb += w
        if prog:
            for e in neu:
                f = faktor(e.familie)
                w = _monatsmittel(lambda t, e=e: e.am(t), m) * f
                if w:
                    je[gr[e.familie]] = je.get(gr[e.familie], 0.0) + w
                    erw += w
                    kl += _monatsmittel(lambda t, e=e: e.am(t, "klein"), m) * f
                    gr_ += _monatsmittel(lambda t, e=e: e.am(t, "gross"), m) * f
        zeilen.append(MZeile(m, "prognose" if prog else "ist", je, geb, erw, kl, gr_))
    tab = familien_tabelle(ks, neu, gr, stichtag, faktor)
    return Prognose(zeilen, neu, stichtag, internat, quelle, gr, tab)


@dataclass
class FZeile:
    familie: str
    gruppe: str
    heute: float
    in6: float
    in12: float
    naechster: date | None
    naechster_wie: str            # gebucht | erwartet | geplant
    kursgroesse: float | None
    verbleib: float | None
    kurse_3j: int


def familien_tabelle(ks: list[Kurs], neu: list[Neu], gr: dict, stichtag: date, faktor) -> list[FZeile]:
    erg = []
    for fam in sorted({k.familie for k in ks}):
        if gr.get(fam) not in ("lang", "vorbereitung", "ibtz"):
            continue
        eigene = [k for k in ks if k.familie == fam]
        n_neu = [e for e in neu if e.familie == fam]

        def wert(t: date) -> float:
            return (sum(k.am(t) for k in eigene) + sum(e.am(t) for e in n_neu)) * faktor(fam)
        kuenftig = sorted([(k.start, "gebucht") for k in eigene if k.start > stichtag]
                          + [(e.start, "geplant" if e.herkunft == "geplant" else "erwartet") for e in n_neu])
        drei = [k for k in eigene if stichtag - timedelta(days=3 * 365) <= k.start <= stichtag]
        verbleib = []
        for k in drei:
            if k.ende < stichtag and len(k.werte) > 90:
                spitze = max(k.werte[:60]) or 0
                if spitze:
                    verbleib.append(k.werte[-31] / spitze if len(k.werte) > 31 else 1.0)
        erg.append(FZeile(fam, gr[fam], wert(stichtag), wert(stichtag + timedelta(days=182)), wert(stichtag + timedelta(days=365)),
                          kuenftig[0][0] if kuenftig else None, kuenftig[0][1] if kuenftig else "",
                          stt.median([k.spitze for k in drei]) if drei else None,
                          stt.median(verbleib) if verbleib else None, len(drei)))
    return sorted(erg, key=lambda z: -z.heute)


@dataclass
class Test:
    jahr: int
    h1: float | None              # mittlere Abweichung in % (Jan–Jun)
    h2: float | None              # (Jul–Dez)
    monate: list                  # (Monat, Ist, Prognose)


def rueckwaertstest(daten: dict | None = None, jahre: list[int] | None = None) -> list[Test]:
    """Wie gut wäre die Prognose gewesen? Stichtag 1. Januar; laufende Kurse mit ihrem Verlauf (vereinfachend: Ist statt
    damals gebucht), neue Kurse wie oben geschätzt. Vergleich der Summe der Gruppen außer „ohne Zimmer“."""
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    if not ks:
        return []
    gr = gruppen(roh)
    zeigen = {f for f in gr if gr[f] != "ohne"}
    daten_ab = date.fromisoformat((roh.get("pivot") or {}).get("von") or min(k.start for k in ks).isoformat())
    daten_bis = date.fromisoformat((roh.get("pivot") or {}).get("bis") or max(k.ende for k in ks).isoformat())
    jahre = jahre or [j for j in range(daten_ab.year + 2, daten_bis.year + 1) if date(j, 12, 31) < date.today()
                      or date(j, 6, 30) < date.today()]
    erg = []
    for j in jahre:
        c = date(j, 1, 1)
        bestand = [k for k in ks if k.start < c and k.familie in zeigen]
        echt_neu = [k for k in ks if c <= k.start < date(j + 1, 1, 1) and k.familie in zeigen]
        neu = erwartete_kurse([k for k in ks if k.start < c], c - timedelta(days=1), date(j, 12, 31), None, daten_ab, zeigen)
        zeilen = []
        for m in _monate(c, 12):
            if m >= date.today().replace(day=1) or m > daten_bis:
                break
            b = sum(_monatsmittel(lambda t, k=k: k.am(t), m) for k in bestand)
            ist = b + sum(_monatsmittel(lambda t, k=k: k.am(t), m) for k in echt_neu)
            prog = b + sum(_monatsmittel(lambda t, e=e: e.am(t), m) for e in neu)
            zeilen.append((m, ist, prog))

        def mittel(zs):
            zs = [(i, p) for _m, i, p in zs if i]
            return sum(100 * (p - i) / i for i, p in zs) / len(zs) if zs else None
        erg.append(Test(j, mittel([z for z in zeilen if z[0].month <= 6]), mittel([z for z in zeilen if z[0].month > 6]), zeilen))
    return erg


def abgleich(daten: dict | None, standort_reihe, monate: int = 18, bis: date | None = None) -> list[tuple[date, float, float]]:
    """Monatsmittel: Teilnehmende laut Maßnahmen-Pivot (alle Arten) gegen den Standort-Pivot. ``standort_reihe``:
    Funktion Tag → Wert (oder None, wenn unbekannt)."""
    ks = kurse(daten)
    if not ks:
        return []
    bis = bis or date.today()
    erster = date(bis.year, bis.month, 1)
    for _ in range(monate):
        erster = date(erster.year - (erster.month == 1), (erster.month - 2) % 12 + 1, 1)
    erg = []
    for m in _monate(erster, monate):
        tn = _monatsmittel(lambda t: sum(k.am(t) for k in ks), m)
        st = _monatsmittel(lambda t: standort_reihe(t) or 0.0, m)
        if tn or st:
            erg.append((m, tn, st))
    return erg


def stand() -> dict:
    """Was ist eingelesen? (für Daten & Import und die Kopfzeile der Ansicht)"""
    roh = _roh()
    pv, li = roh.get("pivot") or {}, roh.get("listen") or {}
    return {"pivot": pv and {k: pv.get(k) for k in ("datei", "importiert_am", "von", "bis", "personen", "luecken")}
            | {"kurse": len(pv.get("kurse") or {})},
            "listen": li and {"kurse": len(li.get("kurse") or {}), "dateien": li.get("dateien") or []},
            "plaetze": roh.get("plaetze") or []}
