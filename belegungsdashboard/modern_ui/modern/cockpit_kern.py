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


@dataclass
class Vorschau:
    """1.18: Was ändert sich, wenn diese Karte an- bzw. abgehakt würde (im angezeigten Monat)?"""
    bw: Bewertung
    an: bool                         # True = Karte käme dazu, False = fiele weg
    bau: float
    moebel: float
    zimmer: int
    umzuege: int
    knapp_vorher: tuple | None       # (Monatsindex, Reserve)
    knapp_nachher: tuple | None
    neue_engpaesse: list


def vorschau(ks: list[Karte], auswahl: dict, k: Karte, monat: int | None, bd: Bedarf | None, budget: float | None,
             andere_bau: float, fl: list, jetzt: Bewertung) -> Vorschau:
    an = k.schluessel not in auswahl
    neu = dict(auswahl)
    if an:
        neu[k.schluessel] = monat if k.art == "etage" else 0
    else:
        neu.pop(k.schluessel)
    bw = bewerten(ks, neu, bd, budget, andere_bau, fl)
    kn = lambda b: (b.knappster, b.reserve[b.knappster]) if b.knappster is not None else None       # noqa: E731
    return Vorschau(bw, an, bw.bau - jetzt.bau, bw.moebel - jetzt.moebel, bw.moebel_zimmer - jetzt.moebel_zimmer,
                    bw.umzuege - jetzt.umzuege, kn(jetzt), kn(bw), [i for i in bw.engpaesse if i not in jetzt.engpaesse])


def _vz(n: int) -> str:
    return f"+{n}" if n >= 0 else f"−{abs(n)}"


def vorschau_texte(v: Vorschau, jahr: int) -> dict:
    """Kurze Texte für die vier Kacheln (leer = keine Änderung)."""
    eur = lambda x: f"{round(abs(x)):,} €".replace(",", ".")                                      # noqa: E731
    t = {}
    if round(v.bau):
        t["budget"] = (f"Vorschau: {'+' if v.bau > 0 else '−'}{eur(v.bau)}"
                       + (f" → {eur(v.bw.rest)} über Budget" if v.bw.rest is not None and v.bw.rest < 0 else
                          f" → Rest {eur(v.bw.rest)}" if v.bw.rest is not None else ""))
    if round(v.moebel) or v.zimmer:
        t["moebel"] = f"Vorschau: {_vz(v.zimmer)} Zimmer · {'+' if v.moebel >= 0 else '−'}{eur(v.moebel)}"
    if v.knapp_nachher and (v.neue_engpaesse or v.knapp_vorher is None
                            or round(v.knapp_nachher[1]) != round(v.knapp_vorher[1])):   # nur bei echter Änderung
        i, r = v.knapp_nachher
        t["engpass"] = (f"Vorschau: {MONATE[i]} fehlen {abs(round(r))} Betten" if r < 0
                        else f"Vorschau: knappster Monat {MONATE[i]} {_vz(round(r))}")
    if v.umzuege:
        t["umzuege"] = f"Vorschau: {_vz(v.umzuege)} Umzüge"
    return t


def diagramm(bd: Bedarf, bw: Bewertung, dunkel: bool = False, text: str = "#334155", vor: Bewertung | None = None,
             wd: "WennDann | None" = None, band: bool = True, null: bool = False) -> dict:
    """ECharts-Option „Decke gegen Bedarf“: von unten der Bedarf (fest, erwartet, obere Spanne), von oben die Decke
    (defekte Zimmer grau, Baustellen orange), rot, wo die obere Spanne über die Decke geht. Alle Reihen ``m_fest``:
    der Diagrammtyp aus „Diagrammentwurf“ stellt dieses Diagramm nicht um (es ist eine Bilanz, kein Verlauf)."""
    fest_f, erw_f, risk_f = ("#566B87" if dunkel else "#1e3a5f"), "#7fb3d5", ("rgba(127,179,213,.35)")
    decke = [round(bd.decke - b, 1) for b in bw.baustellen]
    b0 = bw.baustellen
    b1 = vor.baustellen if vor else b0
    decke_v = [round(bd.decke - b, 1) for b in b1]
    n = lambda v: None if v is None else round(v, 1)                                    # noqa: E731
    fest = [n(f if f is not None else e) for f, e in zip(bd.fest, bd.erwartet)]
    erw = [n(e - f) if e is not None and f is not None else None for e, f in zip(bd.erwartet, fest)]
    risk = [n(h - e) if h is not None and e is not None else None for h, e in zip(bd.hoch, bd.erwartet)]
    eng = [n(max(0.0, h - d)) if h is not None and h > d else None for h, d in zip(bd.hoch, decke_v)]
    werte = [v for v in list(bd.erwartet) + decke if v is not None]       # Achse dort, wo Bedarf und Decke liegen
    unten = 0 if null else (max(0, int((min(werte) - 15) // 10 * 10)) if werte else 0)
    step = {"step": "middle", "symbol": "none", "m_fest": True}
    balken = {"type": "bar", "barWidth": "88%", "m_fest": True, "barGap": "-100%"}
    serien = [
        {**step, "name": "schon gebucht", "type": "line", "stack": "b", "data": fest, "areaStyle": {"color": fest_f, "opacity": 1},
         "lineStyle": {"width": 0}, "itemStyle": {"color": fest_f}, "z": 2},
        {**step, "name": "noch erwartet", "type": "line", "stack": "b", "data": erw, "areaStyle": {"color": erw_f, "opacity": 1},
         "lineStyle": {"width": 0}, "itemStyle": {"color": erw_f}, "z": 2},
        {**step, "name": "ungünstiger Fall (8 von 10)", "type": "line", "stack": "b", "data": risk,
         "areaStyle": {"color": risk_f, "opacity": 1}, "lineStyle": {"width": 1, "type": "dashed", "color": "#0369a1"},
         "itemStyle": {"color": "#9cc3dd"}, "z": 2},
        {**balken, "name": "_frei", "stack": "d", "data": [round(bd.decke - max(x, y), 1) for x, y in zip(b0, b1)],
         "itemStyle": {"color": "transparent"}, "silent": True, "tooltip": {"show": False}},
        {**balken, "name": "Vorschau: Baustelle dazu", "stack": "d", "data": [n(max(0.0, y - x)) or None for x, y in zip(b0, b1)],
         "itemStyle": {"color": "rgba(245,158,11,.30)", "borderColor": "#f59e0b", "borderWidth": 1.5, "borderType": "dashed"},
         "z": 3},
        {**balken, "name": "Vorschau: wird frei", "stack": "d", "data": [n(max(0.0, x - y)) or None for x, y in zip(b0, b1)],
         "itemStyle": {"color": "rgba(16,185,129,.25)", "borderColor": "#10b981", "borderWidth": 1.5, "borderType": "dashed"},
         "z": 3},
        {**balken, "name": "Baustelle", "stack": "d", "data": [n(min(x, y)) or None for x, y in zip(b0, b1)],
         "itemStyle": {"color": "#f59e0b"}, "z": 3},
        {**balken, "name": "defekte Zimmer", "stack": "d", "data": [n(bd.defekt) or None] * 12, "itemStyle": {"color": "#94a3b8"},
         "z": 3},
        {**balken, "name": "_eng0", "stack": "e", "data": [d if e else None for d, e in zip(decke_v, eng)],
         "itemStyle": {"color": "transparent"}, "silent": True, "tooltip": {"show": False}},
        {**balken, "name": "Engpass", "stack": "e", "data": eng, "itemStyle": {"color": "#e11d48"}, "z": 4,
         "label": {"show": True, "position": "insideTop", "color": "#fff", "fontWeight": "bold", "fontSize": 12,
                   "formatter": "fehlen {c}"}},
        {**step, "name": "verfügbare Betten", "type": "line", "data": decke, "lineStyle": {"width": 2.5, "color": text},
         "itemStyle": {"color": text}, "z": 5},
    ]
    if not band:                                          # 1.20: Unsicherheit ausblenden
        serien = [x for x in serien if x["name"] != "ungünstiger Fall (8 von 10)"]
    if wd is not None and wd.vorher is not None:          # 1.19: Vergleich „ohne Wenn-dann“ und der angenommene Punkt
        serien.append({**step, "name": "ohne Wenn-dann", "type": "line", "data": [n(e) for e in wd.vorher.erwartet], "z": 6,
                       "lineStyle": {"width": 2, "type": "dotted", "color": "#7c3aed"}, "itemStyle": {"color": "#7c3aed"}})
        serien.append({"name": "Wenn-dann", "type": "scatter", "m_fest": True, "z": 7, "symbolSize": 14,
                       "data": [[wd.monat, round(wd.wert, 1)]],
                       "itemStyle": {"color": "#fff", "borderColor": "#7c3aed", "borderWidth": 3},
                       "label": {"show": True, "position": "top", "color": "#7c3aed", "fontWeight": "bold",
                                 "formatter": f"wenn {round(wd.wert)}"}})
    if vor:
        serien.append({**step, "name": "Vorschau: verfügbar", "type": "line", "data": decke_v, "z": 6,
                       "lineStyle": {"width": 2, "type": "dashed", "color": "#f59e0b"}, "itemStyle": {"color": "#f59e0b"}})
    return {"animation": False, "grid": {"left": 48, "right": 16, "top": 64, "bottom": 30},
            "legend": {"top": 0, "left": 0, "data": ["schon gebucht", "noch erwartet"] + (["ungünstiger Fall (8 von 10)"] if band else []) + ["defekte Zimmer",
                                          "Baustelle", "Engpass", "verfügbare Betten"]
                       + (["Vorschau: verfügbar"] if vor else []) + (["ohne Wenn-dann"] if wd is not None else [])},
            "tooltip": _tooltip(monats_texte(bd, bw)),
            "xAxis": {"type": "category", "data": [f"{MONATE[d.month - 1]}" for d in bd.monate], "boundaryGap": True},
            "yAxis": {"type": "value", "min": unten, "max": int(bd.kapazitaet + 5)},
            "series": serien}


# ---- 1.19: Wenn-dann ------------------------------------------------------------------------------------------
# „Wenn im März 270 statt 255 belegt sind – wie geht es weiter?“ Die Belegung ist ein Bestand: eine Abweichung bleibt
# eine Weile, klingt aber ab (Abreisen, neue Anreisen). Wie schnell, wird aus der eigenen Geschichte gemessen
# (Beharrung ρ = Korrelation der Abweichung vom Monatsmittel mit der des Folgemonats). Danach:
#   erwartet' = erwartet + d · ρᵏ           (k Monate nach dem gewählten Monat, d = Wert − Planwert)
#   Spanne'   = Spanne · √(1 − ρ²ᵏ)         (im gewählten Monat 0 – der Wert ist ja angenommen –, später wieder breiter)
# Keine neue Simulation, kein drittes Modell: dieselbe Prognose, nur bedingt verschoben.

BEHARRUNG_STANDARD = 0.8


def beharrung(pg) -> float:
    """ρ aus den Ist-Monaten der Belegungsprognose; ohne genug Geschichte (unter 12 Paaren) der Standard 0,8."""
    ist = [(z.monat, float(z.ist)) for z in (pg.zeilen if pg else []) if z.art == "ist" and z.ist is not None]
    if len(ist) < 14:
        return BEHARRUNG_STANDARD
    je_monat: dict[int, list] = {}
    for m, v in ist:
        je_monat.setdefault(m.month, []).append(v)
    mittel = {k: sum(v) / len(v) for k, v in je_monat.items()}
    ab = [v - mittel[m.month] for m, v in ist]
    paare = list(zip(ab[:-1], ab[1:]))
    if len(paare) < 12:
        return BEHARRUNG_STANDARD
    mx = sum(x for x, _ in paare) / len(paare)
    my = sum(y for _, y in paare) / len(paare)
    sxy = sum((x - mx) * (y - my) for x, y in paare)
    sxx = sum((x - mx) ** 2 for x, _ in paare) ** .5
    syy = sum((y - my) ** 2 for _, y in paare) ** .5
    if not sxx or not syy:
        return BEHARRUNG_STANDARD
    return round(min(0.95, max(0.3, sxy / (sxx * syy))), 2)


@dataclass
class WennDann:
    monat: int                       # Index 0–11 im Planjahr
    wert: float
    planwert: float
    rho: float
    bedarf: Bedarf                   # bedingt angepasster Bedarf
    vorher: Bedarf | None = None     # Bedarf ohne Wenn-dann (Vergleichslinie)

    @property
    def abweichung(self) -> float:
        return self.wert - self.planwert


def wenn_dann(bd: Bedarf, monat: int, wert: float, rho: float = BEHARRUNG_STANDARD) -> WennDann | None:
    """Bedarf, wenn im Monat ``monat`` (Index im Planjahr) ``wert`` belegt sind. None bei Ist-Monat oder ohne Prognose."""
    if not bd or not (0 <= monat < len(bd.monate)) or bd.ist[monat] or bd.erwartet[monat] is None:
        return None
    d = float(wert) - bd.erwartet[monat]
    neu = replace(bd, fest=list(bd.fest), erwartet=list(bd.erwartet), hoch=list(bd.hoch))
    for i in range(monat, len(bd.monate)):
        if bd.erwartet[i] is None or bd.hoch[i] is None:
            continue
        k = i - monat
        e = bd.erwartet[i] + d * rho ** k
        if bd.fest[i] is not None:
            e = max(e, bd.fest[i])                          # unter das schon fest Gebuchte geht es nicht
        breite = (bd.hoch[i] - bd.erwartet[i]) * (1 - rho ** (2 * k)) ** .5
        neu.erwartet[i] = round(e, 1)
        neu.hoch[i] = round(e + breite, 1)
    return WennDann(monat, float(wert), bd.erwartet[monat], rho, neu, bd)


def wenn_dann_satz(w: WennDann, vorher: Bewertung, nachher: Bewertung) -> str:
    m = MONATE[w.monat]
    teile = [f"Wenn im {m} {round(w.wert)} statt {round(w.planwert)} belegt sind"]
    folgend = [i for i in range(w.monat + 1, min(w.monat + 4, 12)) if w.bedarf.erwartet[i] is not None]
    if folgend:
        i = folgend[-1]
        teile.append(f"erwartet {MONATE[i]} {round(w.bedarf.erwartet[i])} statt {round(w.vorher.erwartet[i])}")
    if nachher.knappster is not None:
        r = nachher.reserve[nachher.knappster]
        teile.append(f"knappster Monat {MONATE[nachher.knappster]} "
                     + (f"{round(r):+d} Betten".replace("-", "−") if r >= 0 else f"– fehlen {abs(round(r))} Betten"))
    if len(nachher.engpaesse) != len(vorher.engpaesse):
        teile.append(f"{len(nachher.engpaesse)} statt {len(vorher.engpaesse)} Monat(e) mit Engpass")
    return " → ".join([teile[0], " · ".join(teile[1:])]) + f" (Abweichung klingt je Monat auf {round(100 * w.rho)} % ab)"


# ---- 1.20: verständlicher – „Freie Betten je Monat“ und Tooltip als Satz -----------------------------------------

def monats_texte(bd: Bedarf, bw: Bewertung) -> list[str]:
    """Je Monat ein kurzer Klartext (HTML) für den Tooltip – statt einer Liste aller Reihen mit „–“."""
    erg = []
    for i, m in enumerate(bd.monate):
        kopf = f"<b>{MONATE[m.month - 1]} {m.year}</b>"
        if bd.erwartet[i] is None:
            erg.append(kopf + "<br>keine Prognose")
            continue
        verf = bd.decke - bw.baustellen[i]
        frei_e, frei_h = verf - bd.erwartet[i], verf - bd.hoch[i]
        teile = [kopf]
        if bd.ist[i]:
            teile.append(f"belegt: {round(bd.erwartet[i])} (Ist)")
        else:
            gebucht = f" – davon {round(bd.fest[i])} schon gebucht" if bd.fest[i] is not None else ""
            teile.append(f"erwartet belegt: {round(bd.erwartet[i])}{gebucht}")
            teile.append(f"im ungünstigen Fall (8 von 10): bis {round(bd.hoch[i])}")
        abzug = [f"{round(bd.defekt)} defekt" if bd.defekt else "", f"{round(bw.baustellen[i])} Baustelle" if bw.baustellen[i] else ""]
        abzug = [x for x in abzug if x]
        teile.append(f"verfügbar: {round(verf)} Betten" + (f" ({round(bd.kapazitaet)} − {' − '.join(abzug)})" if abzug else ""))
        if bd.ist[i]:
            teile.append(f"frei: {round(frei_e)}")
        else:
            teile.append(f"frei: {round(frei_e)} erwartet · {round(frei_h)} im ungünstigen Fall"
                         if frei_h >= 0 else f"<span style='color:#e11d48'>im ungünstigen Fall fehlen {abs(round(frei_h))} Betten</span>")
        erg.append("<br>".join(teile))
    return erg


def _tooltip(texte: list[str]) -> dict:
    import json

    return {"trigger": "axis", "confine": True,
            ":formatter": f"(ps) => {{ const t = {json.dumps(texte, ensure_ascii=False)}; return t[ps[0].dataIndex] || ''; }}"}


def diagramm_frei(bd: Bedarf, bw: Bewertung, vor: Bewertung | None = None, wd: "WennDann | None" = None,
                  band: bool = True, null: bool = True) -> dict:
    """Je Monat eine Säule „freie Betten“: dunkel = bleibt auch im ungünstigen Fall frei (8 von 10), hell = zusätzlich
    frei, wenn es wie erwartet kommt, rot = fehlen im ungünstigen Fall. ``band`` False: nur der erwartete Wert."""
    n = lambda v: None if v is None else round(v, 1)                                    # noqa: E731
    verf = [bd.decke - b for b in bw.baustellen]
    frei_e = [n(v - e) if e is not None else None for v, e in zip(verf, bd.erwartet)]
    frei_h = [n(v - h) if h is not None else None for v, h in zip(verf, bd.hoch)]
    sicher, extra, fehlt = [], [], []
    for e, h in zip(frei_e, frei_h):
        if e is None:
            sicher.append(None), extra.append(None), fehlt.append(None)
        elif not band:
            sicher.append(max(0.0, e)), extra.append(None), fehlt.append(n(min(0.0, e)) or None)
        else:
            sicher.append(max(0.0, h)), extra.append(n(max(0.0, e) - max(0.0, h)) or None), fehlt.append(n(min(0.0, h)) or None)
    balken = {"type": "bar", "stack": "f", "barMaxWidth": 44, "m_fest": True}
    serien = [
        {**balken, "name": "frei auch im ungünstigen Fall" if band else "frei (erwartet)", "data": sicher,
         "itemStyle": {"color": "#0f766e"}},
        {**balken, "name": "frei, wenn es wie erwartet kommt", "data": extra,
         "itemStyle": {"color": "rgba(15,118,110,.35)"}},
        {**balken, "name": "fehlen", "data": fehlt, "itemStyle": {"color": "#e11d48"},
         "label": {"show": True, "position": "bottom", "color": "#e11d48", "fontWeight": "bold",
                   ":formatter": "(p) => p.value == null ? '' : Math.round(p.value)"}},
        {"type": "line", "name": "_summe", "data": [n(max(0.0, e)) if e is not None else None for e in frei_e],
         "symbol": "none", "lineStyle": {"opacity": 0}, "m_fest": True, "silent": True, "tooltip": {"show": False},
         "label": {"show": True, "position": "top", "fontSize": 12, ":formatter": "(p) => p.value == null ? '' : Math.round(p.value)"}},
    ]
    if vor is not None:
        verf_v = [bd.decke - b for b in vor.baustellen]
        serien.append({"type": "line", "name": "Vorschau", "m_fest": True, "step": "middle", "symbol": "none",
                       "data": [n(v - (h if band else e)) if e is not None else None
                                for v, e, h in zip(verf_v, bd.erwartet, bd.hoch)],
                       "lineStyle": {"width": 2.5, "type": "dashed", "color": "#f59e0b"}, "itemStyle": {"color": "#f59e0b"}, "z": 6})
    if wd is not None and wd.vorher is not None:
        verf0 = verf
        serien.append({"type": "line", "name": "ohne Wenn-dann", "m_fest": True, "step": "middle", "symbol": "none",
                       "data": [n(v - (h if band else e)) if e is not None else None
                                for v, e, h in zip(verf0, wd.vorher.erwartet, wd.vorher.hoch)],
                       "lineStyle": {"width": 2, "type": "dotted", "color": "#7c3aed"}, "itemStyle": {"color": "#7c3aed"}, "z": 6})
    werte = [v for v in (fehlt + frei_e) if v is not None]
    legende = ["frei auch im ungünstigen Fall", "frei, wenn es wie erwartet kommt", "fehlen"] if band else ["frei (erwartet)", "fehlen"]
    return {"animation": False, "grid": {"left": 48, "right": 16, "top": 56, "bottom": 30},
            "legend": {"top": 0, "left": 0, "data": legende + (["Vorschau"] if vor is not None else [])
                       + (["ohne Wenn-dann"] if wd is not None else [])},
            "tooltip": _tooltip(monats_texte(bd, bw)),
            "xAxis": {"type": "category", "data": [MONATE[d.month - 1] for d in bd.monate]},
            "yAxis": {"type": "value", "name": "freie Betten", "nameGap": 10,
                      "nameTextStyle": {"align": "left"}, "min": (min(0, int(min(werte)) - 5) if werte else 0) if null
                      or (werte and min(werte) < 0) else None,
                      "splitLine": {"lineStyle": {"type": "dashed"}}},
            "series": serien}
