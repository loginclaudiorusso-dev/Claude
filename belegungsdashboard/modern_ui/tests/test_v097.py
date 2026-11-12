"""0.97 – Suche zeigt nach Umzug das Zimmer heute, Diagrammschrift mit hohem Kontrast, deutlich verschiedene
Linienfarben, Backtest auch in „Einfach“. Nur erfundene Namen."""

from dataclasses import dataclass
from datetime import date

from belegung.suche import Treffer

from modern import diagramm_stil as ds
from modern import suche_kern as sk

HEUTE = date(2026, 5, 10)
DUNKEL = {"akzent": "#5ED6C6", "text": "#E6E8EC", "text2": "#A2A8B4", "text3": "#8A919D", "fls": "#15171C",
          "bg": "#0E0F12", "hell": False, "rot": "#F87171"}
HELL = {"akzent": "#007F7F", "text": "#1F2A2A", "text2": "#5E6E6E", "text3": "#8A8F98", "fls": "#FFFFFF",
        "bg": "#F7F8F8", "hell": True, "rot": "#d64545"}


@dataclass
class U:
    schluessel: str
    name: str
    von_zimmer: str
    nach_zimmer: str
    ab: date
    status: str = "aktiv"


# ---- Suche nach Umzug ----------------------------------------------------------------------------------------------
def test_nach_umzug_zeigt_die_suche_das_neue_zimmer():
    t = Treffer("Erika Muster", "Kurs", "Reha", date(2026, 4, 1), date(2026, 9, 30), "GS-A101", person="p1")
    erg = sk.korrigieren([t], [U("p1", "Erika Muster", "GS-A101", "GS-B205", date(2026, 5, 3))], HEUTE)
    assert len(erg) == 1
    neu, hinweis = erg[0]
    assert neu.zimmer_id == "GS-B205" and "umgezogen am 03.05.2026 aus A101" in hinweis


def test_umzug_in_der_zukunft_altes_zimmer_mit_hinweis():
    t = Treffer("Erika Muster", "Kurs", "Reha", date(2026, 4, 1), date(2026, 9, 30), "GS-A101", person="p1")
    neu, hinweis = sk.korrigieren([t], [U("p1", "Erika Muster", "GS-A101", "GS-B205", date(2026, 6, 1))], HEUTE)[0]
    assert neu.zimmer_id == "GS-A101" and "zieht am 01.06.2026 nach B205" in hinweis


def test_beide_teile_der_belegung_werden_ein_treffer():
    alt = Treffer("Max Beispiel", "", "", date(2026, 4, 1), date(2026, 5, 3), "GS-A101", "Gebäudeplan")
    neu = Treffer("Max Beispiel", "", "", date(2026, 5, 3), date(2026, 9, 30), "GS-B205", "Gebäudeplan")
    erg = sk.korrigieren([alt, neu], [U("gp:x", "Max Beispiel", "GS-A101", "GS-B205", date(2026, 5, 3))], HEUTE)
    assert len(erg) == 1 and erg[0][0].zimmer_id == "GS-B205"
    assert erg[0][0].von == date(2026, 4, 1) and erg[0][0].bis == date(2026, 9, 30)


def test_hinfaelliger_umzug_und_andere_person_aendern_nichts():
    t = Treffer("Erika Muster", "", "", date(2026, 4, 1), date(2026, 9, 30), "GS-A101", person="p1")
    umz = [U("p1", "Erika Muster", "GS-A101", "GS-B205", date(2026, 5, 3), "hinfaellig"),
           U("p2", "Anna Andere", "GS-A101", "GS-C300", date(2026, 5, 3))]
    assert sk.korrigieren([t], umz, HEUTE)[0] == (t, "")


def test_zimmer_heute_fuer_listen():
    class Lage:
        umzuege = {"u1": U("p1", "Erika Muster", "GS-A101", "GS-B205", date(2026, 5, 3))}
    assert sk.zimmer_heute(Lage(), "p1", "Erika Muster", "GS-A101", None, None, HEUTE) == "GS-B205"
    assert sk.zimmer_heute(Lage(), "p1", "Erika Muster", "", None, None, HEUTE) == ""


# ---- Kontrast ---------------------------------------------------------------------------------------------------------
def test_beschriftung_ohne_farbe_wird_textfarbe():
    o = {"series": [{"type": "line", "data": [1], "label": {"show": True, "position": "top"}}]}
    ds.lesbar(o, DUNKEL)
    assert o["series"][0]["label"]["color"] == DUNKEL["text"]
    assert o["series"][0]["label"]["textBorderWidth"] == 0


def test_blasse_schrift_im_dunkeln_wird_hell():
    o = {"xAxis": {"axisLabel": {"color": "#555555"}},
         "series": [{"type": "line", "endLabel": {"show": True, "color": "#3a3f47"}}]}
    ds.lesbar(o, DUNKEL)
    assert ds.kontrast(o["xAxis"]["axisLabel"]["color"], DUNKEL["fls"]) >= 4.5
    assert ds.kontrast(o["series"][0]["endLabel"]["color"], DUNKEL["fls"]) >= 4.5


def test_blasse_linie_wird_sichtbar_baender_bleiben():
    o = {"series": [{"type": "line", "color": "#2a2f36", "lineStyle": {"color": "#2a2f36"}},
                    {"type": "line", "stack": "b80", "areaStyle": {"color": "rgba(94,214,198,.48)"},
                     "lineStyle": {"color": "rgba(94,214,198,.9)"}}]}
    ds.lesbar(o, DUNKEL)
    assert ds.kontrast(o["series"][0]["lineStyle"]["color"], DUNKEL["fls"]) >= 3
    assert o["series"][1]["areaStyle"]["color"] == "rgba(94,214,198,.48)"


def test_weisser_punkt_mit_rand_und_beschriftung_mit_hintergrund_bleiben():
    o = {"series": [{"type": "line", "markPoint": {"data": [{"itemStyle": {"color": "#fff", "borderColor": "#111",
                                                                            "borderWidth": 2}}]},
                     "label": {"show": True, "color": "#fff", "backgroundColor": "rgba(24,28,34,.82)"}}]}
    ds.lesbar(o, HELL)
    assert o["series"][0]["markPoint"]["data"][0]["itemStyle"]["color"] == "#fff"
    assert o["series"][0]["label"]["color"] == "#fff"


def test_hell_wird_abgedunkelt():
    assert ds.kontrast(ds.angleichen("#cccccc", "#ffffff", 4.5), "#ffffff") >= 4.5


def test_kategorien_deutlich_und_kontrastreich():
    for t in (HELL, DUNKEL):
        k = ds.kategorien(t)
        assert len(set(k)) == len(k) >= 8
        assert all(ds.kontrast(f, t["fls"]) >= 3 for f in k), t["hell"]


def test_backtest_in_einfach():
    from modern import seite_prognose as sp

    assert ds.kontrast(sp.BACKTEST_FARBE[False], DUNKEL["fls"]) >= 3
    assert ds.kontrast(sp.BACKTEST_FARBE[True], HELL["fls"]) >= 3


def test_lesbar_ist_stabil_zweiter_lauf_aendert_nichts():
    """Wichtig für NiceGUI: Die Optionen melden jede Änderung als Aktualisierung – ein zweiter Lauf darf nichts mehr
    schreiben, sonst entsteht eine Endlosschleife."""
    import copy

    o = {"xAxis": {"axisLabel": {"color": "#444444"}}, "textStyle": {},
         "series": [{"type": "line", "color": "#333333", "lineStyle": {"color": "#333333"},
                     "label": {"show": True, "rich": {"a": {}}}, "endLabel": {"show": True}}]}
    ds.lesbar(o, DUNKEL)
    vorher = copy.deepcopy(o)

    class Wache(dict):
        geschrieben = 0

        def __setitem__(self, k, v):
            Wache.geschrieben += 1
            super().__setitem__(k, v)

    def einpacken(x):
        if isinstance(x, dict):
            return Wache({k: einpacken(v) for k, v in x.items()})
        if isinstance(x, list):
            return [einpacken(v) for v in x]
        return x
    w = einpacken(o)
    ds.lesbar(w, DUNKEL)
    assert Wache.geschrieben == 0 and w == vorher
