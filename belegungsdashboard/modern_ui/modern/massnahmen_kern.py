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

1.29 aufgeteilt (nur verschoben): Einlesen (Pivot, Anreiselisten, Zuordnung) → ``massnahmen_import``,
Neuanmeldungen/Halbjahre/Schätzverfahren → ``massnahmen_neuanmeldungen``. Alle Namen bleiben hier erreichbar.
"""

from __future__ import annotations

import re
import statistics as stt
from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import speicher

DATEI = f"{speicher.IMPORT_ORDNER}/modern_massnahmen.json"
GRUPPEN = {"lang": "Hauptmaßnahmen", "rvl": "RVL", "rvt": "RVT", "ibtz": "IBTZ", "uebrige": "Übrige (Assessment, EMR, Info …)",
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


# ---- Zuordnung und eigene Plätze ------------------------------------------------------------------------

def standard_gruppe(fam: str, dauer: int) -> str:
    f = fam.upper()
    if "VIRTUELL" in f:
        return "ohne"
    if re.search(r"\bRVT\b", f):                  # 1.24: RVL und RVT getrennt (vorher eine Gruppe „RVL / RVT“)
        return "rvt"
    if re.search(r"\bRVL\b", f):
        return "rvl"
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
    erg = {}
    for f, d in dauer.items():
        g = eigen.get(f) or standard_gruppe(f, int(stt.median(d)))
        if g == "vorbereitung":                    # gespeicherte Zuordnung bis 1.23 → RVT, wenn es RVT ist, sonst RVL
            g = "rvt" if re.search(r"\bRVT\b", f.upper()) else "rvl"
        erg[f] = g
    return erg


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


def alle_kurse(daten: dict | None = None) -> list[Kurs]:
    """Alle Kurse des Pivots – auch die als veraltet entfernten (für die Verwaltung)."""
    roh = daten if daten is not None else _roh()
    return [Kurs(k, familie(k), date.fromisoformat(v["von"]), _unrle(v["werte"]))
            for k, v in ((roh.get("pivot") or {}).get("kurse") or {}).items()]


def kurse(daten: dict | None = None) -> list[Kurs]:
    """Kurse für alle Prognosen – 1.06: ohne die als veraltet entfernten Maßnahmen."""
    roh = daten if daten is not None else _roh()
    weg = entfernt(roh)
    return [k for k in alle_kurse(roh) if k.familie not in weg]


# ---- 1.06: veraltete Maßnahmen entfernen (bleiben im Pivot, zählen aber nirgends mehr) ----------------------------

def entfernt(daten: dict | None = None) -> set[str]:
    roh = daten if daten is not None else _roh()
    return {str(x) for x in roh.get("entfernt") or []}


@dataclass
class FamilieInfo:
    familie: str
    kurse: int
    erster: date
    letzter: date                 # letzter Kursstart
    teilnehmende: int             # Neuanmeldungen über alle Kurse
    entfernt: bool


def familien_uebersicht(daten: dict | None = None) -> list[FamilieInfo]:
    """Alle Maßnahmen (Kursfamilien) des Pivots – die am längsten nicht mehr gestarteten zuerst."""
    roh = daten if daten is not None else _roh()
    weg = entfernt(roh)
    je: dict[str, list[Kurs]] = {}
    for k in alle_kurse(roh):
        je.setdefault(k.familie, []).append(k)
    erg = [FamilieInfo(f, len(ks), min(k.start for k in ks), max(k.start for k in ks),
                       sum(neu_im_kurs(k) for k in ks), f in weg) for f, ks in je.items()]
    return sorted(erg, key=lambda x: (x.letzter, x.familie))


def entfernt_schritt(familien: list[str]) -> str:
    """Liste der entfernten Maßnahmen ersetzen – mit Rückgängig. Wiederherstellen = aus der Liste nehmen."""
    from .kern import _schritt

    neu = sorted(set(familien))

    def tun():
        roh = _roh()
        if neu:
            roh["entfernt"] = neu
        else:
            roh.pop("entfernt", None)
        _schreiben(roh)
    _schritt("Veraltete Maßnahmen", tun, [DATEI])
    return (f"{len(neu)} Maßnahme(n) entfernt – sie zählen in keiner Prognose mehr (wiederherstellbar)" if neu
            else "Keine Maßnahme mehr entfernt")


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


# ---- 0.55: Verbleib, Nachbuchung, Kurzkurse ------------------------------------------------------------
# Gebuchte Kurse stehen im Pivot bis zum geplanten Ende voll drin – Abbrüche und Wechsel zu „Pendler“ kennt er noch
# nicht. Wie viele erfahrungsgemäß bleiben, zeigt der Verlauf früherer Kurse derselben Art (Verbleibskurve).
# Neue Kurse aus den Vorjahren bringen ihren echten Verlauf schon mit (dort sind Abbrüche enthalten) – für sie gilt die
# Kurve deshalb nicht (sonst doppelt gezählt).

KURZ_TAGE = 45                     # Arten mit kürzeren Kursen: Saisonsockel statt Einzelkurse
PICKUP_HALB = 21                   # Annahme ohne Messwerte: 21 Tage vor Start ist die Hälfte gebucht
KAPPA = 1.5                        # Gewicht der Vorjahre gegenüber dem Buchungsstand (Poisson-Gamma)
MIN_VORLAUF = 30                   # so viele gemessene Anreisen braucht die gemessene Buchungskurve


def verbleib_kurve(ks: list[Kurs], fam: str, bis: date) -> list[float] | None:
    """R(a): Anteil der Spitze (erste 60 Tage), der am Kurstag a noch da ist – Mittel über die Kurse der Art, nur so
    weit sie vor ``bis`` beobachtet waren (kein Blick in die Zukunft). None bei weniger als zwei Kursen."""
    reihen = []
    for k in ks:
        if k.familie != fam or len(k.werte) < 90 or k.start >= bis:
            continue
        spitze = max(k.werte[:60]) or 0
        n = min(len(k.werte), (bis - k.start).days)
        if spitze and n > 60:
            reihen.append([k.werte[a] / spitze for a in range(n)])
    if len(reihen) < 2:
        return None
    r: list[float] = []
    for a in range(max(len(x) for x in reihen)):
        werte = [x[a] for x in reihen if a < len(x)]
        if len(werte) < 2:
            break
        v = sum(werte) / len(werte)
        r.append(min(v, r[-1]) if a >= 60 and r else v)           # ab Tag 60 nur noch fallend
    return r


def verbleib_faktor(r: list[float] | None, a: int, a0: int) -> float:
    """Erwarteter Anteil am Kurstag ``a``, bezogen auf den Bestand am Kurstag ``a0`` (bedingt: wer bis a0 blieb)."""
    if not r or a <= a0 or a < 60:
        return 1.0
    ra = r[min(a, len(r) - 1)]
    r0 = r[min(a0, len(r) - 1)] if a0 >= 60 else max(r[:60])
    return min(1.0, ra / r0) if r0 else 1.0


def gebucht_am(k: Kurs, t: date, stichtag: date, r: list[float] | None) -> float:
    """Gebuchter Kurs am Tag ``t`` (nach dem Stichtag): Pivot-Wert, höchstens Bestand × Verbleib."""
    w = k.am(t)
    if t <= stichtag or not w or r is None:
        return float(w)
    a, a0 = (t - k.start).days, max(0, (stichtag - k.start).days)
    basis = k.am(stichtag) if k.start <= stichtag else k.spitze
    return float(min(w, basis * verbleib_faktor(r, a, a0)))


def pickup_kurve(vorlaeufe: list[int] | None):
    """p(d): Anteil der späteren Teilnehmenden, der d Tage vor Start schon gebucht ist. Gemessen aus den Anreiselisten
    (wann stand jemand zuerst drin?) – ab ``MIN_VORLAUF`` Anreisen; sonst die Annahme ``PICKUP_HALB``."""
    v = sorted(x for x in (vorlaeufe or []) if x >= 0)
    if len(v) >= MIN_VORLAUF:
        def p(d: float) -> float:
            return 1.0 if d <= 0 else sum(1 for x in v if x >= d) / len(v)
        p.quelle = f"gemessen aus {len(v)} Anreisen"
    else:
        def p(d: float) -> float:
            return 1.0 if d <= 0 else 1.0 / (1.0 + (d / PICKUP_HALB) ** 2)
        p.quelle = f"Annahme: {PICKUP_HALB} Tage vor Start ist die Hälfte gebucht"
    return p


def nachbuchung(gebucht: float, vorjahre: float, p: float, kappa: float = KAPPA, deckel: float | None = None) -> float:
    """Erwartete Endstärke eines teilweise gebuchten Kurses (Poisson-Gamma): gebucht + (1 − p) · (κ·Vorjahre + gebucht)
    / (κ + p). Weit vor Start zählen die Vorjahre, kurz vor Start der Buchungsstand. Nie mehr als ``deckel``."""
    if p >= 1 or vorjahre <= 0:
        return float(gebucht)
    erg = gebucht + (1 - p) * (kappa * vorjahre + gebucht) / (kappa + p)
    return float(min(erg, max(deckel, gebucht)) if deckel is not None else erg)


def vorlauf_messen() -> list[int]:
    """Tage zwischen „zuerst in einer Anreiseliste“ und Anreise, je Person (nur echte Daten, keine Platzhalter)."""
    from belegung import anreiseliste

    gesehen = (speicher.lesen("modern_ui_neu.json", {}) or {}).get("gesehen", {})
    erg = []
    try:
        personen, _listen = anreiseliste.laden()
    except Exception:                         # noqa: BLE001 – ohne Listen: Annahme
        return []
    for p in personen:
        g = gesehen.get(p.schluessel, "")
        if not g or g < "2001" or not p.anreise:
            continue
        try:
            d = (p.anreise - date.fromisoformat(g[:10])).days
        except ValueError:
            continue
        if 0 <= d <= 365:
            erg.append(d)
    return erg


def _ist_kurz(ks: list[Kurs], fam: str) -> bool:
    dauer = [len(k.werte) for k in ks if k.familie == fam]
    return bool(dauer) and stt.median(dauer) < KURZ_TAGE


def _sockel(ks: list[Kurs], fam: str, stichtag: date, bis: date, daten_ab: date) -> Neu | None:
    """Kurzkurse: je Kalendermonat die mittlere Belegung der Vorjahre als Sockel; schon Gebuchtes wird abgezogen."""
    eigene = [k for k in ks if k.familie == fam]
    jahre = [j for j in range(1, VORJAHRE + 1) if _jahr_verschoben(stichtag, -j) >= daten_ab]
    if not eigene or not jahre:
        return None
    tage = [stichtag + timedelta(days=i) for i in range(1, (bis - stichtag).days + 1)]
    akt = date(stichtag.year, stichtag.month, 1)
    cache: dict[tuple, float] = {}

    def vorjahr(monat: int, j: int) -> float:
        """Monatsmittel im j-letzten vollständig vergangenen Monat dieses Kalendermonats (nur vor dem Stichtag)."""
        if (monat, j) not in cache:
            jahr = akt.year - (1 if monat >= akt.month else 0) - (j - 1)
            cache[(monat, j)] = _monatsmittel(lambda x: sum(k.am(x) for k in eigene if k.start <= stichtag),
                                              date(jahr, monat, 1))
        return cache[(monat, j)]

    mittel, klein, gross = [], [], []
    for t in tage:
        je = [vorjahr(t.month, j) for j in jahre]
        geb = sum(k.am(t) for k in eigene)                # schon gebucht bzw. laufend
        mittel.append(max(0.0, sum(je) / len(je) - geb))
        klein.append(max(0.0, min(je) - geb))
        gross.append(max(0.0, max(je) - geb))
    if not any(mittel):
        return None
    return Neu(fam, tage[0], mittel, klein, gross, "Sockel")


def erwartete_kurse(ks: list[Kurs], stichtag: date, bis: date, plaetze: list | None = None,
                    daten_ab: date | None = None, familien: set | None = None, pickup=None) -> list[Neu]:
    """Kurse der letzten zwei Jahre ein bzw. zwei Jahre später wiederholen (Mittel aus beiden Jahren); schon gebuchte
    Kurse (gleiche Art, Start ±45 Tage) ersetzen die Schätzung. Kurse, die am Datenbeginn schon liefen, zählen nicht
    (ihr Start ist unbekannt)."""
    daten_ab = daten_ab or min((k.start for k in ks), default=stichtag)
    gebucht = [k for k in ks if k.start > stichtag]
    erg: list[Neu] = []
    pickup = pickup or pickup_kurve(None)
    for fam in sorted({k.familie for k in ks} if familien is None else familien):
        if _ist_kurz(ks, fam):                            # 0.55: Kurzkurse als Saisonsockel (kein ±45-Tage-Raster)
            if (s := _sockel(ks, fam, stichtag, bis, daten_ab)) is not None:
                erg.append(s)
            continue
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
                g = next((g for g in gebucht if g.familie == fam and abs((g.start - s).days) <= 45), None)
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
                if g is not None:
                    # 0.55: schon (teil-)gebucht – der Bestand zählt im Pivot; dazu kommt, was erfahrungsgemäß noch
                    # nachgebucht wird (statt die Schätzung ganz wegzulassen: „Buchungsloch“)
                    sp = max(mittel) or 0.0
                    if not sp:
                        continue
                    ende = nachbuchung(g.spitze, sp, pickup((g.start - stichtag).days), deckel=max(gross))
                    rest = (ende - g.spitze) / sp
                    if rest * sp < 0.5:
                        continue
                    erg.append(Neu(fam, g.start, [w * rest for w in mittel], [0.0] * laenge,
                                   [w * rest * 1.5 for w in mittel], "Nachbuchung"))
                    continue
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
    nachbuchung_quelle: str = ""                   # 0.55: woher die Buchungskurve stammt (gemessen / Annahme)
    mit_verbleib: int = 0                          # 0.55: Arten, für die eine Verbleibskurve vorliegt


def _verlauf_fn(ks: list[Kurs], stichtag: date, verbleib: bool = True):
    """Tag → Wert je gebuchtem Kurs (mit Verbleibskurve der Art) und Zahl der Arten mit Kurve."""
    kurven = {f: verbleib_kurve(ks, f, stichtag) for f in {k.familie for k in ks}} if verbleib else {}

    def am(k: Kurs, t: date) -> float:
        return gebucht_am(k, t, stichtag, kurven.get(k.familie))
    return am, sum(1 for r in kurven.values() if r)


def prognose(daten: dict | None, stichtag: date, zurueck: int = 12, vor: int = 24, internat: bool = False,
             familien: set | None = None, vorlauf: list[int] | None = None) -> Prognose | None:
    """``familien``: nur diese Maßnahmenarten (None = alle außer „ohne Zimmer“)."""
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    if not ks:
        return None
    gr = gruppen(roh)
    anteile, gesamt = internat_anteile(roh)
    faktor = (lambda fam: anteile.get(fam, gesamt if gesamt is not None else 1.0)) if internat else (lambda fam: 1.0)
    quelle = ("aus den Anreiselisten" if anteile else "Anteil über alle Listen" if gesamt is not None
              else "keine Anreiselisten – 100 % angenommen") if internat else ""
    if familien:
        ks = [k for k in ks if k.familie in familien]
        gr = {f: ("uebrige" if g == "ohne" else g) for f, g in gr.items()}        # ausdrücklich gewählt = zählt
        if not ks:
            return None
    zeigen = [f for f in gr if gr[f] != "ohne" and (not familien or f in familien)]
    daten_ab = date.fromisoformat((roh.get("pivot") or {}).get("von") or min(k.start for k in ks).isoformat())
    akt = date(stichtag.year, stichtag.month, 1)
    erster = akt
    for _ in range(zurueck):
        erster = date(erster.year - (erster.month == 1), (erster.month - 2) % 12 + 1, 1)
    monate = _monate(erster, zurueck + vor + 1)
    pk = pickup_kurve(vorlauf)
    neu = erwartete_kurse(ks, stichtag, monate[-1] + timedelta(days=31), roh.get("plaetze"), daten_ab, set(zeigen), pk)
    am, n_kurven = _verlauf_fn(ks, stichtag)
    zeilen = []
    for m in monate:
        prog = m >= akt
        je: dict[str, float] = {}
        geb = erw = kl = gr_ = 0.0
        for k in ks:
            if gr.get(k.familie) == "ohne":
                continue
            w = _monatsmittel(lambda t, k=k: am(k, t), m) * faktor(k.familie)
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
    tab = familien_tabelle(ks, neu, gr, stichtag, faktor, bool(familien), am)
    return Prognose(zeilen, neu, stichtag, internat, quelle, gr, tab, pk.quelle, n_kurven)


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


def familien_tabelle(ks: list[Kurs], neu: list[Neu], gr: dict, stichtag: date, faktor, alle: bool = False,
                     am=None) -> list[FZeile]:
    am = am or (lambda k, t: k.am(t))
    erg = []
    for fam in sorted({k.familie for k in ks}):
        if not alle and gr.get(fam) not in ("lang", "rvl", "rvt", "ibtz"):
            continue
        eigene = [k for k in ks if k.familie == fam]
        n_neu = [e for e in neu if e.familie == fam]

        def wert(t: date) -> float:
            return (sum(am(k, t) for k in eigene) + sum(e.am(t) for e in n_neu)) * faktor(fam)  # noqa: B023 – im selben Durchlauf aufgerufen
        kuenftig = sorted([(k.start, "gebucht") for k in eigene if k.start > stichtag]
                          + [(e.start, "geplant" if e.herkunft == "geplant" else "erwartet") for e in n_neu
                             if e.herkunft != "Nachbuchung"])
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


def rueckwaertstest(daten: dict | None = None, jahre: list[int] | None = None, verbleib: bool = True) -> list[Test]:
    """Wie gut wäre die Prognose gewesen? Stichtag 1. Januar, **nur mit dem Wissen von damals** (0.55): Laufende Kurse
    gehen mit ihrem Bestand am Stichtag ein und werden mit der damals bekannten Verbleibskurve fortgeschrieben (nicht mit
    ihrem tatsächlichen Verlauf); alle späteren Kurse werden geschätzt, als wäre noch keiner gebucht gewesen (eher
    strenger als die Wirklichkeit). ``verbleib=False``: ohne Verbleibskurve (Bestand bleibt bis Kursende) – zum
    Vergleich. Summe der Gruppen außer „ohne Zimmer“."""
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
        vorher = [k for k in ks if k.start < c]
        st = c - timedelta(days=1)
        neu = erwartete_kurse(vorher, st, date(j, 12, 31), None, daten_ab, zeigen)
        kurven = {f: verbleib_kurve(vorher, f, st) for f in {k.familie for k in bestand}} if verbleib else {}

        def damals(k: Kurs, t: date) -> float:
            """Bestand am Stichtag × Verbleib – bis zum (damals geplanten) Kursende; der spätere Verlauf ist unbekannt."""
            if t <= st or not k.am(t):  # noqa: B023 – im selben Durchlauf aufgerufen
                return float(k.am(t))
            a, a0 = (t - k.start).days, (st - k.start).days  # noqa: B023 – im selben Durchlauf aufgerufen
            return float(k.am(st)) * verbleib_faktor(kurven.get(k.familie), a, a0)  # noqa: B023 – im selben Durchlauf aufgerufen

        zeilen = []
        for m in _monate(c, 12):
            if m >= date.today().replace(day=1) or m > daten_bis:
                break
            b_ist = sum(_monatsmittel(lambda t, k=k: k.am(t), m) for k in bestand)
            b = sum(_monatsmittel(lambda t, k=k: damals(k, t), m) for k in bestand)
            ist = b_ist + sum(_monatsmittel(lambda t, k=k: k.am(t), m) for k in echt_neu)
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


# ---- Auswahl und Vergleich (0.52) ------------------------------------------------------------------------

def familien_liste(daten: dict | None = None, stichtag: date | None = None) -> list[tuple[str, str, float]]:
    """(Art, Gruppe, Teilnehmertage der letzten 12 Monate) – für die Auswahl, größte zuerst."""
    roh = daten if daten is not None else _roh()
    stichtag = stichtag or date.today()
    gr = gruppen(roh)
    tage: dict[str, float] = {}
    for k in kurse(roh):
        a = max(k.start, stichtag - timedelta(days=365))
        e = min(k.ende, stichtag)
        if a <= e:
            tage[k.familie] = tage.get(k.familie, 0.0) + sum(k.werte[(a - k.start).days:(e - k.start).days + 1])
        else:
            tage.setdefault(k.familie, 0.0)
    return sorted(((f, gr.get(f, "uebrige"), t) for f, t in tage.items()), key=lambda x: -x[2])


@dataclass
class VZeile:
    """Eine Maßnahmenart im Vergleich – Kennzahlen für die Leitung (keine Wirtschaftlichkeit, dafür fehlen Erlöse)."""
    familie: str
    gruppe: str
    tage_12m: float               # Teilnehmertage der letzten 12 Monate
    tage_vorjahr: float           # die 12 Monate davor
    starts_jahr: float            # Kursstarts je Jahr (Mittel der letzten 3 Jahre)
    groesse: float | None         # Kursgröße (Median letzte 3 Jahre)
    groesse_vorher: float | None  # Kursgröße (Median der 3 Jahre davor)
    verbleib: float | None
    internat: float | None
    heute: float
    in12: float
    in24: float

    @property
    def trend(self) -> float | None:
        return (self.tage_12m / self.tage_vorjahr - 1) if self.tage_vorjahr else None


def vergleich(daten: dict | None, stichtag: date, familien: list[str], internat: bool = False,
              vorlauf: list[int] | None = None) -> list[VZeile]:
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    gr = gruppen(roh)
    anteile, gesamt = internat_anteile(roh)
    erg = []
    for fam in familien:
        eigene = [k for k in ks if k.familie == fam]
        if not eigene:
            continue

        def tage(von: date, bis: date, eigene=eigene) -> float:
            s = 0.0
            for k in eigene:
                a, e = max(k.start, von), min(k.ende, bis)
                if a <= e:
                    s += sum(k.werte[(a - k.start).days:(e - k.start).days + 1])
            return s
        j3 = [k for k in eigene if stichtag - timedelta(days=3 * 365) <= k.start <= stichtag]
        j6 = [k for k in eigene if stichtag - timedelta(days=6 * 365) <= k.start < stichtag - timedelta(days=3 * 365)]
        verbleib = [k.werte[-31] / max(k.werte[:60]) for k in j3
                    if k.ende < stichtag and len(k.werte) > 90 and max(k.werte[:60])]
        einzel = prognose(roh, stichtag, 0, 24, internat, {fam}, vorlauf)
        werte = [z.summe for z in einzel.zeilen] if einzel else [0.0]
        erg.append(VZeile(fam, gr.get(fam, "uebrige"), tage(stichtag - timedelta(days=365), stichtag),
                          tage(stichtag - timedelta(days=730), stichtag - timedelta(days=366)), len(j3) / 3,
                          stt.median([k.spitze for k in j3]) if j3 else None,
                          stt.median([k.spitze for k in j6]) if j6 else None,
                          stt.median(verbleib) if verbleib else None, anteile.get(fam, gesamt),
                          werte[0], werte[min(12, len(werte) - 1)], werte[min(24, len(werte) - 1)]))
    return erg


def je_familie(daten: dict | None, stichtag: date, familien: list[str], zurueck: int, vor: int, internat: bool,
               vorlauf: list[int] | None = None) -> dict:
    """Art → Prognose (für die Vergleichslinien)."""
    roh = daten if daten is not None else _roh()
    return {f: p for f in familien if (p := prognose(roh, stichtag, zurueck, vor, internat, {f}, vorlauf)) is not None}


# =========================================================================================================
# 0.56: Neuanmeldungen je Halbjahr (alle Teilnehmenden – Pendler und Internat)
# =========================================================================================================
# Für die Wirtschaftsplanung zählt nicht der Bestand (eine zweijährige Maßnahme trägt zwei Jahrgänge), sondern wie
# viele je Halbjahr NEU beginnen. Hauptmaßnahmen starten halbjährlich (meist Januar und Juni) – deshalb nach Startwelle:
# Winterstart = November bis April (gezählt zum Jahr des Januars), Sommerstart = Mai bis Oktober. Ein Kalender-Halbjahr
# Jan–Jun würde beide Wellen zusammenwerfen.
# Welches Verfahren schätzt, entscheidet ein Rückwärtstest an den eigenen Daten (mehrere einfache Verfahren im Vergleich).

NACHRUECK_TAGE = 42                # wer in den ersten 6 Wochen nachrückt, zählt zum Kurs
AKTIV_MONATE = 24                  # ohne Start in dieser Zeit (und nichts gebucht): eingestellt
AKTIV_MIN = 5                      # weniger Neuanmeldungen in 24 Monaten (inkl. gebucht): Kleinstmaßnahme
VERFAHREN = {"vorjahr": "wie Vorjahr", "mittel3": "Mittel der letzten 3 Jahre",
             "glatt": "gewichtetes Mittel (jüngere Jahre zählen mehr)", "trend": "gedämpfter Trend (Holt, je Welle)",
             "holtwinters": "Holt-Winters (beide Startwellen gemeinsam)",
             "anteil": "Anteil am Gesamttrend aller Hauptmaßnahmen"}
SAISON_VERFAHREN = ("vorjahr", "mittel3", "glatt", "trend")
KAP_ZUSCHLAG = 1.15                # ohne eigene Angabe: höchste Startwelle der letzten 5 Jahre + 15 %


def neu_im_kurs(k: Kurs) -> int:
    return max(k.werte[:NACHRUECK_TAGE]) if k.werte else 0


# 1.29: aufgeteilt – diese Namen liegen jetzt in massnahmen_import.py (baut hierauf auf); sie bleiben hier
# erreichbar, werden aber erst beim ersten Zugriff geladen (sonst Kreis-Import).
_IN_MASSNAHMEN_IMPORT = frozenset({"ARCHIV_MAX", "ARCHIV_ORDNER", "PivotErgebnis", "archiv_staende", "archivieren",
                                   "listen_aus_text", "listen_lesen", "listen_schritt", "listen_uebernehmen",
                                   "pivot_aus_zeilen", "pivot_lesen", "pivot_schritt", "pivot_uebernehmen",
                                   "plaetze_schritt", "zuordnung_schritt"})


# 1.29: aufgeteilt – diese Namen liegen jetzt in massnahmen_neuanmeldungen.py (baut hierauf auf); sie bleiben hier
# erreichbar, werden aber erst beim ersten Zugriff geladen (sonst Kreis-Import).
_IN_MASSNAHMEN_NEUANMELDUNGEN = frozenset({"HZeile", "MONAT_KURZ", "MONAT_LANG", "NReihe", "SOMMER_AB", "VTest",
                                           "WINTER_AB", "Z80", "Z95", "_erstes_hj", "_folge", "_hj_summe",
                                           "_holt_winters", "_monat_ende", "_monat_plus", "_norm", "_quantil",
                                           "_reihe", "_schaetzen", "_spanne", "_starts", "band", "bestes_verfahren",
                                           "halbjahr", "hj_ende", "hj_kurz", "hj_plus", "hj_start", "hj_text",
                                           "kapazitaet_schritt", "kapazitaeten", "monatlich", "neuanmeldungen",
                                           "schaetzung", "sichtbar_schritt", "sichtbarkeit", "startmuster",
                                           "summen_spanne", "verfahren_testen"})


def __getattr__(name: str):
    if name in _IN_MASSNAHMEN_IMPORT:
        from . import massnahmen_import

        return getattr(massnahmen_import, name)
    if name in _IN_MASSNAHMEN_NEUANMELDUNGEN:
        from . import massnahmen_neuanmeldungen

        return getattr(massnahmen_neuanmeldungen, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
