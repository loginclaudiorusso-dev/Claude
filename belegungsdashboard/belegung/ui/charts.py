"""Diagramme (matplotlib in Qt) mit einheitlichem Stil und Hover-Tooltip.

Stilregeln: dünne Linien (2 px), dezente Achsen, kein Rahmen, eine y-Achse, Prognose
gestrichelt mit 80-%-Band, Ist durchgezogen, Beschriftungen in Textfarben (nie in
Serienfarbe), Legende ab zwei Serien.
"""

from __future__ import annotations

from datetime import date

import matplotlib

matplotlib.use("QtAgg")
matplotlib.rcParams["axes.formatter.use_locale"] = False

import matplotlib.dates as mdates  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402
from PySide6.QtWidgets import QSizePolicy  # noqa: E402

from . import theme  # noqa: E402
from .widgets import MONATE_KURZ, zahl  # noqa: E402

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = theme.mpl_schrift()


def _datum_formatter(spanne_tage: float):
    def fmt(x, _pos):
        d = mdates.num2date(x)
        if spanne_tage <= 120:
            return f"{d.day}. {MONATE_KURZ[d.month - 1]}"
        if spanne_tage <= 400:
            return f"{MONATE_KURZ[d.month - 1]} {str(d.year)[2:]}"
        return str(d.year) if d.month == 1 else MONATE_KURZ[d.month - 1]
    return FuncFormatter(fmt)


class Diagramm(FigureCanvasQTAgg):
    def __init__(self, hoehe: float = 3.2, parent=None):
        self.fig = Figure(figsize=(8, hoehe), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(int(hoehe * 100))
        self.ax = self.fig.add_subplot(111)
        self._hover_x: np.ndarray | None = None
        self._hover_reihen: list[tuple[str, np.ndarray, str]] = []
        self._hover_titel = None
        self._tip = None
        self._vline = None
        self.mpl_connect("motion_notify_event", self._bewegung)
        self.mpl_connect("axes_leave_event", lambda _e: self._tip_aus())

    # ---- Stil ---------------------------------------------------------------------------

    def _vorbereiten(self) -> None:
        t = theme.T
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor(t.surface)
        ax = self.ax
        ax.set_facecolor(t.surface)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(t.border_strong)
        ax.tick_params(colors=t.text_3, labelsize=8.5, length=0, pad=6)
        ax.grid(axis="y", color=t.raster, linewidth=1)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_locator(MaxNLocator(5, integer=True))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: zahl(v)))
        self._hover_x, self._hover_reihen, self._tip, self._vline = None, [], None, None
        self._mit_legende = False

    def _abschliessen(self, x_von=None, x_bis=None) -> None:
        if x_von is not None and x_bis is not None:
            spanne = (x_bis - x_von).days if hasattr(x_bis - x_von, "days") else 365
            if spanne <= 120:
                locator = mdates.AutoDateLocator(minticks=4, maxticks=9)
            else:
                monate = max(1, round(spanne / 30.4 / 8))
                if monate <= 1:
                    locator = mdates.MonthLocator()
                elif monate <= 3:
                    locator = mdates.MonthLocator(bymonth=(1, 4, 7, 10))
                elif monate <= 7:
                    locator = mdates.MonthLocator(bymonth=(1, 7))
                else:
                    locator = mdates.MonthLocator(bymonth=1)
            self.ax.xaxis.set_major_locator(locator)
            self.ax.xaxis.set_major_formatter(_datum_formatter(spanne))
            self.ax.set_xlim(x_von, x_bis)
        # Legende sitzt oberhalb der Achse in einem festen Streifen (in Punkt, unabhängig von der
        # Windows-Skalierung) – so wird sie nie oben abgeschnitten
        hoehe_pt = self.fig.get_figheight() * 72
        top = 1 - (30 if getattr(self, "_mit_legende", False) else 12) / hoehe_pt
        self.fig.subplots_adjust(left=0.06, right=0.985, top=top, bottom=0.13)
        self.draw_idle()

    def _legende(self, anzahl: int) -> None:
        if anzahl >= 2:
            t = theme.T
            griffe, namen = self.ax.get_legend_handles_labels()
            if not griffe:
                return
            leg = self.fig.legend(griffe, namen, loc="upper left", bbox_to_anchor=(0.05, 1.0), ncols=min(anzahl, 6),
                                  frameon=False, fontsize=8.5, handlelength=1.4, columnspacing=1.4, borderaxespad=0.3)
            self._mit_legende = True
            for txt in leg.get_texts():
                txt.set_color(t.text_2)

    def leer(self, text: str) -> None:
        self._vorbereiten()
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.spines["bottom"].set_visible(False)
        self.ax.text(0.5, 0.5, text, ha="center", va="center", transform=self.ax.transAxes,
                     color=theme.T.text_3, fontsize=10)
        self.draw_idle()

    def _kapazitaet(self, kap: float | None, text: str = "Kapazität") -> None:
        if kap:
            t = theme.T
            self.ax.axhline(kap, color=t.text_3, linewidth=1, linestyle=(0, (4, 3)))
            self.ax.annotate(f"{text} {zahl(kap)}", xy=(1, kap), xycoords=("axes fraction", "data"),
                             xytext=(-2, 4), textcoords="offset points", ha="right", fontsize=8, color=t.text_2)

    def _heute(self, x) -> None:
        t = theme.T
        self.ax.axvline(x, color=t.text_3, linewidth=1, linestyle=(0, (2, 3)))
        self.ax.annotate("Heute", xy=(x, 1), xycoords=("data", "axes fraction"), xytext=(4, -2),
                         textcoords="offset points", fontsize=8, color=t.text_2, va="top")

    # ---- Hover --------------------------------------------------------------------------

    def hover_setzen(self, x, reihen: list[tuple[str, np.ndarray, str]], titel=None) -> None:
        """x: Datumswerte oder Zahlen; reihen: (Name, Werte, Farbe); titel(i) -> Überschrift."""
        self._hover_x = mdates.date2num(x) if len(x) and not isinstance(x[0], (int, float, np.floating)) else np.asarray(x, dtype=float)
        self._hover_reihen = reihen
        self._hover_titel = titel

    def _tip_aus(self):
        if self._tip is not None and self._tip.get_visible():
            self._tip.set_visible(False)
            if self._vline is not None:
                self._vline.set_visible(False)
            self.draw_idle()

    def _bewegung(self, e):
        if e.inaxes is not self.ax or self._hover_x is None or not len(self._hover_x) or e.xdata is None:
            self._tip_aus()
            return
        t = theme.T
        i = int(np.argmin(np.abs(self._hover_x - e.xdata)))
        x = self._hover_x[i]
        zeilen = [self._hover_titel(i) if self._hover_titel else mdates.num2date(x).strftime("%d.%m.%Y")]
        for name, werte, _ in self._hover_reihen:
            v = werte[i]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            zeilen.append(f"{name}: {v}" if isinstance(v, str) else f"{name}: {zahl(v)}")
        if self._tip is None:
            self._tip = self.ax.annotate(
                "", xy=(0, 0), xytext=(12, -12), textcoords="offset points", va="top", fontsize=8.5,
                color=t.tooltip_text, zorder=20, bbox=dict(boxstyle="round,pad=0.55,rounding_size=0.4",
                                                           fc=t.tooltip_bg, ec="none", alpha=0.96),
            )
            self._vline = self.ax.axvline(x, color=t.text_3, linewidth=0.8, alpha=0.6, zorder=1)
        rechts = e.x > self.width() * 0.62 * self.devicePixelRatioF()
        self._tip.set_ha("right" if rechts else "left")
        self._tip.set_position((-12 if rechts else 12, -12))
        y_oben = self.ax.get_ylim()[1]
        self._tip.xy = (x, y_oben)
        self._tip.set_text("\n".join(zeilen))
        self._tip.set_visible(True)
        self._vline.set_xdata([x, x])
        self._vline.set_visible(True)
        self.draw_idle()


class VerlaufChart(Diagramm):
    """Tagesverlauf: Ist durchgezogen, Prognose gestrichelt mit 80-%-Band."""

    def zeichnen(self, reihen: dict[str, tuple[pd.DataFrame, str]], kapazitaet: float | None, stichtag: date,
                 band: bool = True, bestand: bool = False) -> None:
        self._vorbereiten()
        if not reihen:
            self.leer("Keine Daten")
            return
        ax = self.ax
        hover = []
        x_ref = None
        for name, (df, farbe) in reihen.items():
            x = df.index
            x_ref = x
            ist = df["ist"].to_numpy()
            w = df["wert"].to_numpy(dtype=float)
            if ist.any():
                ax.plot(x[ist], w[ist], color=farbe, linewidth=2, label=name, solid_capstyle="round")
            if (~ist).any():
                idx = np.where(~ist)[0]
                start = max(idx[0] - 1, 0)
                ax.plot(x[start:], w[start:], color=farbe, linewidth=2, linestyle=(0, (4, 2.5)),
                        label=None if ist.any() else name)
                if band:
                    ax.fill_between(x[idx], df["lo80"].to_numpy()[idx], df["hi80"].to_numpy()[idx],
                                    color=farbe, alpha=0.14, linewidth=0)
                if bestand:
                    ax.plot(x[idx], df["gesichert"].to_numpy()[idx], color=farbe, linewidth=1, linestyle=":")
            hover.append((name, w, farbe))
        if len(reihen) == 1:
            ax.fill_between(x_ref, next(iter(reihen.values()))[0]["wert"].to_numpy(dtype=float),
                            color=next(iter(reihen.values()))[1], alpha=0.06, linewidth=0)
        self._kapazitaet(kapazitaet)
        if x_ref[0].date() <= stichtag < x_ref[-1].date():
            self._heute(pd.Timestamp(stichtag))
        lo = min(float(df["lo80"].min()) for df, _ in reihen.values())
        hi = max(float(df["hi80"].max()) for df, _ in reihen.values())
        hi = max(hi, kapazitaet or 0)
        ax.set_ylim(max(0, lo - (hi - lo) * 0.25), hi + (hi - lo) * 0.12 + 1)
        ist_arr = next(iter(reihen.values()))[0]["ist"].to_numpy()
        wt = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        self.hover_setzen(list(x_ref), hover, lambda i: f"{wt[x_ref[i].weekday()]} {x_ref[i]:%d.%m.%Y}"
                          + ("" if ist_arr[i] else " · Prognose"))
        self._legende(len(reihen))
        self._abschliessen(x_ref[0], x_ref[-1])


class StapelChart(Diagramm):
    """Gestapelte Flächen je Kategorie (Zusammensetzung der Belegung)."""

    def zeichnen(self, kat: pd.DataFrame, kapazitaet: float | None, stichtag: date) -> None:
        self._vorbereiten()
        t = theme.T
        if kat.empty:
            self.leer("Keine Daten")
            return
        farben = [t.kategorie.get(c, t.text_3) for c in kat.columns]
        x = kat.index
        self.ax.stackplot(x, *[kat[c].to_numpy() for c in kat.columns], colors=farben, labels=list(kat.columns),
                          alpha=0.9, linewidth=0.6, edgecolor=t.surface)
        self._kapazitaet(kapazitaet)
        if x[0].date() <= stichtag < x[-1].date():
            self._heute(pd.Timestamp(stichtag))
        summe = kat.sum(axis=1)
        self.ax.set_ylim(0, max(float(summe.max()), kapazitaet or 0) * 1.12 + 1)
        reihen = [(c, kat[c].to_numpy(dtype=float), f) for c, f in zip(kat.columns, farben)]
        reihen.append(("Summe", summe.to_numpy(dtype=float), t.text))
        self.hover_setzen(list(x), reihen)
        self._legende(len(kat.columns))
        self._abschliessen(x[0], x[-1])


class MonatsChart(Diagramm):
    """Monatsmittel: Ist, Prognose mit 80/95-%-Band, gesicherter Bestand, Kapazität, Backtest."""

    def zeichnen(self, zeilen: list[dict], farbe: str, kapazitaet: float | None, band95: bool = True,
                 rueckblick: list[tuple[date, float, float]] | None = None) -> None:
        self._vorbereiten()
        t = theme.T
        if not zeilen:
            self.leer("Keine Prognosedaten")
            return
        ax = self.ax
        x = [pd.Timestamp(z["monat"]) + pd.Timedelta(days=14) for z in zeilen]
        ist = np.array([z["art"] == "ist" for z in zeilen])
        erw = np.array([z["erwartet"] for z in zeilen], dtype=float)
        lo80 = np.array([z["lo80"] for z in zeilen], dtype=float)
        hi80 = np.array([z["hi80"] for z in zeilen], dtype=float)
        idx = np.where(~ist)[0]
        xa = np.array(x)
        if len(idx):
            if band95:
                ax.fill_between(xa[idx], [zeilen[i]["lo95"] for i in idx], [zeilen[i]["hi95"] for i in idx],
                                color=farbe, alpha=0.08, linewidth=0, label="95 %-Spanne")
            ax.fill_between(xa[idx], lo80[idx], hi80[idx], color=farbe, alpha=0.18, linewidth=0, label="80 %-Spanne")
            start = max(idx[0] - 1, 0)
            ax.plot(xa[start:], erw[start:], color=farbe, linewidth=2, linestyle=(0, (4, 2.5)), label="Prognose")
            ges = np.array([zeilen[i]["gesichert"] if zeilen[i]["gesichert"] is not None
                            and zeilen[i]["gesichert"] >= 0.5 * zeilen[i]["erwartet"] else np.nan for i in idx], dtype=float)
            if not np.all(np.isnan(ges)):
                ax.plot(xa[idx], ges, color=t.text_2, linewidth=1.2, linestyle=":", label="Gesichert (Planung)")
        if ist.any():
            ax.plot(xa[ist], erw[ist], color=farbe, linewidth=2, label="Ist")
            ax.scatter(xa[ist], erw[ist], s=14, color=farbe, zorder=3, edgecolors=t.surface, linewidths=1)
        if rueckblick:
            rx = [pd.Timestamp(m) + pd.Timedelta(days=14) for m, _, _ in rueckblick]
            ax.scatter(rx, [p for *_, p in rueckblick], s=22, facecolors=t.surface, edgecolors=t.text_2,
                       linewidths=1.2, zorder=4, label="Blind-Prognose (Backtest)")
        self._kapazitaet(kapazitaet)
        if len(idx):
            self._heute(xa[idx[0]] - pd.Timedelta(days=14))
        oben = max(float(np.nanmax(hi80)), float(max(z["hi95"] for z in zeilen)) if band95 else 0, kapazitaet or 0)
        unten = float(np.nanmin(lo80))
        ax.set_ylim(max(0, unten - (oben - unten) * 0.2), oben + (oben - unten) * 0.1 + 1)

        def titel(i):
            z = zeilen[i]
            art = {"ist": "Ist", "laufend": "laufender Monat", "prognose": "Prognose"}[z["art"]]
            return f"{MONATE_KURZ[z['monat'].month - 1]} {z['monat'].year} · {art}"
        spanne = [f"{zahl(z['lo80'])}–{zahl(z['hi80'])}" if z["art"] != "ist" else None for z in zeilen]
        reihen = [("Ø belegt", erw, farbe), ("80 %-Spanne", np.array(spanne, dtype=object), farbe)]
        if any(z.get("gesichert") is not None for z in zeilen):
            reihen.append(("gesichert", np.array([z["gesichert"] if z["gesichert"] is not None else np.nan for z in zeilen], dtype=float), t.text_2))
        if kapazitaet:
            reihen.append(("Auslastung", np.array([f"{zahl(z['erwartet'] / kapazitaet * 100)} %" for z in zeilen], dtype=object), t.text_2))
        self.hover_setzen(x, reihen, titel)
        self._legende(5)
        self._abschliessen(x[0] - pd.Timedelta(days=20), x[-1] + pd.Timedelta(days=20))


class BalkenChart(Diagramm):
    """Monatssummen (Personentage) als Balken; Prognosemonate heller."""

    def zeichnen(self, monate: list[tuple[date, float, bool]], farbe: str, einheit: str = "Personentage") -> None:
        self._vorbereiten()
        t = theme.T
        if not monate:
            self.leer("Keine Daten")
            return
        x = np.arange(len(monate))
        werte = [w for _, w, _ in monate]
        alphas = [1.0 if ist else 0.45 for *_, ist in monate]
        balken = self.ax.bar(x, werte, width=0.72, color=farbe, edgecolor=t.surface, linewidth=2)
        for b, a in zip(balken, alphas):
            b.set_alpha(a)
        schritt = max(1, len(monate) // 12)
        self.ax.set_xticks(x[::schritt])
        self.ax.set_xticklabels([f"{MONATE_KURZ[m.month - 1]} {str(m.year)[2:]}" for m, *_ in monate][::schritt])
        self.ax.set_xlim(-0.6, len(monate) - 0.4)
        self.hover_setzen(list(x.astype(float)), [(einheit, np.array(werte, dtype=float), farbe)],
                          lambda i: f"{MONATE_KURZ[monate[i][0].month - 1]} {monate[i][0].year}"
                          + ("" if monate[i][2] else " · Prognose"))
        self._abschliessen()


class HeatmapChart(Diagramm):
    """Ø Belegung je Monat (Zeilen) und Wochentag (Spalten), eine Farbrichtung."""

    TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    def __init__(self, parent=None):
        super().__init__(hoehe=3.6, parent=parent)
        self._zellen: np.ndarray | None = None
        self._anzahl: np.ndarray | None = None

    def zeichnen(self, tage: pd.Series, farbe: str) -> None:
        self._vorbereiten()
        t = theme.T
        if tage.empty:
            self.leer("Keine Daten")
            return
        df = pd.DataFrame({"w": tage.to_numpy(dtype=float), "m": tage.index.month, "d": tage.index.weekday})
        pivot = df.pivot_table(index="d", columns="m", values="w", aggfunc="mean").reindex(index=range(7), columns=range(1, 13))
        anzahl = df.pivot_table(index="d", columns="m", values="w", aggfunc="count").reindex(index=range(7), columns=range(1, 13))
        cmap = LinearSegmentedColormap.from_list("seq", [t.surface_2, farbe])
        self.ax.grid(False)
        self.ax.spines["bottom"].set_visible(False)
        self.ax.imshow(pivot.to_numpy(), aspect="auto", cmap=cmap, interpolation="nearest")
        self.ax.set_xticks(range(12))
        self.ax.set_xticklabels(MONATE_KURZ)
        self.ax.set_yticks(range(7))
        self.ax.set_yticklabels(self.TAGE)
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: self.TAGE[int(v)] if 0 <= int(v) < 7 else ""))
        self.ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
        self.ax.set_yticks(np.arange(-0.5, 7, 1), minor=True)
        self.ax.grid(which="minor", color=t.surface, linewidth=2.5)
        self.ax.tick_params(which="minor", length=0)
        self._zellen, self._anzahl = pivot.to_numpy(), anzahl.to_numpy()
        self.fig.subplots_adjust(left=0.05, right=0.99, top=0.97, bottom=0.1)
        self.draw_idle()

    def _bewegung(self, e):
        if e.inaxes is not self.ax or self._zellen is None or e.xdata is None:
            self._tip_aus()
            return
        c, r = int(round(e.xdata)), int(round(e.ydata))
        if not (0 <= c < 12 and 0 <= r < 7) or np.isnan(self._zellen[r, c]):
            self._tip_aus()
            return
        t = theme.T
        if self._tip is None:
            self._tip = self.ax.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points", fontsize=8.5,
                                         color=t.tooltip_text, zorder=20,
                                         bbox=dict(boxstyle="round,pad=0.5", fc=t.tooltip_bg, ec="none"))
        self._tip.xy = (c, r)
        self._tip.set_ha("right" if c > 7 else "left")
        self._tip.set_position((-12 if c > 7 else 12, 12))
        self._tip.set_text(f"{MONATE_KURZ[c]} · {self.TAGE[r]}\nØ {zahl(self._zellen[r, c])} belegt\n{int(self._anzahl[r, c])} Tage")
        self._tip.set_visible(True)
        self.draw_idle()
