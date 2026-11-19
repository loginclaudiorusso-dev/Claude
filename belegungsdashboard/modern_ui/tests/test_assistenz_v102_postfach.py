"""1.02 – Postfach auf „Aufgaben“ mit Öffnen in Outlook, Standorte im Menüband in einer Reihe. Nur erfundene Daten."""

import inspect
from datetime import datetime

from modern import band_ui, outlook_kern as ok, seite_heute, ui_bausteine


def test_mail_merkt_sich_die_kennung_zum_oeffnen():
    m = ok.Mail(datetime(2026, 11, 12, 9, 30), "Anreise Montag", "Erika Muster", True, "ABC123", "STORE1")
    assert (m.eintrag, m.ablage) == ("ABC123", "STORE1")
    assert ok.Mail(datetime(2026, 11, 12), "x", "y", False).eintrag == ""      # alte Aufrufe bleiben gültig


def test_oeffnen_ohne_kennung_oder_ohne_outlook_gibt_verstaendlichen_text():
    assert "nicht öffnen" in ok.oeffnen("")
    text = ok.oeffnen("ABC123")                       # hier ohne Windows/Outlook
    assert text and "Outlook" in text


def test_ordner_oeffnen_ohne_einstellung():
    assert "Kein Outlook-Ordner" in ok.ordner_oeffnen("")


def test_vorschau_merkt_sich_anzahl_getrennt(monkeypatch):
    aufrufe = []
    monkeypatch.setattr(ok, "ordner", lambda: "Internatsdienst")
    monkeypatch.setattr(ok, "lesen", lambda pfad, anzahl=ok.ANZAHL: aufrufe.append(anzahl) or [])
    ok._ZWISCHEN.update(zeit=0.0, pfad=None)
    ok.vorschau(False, 6)
    ok.vorschau(False, 12)
    ok.vorschau(False, 12)
    assert aufrufe == [6, 12]


def test_postfach_steht_auf_der_aufgaben_seite():
    q = inspect.getsource(seite_heute._postfach)
    assert "outlook_kern.block(a, anzahl=12, postfach=True)" in q


def test_mehr_als_drei_optionen_in_einer_reihe():
    assert "reihe" in inspect.signature(band_ui.stapel).parameters
    assert "m-bg-reihe" in band_ui.CSS
    q = inspect.getsource(ui_bausteine.segmente)
    assert 'len(werte) == 4' in q and "raster" in q and "m-bg-raster" in band_ui.CSS


# ---- Diagramme: kräftigere Linien, klare Farben, große Legende -------------------------------------------------------
from modern import diagramm_stil as ds  # noqa: E402

HELL = {"akzent": "#007F7F", "text": "#1F2A2A", "text2": "#5E6E6E", "text3": "#8A8F98", "fls": "#FFFFFF",
        "bg": "#F7F8F8", "hell": True, "rot": "#d64545"}
DUNKEL = {"akzent": "#5ED6C6", "text": "#E6E8EC", "text2": "#A2A8B4", "text3": "#8A919D", "fls": "#15171C",
          "bg": "#0E0F12", "hell": False, "rot": "#F87171"}


def _vj_option():
    return {"xAxis": {"type": "category", "data": ["a", "b"]}, "yAxis": {"type": "value"}, "legend": {},
            "series": [{"name": "Vorvorjahr (Ist)", "type": "line", "data": [1, 2]},
                       {"name": "Vorjahr (Ist)", "type": "line", "data": [2, 3]},
                       {"name": "Aktuell (Ist)", "type": "line", "data": [3, 4]},
                       {"name": "Aktuell (Prognose)", "type": "line", "data": [4, 5], "lineStyle": {"type": "dashed"}}]}


def test_vergleichslinien_bunt_dick_und_unterscheidbar():
    for t in (HELL, DUNKEL):
        o = ds.einheitlich(_vj_option(), t)
        reihen = [se for se in o["series"] if se.get("name")]
        farben = {se["name"]: se["lineStyle"]["color"] for se in reihen}
        assert len(set(farben.values())) == 3                       # Vorvorjahr, Vorjahr, Aktuell (Ist = Prognose)
        for se in reihen:
            assert se["lineStyle"]["width"] >= 2.8
            assert ds.kontrast(se["lineStyle"]["color"], t["fls"]) >= 3
        assert farben["Vorjahr (Ist)"] not in (t["text2"], t["text3"])


def test_legende_gross():
    o = ds.einheitlich(_vj_option(), HELL)
    lg = o["legend"]
    assert lg["textStyle"]["fontSize"] >= 14 and lg["itemWidth"] >= 30 and lg["itemHeight"] >= 14
    klein = {"legend": {"textStyle": {"fontSize": 11}, "itemWidth": 18}, "series": []}
    ds.lesbar(klein, HELL)
    assert klein["legend"]["textStyle"]["fontSize"] == 14 and klein["legend"]["itemWidth"] == 30


def test_flaeche_nicht_fuer_vergleichslinien():
    o = ds.anwenden(_vj_option(), {"dg_typ": "flaeche"})
    hat = {se["name"]: "areaStyle" in se for se in o["series"] if se.get("name")}
    assert not hat["Vorjahr (Ist)"] and not hat["Vorvorjahr (Ist)"] and hat["Aktuell (Ist)"]
