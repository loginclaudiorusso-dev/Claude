"""Bestandsmodell der Maßnahmen-Belegung – Schritt 2 und 3 (0.79). Rein, nur numpy.

    Belegung im Monat m = Restbestand der heute Laufenden (Verbleibskurve)
                        + bekannte künftige Eintritte (geplante Tage im Pivot)
                        + Zugänge aus der Pipeline (Assessment → Vorbereitung/Hauptmaßnahme, Vorbereitung → Haupt)
                        + übrige künftige Zugänge (Saison der letzten 3 Jahre × Szenario)

* **Verbleibskurve (Kaplan-Meier)** je Maßnahmeart – ab 30 Fällen, sonst je Gruppe, sonst über alle. Laufende Fälle
  sind zensiert. Daraus: vorzeitige Abgangsquote = 1 − Verbleib 30 Tage vor dem Soll-Ende.
* **Übergänge:** gleiche Person erst in Assessment (bzw. Vorbereitung), dann innerhalb von 12 Monaten in der nächsten
  Stufe. Quote nur aus Fällen mit vollständig abgelaufenem Beobachtungsfenster; dazu die Verzögerung und die Zielarten.
* **Simulation:** 1000 Durchläufe mit festem Startwert (wiederholbar). Ausgabe je Monat: Median (Planwert), 10./90.
  Perzentil (80 %-Spanne) und die mittlere Zerlegung nach Herkunft.
* **Szenarien** wirken nur auf die übrigen Zugänge – Bestand und Pipeline sind in allen gleich.
* **Kursgröße:** Wo eine Obergrenze hinterlegt ist (VW: 24), werden Zugänge je Startmonat gekappt; der Rest wird als
  „Nachfrage über Kapazität“ ausgewiesen.

**0.86 (Challenge):**

* Die Verbleibskurve rechnet nur mit **beobachteten** Tagen (bis zum Stichtag); künftige Eintritte stehen nicht in der
  Kurve. Sie schätzt nur noch **vorzeitige** Abgänge – reguläre Enden (ab 30 Tage vor dem Soll-Ende) gelten als
  zensiert. Das Ende eines Aufenthalts ist in der Simulation das frühere aus geplantem Ende (Pivot, sonst Solldauer)
  und gezogenem vorzeitigem Abgang.
* Bekannte künftige Eintritte, die keine Folge einer Vorstufe sind, werden von den „weiteren Zugängen“ des Monats
  **abgezogen** (sie stecken schon in der Erfahrungsrate – sonst doppelt gezählt).
* **Gemeinsamer Jahresfaktor** je Lauf (lognormal, Streuung JAHR_STREUUNG): alle Maßnahmearten schwanken gemeinsam
  mit dem Bewilligungsverhalten – die Gesamtspanne wird ehrlicher breit.
* **Frühindikator** meldet nur, was über dem Zufall liegt: |jetzt − vorher| > 2·√(jetzt + vorher).
* **Rückblick** monatlich (18 Stichtage), mit Vergleich „Bestand bleibt wie heute“.
* **Wenn-dann** als bedingte Simulation: aus 3000 Läufen die, die im gewählten Monat nahe am Wert lagen.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from . import bestand_kern as bk

MIN_FAELLE = 30
UEBERGANG_TAGE = 365
JAHRE_HISTORIE = 3
HORIZONT = 24
DURCHLAEUFE = 1000
SEED = 20261108
QUELLEN = ("bestand", "bekannt", "pipeline", "uebrig")
QUELLE_TEXT = {"bestand": "schon da", "bekannt": "fest angemeldet", "pipeline": "aus Assessment/Vorbereitung",
               "uebrig": "weitere Zugänge (Erfahrung)"}
SZENARIEN_STANDARD = {"schwach": {"faktor": -15, "ausloeser": ""}, "basis": {"faktor": 0, "ausloeser": ""},
                      "stark": {"faktor": 10, "ausloeser": ""}}
SZENARIO_NAMEN = {"schwach": "wirtschaftlich schwach", "basis": "normal", "stark": "wirtschaftlich gut"}
VORSTUFEN = {"Assessment": ("Vorbereitung", "Hauptmaßnahme"), "Vorbereitung": ("Hauptmaßnahme",)}
JAHR_STREUUNG = 0.12      # Annahme: gemeinsame Jahresschwankung der Zugänge (±12 % typisch) – sichtbar in ƒx
REGULAER_VOR_SOLL = 30    # Ende ab so vielen Tagen vor dem Soll-Ende = reguläres Ende (kein vorzeitiger Abgang)
WD_LAEUFE = 3000          # Wenn-dann: so viele Läufe, davon die nächsten am gewählten Wert
WD_AUSWAHL = 150


# ---- Fälle -------------------------------------------------------------------------------------------------

@dataclass
class Fall:
    person: int
    kurs: str
    art: str
    gruppe: str
    ein: date
    aus: date
    laufend: bool
    soll: int | None
    geplant: date | None = None     # 0.86: geplantes Ende laut Pivot (nur wenn es nach dem Stichtag liegt)

    @property
    def dauer(self) -> int:
        """Kalendertage vom ersten bis zum letzten Tag mit Wert (inkl.) – bei Laufenden einschließlich geplanter Tage."""
        return (self.aus - self.ein).days + 1

    def beobachtet(self, letzter: date) -> int:
        """0.86: nur die Tage bis zum Stichtag – so geht ein Laufender in die Verbleibskurve ein (zensiert)."""
        return (min(self.aus, letzter) - self.ein).days + 1

    def vorzeitig(self, soll: int | None) -> bool:
        """Beendet und deutlich vor dem Soll-Ende (ohne Solldauer: jedes Ende zählt)."""
        if self.laufend:
            return False
        s = self.soll or soll
        return self.dauer < s - REGULAER_VOR_SOLL if s else True


def faelle(aufenthalte: list[bk.Aufenthalt], tabelle: list[dict], gemessen: dict, letzter: date,
           pivot_ende: date | None = None) -> list[Fall]:
    """pivot_ende (0.86): letzter Tag im Pivot. Wer bis dorthin Werte hat, ist nur abgeschnitten – sein geplantes
    Ende ist unbekannt (dann gilt die Solldauer), nicht der letzte Pivot-Tag."""
    erg = []
    for x in aufenthalte:
        e = bk.zuordnen(x.kurs, tabelle)
        if e is None or e["gruppe"] == "Ignoriert" or x.halbjahr:
            continue
        soll, _q = bk.soll_tage(x.kurs, e, gemessen)
        abgeschnitten = pivot_ende is not None and x.aus >= pivot_ende - timedelta(days=bk.LAUFEND_TAGE)
        erg.append(Fall(x.person, x.kurs, e["art"], e["gruppe"], x.ein, x.aus,
                        x.aus >= letzter - timedelta(days=bk.LAUFEND_TAGE), soll,
                        x.aus if x.aus > letzter and not abgeschnitten else None))
    return erg


# ---- Kaplan-Meier --------------------------------------------------------------------------------------------

@dataclass
class Kurve:
    tage: np.ndarray        # Ereigniszeitpunkte (Tage seit Eintritt), aufsteigend
    s: np.ndarray           # Verbleib direkt nach dem jeweiligen Zeitpunkt
    n: int
    ereignisse: int
    max_tag: int

    def verbleib(self, t) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        if not len(self.tage):                       # 0.86: noch kein Abgang beobachtet → alle bleiben
            return np.ones_like(t)
        i = np.searchsorted(self.tage, t, side="right")
        return np.where(i == 0, 1.0, self.s[np.maximum(i - 1, 0)])

    def ziehen(self, alter: np.ndarray, rng) -> np.ndarray:
        """Gesamtdauer (Tage) für Fälle, die schon ``alter`` Tage da sind – aus der bedingten Verbleibskurve.
        Endet die Kurve über 0, bleiben die Übrigen bis über den Horizont (Dauer = sehr groß)."""
        alter = np.asarray(alter, dtype=float)
        if not len(self.tage):                       # noch kein beendeter Fall: alle bleiben über den Horizont
            rng.random(alter.shape)
            return np.full(alter.shape, 10.0 ** 6)
        ziel = self.verbleib(alter) * rng.random(alter.shape)
        # erster Zeitpunkt, an dem s ≤ ziel (s fällt monoton) → über -s aufsteigend suchen
        i = np.searchsorted(-self.s, -ziel, side="left")
        dauer = np.where(i < len(self.tage), self.tage[np.minimum(i, len(self.tage) - 1)], 10 ** 6)
        return np.maximum(dauer, alter + 1)


def km(dauern, beendet) -> Kurve:
    d = np.asarray(dauern, dtype=float)
    b = np.asarray(beendet, dtype=bool)
    if not len(d):
        return Kurve(np.array([]), np.array([]), 0, 0, 0)
    zeiten = np.unique(d[b])
    s, tage, werte = 1.0, [], []
    for t in zeiten:
        risiko = np.sum(d >= t)
        ende = np.sum((d == t) & b)
        if risiko:
            s *= 1 - ende / risiko
        tage.append(t)
        werte.append(s)
    return Kurve(np.array(tage), np.array(werte), int(len(d)), int(b.sum()), int(d.max()))


# ---- Modell ---------------------------------------------------------------------------------------------------

@dataclass
class Uebergang:
    von: str                 # Gruppe der Vorstufe
    quote: float | None
    basis: int               # Fälle mit abgeschlossenem Beobachtungsfenster
    verzoegerung: np.ndarray  # Tage von Eintritt Vorstufe bis Eintritt Ziel
    ziele: Counter


@dataclass
class Modell:
    letzter: date
    faelle: list[Fall]
    arten: list[str]
    gruppe: dict             # Art → Gruppe
    soll: dict               # Art → typische Solldauer (Tage) oder None
    kurven: dict             # Art → Kurve (ggf. die der Gruppe / aller)
    kurve_quelle: dict       # Art → „Art“ | „Gruppe …“ | „alle“
    uebergaenge: dict        # Gruppe der Vorstufe → Uebergang
    raten: dict              # Art → np.array(12) übrige Zugänge je Kalendermonat (Ø je Jahr)
    kappe: dict              # Art → max. Plätze je Startmonat
    folge: set = field(default_factory=set)   # Index der Vorstufen-Fälle, die schon eine Folge haben
    erklaert: set = field(default_factory=set)   # 0.86: Index der Fälle, die Folge einer Vorstufe sind
    abgang_alt: dict = field(default_factory=dict)   # 0.86: Abgangsquote nach der bisherigen Rechnung (Vergleich)


def _personen(fs: list[Fall]) -> dict[int, list[int]]:
    p: dict[int, list[int]] = {}
    for i, f in enumerate(fs):
        p.setdefault(f.person, []).append(i)
    for v in p.values():
        v.sort(key=lambda i: fs[i].ein)
    return p


def modell(fs: list[Fall], letzter: date, tabelle: list[dict]) -> Modell:
    arten = sorted({f.art for f in fs})
    gruppe = {f.art: f.gruppe for f in fs}
    soll = {}
    for a in arten:
        werte = [f.soll for f in fs if f.art == a and f.soll]
        soll[a] = int(np.median(werte)) if werte else None
    # Verbleibskurven (0.86): nur beobachtete Tage, künftige Eintritte nicht; Ereignis = vorzeitiger Abgang
    beob = [f for f in fs if f.ein <= letzter]

    def kurve(auswahl):
        return km([f.beobachtet(letzter) for f in auswahl], [f.vorzeitig(soll.get(f.art)) for f in auswahl])

    def kurve_alt(auswahl):            # bis 0.85: geplante Tage mitgezählt, jedes Ende ein Ereignis
        return km([f.dauer for f in auswahl], [not f.laufend for f in auswahl])

    def waehlen(a, rechne, menge):
        eigen = [f for f in menge if f.art == a]
        gr = [f for f in menge if f.gruppe == gruppe[a]]
        if len(eigen) >= MIN_FAELLE:
            return rechne(eigen), "Art"
        if len(gr) >= MIN_FAELLE:
            return rechne(gr), f"Gruppe {gruppe[a]}"
        return rechne(menge), "alle"
    kurven, quelle, abgang_alt = {}, {}, {}
    for a in arten:
        kurven[a], quelle[a] = waehlen(a, kurve, beob)
        alt, _q = waehlen(a, kurve_alt, fs)
        if soll[a] and alt.n:
            abgang_alt[a] = float(1 - alt.verbleib(max(1, soll[a] - REGULAER_VOR_SOLL)))
    # Übergänge
    pers = _personen(fs)
    uebergaenge, folge, erklaert = {}, set(), set()
    for von, ziele in VORSTUFEN.items():
        n_abg, treffer, verz, zl = 0, 0, [], Counter()
        for idx in pers.values():
            for k, i in enumerate(idx):
                if fs[i].gruppe != von:
                    continue
                nach = next((j for j in idx[k + 1:] if fs[j].gruppe in ziele
                             and 0 <= (fs[j].ein - fs[i].ein).days <= UEBERGANG_TAGE), None)
                if nach is not None:
                    folge.add(i)
                    erklaert.add(nach)
                if fs[i].ein <= letzter - timedelta(days=UEBERGANG_TAGE):
                    n_abg += 1
                    if nach is not None:
                        treffer += 1
                        verz.append((fs[nach].ein - fs[i].ein).days)
                        zl[fs[nach].art] += 1
        uebergaenge[von] = Uebergang(von, treffer / n_abg if n_abg else None, n_abg, np.array(verz, dtype=float), zl)
    # übrige Zugänge je Art und Kalendermonat (nicht durch eine Vorstufe erklärt), letzte 3 Jahre
    ab = date(letzter.year - JAHRE_HISTORIE, letzter.month, 1)
    raten = {a: np.zeros(12) for a in arten}
    for i, f in enumerate(fs):
        if i not in erklaert and ab <= f.ein <= letzter:
            raten[f.art][f.ein.month - 1] += 1 / JAHRE_HISTORIE
    kappe = {}
    for e in tabelle:
        if e.get("max_plaetze"):
            kappe[e["art"]] = int(e["max_plaetze"])
    return Modell(letzter, fs, arten, gruppe, soll, kurven, quelle, uebergaenge, raten, kappe, folge, erklaert, abgang_alt)


# ---- Simulation ------------------------------------------------------------------------------------------------

@dataclass
class Ergebnis:
    monate: list[date]                 # Messtage (15. des Monats), Index 0 = Stichtag
    arten: list[str]
    median: np.ndarray                 # (Arten + 1 [Alle], T)
    p10: np.ndarray
    p90: np.ndarray
    zerlegung: np.ndarray              # (Quellen, Arten + 1, T) – Mittel
    ueber_kapazitaet: dict             # Art → Ø abgewiesene Zugänge im Horizont
    roh: np.ndarray | None = None      # (Arten + 1, R, T) – für Wenn-dann

    def zeile(self, art: str | None) -> int:
        return len(self.arten) if art in (None, "", "Alle") else self.arten.index(art)


def messtage(letzter: date, horizont: int = HORIZONT) -> list[date]:
    tage = [letzter]
    j, m = letzter.year, letzter.month
    for _ in range(horizont):
        m += 1
        if m > 12:
            j, m = j + 1, 1
        tage.append(date(j, m, 15))
    return tage


def simulieren(md: Modell, faktor_prozent: float = 0.0, durchlaeufe: int = DURCHLAEUFE, seed: int = SEED,
               horizont: int = HORIZONT, roh: bool = False) -> Ergebnis:
    rng = np.random.default_rng(seed)
    R = durchlaeufe
    tage = messtage(md.letzter, horizont)
    t = np.array([(d - md.letzter).days for d in tage], dtype=float)
    A = len(md.arten)
    ai = {a: i for i, a in enumerate(md.arten)}
    teile = []          # (quelle, art_index[N], run[N], start[N], ende[N])

    def dazu(q: int, art: str, runs: np.ndarray, start: np.ndarray, alter: np.ndarray | None = None,
             plan: float | np.ndarray | None = None):
        """plan (0.86): geplante Restdauer ab start – das Ende ist das frühere aus Plan und vorzeitigem Abgang."""
        if not len(runs):
            return
        kv = md.kurven[art]
        if alter is None:
            dauer = kv.ziehen(np.zeros(len(runs)), rng) if kv.n else np.full(len(runs), 10.0 ** 6)
            ende = start + dauer
        else:
            dauer = kv.ziehen(alter, rng) if kv.n else np.full(len(runs), 10.0 ** 6)
            ende = start + (dauer - alter)
        if plan is not None:
            ende = np.minimum(ende, start + plan)
        teile.append((q, np.full(len(runs), ai[art]), runs, start.astype(float), ende.astype(float)))

    def neu_plan(art: str):                   # neue Zugänge: reguläres Ende nach der typischen Solldauer
        return float(md.soll[art]) if md.soll.get(art) else None

    alle_runs = np.arange(R)
    zugang = np.zeros((A, horizont + 1, R))     # Zugänge je Art, Monat (für die Kappe)

    def monat_von(start: np.ndarray) -> np.ndarray:
        return np.clip(np.searchsorted(t, start, side="left"), 0, horizont)

    # 1 Bestand (laufend) und 2 bekannte künftige Eintritte – mit geplantem Ende (Pivot, sonst Solldauer)
    bekannt_frei = np.zeros((A, horizont + 1))    # 0.86: bekannte Eintritte ohne Vorstufe → von „weitere“ abziehen
    for i, f in enumerate(md.faelle):
        if f.laufend and f.ein <= md.letzter:
            alter_tage = float((md.letzter - f.ein).days)
            s_f = f.soll or md.soll.get(f.art)
            plan = float((f.geplant - md.letzter).days + 1) if f.geplant else                 (max(s_f - alter_tage, 15.0) if s_f else None)
            dazu(0, f.art, alle_runs, np.zeros(R), np.full(R, alter_tage), plan)
        elif f.ein > md.letzter:
            s = np.full(R, float((f.ein - md.letzter).days))
            dazu(1, f.art, alle_runs, s, plan=float((f.geplant - f.ein).days + 1) if f.geplant else neu_plan(f.art))
            m_ = monat_von(s[:1])[0]
            zugang[ai[f.art], m_] += 1
            if i not in md.erklaert:
                bekannt_frei[ai[f.art], m_] += 1

    # 3 Pipeline aus laufenden/kürzlich beendeten Vorstufen ohne Folge
    def folgen(von_gruppe: str, start_vorstufe: np.ndarray, runs: np.ndarray, quelle: int, schon: np.ndarray):
        u = md.uebergaenge.get(von_gruppe)
        if u is None or not u.quote or not len(u.verzoegerung) or not len(runs):
            return
        F = lambda x: np.searchsorted(np.sort(u.verzoegerung), x, side="right") / len(u.verzoegerung)  # noqa: E731
        f_s = F(schon)
        p = u.quote * (1 - f_s) / np.maximum(1e-9, 1 - u.quote * f_s)
        ja = rng.random(len(runs)) < p
        if not ja.any():
            return
        v = np.sort(u.verzoegerung)
        idx = np.searchsorted(v, schon[ja], side="right")            # nur Verzögerungen > bisher vergangene Zeit
        rest = len(v) - idx
        ok = rest > 0
        wahl = idx[ok] + (rng.random(ok.sum()) * rest[ok]).astype(int)
        start = start_vorstufe[ja][ok] + v[wahl]
        r = runs[ja][ok]
        ziele = list(u.ziele)
        gew = np.array([u.ziele[z] for z in ziele], dtype=float)
        art_wahl = rng.choice(len(ziele), size=len(r), p=gew / gew.sum())
        for k, z in enumerate(ziele):
            m = art_wahl == k
            if m.any() and z in ai:
                dazu(quelle, z, r[m], start[m], plan=neu_plan(z))
                np.add.at(zugang[ai[z]], (monat_von(start[m]), r[m]), 1)
                if md.gruppe[z] in VORSTUFEN:              # z. B. Vorbereitung → Hauptmaßnahme
                    folgen(md.gruppe[z], start[m], r[m], quelle, np.zeros(m.sum()))

    for i, f in enumerate(md.faelle):
        if f.gruppe in VORSTUFEN and i not in md.folge and f.ein <= md.letzter \
                and (md.letzter - f.ein).days <= UEBERGANG_TAGE:
            s0 = float((f.ein - md.letzter).days)
            folgen(f.gruppe, np.full(R, s0), alle_runs, 2, np.full(R, float((md.letzter - f.ein).days)))

    # 4 übrige Zugänge (Saison × Szenario × gemeinsamer Jahresfaktor), abzüglich schon bekannter, Kappe je Startmonat
    faktor = max(0.0, 1 + faktor_prozent / 100)
    jahr = rng.lognormal(-JAHR_STREUUNG ** 2 / 2, JAHR_STREUUNG, R) if JAHR_STREUUNG > 0 else np.ones(R)
    ueber = {}
    for a in md.arten:
        for k in range(1, horizont + 1):
            lam = md.raten[a][tage[k].month - 1] * faktor
            if lam <= 0:
                continue
            n = np.maximum(0, rng.poisson(lam * jahr) - int(bekannt_frei[ai[a], k]))
            kap = md.kappe.get(a)
            if kap is not None:
                frei = np.maximum(0, kap - zugang[ai[a], k])
                ueber[a] = ueber.get(a, 0.0) + float(np.mean(np.maximum(0, n - frei)))
                n = np.minimum(n, frei).astype(int)
            if not n.any():
                continue
            runs = np.repeat(alle_runs, n)
            start = t[k - 1] + rng.random(len(runs)) * (t[k] - t[k - 1])
            dazu(3, a, runs, start, plan=neu_plan(a))
            if md.gruppe[a] in VORSTUFEN:
                folgen(md.gruppe[a], start, runs, 3, np.zeros(len(runs)))

    # zählen: anwesend am Messtag, wenn start ≤ t < ende
    bestand = np.zeros((len(QUELLEN), A + 1, R, len(t)))
    for q, art, runs, start, ende in teile:
        anw = (start[:, None] <= t[None, :]) & (t[None, :] < ende[:, None])
        np.add.at(bestand[q, :A], (art, runs), anw.astype(float))
    bestand[:, A] = bestand[:, :A].sum(axis=1)
    gesamt = bestand.sum(axis=0)                                     # (A+1, R, T)
    return Ergebnis(tage, md.arten, np.median(gesamt, axis=1), np.percentile(gesamt, 10, axis=1),
                    np.percentile(gesamt, 90, axis=1), bestand.mean(axis=2), ueber, gesamt if roh else None)


# ---- Kennzahlen, Ist-Verlauf, Frühindikator ------------------------------------------------------------------------

def abgangsquote(md: Modell, art: str) -> float | None:
    """Vorzeitige Abgangsquote = 1 − Verbleib 30 Tage vor dem Soll-Ende (aus der Kurve, nicht naiv gezählt)."""
    s = md.soll.get(art)
    kv = md.kurven.get(art)
    if not s or kv is None or not kv.n:
        return None
    return float(1 - kv.verbleib(max(1, s - 30)))


def ist_verlauf(fs: list[Fall], letzter: date, art: str | None = None, monate: int = 12) -> list[tuple[date, int]]:
    erg = []
    j, m = letzter.year, letzter.month
    tage = []
    for _ in range(monate):
        tage.append(date(j, m, 15) if date(j, m, 15) <= letzter else None)
        m -= 1
        if m == 0:
            j, m = j - 1, 12
    for d in reversed([x for x in tage if x]):
        erg.append((d, sum(1 for f in fs if (art in (None, "", "Alle") or f.art == art) and f.ein <= d <= f.aus)))
    return erg


def fruehindikator(fs: list[Fall], letzter: date, tage: int = 90) -> tuple[str, float | None, int, int]:
    """Assessment-Eintritte der letzten 90 Tage gegen dieselben 90 Tage im Vorjahr → (Szenario, Verhältnis, jetzt, vorher)."""
    def zaehlen(bis: date):
        return sum(1 for f in fs if f.gruppe == "Assessment" and bis - timedelta(days=tage) < f.ein <= bis)
    jetzt, vorher = zaehlen(letzter), zaehlen(letzter - timedelta(days=365))
    if not vorher:
        return "basis", None, jetzt, vorher
    r = jetzt / vorher
    if not ueber_zufall(jetzt, vorher):          # 0.86: Unterschied im Rahmen des Zufalls → „normal“
        return "basis", r, jetzt, vorher
    return ("schwach" if r < .9 else "stark" if r > 1.1 else "basis"), r, jetzt, vorher


def ueber_zufall(a: int, b: int) -> bool:
    """Zwei Zählungen unterscheiden sich erst dann sicher, wenn |a − b| > 2·√(a + b) (Poisson, grob 95 %)."""
    return abs(a - b) > 2 * (a + b) ** .5


# ---- Wenn-dann --------------------------------------------------------------------------------------------------

@dataclass
class WennDann:
    monat: date
    ziel: float
    anteil: float                 # 0.86: Anteil der Läufe, die im Monat so nah am Wert lagen (± Toleranz)
    erreicht: float               # Median der ausgewählten Läufe im gewählten Monat
    erreichbar: bool              # liegt der Wert in dem, was das Modell für möglich hält (1.–99. Perzentil)?
    verlauf: list[tuple[date, float, float, float]]   # (Monat, Median, p10, p90) der ausgewählten Läufe
    sicher_im_monat: float        # Bestand + fest Angemeldete im Monat
    spanne: tuple[float, float] = (0.0, 0.0)          # 1.–99. Perzentil aller Läufe im Monat


def wenn_dann(md: Modell, monat_index: int, ziel: float, art: str | None = None,
              durchlaeufe: int = WD_LAEUFE) -> WennDann:
    """„Wenn wir im Monat m X Teilnehmende haben – wie geht es weiter?“ (0.86: bedingte Simulation)

    Statt eine dauerhafte Niveauänderung zu unterstellen, werden viele Läufe gerechnet und nur die weiterverfolgt,
    die im Monat m nahe an X lagen – so kommen X auf dem Weg zustande, auf dem es auch wirklich passieren würde.
    Liegt X außerhalb aller plausiblen Läufe, sagt das Ergebnis das (``erreichbar`` = False)."""
    e = simulieren(md, 0.0, durchlaeufe, roh=True)
    z = e.zeile(art)
    werte = e.roh[z, :, monat_index]
    lo, hi = float(np.percentile(werte, 1)), float(np.percentile(werte, 99))
    toleranz = max(1.0, 0.03 * ziel)
    anteil = float(np.mean(np.abs(werte - ziel) <= toleranz))
    wahl = np.argsort(np.abs(werte - ziel), kind="stable")[:WD_AUSWAHL]
    teil = e.roh[z, wahl, :]
    verlauf = [(d, float(np.median(teil[:, i])), float(np.percentile(teil[:, i], 10)),
                float(np.percentile(teil[:, i], 90))) for i, d in enumerate(e.monate)]
    sicher = float(e.zerlegung[0, z, monat_index] + e.zerlegung[1, z, monat_index])
    return WennDann(e.monate[monat_index], ziel, anteil, float(np.median(teil[:, monat_index])),
                    lo <= ziel <= hi, verlauf, sicher, (lo, hi))


# ---- Rückblick-Test ------------------------------------------------------------------------------------------------

@dataclass
class Rueckblick:
    horizont: int
    n: int
    mae: float | None
    wape: float | None
    treffer80: float | None
    mae_vorjahr: float | None     # Vergleich: „wie vor 12 Monaten“
    mae_bleibt: float | None = None   # 0.86: Vergleich „Bestand bleibt wie heute“
    treffer: int = 0                  # 0.86: Anzahl Stichtage mit Ist in der 80 %-Spanne


def _abgeschnitten(fs: list[Fall], s: date) -> list[Fall]:
    erg = []
    for f in fs:
        if f.ein > s:
            continue
        aus = min(f.aus, s)
        erg.append(Fall(f.person, f.kurs, f.art, f.gruppe, f.ein, aus, aus >= s - timedelta(days=bk.LAUFEND_TAGE), f.soll))
    return erg


def rueckblick(fs: list[Fall], letzter: date, tabelle: list[dict], monate: int = 18, schritt: int = 1,
               durchlaeufe: int = 200) -> list[Rueckblick]:
    def anwesend(d: date) -> int:
        return sum(1 for f in fs if f.ein <= d <= f.aus)
    fehler: dict[int, list] = {h: [] for h in (1, 3, 6, 12)}
    for k in range(schritt, monate + 1, schritt):
        j, m = letzter.year, letzter.month - k
        while m <= 0:
            j, m = j - 1, m + 12
        s = date(j, m, 15)
        teil = _abgeschnitten(fs, s)
        if len(teil) < 20:
            continue
        e = simulieren(modell(teil, s, tabelle), 0, durchlaeufe, horizont=12)
        for h in fehler:
            if h >= len(e.monate) or e.monate[h] > letzter:
                continue
            ist = anwesend(e.monate[h])
            vj = e.monate[h].replace(year=e.monate[h].year - 1)
            fehler[h].append((ist, float(e.median[-1, h]), float(e.p10[-1, h]), float(e.p90[-1, h]), anwesend(vj),
                              anwesend(s)))
    erg = []
    for h, xs in fehler.items():
        if not xs:
            erg.append(Rueckblick(h, 0, None, None, None, None))
            continue
        ist = np.array([x[0] for x in xs], dtype=float)
        p = np.array([x[1] for x in xs])
        summe = ist.sum()
        drin = [x[2] <= x[0] <= x[3] for x in xs]
        erg.append(Rueckblick(h, len(xs), float(np.mean(np.abs(ist - p))),
                              float(np.sum(np.abs(ist - p)) / summe) if summe else None,
                              float(np.mean(drin)), float(np.mean([abs(x[0] - x[4]) for x in xs])),
                              float(np.mean([abs(x[0] - x[5]) for x in xs])), int(sum(drin))))
    return erg


# ---- Ein Aufruf für die Oberfläche (mit Zwischenspeicher) ------------------------------------------------------------

_CACHE: dict = {}


def alles(aufenthalte, meta: dict, tabelle: list[dict], gemessen: dict, szenarien: dict, stichtag: date) -> dict:
    letzter = min(stichtag, date.fromisoformat(meta["bis"])) if meta.get("bis") else stichtag
    schluessel = (len(aufenthalte), meta.get("stichtag"), meta.get("bis"), repr(tabelle), repr(sorted(gemessen.items(),
                  key=lambda x: x[0]) if gemessen else []), repr(sorted((k, v.get("faktor")) for k, v in szenarien.items())),
                  letzter)
    if schluessel in _CACHE:
        return _CACHE[schluessel]
    fs = faelle(aufenthalte, tabelle, gemessen, letzter, date.fromisoformat(meta["bis"]) if meta.get("bis") else None)
    md = modell(fs, letzter, tabelle)
    erg = {"modell": md, "faelle": fs, "letzter": letzter,
           "szenarien": {k: simulieren(md, float(szenarien.get(k, SZENARIEN_STANDARD[k]).get("faktor", 0)),
                                        DURCHLAEUFE if k == "basis" else 400) for k in ("basis", "schwach", "stark")},
           "rueckblick": rueckblick(fs, letzter, tabelle), "frueh": fruehindikator(fs, letzter)}
    _CACHE.clear()
    _CACHE[schluessel] = erg
    return erg


def szenarien_lesen(roh: dict) -> dict:
    eigen = roh.get("bestand_szenarien") or {}
    erg = {}
    for k, std in SZENARIEN_STANDARD.items():
        e = eigen.get(k) or {}
        try:
            f = float(e.get("faktor", std["faktor"]))
        except (TypeError, ValueError):
            f = std["faktor"]
        erg[k] = {"faktor": max(-90.0, min(200.0, f)) if k != "basis" else 0.0, "ausloeser": str(e.get("ausloeser") or "")[:300]}
    return erg


def szenarien_schritt(werte: dict) -> str:
    from . import massnahmen_kern as mk
    from .kern import _schritt

    def tun():
        roh = mk._roh()
        roh["bestand_szenarien"] = szenarien_lesen({"bestand_szenarien": werte})
        mk._schreiben(roh)
    _schritt("Szenarien der Maßnahmen-Prognose geändert", tun, [mk.DATEI])
    return "Szenarien gespeichert"
