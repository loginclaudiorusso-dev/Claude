"""0.15: Heute als Newsfeed mit Briefing, schnellere Prognose (gleiche Werte, Zwischenspeicher) – erfundene Daten."""

from datetime import date
from types import SimpleNamespace as N

import pandas as pd

HEUTE = date(2026, 10, 25)


def _tag():
    from modern.seite_heute import Tag

    t = Tag({"frei": 12, "belegt": 30, "gesperrt": 1, "ohne_zimmer": 5})
    t.anreisen = [("2026-10-25", "So 25.10. · RVL (3)", 3, 1), ("2026-10-26", "Mo 26.10. · EMR (4)", 4, 4)]
    t.abreisen = [("heute", "Muster, Max", "2-101"), ("morgen", "Probe, Paula", "3-204")]
    t.reinigung = (2, 7)
    t.neuigkeiten = [("25.10. 08:00", "Gebäudeplan übernommen", "info"), ("25.10. 07:00", "Liste unvollständig", "warnung")]
    return t


def _karten():
    return [N(stufe="dringend", titel="3 Personen ohne Zimmer"), N(stufe="bald", titel="Termin"), N(stufe="info", titel="Info")]


def test_briefing_drei_fakten_ohne_namen():
    from modern.seite_heute import briefing

    sz = briefing(_tag(), _karten(), HEUTE)
    text = " ".join(sz)
    assert sz[0] == "Guten Morgen. Das Briefing für Sonntag, den 25. Oktober." and sz[-1] == "Ende des Briefings."
    assert "Heute reisen 3 Personen an, 2 davon haben noch kein Zimmer." in sz
    assert "12 Zimmer sind heute frei, 5 Personen der nächsten Wochen warten noch auf ein Zimmer." in sz
    assert "1 dringende Aufgabe. Zuerst: 3 Personen ohne Zimmer." in sz
    assert "Muster" not in text and "Probe" not in text and len(sz) == 5
    leer = _tag()
    leer.anreisen = []
    assert "Heute und morgen sind keine Anreisen geplant." in briefing(leer, [], HEUTE)


def test_feed_nur_das_wesentliche():
    from modern.seite_heute import feed_eintraege

    f = feed_eintraege(_tag(), _karten(), HEUTE)
    assert [k.titel for k in f["jetzt"]] == ["3 Personen ohne Zimmer"] and len(f["weitere"]) == 2
    assert [x[0] for x in f["heute_an"]] == ["2026-10-25"] and [x[0] for x in f["morgen_an"]] == ["2026-10-26"]
    assert f["heute_ab"][0][1] == "Muster, Max" and f["reinigung"] == 2
    assert [w[1] for w in f["warnungen"]] == ["Liste unvollständig"]          # nur Warnungen, keine Infos


class _Ds:
    """Datenstand mit Modellwerten je Monat und Listen-Einträgen (Verträge) – zählt Aufrufe von kategorien()."""

    stichtag = date(2026, 10, 25)

    def __init__(self):
        self.aufrufe = 0
        monate = [(pd.Timestamp("2026-10-01") + pd.DateOffset(months=i)).date() for i in range(-3, 3)]
        self.prognose = N(werte={"BFW GS": [N(monat=m, art="ist" if m < date(2026, 10, 1) else "laufend" if m == date(2026, 10, 1)
                                              else "prognose", erwartet=50.0 + i, lo80=48.0 + i, hi80=52.0 + i, lo95=46.0 + i,
                                              hi95=54.0 + i, gesichert=40.0, ist=50.0 + i if m < date(2026, 10, 1) else None)
                                            for i, m in enumerate(monate)]},
                          modelle={})

    def kategorien(self, standort, von, bis, brutto=False):
        self.aufrufe += 1
        tage = pd.date_range(von, bis, freq="D")
        return pd.DataFrame({"Reha": 50.0, "Mieter": [3.0 if t.month in (11, 12) else 1.0 for t in tage], "UWT": 2.0}, index=tage)

    def kapazitaet(self, standort, brutto=False):
        return 80

    def monatsprognose(self, standort, monat, brutto=False):          # Rechenweg des Hauptprogramms (je Monat)
        w = next((x for x in self.prognose.werte[standort] if x.monat == monat), None)
        if w is None:
            return None
        ende = (pd.Timestamp(monat) + pd.offsets.MonthEnd(0)).date()
        df = self.kategorien(standort, monat, ende, brutto)
        v = float(df[["Mieter", "UWT"]].sum(axis=1).mean())
        return {"erwartet": w.erwartet + v, "vertraege": v, "hi80": w.hi80 + v, "gesichert": w.gesichert + v}


def test_schnelle_prognose_gleich_wie_monatsrechnung_und_zwischengespeichert():
    from modern import auswertung_kern as ak

    ds = _Ds()
    pg = ak.prognose(ds, "BFW GS", False, 3, 3)
    aufrufe = ds.aufrufe
    assert aufrufe == 1                                                       # eine Tagesrechnung statt einer je Monat
    for z in pg.zeilen:
        alt = ds.monatsprognose("BFW GS", z.monat)
        assert abs(alt["erwartet"] - z.erwartet) < 1e-9 and abs(alt["vertraege"] - z.vertraege) < 1e-9
        assert abs(alt["hi80"] - z.hi80) < 1e-9 and abs(alt["gesichert"] - z.gesichert) < 1e-9
    ds.aufrufe = 0
    assert ak.prognose(ds, "BFW GS", False, 3, 3) is pg and ds.aufrufe == 0   # Zwischenspeicher
    assert ak.prognose(_Ds(), "BFW GS", False, 3, 3) is not pg                # neuer Datenstand → frisch gerechnet


def test_graph_wechsel_im_browser_vorbereitet():
    from modern import seite_prognose as sp

    assert "mGraph" in sp.GRAPH_JS and "notMerge" in sp.GRAPH_JS and "mgraph" in sp.GRAPH_JS
    assert "mSofort" in sp.GRAPH_JS
