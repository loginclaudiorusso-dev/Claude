"""1.12 – Gantt lesbar, Diagrammtyp gilt für alle Diagramme (auch Säulen), Zurück nach einem Sprung."""

import inspect
from datetime import date

from modern import darstellung_kern as dk
from modern import diagramm_stil as ds


def _saeulen():
    return {"xAxis": {"type": "category", "data": list("abcd")}, "legend": {"top": 0}, "grid": {"bottom": 20},
            "series": [{"name": "Ist", "type": "bar", "stack": "w", "data": [3, 4, None, None],
                        "itemStyle": {"color": "#123456", "borderRadius": [3, 3, 0, 0]}, "barMaxWidth": 26},
                       {"name": "erwartet", "type": "bar", "stack": "w", "data": [None, None, 5, 6],
                        "itemStyle": {"color": "#123456", "opacity": .45}},
                       {"name": "_lo", "type": "bar", "data": [1, 1, 1, 1]},
                       {"name": "Anteil", "type": "bar", "stack": "100", "m_fest": True, "data": [50, 50, 50, 50]}]}


def test_automatisch_laesst_alles_wie_es_ist():
    o = _saeulen()
    assert ds.anwenden(o, {"dg_typ": "auto"}) is o


def test_linie_stellt_saeulen_um():
    o = ds.anwenden(_saeulen(), {"dg_typ": "linie"})
    ist, erw, lo, ant = o["series"]
    assert ist["type"] == "line" and "stack" not in ist and "barMaxWidth" not in ist
    assert erw["type"] == "line" and erw["lineStyle"]["type"] == "dashed"         # Prognose bleibt erkennbar
    assert ist["lineStyle"]["color"] == "#123456"
    assert lo["type"] == "bar" and ant["type"] == "bar"                          # Hilfsreihe, Anteile bleiben
    assert o["xAxis"]["boundaryGap"] is False


def test_flaeche_und_saeule():
    o = ds.anwenden(_saeulen(), {"dg_typ": "flaeche"})
    assert o["series"][0]["type"] == "line" and "areaStyle" in o["series"][0]
    li = {"series": [{"name": "Ist", "type": "line", "data": [1, 2]}], "xAxis": {"type": "category"}}
    assert ds.anwenden(li, {"dg_typ": "saeule"})["series"][0]["type"] == "bar"


def test_zweimal_anwenden_ist_gleich():
    d = {"dg_typ": "linie", "dg_legende": "unten"}
    einmal = ds.anwenden(_saeulen(), d)
    assert ds.anwenden(einmal, d)["grid"]["bottom"] == einmal["grid"]["bottom"] == 44


def test_alte_einstellung_linie_wird_automatisch():
    assert dk.bereinigen({"dg_typ": "linie"})["dg_typ"] == "auto"                 # bis 1.11 = Standard
    assert dk.bereinigen({"dg_typ": "linie", "dg_typ_v": 2})["dg_typ"] == "linie"  # ab 1.12 bewusst gewählt
    assert list(dk.DG_TYPEN)[0] == "auto" and dk.STANDARD["dg_typ"] == "auto"


def test_jedes_diagramm_bekommt_den_typ():
    from modern import diagramm_ui

    assert "_ds.anwenden(options" in inspect.getsource(diagramm_ui)


def test_gantt_beschriftung():
    from modern import seite_steuerung as st

    assert st.gantt_text(date(2027, 6, 10), date(2027, 6, 24), "2-101, 2-102, 2-103", "zimmer") == "10.06.–24.06. · 3 Zi."
    assert st.gantt_text(date(2027, 7, 5), date(2027, 8, 20), "", "etage") == "05.07.–20.08."
    assert st.gantt_kosten(0, 8000, 8000) == "Möbel 8 T€"                       # kein „Bau 0 T€“ mehr
    assert st.gantt_kosten(20000, 8000, 28000) == "Bau 20 T€ · Möbel 8 T€ = 28 T€"


def test_zurueck_nach_sprung():
    from modern import oberflaeche, seite_prognose

    q = inspect.getsource(oberflaeche)
    assert 'von = zustand.pop("von", None)' in q and "def _zurueck_knopf" in q and "self._zurueck_knopf()" in q
    assert inspect.getsource(seite_prognose).count('von=("Belegungs\\u00adprognose"') == 2
