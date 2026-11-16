"""Cockpit (1.16) – Leitungsansicht „Ursache → Wirkung“: Renovierungs-Karten an- und abhaken, Monat schieben, sofort
sehen, was mit Baubudget, Möbel-Antrag, freien Betten und Umzügen passiert. Rein, ohne NiceGUI.

Rechnet nichts neu, sondern setzt vorhandene Bausteine zusammen:
* Karten = Jahresplan (vorgemerkt + Vorschlag der gewählten Variante) + weitere Etagen mit Bedarf (nicht angehakt).
* Je Etagen-Karte werden alle 12 Monate **einmal** vorgerechnet (Ausweichprüfung wie in „Vorhaben“: Umzüge, fehlender
  Ausweich, gesperrte Monate, Vorlauf vorbei). Danach ist jede Änderung nur noch Addieren – deshalb sofort.
* Einzelzimmer- und Möbel-Kampagnen nutzen Leerstand (eigene Termine je Zimmer); sie lassen sich an- und abhaken,
  ihr Termin bleibt (neu planen unter „Vorhaben“).
* Bedarf = Belegungsprognose: fest gebucht, erwartet (Planwert), obere Spanne (8 von 10). Decke = Kapazität minus
  defekte Zimmer minus gewählte Baustellen. Reserve = Decke − obere Spanne.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from . import renovierung_kern as rk

MONATE = rk.MONATE
EXTRA_ETAGEN = 6                     # so viele weitere Etagen mit Bedarf als (nicht angehakte) Karten


@dataclass
class Monat:
    moeglich: bool
    umzuege: int = 0
    ohne_ausweich: int = 0
    grund: str = ""                  # warum nicht möglich (gesperrt, Vorlauf vorbei)
    pruefbar: bool = True


@dataclass
class Karte:
    schluessel: str
    titel: str
    art: str                         # etage | zimmer | moebel
    flur: str
    haus: str
    zimmer_ids: list
    betten: int
    kosten: rk.Kosten
    klassen_bau: tuple
    klassen_moebel: tuple
    vorgemerkt: bool
    zeile: rk.PlanZeile              # Termin(e) wie geplant bzw. vorgeschlagen
    monate: dict = field(default_factory=dict)      # 1..12 → Monat (nur Etagen)
    bester: int | None = None
    gruende: list = field(default_factory=list)
    vorschlag: bool = True           # gehört zur gewählten Variante bzw. ist vorgemerkt

    @property
    def schiebbar(self) -> bool:
        return self.art == "etage" and bool(self.monate)

    @property
    def klasse(self) -> str:
        for i, k in enumerate("ABC"):
            if self.klassen_bau[i]:
                return k
        for i, k in enumerate("ABC"):
            if self.klassen_moebel[i]:
                return k
        return ""

    def zeile_im(self, monat: int | None) -> rk.PlanZeile:
        """Termin der Karte, für Etagen in den gewählten Monat verschoben (gleiche Dauer)."""
        z = self.zeile
        if not self.schiebbar or not monat or monat == z.start.month:
            return z
        start = date(z.start.year, monat, 1)
        return replace(z, start=start, ende=start + (z.ende - z.start), stopp_ab=start - (z.start - z.stopp_ab))

    def umzuege(self, monat: int | None) -> int:
        if self.art != "etage":
            return 0
        m = self.monate.get(monat or self.zeile.start.month)
        return m.umzuege if m else 0


@dataclass
class Bedarf:
    monate: list                     # date (Monatserster) des Planjahres
    fest: list
    erwartet: list
    hoch: list                       # obere 80-%-Spanne
    ist: list                        # bool: Monat liegt in der Vergangenheit (Ist)
    kapazitaet: float
    defekt: float

    @property
    def decke(self) -> float:
        return self.kapazitaet - self.defekt


@dataclass
class Bewertung:
    bau: float
    bau_spanne: float
    andere_bau: float
    budget: float | None
    moebel: float
    moebel_zimmer: int
    umzuege: int
    baustellen: list                 # Betten je Monat
    reserve: list                    # je Monat (None ohne Prognose)
    knappster: int | None            # Index des knappsten künftigen Monats
    engpaesse: list                  # Indizes mit Reserve < 0
    a_offen: int
    hinweise: list

    @property
    def verplant(self) -> float:
        return self.bau + self.andere_bau

    @property
    def rest(self) -> float | None:
        return None if self.budget is None else self.budget - self.verplant


def bedarf(pg, jahr: int, heute: date, kapazitaet: float | None, defekt: float) -> Bedarf | None:
    """Monate Jan–Dez des Planjahres aus der Belegungsprognose (PZeile: monat, art, erwartet, hi80, gesichert, ist)."""
    if not pg or not kapazitaet:
        return None
    je = {(z.monat.year, z.monat.month): z for z in pg.zeilen}
    b = Bedarf([], [], [], [], [], float(kapazitaet), float(defekt))
    for m in range(1, 13):
        z = je.get((jahr, m))
        b.monate.append(date(jahr, m, 1))
        if z is None:
            b.fest.append(None), b.erwartet.append(None), b.hoch.append(None), b.ist.append(False)
            continue
        ist = z.art == "ist" and z.ist is not None
        wert = z.ist if ist else z.erwartet
        b.ist.append(ist or date(jahr, m, 1) < date(heute.year, heute.month, 1))
        b.erwartet.append(round(float(wert), 1))
        b.hoch.append(round(float(wert if ist else z.hi80), 1))
        fest = z.gesichert if z.gesichert is not None else (wert if ist else None)
        b.fest.append(round(float(min(fest, wert)), 1) if fest is not None else None)
    return b


def karten(stand, fl: list, p: dict, jahr: int, heute: date, zeilen: list, machbar: set | None = None,
           prognose: dict | None = None) -> list[Karte]:
    """Karten aus dem Jahresplan (``zeilen``: PlanZeilen – vorgemerkt und Vorschlag) und weitere Etagen mit Bedarf."""
    nach_schl = {f.schluessel: f for f in fl}
    erg: list[Karte] = []
    gesehen: set = set()
    for z in zeilen:
        if z.start.year != jahr:
            continue
        f = nach_schl.get(z.flur)
        if f is None:
            continue
        ids = [t[0] for t in z.teile] if z.teile else [x.id for x in f.zimmer]
        erg.append(_karte(stand, f, p, jahr, heute, z, ids, z.status == "vorgemerkt", True, prognose))
        if z.art == "etage":
            gesehen.add(f.schluessel)
    belegt = {zid for k in erg for zid in k.zimmer_ids}
    extra = [f for f in fl if f.schluessel not in gesehen and f.wert > 0 and (machbar is None or f.schluessel in machbar)
             and not any(x.id in belegt for x in f.zimmer)]
    extra.sort(key=lambda f: (tuple(-x for x in rk.klassen_zahl([(f, x, "etage") for x in f.zimmer])), -f.wert))
    for f in extra[:EXTRA_ETAGEN]:
        k = rk.kosten(p, f.haus, len(f.zimmer), jahr)
        dauer = int((p["kosten"].get(f.haus) or {}).get("dauer_tage") or p.get("dauer_tage") or 30)
        start = date(jahr, 1, 1)
        z = rk.PlanZeile(f.schluessel, f.text, len(f.zimmer), f.betten, start, start + timedelta(days=dauer - 1),
                         start - timedelta(days=int(p["vorlauf_tage"])), "vorschlag", k)
        karte = _karte(stand, f, p, jahr, heute, z, [x.id for x in f.zimmer], False, False, prognose)
        if karte.bester:                                     # nur Etagen, die in diesem Jahr überhaupt gehen
            karte.zeile = karte.zeile_im(karte.bester)
            erg.append(karte)
    rang = lambda k: (not k.vorschlag, tuple(-x for x in k.klassen_bau), tuple(-x for x in k.klassen_moebel), k.titel)  # noqa: E731
    return sorted(erg, key=rang)


def _karte(stand, f, p, jahr, heute, z, ids, vorgemerkt, vorschlag, prognose) -> Karte:
    zs = [x for x in f.zimmer if x.id in set(ids)]
    liste = [(f, x, z.art) for x in zs]
    titel = f.text if z.art == "etage" else f"{f.text} · {len(zs)} Zimmer {('komplett' if z.art == 'zimmer' else 'nur Möbel')}"
    k = Karte(f"{z.art}|{f.schluessel}|{','.join(sorted(ids)) if z.art != 'etage' else ''}", titel, z.art, f.schluessel,
              f.haus, list(ids), sum(x.betten for x in zs), z.kosten, rk.klassen_zahl(liste, "bau"),
              rk.klassen_zahl(liste, "moebel"), vorgemerkt, z, vorschlag=vorschlag)
    k.gruende = [t for _w, t in sorted(f.gruende, key=lambda g: -g[0])][:4]
    if z.art == "etage":
        fs = rk.monatsfenster(stand, f, jahr, p, prognose)
        for fe in fs:
            grund = "gesperrt" if fe.gesperrt else ("Vorlauf vorbei" if fe.stopp_ab < heute else "")
            k.monate[fe.start.month] = Monat(not grund, fe.betroffen, len(fe.ohne_ausweich), grund, fe.pruefbar)
        best = rk.bester_monat(fs, heute)
        k.bester = best.start.month if best else None
    return k


def standard_auswahl(ks: list[Karte]) -> dict:
    """Schlüssel → Monat (Etage) bzw. 0 (Kampagne) für angehakte Karten; nicht angehakte fehlen.
    Gibt es im Jahr schon Vormerkungen, sind nur diese angehakt (eine bewusst abgehakte Etage taucht nach dem
    Übernehmen nicht wieder angehakt auf); sonst ist der Vorschlag der gewählten Variante angehakt."""
    gewaehlt = [k for k in ks if k.vorgemerkt] or [k for k in ks if k.vorschlag]
    return {k.schluessel: (k.zeile.start.month if k.art == "etage" else 0) for k in gewaehlt}


def bewerten(ks: list[Karte], auswahl: dict, bd: Bedarf | None, budget: float | None, andere_bau: float,
             fl: list) -> Bewertung:
    gew = [k for k in ks if k.schluessel in auswahl]
    summe = rk.Kosten(0, 0, herkunft_bau="", herkunft_moebel="")
    for k in gew:
        summe = summe.plus(k.kosten)
    bau_lo, bau_hi = summe.spanne_von("bau")
    zeilen = [k.zeile_im(auswahl.get(k.schluessel)) for k in gew]
    baust = [rk.gesperrte_betten(zeilen, date(bd.monate[0].year, m, 1)) if bd else 0.0 for m in range(1, 13)] \
        if bd else [0.0] * 12
    reserve, eng, knapp = [], [], None
    for i in range(12):
        if not bd or bd.hoch[i] is None:
            reserve.append(None)
            continue
        r = round(bd.decke - baust[i] - bd.hoch[i], 1)
        reserve.append(r)
        if bd.ist[i]:
            continue
        if r < 0:
            eng.append(i)
        if knapp is None or r < reserve[knapp]:
            knapp = i
    drin = {zid for k in gew if k.art != "moebel" for zid in k.zimmer_ids}
    a_offen = sum(1 for f in fl for x in f.zimmer if x.id not in drin
                  and (b := f.bedarfe.get(x.id)) is not None and b.bau == "A" and not b.frisch)
    hinweise = []
    if a_offen and any(k.klassen_bau[2] and not k.klassen_bau[0] and not k.klassen_bau[1] for k in gew):
        hinweise.append(f"C-Bedarf ist gewählt, obwohl noch {a_offen} Zimmer mit A-Bedarf offen sind.")
    for k in gew:
        m = k.monate.get(auswahl.get(k.schluessel) or 0) if k.schiebbar else None
        if m is not None and not m.moeglich:
            hinweise.append(f"{k.titel}: {MONATE[auswahl[k.schluessel] - 1]} ist nicht möglich ({m.grund}).")
        elif m is not None and m.ohne_ausweich:
            hinweise.append(f"{k.titel}: im {MONATE[auswahl[k.schluessel] - 1]} fehlt für {m.ohne_ausweich} Person(en) "
                            "ein Ausweichzimmer.")
    return Bewertung(summe.instandhaltung, (bau_hi - bau_lo) / 2, andere_bau, budget, summe.investition,
                     sum(len(k.zimmer_ids) for k in gew), sum(k.umzuege(auswahl.get(k.schluessel)) for k in gew),
                     baust, reserve, knapp, eng, a_offen, hinweise)


def wirkung_text(k: Karte, monat: int | None, bw: Bewertung) -> tuple[str, str]:
    """(Text, Stufe ok|warn|krit) für die Karte im gewählten Monat."""
    if k.art != "etage":
        z = k.zeile
        return (f"Leerstand {z.start:%d.%m.}–{z.ende:%d.%m.}", "ok")
    m = monat or k.zeile.start.month
    i = m - 1
    r = bw.reserve[i] if bw.reserve else None
    if r is None:
        return ("Reserve unbekannt (keine Prognose)", "warn")
    stufe = "krit" if r < 0 else "warn" if r < 10 else "ok"
    return ((f"im {MONATE[i]} fehlen {abs(round(r))} Betten" if r < 0 else f"Reserve {MONATE[i]} {round(r):+d}"), stufe)


def eintraege(k: Karte, monat: int | None) -> list:
    """Vormerk-Einträge wie in „Vorhaben“: Etage (Flur, Start, Ende), Kampagne je Zimmer (Flur, von, bis, Art, [ID])."""
    z = k.zeile_im(monat)
    if k.art == "etage":
        return [(k.flur, z.start, z.ende)]
    return [(k.flur, von, bis, k.art, [zid]) for zid, _kurz, von, bis, _b in z.teile]


def uebernehmen(ks: list[Karte], auswahl: dict) -> str:
    """Angehakte Karten vormerken (Etagen im gewählten Monat), abgehakte Vormerkungen entfernen – ein Schritt."""
    neu, weg = [], []
    for k in ks:
        an = k.schluessel in auswahl
        if an and (not k.vorgemerkt or (k.art == "etage" and auswahl[k.schluessel] != k.zeile.start.month)):
            if k.vorgemerkt:                                     # verschoben: alte Vormerkung ersetzen
                weg.append((k.flur, k.zeile.start.isoformat(), "etage"))
            neu += eintraege(k, auswahl[k.schluessel])
        elif not an and k.vorgemerkt:
            weg += ([(k.flur, k.zeile.start.isoformat(), "etage")] if k.art == "etage"
                    else [(k.flur, von.isoformat(), k.art) for _zid, _kurz, von, _bis, _b in k.zeile.teile])
    for flur, start, art in weg:
        rk.entfernen(flur, start, art)
    for e in neu:
        flur, start, ende, *rest = e
        rk.vormerken(flur, start, ende, "", *(rest[:1] or ["etage"]), *(rest[1:2] or [None]))
    return (f"Cockpit übernommen: {len(neu)} vorgemerkt" + (f", {len(weg)} entfernt" if weg else "")) if neu or weg \
        else "Nichts zu übernehmen – alles wie vorgemerkt."


def uebernehmen_schritt(ks: list[Karte], auswahl: dict) -> str:
    from .kern import _schritt

    erg = []
    _schritt("Cockpit: Renovierungsauswahl übernommen", lambda: erg.append(uebernehmen(ks, auswahl)), [rk.DATEI])
    return erg[0]


def diagramm(bd: Bedarf, bw: Bewertung, dunkel: bool = False, text: str = "#334155") -> dict:
    """ECharts-Option „Decke gegen Bedarf“: von unten der Bedarf (fest, erwartet, obere Spanne), von oben die Decke
    (defekte Zimmer grau, Baustellen orange), rot, wo die obere Spanne über die Decke geht. Alle Reihen ``m_fest``:
    der Diagrammtyp aus „Diagrammentwurf“ stellt dieses Diagramm nicht um (es ist eine Bilanz, kein Verlauf)."""
    fest_f, erw_f, risk_f = ("#566B87" if dunkel else "#1e3a5f"), "#7fb3d5", ("rgba(127,179,213,.35)")
    decke = [round(bd.decke - b, 1) for b in bw.baustellen]
    n = lambda v: None if v is None else round(v, 1)                                    # noqa: E731
    fest = [n(f if f is not None else e) for f, e in zip(bd.fest, bd.erwartet)]
    erw = [n(e - f) if e is not None and f is not None else None for e, f in zip(bd.erwartet, fest)]
    risk = [n(h - e) if h is not None and e is not None else None for h, e in zip(bd.hoch, bd.erwartet)]
    eng = [n(max(0.0, h - d)) if h is not None and h > d else None for h, d in zip(bd.hoch, decke)]
    werte = [v for v in list(bd.erwartet) + decke if v is not None]       # Achse dort, wo Bedarf und Decke liegen
    unten = max(0, int((min(werte) - 15) // 10 * 10)) if werte else 0
    step = {"step": "middle", "symbol": "none", "m_fest": True}
    balken = {"type": "bar", "barWidth": "88%", "m_fest": True, "barGap": "-100%"}
    serien = [
        {**step, "name": "fest gebucht / laufend", "type": "line", "stack": "b", "data": fest, "areaStyle": {"color": fest_f, "opacity": 1},
         "lineStyle": {"width": 0}, "itemStyle": {"color": fest_f}, "z": 2},
        {**step, "name": "erwartet dazu", "type": "line", "stack": "b", "data": erw, "areaStyle": {"color": erw_f, "opacity": 1},
         "lineStyle": {"width": 0}, "itemStyle": {"color": erw_f}, "z": 2},
        {**step, "name": "Risiko (8 von 10)", "type": "line", "stack": "b", "data": risk,
         "areaStyle": {"color": risk_f, "opacity": 1}, "lineStyle": {"width": 1, "type": "dashed", "color": "#0369a1"},
         "itemStyle": {"color": "#9cc3dd"}, "z": 2},
        {**balken, "name": "_frei", "stack": "d", "data": decke, "itemStyle": {"color": "transparent"}, "silent": True,
         "tooltip": {"show": False}},
        {**balken, "name": "Baustelle", "stack": "d", "data": [n(b) or None for b in bw.baustellen],
         "itemStyle": {"color": "#f59e0b"}, "z": 3},
        {**balken, "name": "defekte Zimmer", "stack": "d", "data": [n(bd.defekt) or None] * 12, "itemStyle": {"color": "#94a3b8"},
         "z": 3},
        {**balken, "name": "_eng0", "stack": "e", "data": [d if e else None for d, e in zip(decke, eng)],
         "itemStyle": {"color": "transparent"}, "silent": True, "tooltip": {"show": False}},
        {**balken, "name": "Engpass", "stack": "e", "data": eng, "itemStyle": {"color": "#e11d48"}, "z": 4,
         "label": {"show": True, "position": "insideTop", "color": "#fff", "fontWeight": "bold", "fontSize": 12,
                   "formatter": "fehlen {c}"}},
        {**step, "name": "verfügbare Betten", "type": "line", "data": decke, "lineStyle": {"width": 2.5, "color": text},
         "itemStyle": {"color": text}, "z": 5},
    ]
    return {"animation": False, "grid": {"left": 48, "right": 16, "top": 64, "bottom": 30},
            "legend": {"top": 0, "left": 0, "data": ["fest gebucht / laufend", "erwartet dazu", "Risiko (8 von 10)", "defekte Zimmer",
                                          "Baustelle", "Engpass", "verfügbare Betten"]},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [f"{MONATE[d.month - 1]}" for d in bd.monate], "boundaryGap": True},
            "yAxis": {"type": "value", "min": unten, "max": int(bd.kapazitaet + 5)},
            "series": serien}
