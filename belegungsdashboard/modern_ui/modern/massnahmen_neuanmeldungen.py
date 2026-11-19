"""1.29: Maßnahmen – Neuanmeldungen je Halbjahr, Startwelle und Monat: Schätzverfahren (Saison, Holt-Winters …),
Rückwärtstest, Kapazitäten, Sichtbarkeit.

Baut auf massnahmen_kern auf. Aus massnahmen_kern.py ausgelagert (nur verschoben, keine Funktionsänderung); dort
weiter erreichbar."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from .massnahmen_kern import (  # baut auf massnahmen_kern auf
    AKTIV_MIN, AKTIV_MONATE, DATEI, KAP_ZUSCHLAG, Kurs, SAISON_VERFAHREN, VERFAHREN, _jahr_verschoben, _roh,
    _schreiben, gruppen, kurse, nachbuchung, neu_im_kurs, pickup_kurve,
)


WINTER_AB, SOMMER_AB = 11, 5       # Monat, ab dem die Winter- bzw. Sommerwelle zählt


def halbjahr(d: date) -> tuple[int, int]:
    """Startwelle: (Jahr, 1) = Winterstart Nov(Vorjahr)–Apr, (Jahr, 2) = Sommerstart Mai–Okt."""
    if d.month >= WINTER_AB:
        return d.year + 1, 1
    return (d.year, 1) if d.month < SOMMER_AB else (d.year, 2)


MONAT_KURZ = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")
MONAT_LANG = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
              "Dezember")


def hj_text(h: tuple) -> str:
    if len(h) == 3:                                   # 1.05: Monat (Jahr, Monat, "m")
        return f"{MONAT_LANG[h[1] - 1]} {h[0]}"
    return f"{'Winterstart' if h[1] == 1 else 'Sommerstart'} {h[0]}"


def hj_kurz(h: tuple) -> str:
    if len(h) == 3:
        return f"{MONAT_KURZ[h[1] - 1]} {h[0] % 100:02d}"
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
            return float(sum(neu_im_kurs(k) for k in alle_eigene if a < k.start <= b))  # noqa: B023 – im selben Durchlauf aufgerufen
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


# ---- 1.05: Neuanmeldungen je Monat (statt je Startwelle) -------------------------------------------------------------

def _monat_plus(d: date, n: int) -> date:
    i = d.year * 12 + d.month - 1 + n
    return date(i // 12, i % 12 + 1, 1)


def _monat_ende(d: date) -> date:
    return _monat_plus(d, 1) - timedelta(days=1)


def startmuster(ks: list, welle: int, vor: date) -> list[float]:
    """Anteil jedes der 6 Monate einer Startwelle (Winter 1 / Sommer 2) an ihren Neuanmeldungen – aus den vollständig
    vergangenen Wellen vor ``vor``. Ohne Daten gleich verteilt."""
    summe = [0.0] * 6
    for k in ks:
        h = halbjahr(k.start)
        if h[1] != welle or hj_ende(h) >= vor:
            continue
        a = hj_start(h)
        i = (k.start.year - a.year) * 12 + k.start.month - a.month
        if 0 <= i < 6:
            summe[i] += neu_im_kurs(k)
    ges = sum(summe)
    return [x / ges for x in summe] if ges > 0 else [1 / 6] * 6


def monatlich(daten: dict | None, stichtag: date, reihen: dict, monate_zurueck: int = 24) -> dict:
    """Dieselben Reihen je Monat. Vergangene Monate: Ist (Neuanmeldungen in Kursen, die in dem Monat begonnen haben).
    Offene Monate einer Welle: schon begonnen + schon gebucht im jeweiligen Monat, dazu der Rest der Wellen-Erwartung
    nach dem Startmuster früherer Wellen verteilt. Die Summe der Monate einer Welle ist genau die Wellen-Erwartung."""
    roh = daten if daten is not None else _roh()
    ks = kurse(roh)
    if not ks:
        return {}
    daten_ab = date.fromisoformat((roh.get("pivot") or {}).get("von") or min(k.start for k in ks).isoformat())
    starts = _starts(ks, daten_ab)
    ab = _monat_plus(date(stichtag.year, stichtag.month, 1), -monate_zurueck)
    erg = {}
    for fam, r in reihen.items():
        eigene = [k for k in starts if k.familie == fam]
        muster = {w: startmuster(eigene, w, stichtag) for w in (1, 2)}
        zeilen: list[HZeile] = []
        for z in r.zeilen:
            a = hj_start(z.hj)
            ms = [_monat_plus(a, i) for i in range(6)]
            ist = [float(sum(neu_im_kurs(k) for k in eigene if m <= k.start <= min(_monat_ende(m), stichtag))) for m in ms]
            gebucht = [float(sum(neu_im_kurs(k) for k in eigene if m <= k.start <= _monat_ende(m) and k.start > stichtag))
                       for m in ms]
            offen = [z.art != "ist" and _monat_ende(m) >= stichtag for m in ms]
            anteil = [muster[z.hj[1]][i] if offen[i] else 0.0 for i in range(6)]
            if any(offen) and sum(anteil) <= 0:
                anteil = [1.0 if o else 0.0 for o in offen]
            g = sum(anteil) or 1.0
            anteil = [x / g for x in anteil]
            bekannt = sum(ist) + sum(gebucht)

            def verteilt(gesamt: float, i: int) -> float:
                return ist[i] + gebucht[i] + max(0.0, gesamt - bekannt) * anteil[i]  # noqa: B023 – im selben Durchlauf aufgerufen
            for i, m in enumerate(ms):
                if _monat_ende(m) < ab:
                    continue
                if not offen[i]:
                    v = ist[i]
                    zeilen.append(HZeile((m.year, m.month, "m"), "ist", v, 0.0, v, v, v, False, v, v))
                else:
                    zeilen.append(HZeile((m.year, m.month, "m"), "prognose", ist[i], gebucht[i], verteilt(z.erwartet, i),
                                         verteilt(z.klein, i), verteilt(z.gross, i), z.geplant,
                                         verteilt(z.klein95, i), verteilt(z.gross95, i)))
        erg[fam] = replace(r, zeilen=zeilen)
    return erg
