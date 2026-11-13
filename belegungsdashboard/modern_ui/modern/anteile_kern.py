"""Anteils-Diagramme (0.96) – „wer macht wie viel aus, und wann“ wie in Excel: Ring, Kreis, 100 %-Säulen, 100 %-Fläche.

Rein (keine Oberfläche): Eingang sind benannte Reihen über einer gemeinsamen Achse (Halbjahre, Monate, Tage).
* Kleine Anteile werden zu „Übrige“ zusammengefasst (höchstens ``oben`` + 1 Stücke) – sonst wird ein Kreis unlesbar.
* Ring und Kreis zeigen die Summe über ein Fenster (Standard: die Ist-Perioden), 100 %-Säulen/-Fläche den Verlauf.
* Prognose-Perioden werden heller gezeichnet und in der Achse mit „(P)“ markiert.
* Eine Aussage als Satz: größter Anteil, und wo sich ein Anteil am stärksten verschiebt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

UEBRIGE = "Übrige"
ARTEN = ("ring", "kreis", "saeule100", "flaeche100")


@dataclass
class Anteile:
    namen: list[str]                       # nach Summe absteigend, „Übrige“ zuletzt
    achse: list[str]
    werte: dict[str, list[float]]          # Name → Wert je Periode (≥ 0)
    prognose: list[bool]                   # je Periode
    summe: dict[str, float]                # Name → Summe im Fenster
    fenster: str                           # Text: worüber Ring/Kreis summiert
    satz: str = ""
    zusammengefasst: list[str] = field(default_factory=list)

    def prozent(self, name: str) -> list[float | None]:
        out = []
        for i in range(len(self.achse)):
            ges = sum(self.werte[n][i] for n in self.namen)
            out.append(round(100 * self.werte[name][i] / ges, 1) if ges > 0 else None)
        return out

    def anteil(self, name: str) -> float:
        ges = sum(self.summe.values())
        return 100 * self.summe.get(name, 0) / ges if ges > 0 else 0.0


def _zahl(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def _pz(x: float) -> str:
    return f"{x:.0f} %"


def berechnen(reihen: dict[str, list[float | None]], achse: list[str], prognose: list[bool] | None = None,
              oben: int = 6, fenster: list[int] | None = None, fenster_text: str = "") -> Anteile:
    """``fenster``: Indizes der Perioden für Ring/Kreis (Standard: alle Ist-Perioden, sonst alle)."""
    n = len(achse)
    prognose = list(prognose or [False] * n)[:n] + [False] * max(0, n - len(prognose or []))
    sauber = {k: [max(0.0, float(v or 0)) for v in (list(w) + [0] * n)[:n]] for k, w in reihen.items()}
    sauber = {k: w for k, w in sauber.items() if sum(w) > 0}
    if fenster is None:
        fenster = [i for i in range(n) if not prognose[i]] or list(range(n))
        fenster_text = fenster_text or (f"{achse[fenster[0]]} – {achse[fenster[-1]]}" if fenster else "")
    reihenfolge = sorted(sauber, key=lambda k: -sum(sauber[k][i] for i in fenster))
    gross, klein = reihenfolge[:oben], reihenfolge[oben:]
    if len(klein) == 1:                     # ein einzelnes „Übrige“ wäre nur ein Umbenennen
        gross, klein = gross + klein, []
    werte = {k: sauber[k] for k in gross}
    if klein:
        werte[UEBRIGE] = [round(sum(sauber[k][i] for k in klein), 2) for i in range(n)]
    namen = list(werte)
    summe = {k: round(sum(werte[k][i] for i in fenster), 2) for k in namen}
    a = Anteile(namen, list(achse), werte, prognose, summe, fenster_text, zusammengefasst=klein)
    a.satz = aussage(a)
    return a


def aussage(a: Anteile) -> str:
    if not a.namen or not sum(a.summe.values()):
        return "Keine Werte im gewählten Zeitraum."
    erst = max((k for k in a.namen if k != UEBRIGE), key=lambda k: a.summe[k], default=a.namen[0])
    teile = [f"Den größten Anteil hat {erst} mit {_pz(a.anteil(erst))}"
             + (f" ({a.fenster})" if a.fenster else "") + "."]
    if len(a.achse) >= 2:                   # stärkste Verschiebung zwischen erster und letzter Periode mit Werten
        mit = [i for i in range(len(a.achse)) if sum(a.werte[k][i] for k in a.namen) > 0]
        if len(mit) >= 2:
            i0, i1 = mit[0], mit[-1]
            def p(k, i):
                g = sum(a.werte[x][i] for x in a.namen)
                return 100 * a.werte[k][i] / g if g else 0
            k, d = max(((k, p(k, i1) - p(k, i0)) for k in a.namen if k != UEBRIGE), key=lambda x: abs(x[1]),
                       default=(None, 0))
            if k and abs(d) >= 5:
                teile.append(f"Am stärksten {'gewachsen' if d > 0 else 'geschrumpft'} ist {k}: von {_pz(p(k, i0))} "
                             f"({a.achse[i0]}) auf {_pz(p(k, i1))} ({a.achse[i1]}).")
    return " ".join(teile)


def option(a: Anteile, art: str, t: dict, farben: dict[str, str] | list[str], titel_mitte: str = "") -> dict:
    """ECharts-Option. ``t``: Themenfarben (text, text2, rand, …); ``farben``: Name → Farbe oder Liste."""
    def farbe(i: int, k: str) -> str:
        if k == UEBRIGE:
            return t.get("text3", "#9aa0a6")
        if isinstance(farben, dict):
            return farben.get(k) or list(farben.values())[i % max(1, len(farben))]
        return farben[i % len(farben)]
    art = art if art in ARTEN else "ring"
    text, text2 = t.get("text", "#222"), t.get("text2", "#555")
    if art in ("ring", "kreis"):
        ges = sum(a.summe.values()) or 1
        daten = [{"name": k, "value": round(a.summe[k], 1), "itemStyle": {"color": farbe(i, k)}}
                 for i, k in enumerate(a.namen) if a.summe[k] > 0]
        opt = {"animation": False, "textStyle": {"fontSize": 13},
               "tooltip": {"trigger": "item", ":formatter": "(p) => p.name + ': ' + Math.round(p.value).toLocaleString"
                                                              "('de-DE') + ' (' + p.percent.toFixed(0) + ' %)'"},
               "legend": {"show": False},
               "series": [{"type": "pie", "radius": ["48%", "74%"] if art == "ring" else [0, "74%"],
                           "center": ["50%", "52%"], "data": daten, "startAngle": 90, "avoidLabelOverlap": True,
                           "minShowLabelAngle": 4,
                           "itemStyle": {"borderColor": t.get("bg", "#fff"), "borderWidth": 2},
                           "label": {"show": True, "color": text, "fontSize": 13, "textBorderWidth": 0,
                                     ":formatter": "(p) => p.name + '\\n' + p.percent.toFixed(0) + ' %'"},
                           "labelLine": {"length": 10, "length2": 8, "lineStyle": {"color": text2}}}]}
        if art == "ring":
            mitte = titel_mitte or _zahl(ges)
            opt["graphic"] = [{"type": "text", "left": "center", "top": "46%",
                               "style": {"text": mitte, "fill": text, "fontSize": 20, "fontWeight": 700,
                                         "textAlign": "center"}},
                              {"type": "text", "left": "center", "top": "56%",
                               "style": {"text": "gesamt", "fill": text2, "fontSize": 12, "textAlign": "center"}}]
        return opt
    achse = [x + (" (P)" if a.prognose[i] else "") for i, x in enumerate(a.achse)]
    reihen = []
    for i, k in enumerate(a.namen):
        pz = a.prozent(k)
        f = farbe(i, k)
        if art == "saeule100":
            # Prognose: gleiche Farbe (weiße Zahlen bleiben lesbar), gestrichelter Rand + „(P)“ + hinterlegter Bereich
            daten = [{"value": v, "itemStyle": {"color": f, "borderColor": t.get("bg", "#fff"), "borderWidth": 1.5,
                                                "borderType": "dashed"} if a.prognose[j] else {"color": f}}
                     for j, v in enumerate(pz)]
            reihen.append({"name": k, "type": "bar", "stack": "100", "m_fest": True, "data": daten, "barMaxWidth": 46,
                           "itemStyle": {"color": f}, "color": f,
                           "label": {"show": len(a.achse) <= 16, "position": "inside", "color": "#fff", "fontSize": 12,
                                     "textBorderWidth": 0,
                                     ":formatter": "(p) => (p.value == null || p.value < 8) ? '' : Math.round(p.value) + ' %'"}})
        else:
            reihen.append({"name": k, "type": "line", "stack": "100", "m_fest": True, "data": pz, "symbol": "none", "smooth": False,
                           "color": f, "lineStyle": {"color": f, "width": 1}, "areaStyle": {"color": f, "opacity": .75}})
    if any(a.prognose) and not all(a.prognose) and reihen:
        ab = next(i for i, p in enumerate(a.prognose) if p)
        reihen[0]["markArea"] = {"silent": True, "itemStyle": {"color": "rgba(127,127,127,.08)"},
                                 "label": {"show": True, "position": "top", "formatter": "Prognose →",
                                           "color": text2, "fontSize": 12, "textBorderWidth": 0},
                                 "data": [[{"xAxis": achse[ab]}, {"xAxis": achse[-1]}]]}
    return {"animation": False, "textStyle": {"fontSize": 13},
            "grid": {"left": 48, "right": 16, "top": 60, "bottom": 34},
            "legend": {"top": 0, "left": 0, "type": "scroll", "data": list(a.namen), "textStyle": {"color": text2}},
            "tooltip": {"trigger": "axis", ":valueFormatter": "(v) => v == null ? '–' : Math.round(v) + ' %'"},
            "xAxis": {"type": "category", "data": achse, "boundaryGap": art == "saeule100",
                      "axisLabel": {"color": text2, "fontSize": 12, "interval": 0 if len(achse) <= 16 else "auto",
                                    "hideOverlap": True}},
            "yAxis": {"type": "value", "min": 0, "max": 100, "interval": 25,
                      "axisLabel": {"color": text2, "fontSize": 12, "formatter": "{value} %"},
                      "splitLine": {"lineStyle": {"color": t.get("rand", "#ddd"), "opacity": .5}}},
            "series": reihen}


def tabelle(a: Anteile) -> list[list[str]]:
    """Dieselben Zahlen als Tabelle (Kopieren/Vorlesen): Name, Summe, Anteil."""
    return [["Name", "Summe", "Anteil"]] + [[k, _zahl(a.summe[k]), _pz(a.anteil(k))] for k in a.namen]


def monate_buendeln(tage: list[str], werte: dict[str, list[float]], ist: list[bool]) -> tuple[list[str], dict, list[bool]]:
    """Tageswerte („TT.MM.“) zu Monaten (aufeinanderfolgende Tage desselben Monats) – Summe = Personentage."""
    MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    achse, gruppen, prog = [], [], []
    for i, tg in enumerate(tage):
        teile = str(tg).strip(".").split(".")
        mon = teile[1] if len(teile) >= 2 else ""
        if not gruppen or gruppen[-1][0] != mon:
            try:
                name = MON[int(mon) - 1]
            except (ValueError, IndexError):
                name = mon
            gruppen.append((mon, []))
            achse.append(name)
            prog.append(False)
        gruppen[-1][1].append(i)
        if i < len(ist) and not ist[i]:
            prog[-1] = True
    neu = {k: [round(sum(v[i] or 0 for i in idx), 1) for _m, idx in gruppen] for k, v in werte.items()}
    return achse, neu, prog
