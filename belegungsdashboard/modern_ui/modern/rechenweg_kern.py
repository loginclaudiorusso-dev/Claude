"""1.23: Rechenweg einer Monatsprognose – Schritt für Schritt mit den echten Zahlen. Rein, ohne Oberfläche.

Rechnet mit denselben Funktionen wie das Hauptprogramm (``belegung.prognose``, nur lesend) nach und zeigt jeden
Zwischenwert: Datenbasis, Rückwärtstest aller Modelle (mittlerer absoluter Fehler), Zerlegung des gewählten Modells
(Niveau, Saisonindex bzw. Holt-Winters-Parameter α, β, γ, φ), gebuchter Bestand, laufender Monat, Unsicherheitsband
aus den Rückwärtstest-Fehlern (Quantile, Mittelwert, Standardabweichung, Vergleich mit der Normalverteilung) und für
„Gesamt“ die Korrelation der Standortfehler (Kovarianz) – sie entscheidet, wie breit das Band der Summe ist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

Z80, Z95 = 1.2816, 1.9600
MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


@dataclass
class Schritt:
    titel: str
    formel: str = ""
    rechnung: str = ""                       # Formel mit eingesetzten Zahlen = Ergebnis
    details: list[str] = field(default_factory=list)
    kurz: str = ""                           # 1.76: Überschrift in Alltagssprache
    einfach: str = ""                        # 1.76: Erklärung für Laien – mit den echten Zahlen


def _z(x: float | None, n: int = 1) -> str:
    if x is None or x != x:
        return "–"
    t = f"{abs(x):,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"−{t}" if x < 0 and t.strip("0,.") else t


def _k(x: float | None, n: int = 1) -> str:
    """Zahl als Rechenglied: negative in Klammern."""
    t = _z(x, n)
    return f"({t})" if t.startswith("−") else t


def _m(d: date) -> str:
    return f"{MONATE[d.month - 1]} {d.year}"


@dataclass
class _Reihe:
    y: np.ndarray
    monate: list[date]
    laufend: tuple | None
    bester: object | None                    # _Backtest des gewählten Modells
    alle: list                               # alle _Backtest, nach MAE sortiert


_CACHE: dict = {}


def _reihe(ds, standort: str) -> _Reihe:
    from belegung import prognose as P

    schl = (id(ds), standort)
    if schl in _CACHE and _CACHE[schl][0] is ds:
        return _CACHE[schl][1]
    mittel, laufend = P.monatsreihe(ds.reha(standort).astype(float), ds.stichtag)
    start = P.struktur_start(mittel.to_numpy())
    mittel = mittel.iloc[start:]
    y = mittel.to_numpy()
    ursprung_ab = max(len(y) - P.BACKTEST_URSPRUENGE, 0)
    alle = []
    for k in P.KANDIDATEN:
        if ursprung_ab < k.min_laenge:
            continue
        bt = P._backtest(y, k, ursprung_ab)
        if bt:
            alle.append(bt)
    alle.sort(key=lambda b: b.mae)
    r = _Reihe(y, [ts.date() for ts in mittel.index], laufend, alle[0] if alle else None, alle)
    if len(_CACHE) > 16:
        _CACHE.clear()
    _CACHE[schl] = (ds, r)
    return r


def _horizont(r: _Reihe, monat: date, stichtag: date) -> tuple[int, int]:
    """(k = Index ab dem Stichtagsmonat, H = Monate nach dem letzten abgeschlossenen Monat)."""
    nach = stichtag.toordinal() + 1                     # 1.26: erster Prognosemonat = Monat nach dem Stichtag
    erster = date.fromordinal(nach).replace(day=1)
    k = (monat.year - erster.year) * 12 + monat.month - erster.month
    versatz = 0 if (not r.monate or r.monate[-1] < erster) else 1
    return k, k + 1 + versatz


def _modell_schritte(r: _Reihe, name: str, H: int) -> list[Schritt]:
    """Zerlegung des Modellwerts für den H-ten Monat nach dem letzten abgeschlossenen Monat."""
    from belegung import prognose as P

    y, n = r.y, len(r.y)
    erg: list[Schritt] = []

    def saison_niveau() -> float:
        idx = P._saisonindex(y)
        teile = [(r.monate[t], y[t], idx[(t - n) % 12]) for t in range(n - 6, n)]
        niveau = float(np.mean([v - s for _m_, v, s in teile]))
        s_h = float(idx[(H - 1) % 12])
        erg.append(Schritt(
            "Saisonprofil auf aktuellem Niveau",
            "Saisonindex(Monat) = gewichtetes Mittel der Abweichungen vom gleitenden 12-Monats-Mittel (jüngere Jahre "
            "zählen bis doppelt), zentriert auf Summe 0 · Niveau = Ø der letzten 6 Monate ohne Saison · "
            "Modell = Niveau + Saisonindex",
            f"Niveau = Ø({'; '.join(f'{_z(v)} − {_k(s)}' for _m_, v, s in teile)}) = {_z(niveau)} · "
            f"Saisonindex = {_z(s_h)} → {_z(niveau)} + {_k(s_h)} = {_z(niveau + s_h)}",
            ["Letzte 6 Monate: " + ", ".join(f"{_m(m_)} {_z(v)}" for m_, v, _s in teile)],
            "Typischer Verlauf im Jahr",
            f"Jeder Monat hat sein eigenes Muster – in manchen Monaten ist mehr los, in anderen weniger. Ohne dieses "
            f"Monatsmuster lag die Belegung zuletzt bei rund {_z(niveau, 0)} Plätzen. In diesem Monat sind es "
            f"erfahrungsgemäß {_z(abs(s_h), 0)} Plätze {'mehr' if s_h >= 0 else 'weniger'}. Ergebnis: rund "
            f"{_z(niveau + s_h, 0)}."))
        return niveau + s_h

    def ets() -> float:
        import warnings

        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
                                       initialization_method="estimated").fit()
        p = fit.params
        a, b, g, phi = (float(p.get(k, np.nan)) for k in ("smoothing_level", "smoothing_trend", "smoothing_seasonal",
                                                           "damping_trend"))
        lev, tr = float(fit.level[-1]), float(fit.trend[-1])
        s = float(fit.season[-12 + (H - 1) % 12])
        summe_phi = float(sum(phi ** j for j in range(1, H + 1)))
        wert = float(np.asarray(fit.forecast(H))[-1])
        erg.append(Schritt(
            "Holt-Winters mit gedämpftem Trend (exponentielle Glättung)",
            "ŷ = Niveau ℓ + (φ + φ² + … + φ^H)·Trend b + Saison s · Glättung je Monat: ℓ ← α·(Wert − s) + (1−α)·(ℓ + φ·b), "
            "b ← β·(ℓ neu − ℓ alt) + (1−β)·φ·b, s ← γ·(Wert − ℓ) + (1−γ)·s",
            f"α = {_z(a, 3)}, β = {_z(b, 3)}, γ = {_z(g, 3)}, φ = {_z(phi, 3)} (geschätzt nach kleinster Fehlerquadratsumme) · "
            f"ℓ = {_z(lev)}, b = {_z(tr, 2)}, Σφ^j (j=1…{H}) = {_z(summe_phi, 2)}, s = {_z(s)} → "
            f"{_z(lev)} + {_z(summe_phi, 2)}·{_k(tr, 2)} + {_k(s)} = {_z(wert)}",
            [f"Fehlerquadratsumme der Anpassung: {_z(float(fit.sse), 0)}"],
            "Niveau, Trend und Jahreszeit",
            f"Das Verfahren betrachtet drei Dinge: wo die Belegung gerade steht (rund {_z(lev, 0)} Plätze), ob sie "
            f"eher steigt oder fällt ({'steigend' if tr > 0.05 else 'fallend' if tr < -0.05 else 'gleichbleibend'} – "
            f"dieser Trend wird für die Zukunft vorsichtig abgeschwächt) und das typische Muster dieses Monats "
            f"({_z(s, 0) if s < 0 else '+' + _z(s, 0)} Plätze). Neuere Monate zählen mehr als ältere. Zusammen: rund "
            f"{_z(wert, 0)}."))
        return wert

    if name.startswith("Kombination"):
        e, sn = ets(), saison_niveau()
        erg.append(Schritt("Kombination", "Modell = (Holt-Winters + Saisonprofil) ÷ 2",
                           f"({_z(e)} + {_z(sn)}) ÷ 2 = {_z((e + sn) / 2)}", kurz="Beide Verfahren gemittelt",
                           einfach=f"Beide Verfahren werden zu gleichen Teilen gemittelt – so gleichen sich ihre "
                                   f"Schwächen aus: ({_z(e, 0)} + {_z(sn, 0)}) ÷ 2 = rund {_z((e + sn) / 2, 0)}."))
    elif name.startswith("Holt"):
        ets()
    elif name.startswith("Saisonprofil"):
        saison_niveau()
    elif name.startswith("Vorjahres"):
        i = n - 12 + (H - 1) % 12
        erg.append(Schritt("Vorjahresmonat", "Modell = Wert desselben Monats ein Jahr vorher",
                           f"{_m(r.monate[i])}: {_z(float(y[i]))}", kurz="Wie im Vorjahr",
                           einfach=f"Es wird der Wert desselben Monats im Vorjahr genommen: {_m(r.monate[i])} waren "
                                   f"es rund {_z(float(y[i]), 0)} Plätze."))
    elif name.startswith("Mittel"):
        xs = y[-6:]
        erg.append(Schritt("Mittel der letzten 6 Monate", "Modell = (x₁ + … + x₆) ÷ 6",
                           f"({' + '.join(_z(float(v)) for v in xs)}) ÷ 6 = {_z(float(np.mean(xs)))}",
                           kurz="Durchschnitt der letzten Monate",
                           einfach=f"Es wird der Durchschnitt der letzten 6 Monate genommen: rund "
                                   f"{_z(float(np.mean(xs)), 0)} Plätze."))
    return erg


def _fehler_statistik(bt, H: int, anteil: float = 1.0) -> tuple[Schritt, float, float]:
    """Band aus den Rückwärtstest-Fehlern: k80/k95 = Quantile von |e|/√h; Halbbreite = k·√H (· Restanteil)."""
    fe = [(h, e) for h, es in bt.fehler.items() for e in es]
    norm = np.array([abs(e) / np.sqrt(h) for h, e in fe])
    roh = np.array([e for _h, e in fe])
    k80 = float(np.quantile(norm, .80))
    k95 = max(float(np.quantile(norm, .95)), k80 * Z95 / Z80)
    sig = float(np.std(norm * np.sign([e for _h, e in fe]), ddof=1)) if len(norm) > 1 else 0.0
    b80, b95 = k80 * np.sqrt(H) * anteil, k95 * np.sqrt(H) * anteil
    abd = float(np.mean([abs(e) <= k80 * np.sqrt(h) for h, e in fe])) if fe else 0.0
    st = Schritt(
        "Unsicherheit (Band) aus den eigenen Fehlern",
        "Fehler e = Prognose − Ist (Rückwärtstest, je Abstand h = 1…12 Monate) · normiert |e|/√h · "
        "k80 = 80-%-Quantil, k95 = max(95-%-Quantil; k80·1,960/1,282) · Halbbreite = k·√H"
        + (" · laufender Monat: × Anteil der Resttage" if anteil < 1 else ""),
        f"N = {len(fe)} Fehler · k80 = {_z(k80, 2)}, k95 = {_z(k95, 2)} · H = {H}: "
        f"80 %: {_z(k80, 2)}·√{H}{f'·{_z(anteil, 2)}' if anteil < 1 else ''} = ±{_z(b80)} · "
        f"95 %: {_z(k95, 2)}·√{H}{f'·{_z(anteil, 2)}' if anteil < 1 else ''} = ±{_z(b95)}",
        [f"Mittlerer Fehler (Verzerrung) {_z(float(np.mean(roh)), 2)} · mittlerer absoluter Fehler {_z(float(np.mean(np.abs(roh))), 2)}",
         f"Standardabweichung der normierten Fehler σ = {_z(sig, 2)} → bei Normalverteilung wäre k80 = 1,282·σ = "
         f"{_z(Z80 * sig, 2)} und k95 = 1,960·σ = {_z(Z95 * sig, 2)}. Verwendet werden die echten Quantile, weil die "
         "Fehler selten normalverteilt sind (Ausreißer, Schiefe).",
         f"Probe: im Rückwärtstest lagen {_z(100 * abd, 0)} % der Fälle im 80-%-Band."],
        "Wie sicher ist das?",
        f"Keine Vorhersage trifft genau. Wie weit das Programm früher danebenlag, zeigt, wie unsicher es jetzt ist. "
        f"Bei {H} Monat{'en' if H != 1 else ''} Abstand lag der echte Wert in 8 von 10 Fällen höchstens "
        f"{_z(b80, 0)} Plätze neben der Vorhersage, in 19 von 20 Fällen höchstens {_z(b95, 0)}. Je weiter ein Monat "
        f"in der Zukunft liegt, desto größer wird dieser Spielraum.")
    return st, b80, b95


def rechenweg(ds, standort: str, monat: date, vertraege: float = 0.0, angezeigt: dict | None = None) -> list[Schritt]:
    """Alle Schritte für einen Monat (Prognose oder laufend). ``angezeigt``: Werte wie im Diagramm (erwartet, lo80,
    hi80, lo95, hi95, gesichert) – zur Kontrolle am Ende."""
    from belegung import konfig

    if ds is None or ds.prognose is None:
        return []
    if standort == konfig.GESAMT:
        return _gesamt(ds, monat, vertraege, angezeigt)
    w = next((x for x in ds.prognose.werte.get(standort, []) if x.monat == monat), None)
    info = ds.prognose.modelle.get(standort)
    if w is None or info is None or w.art == "ist":
        return []
    r = _reihe(ds, standort)
    if r.bester is None:
        return [Schritt("Zu wenig Historie", "Mittel der letzten Monate, Band aus der Streuung der letzten 12 Monate",
                        kurz="Noch zu wenig Erfahrungswerte",
                        einfach="Für diesen Standort gibt es noch zu wenige Monate, um Rechenwege zu vergleichen. "
                                "Verwendet wird der Durchschnitt der letzten Monate.")]
    k, H = _horizont(r, monat, ds.stichtag)
    erg = [Schritt(
        "Datenbasis",
        "Monatsmittel der belegten Plätze (Teilnehmende laut Pivot) je abgeschlossenem Monat",
        f"{len(r.y)} Monate ({_m(r.monate[0])} – {_m(r.monate[-1])}) · {_m(monat)} liegt H = {H} Monat(e) nach dem "
        f"letzten abgeschlossenen Monat",
        ["Letzte 12 Monate: " + ", ".join(f"{_m(m_)} {_z(float(v))}" for m_, v in zip(r.monate[-12:], r.y[-12:]))],
        "Woher kommen die Zahlen?",
        f"Grundlage sind die tatsächlich belegten Plätze der letzten {len(r.y)} Monate (Durchschnitt je Monat). Daraus "
        f"lernt das Programm, wie sich die Belegung üblicherweise entwickelt. {_m(monat)} liegt {H} Monat"
        f"{'e' if H != 1 else ''} nach dem letzten abgeschlossenen Monat – je weiter weg, desto unsicherer.")]
    erg.append(Schritt(
        "Modellwahl im Rückwärtstest",
        "Jedes Modell sagt von 18 früheren Zeitpunkten aus 1–12 Monate voraus, nur mit den Daten, die damals bekannt "
        "waren · MAE = Ø |Prognose − Ist| · gewählt wird das Modell mit dem kleinsten MAE",
        " · ".join(f"{b.kandidat.name}: MAE {_z(b.mae, 2)}" for b in r.alle) + f" → {r.bester.kandidat.name}",
        kurz="Welcher Rechenweg passt am besten?",
        einfach=f"Es gibt mehrere Rechenwege – zum Beispiel „wie im Vorjahr“ oder „Durchschnitt der letzten Monate“. "
                f"Jeder wurde an der Vergangenheit ausprobiert: Was hätte er damals vorhergesagt, und was kam wirklich? "
                f"Am besten traf „{r.bester.kandidat.name}“ – im Schnitt nur {_z(r.bester.mae, 1)} Plätze daneben. "
                f"Dieser Rechenweg wird verwendet."))
    erg += _modell_schritte(r, r.bester.kandidat.name, H)
    modell = float(w.modell) if w.modell is not None else None
    anteil = 1.0
    if w.art == "laufend" and r.laufend:
        _m0, ist_m, n_ist, n_t = r.laufend
        anteil = (n_t - n_ist) / n_t
        rest = max(modell or 0.0, w.gesichert) if w.gesichert is not None else (modell or 0.0)
        erg.append(Schritt(
            "Laufender Monat",
            "Erwartet = Ist-Mittel × (Ist-Tage ÷ Tage) + Rest × (Resttage ÷ Tage) · Rest = max(Modell; gebucht)",
            f"{_z(ist_m)} × {n_ist}/{n_t} + {_z(rest)} × {n_t - n_ist}/{n_t} = {_z(w.erwartet)}",
            kurz="Der Monat hat schon begonnen",
            einfach=f"Von {n_t} Tagen sind {n_ist} schon vorbei – dort ist die Belegung bekannt (im Schnitt "
                    f"{_z(ist_m, 0)}). Für die restlichen {n_t - n_ist} Tage wird geschätzt (rund {_z(rest, 0)}). "
                    f"Beides zusammen ergibt rund {_z(w.erwartet, 0)}."))
    else:
        erg.append(Schritt(
            "Gebuchter Bestand als Untergrenze",
            "Erwartet = max(Modellwert; Ø gebuchte Plätze im Monat) – was schon gebucht ist, steht fest",
            f"max({_z(modell)}; {_z(w.gesichert)}) = {_z(w.erwartet)}",
            kurz="Was schon gebucht ist",
            einfach=(f"Für diesen Monat sind schon rund {_z(w.gesichert, 0)} Plätze fest gebucht – darunter kann die "
                     f"Vorhersage nicht liegen. " if w.gesichert else "Für diesen Monat ist noch nichts fest gebucht. ")
                    + f"Der Rechenweg ergibt rund {_z(modell, 0)}, verwendet wird deshalb rund {_z(w.erwartet, 0)}."))
    st, b80, b95 = _fehler_statistik(r.bester, H, anteil)
    erg.append(st)
    erg.append(_schluss(w.erwartet, b80, b95, vertraege, w.gesichert, angezeigt))
    return erg


def _schluss(erw: float, b80: float, b95: float, v: float, gesichert: float | None, angezeigt: dict | None) -> Schritt:
    t = [f"Reha erwartet {_z(erw)} ± {_z(b80)} (80 %) bzw. ± {_z(b95)} (95 %)"]
    if v:
        t.append(f"+ Ø Verträge (Mieter, Gäste u. a. laut Listen) {_z(v)}")
    rech = ((f"{_z(erw)} + {_z(v)} = {_z(erw + v)}" if v else f"erwartet {_z(erw)}") + " · 80 %: {_z(max(erw - b80, 0) + v)} – {_z(erw + b80 + v)}"
            f" · 95 %: {_z(max(erw - b95, 0) + v)} – {_z(erw + b95 + v)}")
    det = ["Untergrenzen fallen nie unter den gebuchten Bestand"
           + (f" ({_z(gesichert + v)})" if gesichert is not None else "") + " und nie unter 0."]
    if angezeigt:
        det.append("Im Diagramm: erwartet {e}, 80 % {a} – {b}, 95 % {c} – {d}".format(
            e=_z(angezeigt.get("erwartet")), a=_z(angezeigt.get("lo80")), b=_z(angezeigt.get("hi80")),
            c=_z(angezeigt.get("lo95")), d=_z(angezeigt.get("hi95"))))
    einfach = (f"Erwartet werden rund {_z(erw + v, 0)} belegte Plätze. Sehr wahrscheinlich (8 von 10 Fällen) sind es "
               f"zwischen {_z(max(erw - b80, 0) + v, 0)} und {_z(erw + b80 + v, 0)}, fast sicher (19 von 20 Fällen) "
               f"zwischen {_z(max(erw - b95, 0) + v, 0)} und {_z(erw + b95 + v, 0)}.")
    if v:
        einfach += f" Darin sind rund {_z(v, 0)} Plätze aus Verträgen (Mieter, Gäste) enthalten, die fest eingeplant sind."
    return Schritt("Ergebnis", "Angezeigt = Reha-Prognose + Verträge; Band = erwartet ± Halbbreite", rech, t[1:] + det,
                   "Ergebnis", einfach)


def _gesamt(ds, monat: date, vertraege: float, angezeigt: dict | None) -> list[Schritt]:
    from belegung import konfig
    from belegung import prognose as P

    teile, je_monat, b80s, erw_sum = [], [], [], 0.0
    for s in konfig.STANDORTE:
        w = next((x for x in ds.prognose.werte.get(s, []) if x.monat == monat), None)
        if w is None or w.art == "ist":
            return []
        r = _reihe(ds, s)
        teile.append((konfig.STANDORT_LABEL.get(s, s), w, r))
        erw_sum += w.erwartet
        b80s.append(w.hi80 - w.erwartet)
        if r.bester is not None:
            idx = [date(m.year, m.month, 1) for m in r.monate]
            je_monat.append({(idx[o], h): e for (o, h), e in r.bester.je_ursprung.items()})
    erg = [Schritt(
        "Summe der Standorte",
        "Gesamt erwartet = Σ erwartet je Standort (jeder Standort hat sein eigenes, im Rückwärtstest gewähltes Modell)",
        " + ".join(f"{n} {_z(w.erwartet)}" for n, w, _r in teile) + f" = {_z(erw_sum)}",
        [f"{n}: {r.bester.kandidat.name if r.bester else '–'}" for n, _w, r in teile]
        + ["Den Rechenweg je Standort (Modell, Saison, Parameter) zeigt die Auswahl eines Standorts oben."],
        "Alle Standorte zusammen",
        "Die Gesamtzahl ist die Summe der drei Standorte: " + ", ".join(f"{n} rund {_z(w.erwartet, 0)}"
                                                                         for n, w, _r in teile)
        + f" – zusammen rund {_z(erw_sum, 0)}. Jeder Standort wird mit dem Rechenweg vorhergesagt, der dort am "
          "besten passt. Wählen Sie oben einen Standort, um seinen Rechenweg im Einzelnen zu sehen.")]
    if len(je_monat) == len(teile) and je_monat:
        gemeinsam = sorted(set(je_monat[0]).intersection(*je_monat[1:]))
        summe = {}
        for g in gemeinsam:
            summe.setdefault(g[1], []).append(sum(m[g] for m in je_monat))
        band = P._band(summe)
        erster = date.fromordinal(ds.stichtag.toordinal() + 1).replace(day=1)       # 1.26: wie die Prognose
        H = (monat.year - erster.year) * 12 + monat.month - erster.month + 1
        B80 = band.breite(H)
        unab = float(np.sqrt(sum(b * b for b in b80s)))
        quer = sum(b80s[i] * b80s[j] for i in range(len(b80s)) for j in range(len(b80s)) if i != j)
        rho = (B80 ** 2 - sum(b * b for b in b80s)) / quer if quer else None
        # Korrelation der 1-Monats-Fehler je Standortpaar (Kovarianz ÷ Standardabweichungen)
        eins = [{g[0]: m[g] for g in gemeinsam if g[1] == 1} for m in je_monat]
        paare = []
        for i in range(len(teile)):
            for j in range(i + 1, len(teile)):
                ms = sorted(set(eins[i]) & set(eins[j]))
                if len(ms) >= 3:
                    a_ = np.array([eins[i][m] for m in ms])
                    b_ = np.array([eins[j][m] for m in ms])
                    cov = float(np.cov(a_, b_, ddof=1)[0, 1])
                    sa, sb = float(np.std(a_, ddof=1)), float(np.std(b_, ddof=1))
                    r_ = cov / (sa * sb) if sa and sb else float("nan")
                    paare.append(f"{teile[i][0]} ↔ {teile[j][0]}: Kovarianz {_z(cov, 2)}, σ {_z(sa, 2)} / {_z(sb, 2)} → "
                                 f"Korrelation r = {_z(r_, 2)} (n = {len(ms)})")
        erg.append(Schritt(
            "Band der Summe aus den Fehlern der Summe",
            "Fehler Gesamt = Σ Fehler der Standorte am selben Monat und Abstand · k80 = 80-%-Quantil von |Fehler|/√h · "
            "Halbbreite = k80·√H. So steckt der Gleichlauf der Standorte (Kovarianz) schon in den Zahlen.",
            f"N = {sum(len(x) for x in summe.values())} gemeinsame Fehler · k80 = {_z(band.k80, 2)} · H = {H} → ±{_z(B80)}",
            [f"Zum Vergleich, wenn die Standorte unabhängig wären: √(Σ Halbbreite²) = √({' + '.join(_z(b) + '²' for b in b80s)})"
             f" = ±{_z(unab)}"]
            + ([f"Daraus mittlere Korrelation der Standortfehler ρ ≈ (B² − Σb²) ÷ Σ bᵢ·bⱼ = {_z(rho, 2)}"
                + (" – sie schwanken gemeinsam, das Band ist breiter als bei Unabhängigkeit." if rho and rho > 0.1 else
                   " – kaum gemeinsames Schwanken.")] if rho is not None else [])
            + paare,
            "Wie sicher ist die Gesamtzahl?",
            f"Die Standorte schwanken nicht völlig unabhängig voneinander. Deshalb wird die Unsicherheit der Gesamtzahl "
            f"direkt daraus berechnet, wie weit die Summe früher danebenlag: in 8 von 10 Fällen höchstens "
            f"{_z(B80, 0)} Plätze."
            + (" Die Standorte schwanken dabei oft gemeinsam – der Spielraum ist deshalb etwas größer, als wenn sie "
               "unabhängig wären." if rho is not None and rho > 0.1 else
               " Die Standorte gleichen sich dabei teilweise aus." if rho is not None and rho < -0.1 else "")))
        hi80 = angezeigt.get("hi80") if angezeigt else None
        erg.append(_schluss(erw_sum, B80, band.breite(H, 95), vertraege, None, angezeigt) if hi80 is not None else
                   Schritt("Ergebnis", "", f"{_z(erw_sum)} ± {_z(B80)}", kurz="Ergebnis",
                           einfach=f"Erwartet werden rund {_z(erw_sum, 0)} belegte Plätze. Sehr wahrscheinlich "
                                   f"(8 von 10 Fällen) sind es zwischen {_z(max(erw_sum - B80, 0), 0)} und "
                                   f"{_z(erw_sum + B80, 0)}."))
    return erg
