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
    bestand: dict = field(default_factory=dict)   # 0.76: Aufenthalte je Person (nur Nummern) + Prüfwerte fürs Bestandsmodell

    @property
    def text(self) -> str:
        t = f"{len(self.kurse)} Kurse, {self.personen} Teilnahmen, {self.von:%d.%m.%Y} – {self.bis:%d.%m.%Y}"
        if self.luecken:
            t += " · überbrückt: " + ", ".join(f"{a:%d.%m.%y}–{b:%d.%m.%y}" for a, b in self.luecken)
        return t


def pivot_aus_zeilen(zeilen, stichtag: date | None = None) -> PivotErgebnis:
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
    # 0.76: Aufenthalte je Person und Kurs fürs Bestandsmodell (Namen werden nicht gespeichert – nur Nummern)
    from . import bestand_kern as bk

    stichtag = stichtag or date.today()
    datum_idx = {i for i, _d in spalten}
    hj_idx = [i for i, v in enumerate(kopf) if i and v not in (None, "") and i not in datum_idx
              and not str(v).strip().lower().startswith("gesamt")]
    sammler = bk.Sammler(von, stichtag)
    summen: dict[str, list[float]] = {}
    dauer: dict[str, list[int]] = {}
    personen = 0
    for z in it:
        if not z or not isinstance(z[0], str):
            continue
        t = z[0].strip()
        if t.lower().startswith("gesamt"):
            break
        sammler.zeile(t, [k for i, k in pos if i < len(z) and z[i]], any(i < len(z) and z[i] for i in hj_idx))
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
    sammler.ende()
    bestand = {"aufenthalte": [x.als_liste() for x in sammler.aufenthalte],
               "meta": {"von": von.isoformat(), "bis": bis.isoformat(), "stichtag": stichtag.isoformat(),
                        "halbjahr_spalten": len(hj_idx), "teilsummen": sammler.teilsummen, "langnamen": sammler.langnamen,
                        "nur_halbjahr": sammler.nur_halbjahr, "ohne_person": sammler.ohne_person,
                        "kuenftig_spalten": sum(1 for d in tage if d > stichtag), "kuenftig_tage": sammler.kuenftig_tage,
                        "kuenftig_personen": len(sammler.kuenftig_personen)}}
    return PivotErgebnis(von, bis, kurse, personen, luecken, bestand)


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
    if erg.bestand:
        roh["bestand"] = erg.bestand
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
        if not alle and gr.get(fam) not in ("lang", "vorbereitung", "ibtz"):
            continue
        eigene = [k for k in ks if k.familie == fam]
        n_neu = [e for e in neu if e.familie == fam]

        def wert(t: date) -> float:
            return (sum(am(k, t) for k in eigene) + sum(e.am(t) for e in n_neu)) * faktor(fam)
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
            if t <= st or not k.am(t):
                return float(k.am(t))
            a, a0 = (t - k.start).days, (st - k.start).days
            return float(k.am(st)) * verbleib_faktor(kurven.get(k.familie), a, a0)

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


WINTER_AB, SOMMER_AB = 11, 5       # Monat, ab dem die Winter- bzw. Sommerwelle zählt


def halbjahr(d: date) -> tuple[int, int]:
    """Startwelle: (Jahr, 1) = Winterstart Nov(Vorjahr)–Apr, (Jahr, 2) = Sommerstart Mai–Okt."""
    if d.month >= WINTER_AB:
        return d.year + 1, 1
    return (d.year, 1) if d.month < SOMMER_AB else (d.year, 2)


def hj_text(h: tuple[int, int]) -> str:
    return f"{'Winterstart' if h[1] == 1 else 'Sommerstart'} {h[0]}"


def hj_kurz(h: tuple[int, int]) -> str:
    return f"{'W' if h[1] == 1 else 'S'} {h[0] % 100:02d}"


def hj_start(h: tuple[int, int]) -> date:
    return date(h[0] - 1, WINTER_AB, 1) if h[1] == 1 else date(h[0], SOMMER_AB, 1)


def hj_ende(h: tuple[int, int]) -> date:
    return (date(h[0], SOMMER_AB, 1) if h[1] == 1 else date(h[0], WINTER_AB, 1)) - timedelta(days=1)


def hj_plus(h: tuple[int, int], n: int) -> tuple[int, int]:
    i = h[0] * 2 + (h[1] - 1) + n
    return i // 2, i % 2 + 1


def _schaetzen(reihe: list[float], verfahren: str) -> float | None:
    """Nächster Wert aus der Reihe desselben Halbjahrs (älteste zuerst)."""
    if not reihe:
        return None
    if verfahren == "vorjahr":
        return reihe[-1]
    if verfahren == "mittel3":
        r = reihe[-3:]
        return sum(r) / len(r)
    if verfahren == "glatt":                       # exponentielle Glättung, α = 0,5
        s = reihe[0]
        for x in reihe[1:]:
            s = .5 * x + .5 * s
        return s
    if verfahren == "trend":                       # Holt, gedämpft (φ = 0,8), nie unter 0
        if len(reihe) < 3:
            return sum(reihe[-3:]) / len(reihe[-3:])
        niveau, steig = reihe[0], reihe[1] - reihe[0]
        for x in reihe[1:]:
            alt = niveau
            niveau = .5 * x + .5 * (niveau + .8 * steig)
            steig = .3 * (niveau - alt) + .7 * .8 * steig
        return max(0.0, niveau + .8 * steig)
    raise ValueError(verfahren)


@dataclass
class HZeile:
    hj: tuple[int, int]
    art: str                      # ist | laufend | prognose
    ist: float                    # schon begonnen (bzw. Ist)
    gebucht: float                # schon gebucht, Start noch offen
    erwartet: float               # Schätzung gesamt (Ist + gebucht + Nachbuchung bzw. Verfahren)
    klein: float                  # 80 %: mit 80 % Wahrscheinlichkeit zwischen klein und gross
    gross: float
    geplant: bool = False         # eigene geplante Plätze
    klein95: float = 0.0          # 0.57: 95 %-Spanne
    gross95: float = 0.0
    # 0.58: Rückwärtstest je vergangener Welle – was das Verfahren damals geschätzt hätte, mit den Spannen, die damals
    # bekannt waren (nur aus Fehlern früherer Wellen)
    rueck: float | None = None
    rueck_band: tuple | None = None   # (unten 80, oben 80, unten 95, oben 95)

    @property
    def im80(self) -> bool | None:
        return None if self.rueck_band is None else self.rueck_band[0] - .5 <= self.ist <= self.rueck_band[1] + .5

    @property
    def im95(self) -> bool | None:
        return None if self.rueck_band is None else self.rueck_band[2] - .5 <= self.ist <= self.rueck_band[3] + .5

    @property
    def text(self) -> str:
        return hj_text(self.hj)


def summen_spanne(zeilen: list, stufe: int = 80) -> tuple[float, float]:
    """Spanne einer Summe mehrerer Schätzungen. Die Abweichungen gleichen sich teils aus – deshalb nicht die Spannen
    addieren (zu breit), sondern die Abstände zum erwarteten Wert quadratisch (unabhängig angenommen)."""
    e = sum(z.erwartet for z in zeilen)
    lo, hi = (("klein", "gross") if stufe == 80 else ("klein95", "gross95"))
    unten = sum((z.erwartet - getattr(z, lo)) ** 2 for z in zeilen) ** .5
    oben = sum((getattr(z, hi) - z.erwartet) ** 2 for z in zeilen) ** .5
    sicher = sum(z.ist + z.gebucht for z in zeilen if z.art != "ist")
    return max(sicher, e - unten), e + oben


@dataclass
class NReihe:
    familie: str
    gruppe: str
    zeilen: list[HZeile]
    letzte12: float               # Neuanmeldungen der letzten 12 Monate
    vorige12: float               # die 12 Monate davor
    jahr_mittel: float            # Ø je Jahr (letzte 3 volle Jahre)
    naechstes_jahr: float         # erwartet im nächsten Kalenderjahr (H1 + H2)
    eingestellt: bool
    klein_massnahme: bool
    ausgeschlossen: bool = False  # 0.58: z. B. UWT – eigene Planung, gehört nicht in die Maßnahmen-Prognose
    kapazitaet: int | None = None   # 0.63: höchstens so viele je Startwelle
    kap_quelle: str = ""            # eigene Angabe | automatisch

    def jahr_spanne(self, jahr: int, stufe: int = 80) -> tuple[float, float]:
        """Spanne der Neuanmeldungen eines Jahres (Winter + Sommer)."""
        return summen_spanne([z for z in self.zeilen if z.hj[0] == jahr], stufe)


    @property
    def trend(self) -> float | None:
        return (self.letzte12 / self.vorige12 - 1) if self.vorige12 >= 3 else None

    @property
    def aktiv(self) -> bool:
        return not self.eingestellt and not self.klein_massnahme and not self.ausgeschlossen

    @property
    def grund(self) -> str:
        return ("UWT – eigene Planung" if self.ausgeschlossen else "eingestellt" if self.eingestellt
                else "Kleinstmaßnahme" if self.klein_massnahme else "")


@dataclass
class VTest:
    verfahren: str
    text: str
    wape: float | None            # Σ|Fehler| / Σ Ist über alle Halbjahre und Maßnahmen
    bias: float | None            # Σ Fehler / Σ Ist (+ = zu hoch geschätzt)
    n: int                        # verglichene Halbjahre (je Maßnahme)
    fehler: list = field(default_factory=list)    # (Ist − Schätzung) / Schätzung – für die Spanne
    punkte: list = field(default_factory=list)    # 0.58: (Welle, relativer Fehler) – für Spannen „wie damals“
    treffer80: tuple = (0, 0)     # 0.58: (im Band, geprüft) – mit Spannen nur aus früheren Wellen
    treffer95: tuple = (0, 0)


def _folge(ks: list[Kurs], vor: date, erster: tuple[int, int]) -> list[tuple[tuple[int, int], float]]:
    """Alle vollständig vor ``vor`` beobachteten Startwellen in zeitlicher Reihenfolge (Winter, Sommer, Winter …)."""
    erg, h = [], erster
    while hj_ende(h) < vor:
        erg.append((h, _hj_summe(ks, h)))
        h = hj_plus(h, 1)
    return erg


def _holt_winters(folge: list[tuple[tuple[int, int], float]], ziel: tuple[int, int],
                  alpha: float = .4, beta: float = .15, gamma: float = .3, phi: float = .8) -> float | None:
    """Holt-Winters (additiv, gedämpfter Trend) mit Saisonlänge 2 – Winter- und Sommerwelle teilen sich Niveau und
    Trend, jede hat ihren eigenen Saisonanteil. Nutzt so doppelt so viele Werte wie die Verfahren je Welle."""
    if len(folge) < 4:
        return None
    werte = [v for _h, v in folge]
    niveau = (werte[0] + werte[1]) / 2
    steig = ((werte[2] + werte[3]) - (werte[0] + werte[1])) / 4
    saison = {folge[0][0][1]: werte[0] - niveau, folge[1][0][1]: werte[1] - niveau}
    for (h, x) in folge[2:]:
        s = saison.get(h[1], 0.0)
        alt = niveau
        niveau = alpha * (x - s) + (1 - alpha) * (niveau + phi * steig)
        steig = beta * (niveau - alt) + (1 - beta) * phi * steig
        saison[h[1]] = gamma * (x - niveau) + (1 - gamma) * s
    letzte = folge[-1][0]
    schritte = (ziel[0] * 2 + ziel[1]) - (letzte[0] * 2 + letzte[1])
    trend = sum(phi ** i for i in range(1, max(1, schritte) + 1)) * steig
    return max(0.0, niveau + trend + saison.get(ziel[1], 0.0))


def schaetzung(eigene: list[Kurs], h: tuple[int, int], vor: date, erster: tuple[int, int], verfahren: str,
               gesamt: list[Kurs] | None = None) -> float | None:
    """Neuanmeldungen der Welle ``h`` – nur mit dem, was vor ``vor`` bekannt war."""
    reihe = _reihe(eigene, h, vor, erster)
    if verfahren in SAISON_VERFAHREN:
        return _schaetzen(reihe, verfahren)
    if verfahren == "holtwinters":
        w = _holt_winters(_folge(eigene, vor, erster), h)
        return w if w is not None else _schaetzen(reihe, "mittel3")
    if verfahren == "anteil":
        ges = _reihe(gesamt or eigene, h, vor, erster)
        if len(reihe) < 2 or not sum(ges[-3:]):
            return _schaetzen(reihe, "mittel3")
        return sum(reihe[-3:]) / sum(ges[-3:]) * (_schaetzen(ges, "trend") or 0.0)
    raise ValueError(verfahren)


def kapazitaeten(daten: dict | None = None) -> dict[str, int]:
    """Eigene Obergrenzen je Maßnahme (Plätze je Startwelle)."""
    roh = daten if daten is not None else _roh()
    return {k: int(v) for k, v in (roh.get("kapazitaet") or {}).items() if v}


def kapazitaet_schritt(fam: str, plaetze: int | None) -> str:
    from .kern import _schritt

    def tun():
        roh = _roh()
        k = roh.setdefault("kapazitaet", {})
        if plaetze:
            k[fam] = int(plaetze)
        else:
            k.pop(fam, None)
        _schreiben(roh)
    _schritt(f"Plätze je Startwelle: {fam}", tun, [DATEI])
    return f"{fam}: höchstens {plaetze} je Startwelle" if plaetze else f"{fam}: Obergrenze wieder automatisch"


def _starts(ks: list[Kurs], daten_ab: date) -> list[Kurs]:
    """Kurse mit bekanntem Start (nicht schon am Datenbeginn gelaufen)."""
    return [k for k in ks if k.start > daten_ab + timedelta(days=30)]


def _hj_summe(ks: list[Kurs], h: tuple[int, int], bis: date | None = None) -> float:
    a, e = hj_start(h), hj_ende(h)
    if bis is not None:
        e = min(e, bis)
    return float(sum(neu_im_kurs(k) for k in ks if a <= k.start <= e))


def _reihe(ks: list[Kurs], h: tuple[int, int], vor: date, erster: tuple[int, int]) -> list[float]:
    """Werte desselben Halbjahrs in früheren Jahren (ab ``erster``, nur vollständig vor ``vor`` beobachtete)."""
    erg, j = [], erster[0] + (1 if erster[1] > h[1] else 0)
    while (j, h[1]) < h:
        if hj_ende((j, h[1])) < vor:
            erg.append(_hj_summe(ks, (j, h[1])))
        j += 1
    return erg


def _erstes_hj(daten_ab: date) -> tuple[int, int]:
    """Erstes Halbjahr, in dem alle Starts bekannt sind (Kurse im ersten Monat der Daten können schon gelaufen sein)."""
    h = halbjahr(daten_ab + timedelta(days=31))
    return h if hj_start(h) > daten_ab + timedelta(days=30) else hj_plus(h, 1)


def verfahren_testen(daten: dict | None = None, familien: list[str] | None = None) -> list[VTest]:
    """Rückwärtstest je Verfahren: Für jedes vergangene Halbjahr mit mindestens 2 Vorjahren schätzen – nur mit dem,
    was vorher bekannt war (keine Buchungen, also eher streng) – und mit dem Ist vergleichen. Kleinster WAPE gewinnt."""
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    if not ks:
        return []
    daten_ab = date.fromisoformat((roh.get("pivot") or {}).get("von") or min(k.start for k in ks).isoformat())
    daten_bis = date.fromisoformat((roh.get("pivot") or {}).get("bis") or max(k.ende for k in ks).isoformat())
    ende = min(daten_bis, date.today())
    fams = familien if familien is not None else sorted({k.familie for k in ks})
    starts = _starts(ks, daten_ab)
    erster = _erstes_hj(daten_ab)
    gesamt = [k for k in starts if k.familie in set(fams)]
    erg = []
    for v, text in VERFAHREN.items():
        summe_ist = summe_abs = summe_fehler = 0.0
        n, rel, punkte, paare = 0, [], [], []
        for fam in fams:
            eigene = [k for k in starts if k.familie == fam]
            h = hj_plus(erster, 4)                               # erst ab 2 Vorjahren
            while hj_ende(h) < ende:
                vorher = _reihe(eigene, h, hj_start(h), erster)
                if len(vorher) >= 2:
                    p, i = schaetzung(eigene, h, hj_start(h), erster, v, gesamt), _hj_summe(eigene, h)
                    if p is not None and (i or p):
                        summe_ist += i
                        summe_abs += abs(p - i)
                        summe_fehler += p - i
                        n += 1
                        rel.append(_norm(i, p))   # Abweichung in Wurzel-Einheiten (siehe _norm)
                        punkte.append((h, _norm(i, p)))
                        paare.append((h, p, i))
                h = hj_plus(h, 1)
        t80 = t95 = geprueft = 0
        for h, p, i in paare:                     # ehrlich: Spanne nur aus Fehlern früherer Wellen
            frueher = [r for hh, r in punkte if hh < h]
            if len(frueher) < 5:
                continue
            lo, hi, lo95, hi95 = _spanne(frueher)
            geprueft += 1
            t80 += band(p, lo) - .5 <= i <= band(p, hi) + .5
            t95 += band(p, lo95) - .5 <= i <= band(p, hi95) + .5
        erg.append(VTest(v, text, summe_abs / summe_ist if summe_ist else None,
                         summe_fehler / summe_ist if summe_ist else None, n, rel, punkte, (t80, geprueft), (t95, geprueft)))
    return sorted(erg, key=lambda t: (t.wape is None, t.wape or 0))


def bestes_verfahren(tests: list[VTest]) -> str:
    gut = [t for t in tests if t.wape is not None and t.n >= 3]
    return gut[0].verfahren if gut else "mittel3"


Z80, Z95 = 1.2816, 1.96            # Normalverteilung: 80 % bzw. 95 % liegen innerhalb ±z Standardabweichungen


def _quantil(r: list[float], q: float) -> float:
    """Lineares Quantil einer sortierten Liste."""
    x = q * (len(r) - 1)
    i = int(x)
    return r[i] if i + 1 >= len(r) else r[i] + (x - i) * (r[i + 1] - r[i])


def _norm(i: float, p: float) -> float:
    """0.63: Abweichung in „Wurzel-Einheiten“: (Ist − Schätzung) / √Schätzung. Bei Zählwerten wächst die Streuung etwa
    mit der Wurzel – 3 ± 2 ist üblich, 18 ± 12 nicht. So lernen große und kleine Maßnahmen gemeinsam, ohne dass die
    hohen Prozentfehler der kleinen die Spanne der großen aufblähen (vorher: Fehler in Prozent)."""
    return (i - p) / max(p, 1.0) ** .5


def band(p: float, a: float) -> float:
    """Grenze zu einer Abweichung ``a`` in Wurzel-Einheiten (nie unter 0)."""
    return max(0.0, p + a * max(p, 1.0) ** .5)


def _spanne(rel: list[float]) -> tuple[float, float, float, float]:
    """Spanne aus den Abweichungen des Rückwärtstests (in Wurzel-Einheiten, siehe ``_norm``): (unten 80, oben 80,
    unten 95, oben 95). 80 %: 10.–90. Perzentil; 95 %: 2,5.–97,5. Perzentil ab 40 Werten, sonst aus der 80-%-Spanne
    hochgerechnet (× 1,96 / 1,28). Wenige Werte werden leicht geweitet (1 + 2/n). Ohne Test: wie bei Zufallsschwankung
    (Poisson: ±1,28 bzw. ±1,96)."""
    if len(rel) < 5:
        lo, hi = -Z80, Z80
    else:
        r = sorted(rel)
        lo, hi = min(_quantil(r, .1), -.3), max(_quantil(r, .9), .3)
    if len(rel) >= 40:
        r = sorted(rel)
        lo95, hi95 = min(_quantil(r, .025), lo), max(_quantil(r, .975), hi)
    else:
        lo95, hi95 = lo * Z95 / Z80, hi * Z95 / Z80
    k = 1 + 2 / max(len(rel), 5)
    return lo * k, hi * k, lo95 * k, hi95 * k


def neuanmeldungen(daten: dict | None, stichtag: date, familien: list[str] | None = None, zurueck: int = 8,
                   vor: int = 4, verfahren: str | None = None, vorlauf: list[int] | None = None,
                   tests: list[VTest] | None = None) -> dict[str, NReihe]:
    """Je Maßnahmenart: Neuanmeldungen je Halbjahr – ``zurueck`` Halbjahre Ist, das laufende, ``vor`` Halbjahre voraus.

    Künftige Halbjahre: schon gebuchte Starts + erwartete Nachbuchung (Buchungskurve wie 0.55); ohne Buchungen das
    Verfahren mit dem kleinsten Fehler im Rückwärtstest. Eigene geplante Plätze ersetzen die Schätzung."""
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    if not ks:
        return {}
    gr = gruppen(roh)
    daten_ab = date.fromisoformat((roh.get("pivot") or {}).get("von") or min(k.start for k in ks).isoformat())
    erster = _erstes_hj(daten_ab)
    starts = _starts(ks, daten_ab)
    tests = tests if tests is not None else verfahren_testen(roh)
    verfahren = verfahren or bestes_verfahren(tests)
    lo, hi, lo95, hi95 = _spanne(next((t.fehler for t in tests if t.verfahren == verfahren), []))
    punkte_v = next((t.punkte for t in tests if t.verfahren == verfahren), [])
    eigene_kap = kapazitaeten(roh)
    haupt = [k for k in starts if gr.get(k.familie) == "lang"]       # für „Anteil am Gesamttrend“
    pk = pickup_kurve(vorlauf)
    geplant: dict[tuple, int] = {}
    for p in roh.get("plaetze") or []:
        try:
            h = halbjahr(date.fromisoformat(p["monat"] + "-01"))
        except (KeyError, ValueError):
            continue
        geplant[(p["familie"], h)] = geplant.get((p["familie"], h), 0) + int(p["plaetze"])
    jetzt = halbjahr(stichtag)
    fams = familien if familien is not None else sorted({k.familie for k in ks})
    erg = {}
    for fam in fams:
        eigene = [k for k in starts if k.familie == fam]
        alle_eigene = [k for k in ks if k.familie == fam]
        if not alle_eigene:
            continue
        # Obergrenze je Startwelle: eigene Angabe, sonst höchste Welle der letzten 5 Jahre + 15 %
        hoechste = max((v for hh, v in _folge(eigene, stichtag, erster) if hh[0] >= stichtag.year - 5), default=0.0)
        kap = float(eigene_kap[fam]) if fam in eigene_kap else (float(-(-hoechste * KAP_ZUSCHLAG // 1)) if hoechste
                                                               else 9999.0)
        kap_quelle = "eigene Angabe" if fam in eigene_kap else ("automatisch" if hoechste else "")
        zeilen = []
        for n in range(-zurueck, vor + 1):
            h = hj_plus(jetzt, n)
            if h < erster:
                continue
            if n < 0:
                i = _hj_summe(eigene, h)
                z = HZeile(h, "ist", i, 0.0, i, i, i, False, i, i)
                vorher = _reihe(eigene, h, hj_start(h), erster)
                if len(vorher) >= 2:
                    z.rueck = schaetzung(eigene, h, hj_start(h), erster, verfahren, haupt)
                    frueher = [r for hh, r in punkte_v if hh < h]
                    if len(frueher) >= 5 and z.rueck is not None:
                        a8, b8, a9, b9 = _spanne(frueher)
                        z.rueck_band = (band(z.rueck, a8), band(z.rueck, b8), band(z.rueck, a9), band(z.rueck, b9))
                zeilen.append(z)
                continue
            ist = _hj_summe(eigene, h, stichtag)
            gebuchte = [k for k in eigene if stichtag < k.start <= hj_ende(h)
                        and k.start >= hj_start(h)]
            geb = float(sum(neu_im_kurs(k) for k in gebuchte))
            reihe = _reihe(eigene, h, stichtag, erster)
            voll = schaetzung(eigene, h, stichtag, erster, verfahren, haupt) or 0.0
            # Anteil des Halbjahrs, der noch aussteht (in den Vorjahren: Starts nach dem heutigen Tag im Halbjahr)
            if n == 0 and reihe:
                vorj = [_hj_summe(eigene, (h[0] - j, h[1])) for j in range(1, 4) if (h[0] - j, h[1]) >= erster]
                rest_vorj = [_hj_summe([k for k in eigene if k.start > _jahr_verschoben(stichtag, -j)], (h[0] - j, h[1]))
                             for j in range(1, 4) if (h[0] - j, h[1]) >= erster]
                anteil_rest = (sum(rest_vorj) / sum(vorj)) if sum(vorj) else 0.0
            else:
                anteil_rest = 1.0
            hist_rest = voll * anteil_rest
            if gebuchte:
                d = sum((k.start - stichtag).days for k in gebuchte) / len(gebuchte)
                rest = nachbuchung(geb, hist_rest, pk(d), deckel=max(reihe) if reihe else None)
            else:
                d = max(0, (hj_start(h) - stichtag).days) + 60
                rest = hist_rest if n > 0 else nachbuchung(0.0, hist_rest, pk(d))
            sicher = ist + geb                     # schon begonnen bzw. gebucht – untere Grenze
            deckel = max(kap, sicher)              # 0.63: nie mehr als Plätze da sind (es sei denn, schon gebucht)
            gesamt = min(ist + max(rest, geb), deckel)
            plan = geplant.get((fam, h))
            if plan is not None:
                p_ = float(plan)
                zeilen.append(HZeile(h, "laufend" if n == 0 else "prognose", ist, geb, p_, p_, p_, True, p_, p_))
            else:
                zeilen.append(HZeile(h, "laufend" if n == 0 else "prognose", ist, geb, gesamt,
                                     min(gesamt, max(sicher, band(gesamt, lo))), min(deckel, band(gesamt, hi)), False,
                                     min(gesamt, max(sicher, band(gesamt, lo95))), min(deckel, band(gesamt, hi95))))
        heute = stichtag

        def neu_zw(a: date, b: date) -> float:
            return float(sum(neu_im_kurs(k) for k in alle_eigene if a < k.start <= b))
        letzte, vorige = neu_zw(heute - timedelta(days=365), heute), neu_zw(heute - timedelta(days=730), heute - timedelta(days=365))
        volle = [neu_zw(date(heute.year - j - 1, 12, 31), date(heute.year - j, 12, 31)) for j in range(1, 4)]
        naechst = sum(z.erwartet for z in zeilen if z.hj[0] == heute.year + 1)
        letzter_start = max((k.start for k in alle_eigene if k.start <= heute), default=None)
        kuenftig = any(k.start > heute for k in alle_eigene)
        eingestellt = not kuenftig and (letzter_start is None or (heute - letzter_start).days > AKTIV_MONATE * 30.4)
        klein_m = (neu_zw(heute - timedelta(days=730), heute) + sum(neu_im_kurs(k) for k in alle_eigene if k.start > heute)
                   ) < AKTIV_MIN
        erg[fam] = NReihe(fam, gr.get(fam, "uebrige"), zeilen, letzte, vorige, sum(volle) / 3, naechst, eingestellt, klein_m,
                          bool(re.search(r"\bUWT\b", fam)), int(kap) if kap < 9999 else None, kap_quelle)
    return erg


def sichtbarkeit(daten: dict | None = None) -> dict[str, bool]:
    """Eigene Entscheidung je Art: True = immer zeigen, False = immer ausblenden (sonst gilt die Regel)."""
    roh = daten if daten is not None else _roh()
    return dict(roh.get("sichtbar") or {})


def sichtbar_schritt(fam: str, wert: bool | None) -> str:
    from .kern import _schritt

    def tun():
        roh = _roh()
        s = roh.setdefault("sichtbar", {})
        if wert is None:
            s.pop(fam, None)
        else:
            s[fam] = bool(wert)
        _schreiben(roh)
    _schritt(f"Maßnahme {'eingeblendet' if wert else 'ausgeblendet'}: {fam}", tun, [DATEI])
    return f"{fam} {'wird immer gezeigt' if wert else 'ausgeblendet' if wert is False else 'nach Regel'}"
