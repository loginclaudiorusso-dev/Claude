"""Monatsprognose der Reha-Belegung je Standort.

Was sich gegenüber der Vorversion ändert und warum:

1. **Modellauswahl per Backtest statt In-Sample-AIC.** Die alte AIC-Auswahl rechnete
   Holt-Winters mit 3 Parametern, obwohl das Modell rund 17 schätzt (Glättungsparameter,
   Startniveau, Trend, 12 Saisonwerte). Das begünstigt systematisch das komplexeste Modell.
   Jetzt wird jedes Kandidatenmodell rollierend auf den letzten Monaten "blind" getestet
   (nur mit Daten, die zum jeweiligen Zeitpunkt vorlagen) und nach mittlerem absolutem
   Fehler gewählt.
2. **Unsicherheit wächst mit dem Horizont.** Die Bänder basieren auf den Backtest-Fehlern je
   Prognosehorizont (1…12 Monate, geglättet mit √h und darüber hinaus fortgeschrieben).
   Vorher war das Band für nächsten Monat und in drei Jahren gleich breit.
3. **Strukturbrüche werden abgeschnitten.** Goslar hatte vor der Eröffnung (bis 08/2021)
   Nullwerte; die flossen bisher als "Historie" in die Modelle ein.
4. **Der laufende Monat ist kein Trainingspunkt**, sondern wird aus Ist-Tagen und
   Prognose für die Resttage zusammengesetzt.
5. **Gebuchter Bestand wird genutzt.** Die Pivot kennt künftige Belegung bereits
   (Teilnehmende mit geplantem Ende) – das ist die sicherste Information für die nahe
   Zukunft. Die Prognose fällt nie unter diesen gesicherten Bestand.
6. **Gesamt** bekommt ein Band aus den tatsächlichen Backtest-Fehlern der Summe, statt die
   Standorte als unabhängig anzunehmen.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .konfig import GESAMT, STANDORTE

log = logging.getLogger(__name__)

HORIZONT_MONATE = 36
BACKTEST_URSPRUENGE = 18
BACKTEST_HORIZONT = 12
Z80, Z95 = 1.2816, 1.96


@dataclass
class Monatswert:
    monat: date                 # Monatserster
    art: str                    # "ist" | "laufend" | "prognose"
    erwartet: float
    lo80: float
    hi80: float
    lo95: float
    hi95: float
    ist: float | None = None    # Ist-Mittel (bei "laufend": der bisherigen Tage)
    gesichert: float | None = None  # gebuchter Bestand (Mittel der künftigen Tage)
    modell: float | None = None     # reine Modellprognose vor Bestandsuntergrenze


@dataclass
class Modellinfo:
    name: str
    beschreibung: str
    mae: float | None = None                       # Ø absoluter Fehler im Backtest (alle Horizonte)
    mae_1m: float | None = None                    # dto. nur 1 Monat voraus
    abdeckung80: float | None = None               # Anteil Backtest-Fälle im 80-%-Band
    kandidaten: list[tuple[str, float]] = field(default_factory=list)
    monate_historie: int = 0
    start_monat: date | None = None
    rueckblick: list[tuple[date, float, float]] = field(default_factory=list)  # (Monat, Ist, blind 1M)
    sigma_je_horizont: list[float] = field(default_factory=list)


@dataclass
class Prognose:
    stichtag: date
    werte: dict[str, list[Monatswert]]
    modelle: dict[str, Modellinfo]

    def monat(self, standort: str, jahr: int, monat: int) -> Monatswert | None:
        return next((w for w in self.werte.get(standort, []) if w.monat.year == jahr and w.monat.month == monat), None)


# ---------------------------------------------------------------------------------------
# Modelle: f(train, h) -> Array der Länge h (Monate nach dem letzten Trainingsmonat)
# ---------------------------------------------------------------------------------------

def _mittel6(train: np.ndarray, h: int) -> np.ndarray:
    return np.full(h, float(np.mean(train[-6:])))


def _saison_naiv(train: np.ndarray, h: int) -> np.ndarray:
    letzte12 = train[-12:]
    return np.array([letzte12[k % 12] for k in range(h)], dtype=float)


def _saisonindex(train: np.ndarray) -> np.ndarray:
    """Saisonabweichung je Monatsposition (Position 0 = Monat nach Trainingsende), aus den
    Abweichungen vom gleitenden 12-Monats-Mittel; jüngere Jahre stärker gewichtet."""
    n = len(train)
    abw = np.full(n, np.nan)
    for t in range(11, n):
        abw[t] = train[t] - train[t - 11:t + 1].mean()
    idx = np.zeros(12)
    for pos in range(12):
        # Trainingsindex t entspricht Position (t - n) % 12
        ts = [t for t in range(n) if (t - n) % 12 == pos and not np.isnan(abw[t])]
        if ts:
            gewichte = np.linspace(1.0, 2.0, len(ts))
            idx[pos] = float(np.average(abw[ts], weights=gewichte))
    return idx - idx.mean()


def _saison_niveau(train: np.ndarray, h: int) -> np.ndarray:
    idx = _saisonindex(train)
    n = len(train)
    bereinigt = [train[t] - idx[(t - n) % 12] for t in range(n - 6, n)]
    niveau = float(np.mean(bereinigt))
    return np.array([niveau + idx[k % 12] for k in range(h)])


_ETS_CACHE: dict[tuple[bytes, int], np.ndarray] = {}


def _ets(train: np.ndarray, h: int) -> np.ndarray:
    schluessel = (np.asarray(train, dtype=float).tobytes(), h)
    if schluessel not in _ETS_CACHE:
        if len(_ETS_CACHE) > 512:
            _ETS_CACHE.clear()
        _ETS_CACHE[schluessel] = _ets_rechnen(train, h)
    return _ETS_CACHE[schluessel]


def _ets_rechnen(train: np.ndarray, h: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(
            train, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
            initialization_method="estimated",
        ).fit()
        return np.asarray(fit.forecast(h), dtype=float)


def _kombination(train: np.ndarray, h: int) -> np.ndarray:
    return (_ets(train, h) + _saison_niveau(train, h)) / 2


@dataclass(frozen=True)
class _Kandidat:
    name: str
    beschreibung: str
    min_laenge: int
    f: object


KANDIDATEN = [
    _Kandidat("Kombination ETS + Saison/Niveau",
              "Mittel aus Holt-Winters (gedämpfter Trend) und Saisonprofil auf aktuellem Niveau", 30, _kombination),
    _Kandidat("Holt-Winters (gedämpfter Trend)",
              "Exponentielle Glättung mit Jahressaison und abflachendem Trend", 30, _ets),
    _Kandidat("Saisonprofil auf aktuellem Niveau",
              "Typischer Jahresverlauf, verschoben auf das Niveau der letzten 6 Monate", 24, _saison_niveau),
    _Kandidat("Vorjahresmonat", "Wert des gleichen Monats im Vorjahr", 13, _saison_naiv),
    _Kandidat("Mittel der letzten 6 Monate", "Konstantes Niveau ohne Saison", 3, _mittel6),
]


# ---------------------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------------------

def monatsreihe(tage: pd.Series, stichtag: date) -> tuple[pd.Series, tuple[date, float, int, int] | None]:
    """(abgeschlossene Monatsmittel, laufender Monat als (Monat, Ist-Mittel, Ist-Tage, Tage))."""
    ist = tage[: pd.Timestamp(stichtag)]
    if ist.empty:
        return pd.Series(dtype=float), None
    mittel = ist.groupby(ist.index.to_period("M")).mean()
    stich_p = pd.Timestamp(stichtag).to_period("M")
    laufend = None
    if pd.Timestamp(stichtag) != stich_p.end_time.normalize():
        tage_im_monat = stich_p.days_in_month
        n_ist = int((ist.index.to_period("M") == stich_p).sum())
        laufend = (stich_p.start_time.date(), float(mittel.get(stich_p, np.nan)), n_ist, tage_im_monat)
        mittel = mittel[mittel.index < stich_p]
    mittel.index = mittel.index.to_timestamp()
    return mittel.astype(float), laufend


def struktur_start(werte: np.ndarray) -> int:
    """Erster Index, ab dem die Reihe im Regelbetrieb ist (z. B. nach einer Eröffnung)."""
    if len(werte) < 3:
        return 0
    referenz = float(np.median(werte[-12:]))
    if referenz <= 0:
        return 0
    for i in range(len(werte) - 1):
        if werte[i] >= 0.3 * referenz and werte[i + 1] >= 0.3 * referenz:
            return i
    return 0


@dataclass
class _Band:
    """Halbe Bandbreite = k·√h. k80/k95 sind empirische Quantile der auf √h normierten
    Backtest-Fehler – das 80-%-Band enthält damit im Backtest tatsächlich ~80 % der Fälle."""
    k80: float = 0.0
    k95: float = 0.0

    def breite(self, h: float, stufe: int = 80) -> float:
        return (self.k80 if stufe == 80 else self.k95) * np.sqrt(max(h, 0.0))

    def abdeckung(self, fehler: dict[int, list[float]]) -> float | None:
        faelle = [abs(e) <= self.breite(h) for h, es in fehler.items() for e in es]
        return float(np.mean(faelle)) if faelle else None


def _band(fehler: dict[int, list[float]]) -> _Band:
    normiert = [abs(e) / np.sqrt(h) for h, es in fehler.items() for e in es]
    if len(normiert) < 5:
        return _Band()
    k80 = float(np.quantile(normiert, 0.80))
    k95 = max(float(np.quantile(normiert, 0.95)), k80 * Z95 / Z80)
    return _Band(k80, k95)


@dataclass
class _Backtest:
    kandidat: _Kandidat
    mae: float
    fehler: dict[int, list[float]]                  # Horizont -> Fehler (Prognose - Ist)
    je_ursprung: dict[tuple[int, int], float]       # (Zielindex, h) -> Fehler
    blind_1m: dict[int, float]                      # Zielindex -> Prognose 1 Monat voraus


def _backtest(werte: np.ndarray, kandidat: _Kandidat, ursprung_ab: int) -> _Backtest | None:
    n = len(werte)
    fehler: dict[int, list[float]] = {h: [] for h in range(1, BACKTEST_HORIZONT + 1)}
    je_ursprung: dict[tuple[int, int], float] = {}
    blind: dict[int, float] = {}
    for o in range(ursprung_ab, n):
        train = werte[:o]
        if len(train) < kandidat.min_laenge:
            return None
        h_max = min(BACKTEST_HORIZONT, n - o)
        try:
            vorhersage = kandidat.f(train, h_max)
        except Exception as exc:  # Modell konvergiert nicht o. Ä. -> Kandidat verwerfen
            log.debug("Backtest %s fehlgeschlagen: %s", kandidat.name, exc)
            return None
        for k in range(h_max):
            e = float(vorhersage[k] - werte[o + k])
            fehler[k + 1].append(e)
            je_ursprung[(o + k, k + 1)] = e
        blind[o] = float(vorhersage[0])
    alle = [abs(e) for es in fehler.values() for e in es]
    if not alle:
        return None
    return _Backtest(kandidat, float(np.mean(alle)), fehler, je_ursprung, blind)


# ---------------------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------------------

def berechne(reha: pd.DataFrame, bestand: pd.DataFrame, stichtag: date) -> Prognose:
    """reha: Tageswerte je Standort (Ist bis Stichtag, danach gebuchter Bestand laut Pivot).
    bestand: zusätzlicher gesicherter Bestand je Tag und Standort ab Stichtag (z. B.
    importierte Anreisen), gleiche Spalten wie reha; darf leer sein."""
    werte: dict[str, list[Monatswert]] = {}
    modelle: dict[str, Modellinfo] = {}
    backtests: dict[str, tuple[_Backtest | None, pd.DatetimeIndex]] = {}
    erster_prognosemonat = pd.Timestamp(stichtag).to_period("M").start_time
    zukunft_monate = pd.date_range(erster_prognosemonat, periods=HORIZONT_MONATE, freq="MS")

    for standort in STANDORTE:
        tage = reha[standort].astype(float)
        zusatz = bestand[standort] if standort in bestand else pd.Series(dtype=float)
        mittel, laufend = monatsreihe(tage, stichtag)
        start = struktur_start(mittel.to_numpy())
        mittel = mittel.iloc[start:]
        y = mittel.to_numpy()
        n = len(y)

        # Backtest aller passenden Kandidaten auf denselben Ursprüngen
        ursprung_ab = max(n - BACKTEST_URSPRUENGE, 0)
        ergebnisse = []
        for kandidat in KANDIDATEN:
            if ursprung_ab < kandidat.min_laenge:
                continue
            bt = _backtest(y, kandidat, ursprung_ab)
            if bt:
                ergebnisse.append(bt)
        ergebnisse.sort(key=lambda b: b.mae)
        bester = ergebnisse[0] if ergebnisse else None

        if bester:
            kandidat = bester.kandidat
            band = _band(bester.fehler)
            try:
                vorhersage = kandidat.f(y, HORIZONT_MONATE + 1)
            except Exception:
                kandidat, vorhersage = KANDIDATEN[-1], _mittel6(y, HORIZONT_MONATE + 1)
            info = Modellinfo(
                name=kandidat.name, beschreibung=kandidat.beschreibung, mae=bester.mae,
                mae_1m=float(np.mean(np.abs(bester.fehler[1]))) if bester.fehler[1] else None,
                abdeckung80=band.abdeckung(bester.fehler),
                kandidaten=[(b.kandidat.name, b.mae) for b in ergebnisse],
                monate_historie=n, start_monat=mittel.index[0].date(),
                rueckblick=[(mittel.index[o].date(), float(y[o]), p) for o, p in sorted(bester.blind_1m.items())][-12:],
                sigma_je_horizont=[band.breite(h) for h in range(1, BACKTEST_HORIZONT + 1)],
            )
        elif n:
            streuung = float(np.std(y[-12:])) if n > 1 else 0.0
            band = _Band(Z80 * streuung, Z95 * streuung)
            vorhersage = _mittel6(y, HORIZONT_MONATE + 1)
            info = Modellinfo(name="Mittel der letzten Monate",
                              beschreibung="Zu wenig Historie für Backtest und Saisonmodelle",
                              monate_historie=n, start_monat=mittel.index[0].date())
        else:
            band, vorhersage = _Band(), np.zeros(HORIZONT_MONATE + 1)
            info = Modellinfo(name="keine Daten", beschreibung="Keine Ist-Werte vorhanden")
        modelle[standort] = info
        backtests[standort] = (bester, mittel.index)

        liste: list[Monatswert] = [
            Monatswert(monat=ts.date(), art="ist", erwartet=v, lo80=v, hi80=v, lo95=v, hi95=v, ist=v)
            for ts, v in zip(mittel.index, y)
        ]
        # vorhersage[0] gilt für den Monat nach dem letzten abgeschlossenen Monat.
        versatz = 0 if (n == 0 or mittel.index[-1] < erster_prognosemonat) else 1
        for k, monat in enumerate(zukunft_monate):
            h = float(k + 1 + versatz)
            modellwert = float(vorhersage[min(k + versatz, len(vorhersage) - 1)])
            gesichert = _gesichert(tage, zusatz, monat, stichtag)
            if laufend and monat.date() == laufend[0]:
                _, ist_mittel, n_ist, n_tage = laufend
                anteil_rest = (n_tage - n_ist) / n_tage
                rest = max(modellwert, gesichert) if gesichert is not None else modellwert
                erwartet = ist_mittel * (1 - anteil_rest) + rest * anteil_rest
                b80, b95 = band.breite(h) * anteil_rest, band.breite(h, 95) * anteil_rest
                art, ist = "laufend", ist_mittel
            else:
                erwartet = max(modellwert, gesichert) if gesichert is not None else modellwert
                b80, b95 = band.breite(h), band.breite(h, 95)
                art, ist = "prognose", None
            liste.append(_mit_band(monat.date(), art, erwartet, b80, b95, ist=ist,
                                   gesichert=gesichert, modell=modellwert))
        werte[standort] = liste

    werte[GESAMT], modelle[GESAMT] = _gesamt(werte, backtests, stichtag)
    return Prognose(stichtag=stichtag, werte=werte, modelle=modelle)


def _mit_band(monat: date, art: str, erwartet: float, b80: float, b95: float, **kw) -> Monatswert:
    erwartet = max(erwartet, 0.0)
    return Monatswert(
        monat=monat, art=art, erwartet=erwartet,
        lo80=max(erwartet - b80, 0.0), hi80=erwartet + b80,
        lo95=max(erwartet - b95, 0.0), hi95=erwartet + b95, **kw,
    )


def _gesichert(tage: pd.Series, zusatz: pd.Series, monat: pd.Timestamp, stichtag: date) -> float | None:
    """Mittel des gebuchten Bestands über die Tage des Monats nach dem Stichtag."""
    ende = monat + pd.offsets.MonthEnd(0)
    von = max(monat, pd.Timestamp(stichtag) + pd.Timedelta(days=1))
    if von > ende:
        return None
    index = pd.date_range(von, ende, freq="D")
    basis = tage.reindex(index, fill_value=0.0)
    if not zusatz.empty:
        basis = basis + zusatz.reindex(index, fill_value=0.0)
    return float(basis.mean())


def _gesamt(werte: dict[str, list[Monatswert]], backtests: dict, stichtag: date) -> tuple[list[Monatswert], Modellinfo]:
    # Backtest-Fehler der Summe: nur Zielmonate/Horizonte, die alle Standorte haben.
    fehler: dict[int, list[float]] = {h: [] for h in range(1, BACKTEST_HORIZONT + 1)}
    alle_bt = [backtests[s] for s in STANDORTE]
    if all(bt is not None for bt, _ in alle_bt):
        je_monat = []
        for bt, index in alle_bt:
            je_monat.append({(index[o], h): e for (o, h), e in bt.je_ursprung.items()})
        gemeinsam = set(je_monat[0]).intersection(*je_monat[1:])
        for schluessel in gemeinsam:
            fehler[schluessel[1]].append(sum(m[schluessel] for m in je_monat))
    band = _band(fehler)

    monate = sorted({w.monat for s in STANDORTE for w in werte[s]})
    je = {s: {w.monat: w for w in werte[s]} for s in STANDORTE}
    erster = date(stichtag.year, stichtag.month, 1)
    liste = []
    for monat in monate:
        teile = [je[s].get(monat) for s in STANDORTE]
        if any(t is None for t in teile):
            continue  # Gesamt nur, wo alle Standorte Werte haben
        erwartet = sum(t.erwartet for t in teile)
        if all(t.art == "ist" for t in teile):
            liste.append(Monatswert(monat, "ist", erwartet, erwartet, erwartet, erwartet, erwartet, ist=erwartet))
            continue
        art = "laufend" if any(t.art == "laufend" for t in teile) else "prognose"
        h = float(sum(1 for m in monate if erster <= m <= monat))
        if band.k80:
            b80, b95 = band.breite(h), band.breite(h, 95)
            if art == "laufend":  # auf den Restmonat skalieren wie bei den Standorten
                b80 = min(b80, sum(t.hi80 - t.erwartet for t in teile))
                b95 = min(b95, sum(t.hi95 - t.erwartet for t in teile))
        else:  # kein gemeinsamer Backtest: Unabhängigkeit annehmen
            b80 = float(np.sqrt(sum((t.hi80 - t.erwartet) ** 2 for t in teile)))
            b95 = float(np.sqrt(sum((t.hi95 - t.erwartet) ** 2 for t in teile)))
        liste.append(_mit_band(
            monat, art, erwartet, b80, b95,
            ist=sum(t.ist or 0.0 for t in teile) if art == "laufend" else None,
            gesichert=sum(t.gesichert or 0.0 for t in teile),
            modell=sum(t.modell or 0.0 for t in teile),
        ))
    namen = list(dict.fromkeys(backtests[s][0].kandidat.name for s in STANDORTE if backtests[s][0]))
    fehler_alle = [abs(e) for es in fehler.values() for e in es]
    info = Modellinfo(
        name="Summe der Standortprognosen",
        beschreibung="Modelle je Standort: " + (", ".join(namen) or "–"),
        mae=float(np.mean(fehler_alle)) if fehler_alle else None,
        mae_1m=float(np.mean(np.abs(fehler[1]))) if fehler[1] else None,
        abdeckung80=band.abdeckung(fehler),
        sigma_je_horizont=[band.breite(h) for h in range(1, BACKTEST_HORIZONT + 1)],
    )
    return liste, info
