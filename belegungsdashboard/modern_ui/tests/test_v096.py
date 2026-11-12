"""0.96 – deutliche Bänder, Schrift ohne Kontur, Bildschirmfoto, Diagrammentwurf im Menüband, Anteils-Diagramme.
Nur erfundene Namen und Zahlen."""

import struct
import zlib
from datetime import datetime

from modern import anteile_kern as ank
from modern import bildschirmfoto_kern as bf
from modern import darstellung_kern as dk
from modern import diagramm_stil as ds
from modern import menueband as mb

HELL = {"akzent": "#007F7F", "text": "#111111", "text2": "#555555", "text3": "#999999", "rand": "#dddddd", "hell": True}
DUNKEL = {**HELL, "hell": False}


# ---- Bänder und Schrift ---------------------------------------------------------------------------------------------
def test_band_80_kraeftiger_als_95_und_im_dunkeln_kraeftiger():
    a80, a95 = ds.band_flaeche(HELL, "band"), ds.band_flaeche(HELL, "band95")
    alpha = lambda s: float(s.rsplit(",", 1)[1].rstrip(")"))  # noqa: E731
    assert alpha(a80) >= 2 * alpha(a95)
    assert alpha(ds.band_flaeche(DUNKEL, "band")) > alpha(a80)
    assert alpha(a80) >= .3                                   # vorher .16 – kaum zu sehen


def test_band_hat_kante_80_durchgezogen_95_gestrichelt():
    assert ds.band_kante(HELL, "band")["type"] == "solid"
    assert ds.band_kante(HELL, "band95")["type"] != "solid"
    se = ds.band_reihe({"name": "x", "type": "line", "stack": "b80", "areaStyle": {}}, HELL, "band")
    assert se["lineStyle"]["opacity"] == 1 and "rgba(0,127,127" in se["areaStyle"]["color"]


def test_einheitlich_ueberschreibt_baender_nicht_mehr_mit_blass():
    opt = {"xAxis": {"type": "category", "data": ["a", "b"]}, "yAxis": {"type": "value"},
           "series": [{"name": "_u", "type": "line", "stack": "b80", "data": [1, 2]},
                      {"name": "80 %-Band", "type": "line", "stack": "b80", "data": [3, 3], "areaStyle": {"opacity": .1}}]}
    o = ds.einheitlich(opt, HELL)
    assert o["series"][1]["areaStyle"]["color"] == ds.band_flaeche(HELL, "band")


def test_ohne_textrand_alle_beschriftungen():
    o = {"series": [{"label": {"show": True, "rich": {"a": {"color": "#fff"}}},
                     "endLabel": {"show": True},
                     "markLine": {"data": [{"label": {"formatter": "x"}}]},
                     "emphasis": {"label": {"show": True}}}],
         "xAxis": {"nameTextStyle": {}}}
    ds.ohne_textrand(o)
    se = o["series"][0]
    for lab in (se["label"], se["endLabel"], se["markLine"]["data"][0]["label"], se["emphasis"]["label"],
                se["label"]["rich"]["a"], o["xAxis"]["nameTextStyle"], o["textStyle"]):
        assert lab["textBorderWidth"] == 0
    assert "textBorderWidth" not in se["label"]["rich"]          # rich bleibt eine Liste von Stilen


def test_ohne_textrand_laesst_eigene_werte_und_js():
    o = {"series": [{"label": {"textBorderWidth": 2, ":formatter": "(p) => p"}}]}
    ds.ohne_textrand(o)
    assert o["series"][0]["label"]["textBorderWidth"] == 2
    assert o["series"][0]["label"][":formatter"] == "(p) => p"


# ---- Bildschirmfoto ---------------------------------------------------------------------------------------------------
def _png_pixel(daten: bytes):
    assert daten[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, kopf = 8, b"", None
    while pos < len(daten):
        n = struct.unpack(">I", daten[pos:pos + 4])[0]
        art, inhalt = daten[pos + 4:pos + 8], daten[pos + 8:pos + 8 + n]
        crc = struct.unpack(">I", daten[pos + 8 + n:pos + 12 + n])[0]
        assert crc == zlib.crc32(art + inhalt) & 0xFFFFFFFF
        if art == b"IHDR":
            kopf = struct.unpack(">IIBBBBB", inhalt)
        elif art == b"IDAT":
            idat += inhalt
        pos += 12 + n
    return kopf, zlib.decompress(idat)


def test_png_rgb_aus_bgra():
    bgra = bytes([0, 0, 255, 255, 0, 255, 0, 255, 255, 0, 0, 255, 10, 20, 30, 255])     # rot, grün / blau, (30,20,10)
    kopf, roh = _png_pixel(bf.png(2, 2, bgra))
    assert kopf[:2] == (2, 2) and kopf[2:4] == (8, 2)
    assert roh == b"\x00" + bytes([255, 0, 0, 0, 255, 0]) + b"\x00" + bytes([0, 0, 255, 30, 20, 10])


def test_png_falsche_groesse():
    import pytest

    with pytest.raises(ValueError):
        bf.png(3, 3, b"\x00" * 8)


def test_dib_kopf_oben_nach_unten():
    d = bf.dib(4, 3, b"\x01" * 48)
    groesse, b, h, _ebenen, bits = struct.unpack("<IiiHH", d[:16])
    assert (groesse, b, h, bits) == (40, 4, -3, 32) and len(d) == 40 + 48


def test_dateiname_ohne_sonderzeichen():
    n = bf.dateiname(datetime(2026, 3, 4, 5, 6, 7), "auswertung/prognose: Test")
    assert n == "INNternat_2026-03-04_05-06-07_auswertungprognose_Test.png"


def test_aufnehmen_ausserhalb_windows_meldet_freundlich(monkeypatch):
    monkeypatch.setattr(bf, "verfuegbar", lambda: False)
    erg = bf.aufnehmen()
    assert erg["ok"] is False and "Windows" in erg["fehler"]


# ---- Menüband: Diagrammentwurf ----------------------------------------------------------------------------------------
def _entwurf():
    r = mb.reiter({}, True, {"G": "Gesamt", "A": "Ort A"})
    return next(x for x in r if x.key == "diagramm")


def test_diagrammentwurf_wie_excel():
    d = _entwurf()
    assert d.titel == "Diagrammentwurf" and d.kontext
    titel = [g.titel for g in d.gruppen]
    assert titel == ["Daten", "Diagramm", "Darstellung", "Typ", "Elemente"]
    anteile = next(p for p in d.gruppen[3].punkte if p.text == "Anteile")
    assert [q.ziel[1] for q in anteile.menue] == [f"dg_anteil:{k}" for k in dk.DG_ANTEILE]
    elemente = [q.ziel[1] for q in d.gruppen[4].punkte[0].menue]
    assert "awt:aw_95" in elemente and "awt:aw_backtest" in elemente


def test_daten_und_prognose_nur_auf_der_prognose():
    d = _entwurf()
    nur = {g.titel: g for g in d.gruppen}
    assert mb.gruppe_sichtbar(nur["Daten"], "auswertung", "prognose")
    assert not mb.gruppe_sichtbar(nur["Daten"], "auswertung", "belegung")
    assert mb.gruppe_sichtbar(nur["Typ"], "auswertung", "belegung")
    standort = next(p for p in nur["Daten"].punkte if p.text == "Standort")
    assert [q.ziel for q in standort.menue] == [mb.A("aw:aw_standort=G"), mb.A("aw:aw_standort=A")]


def test_aw_wert_typen():
    assert mb.aw_wert("aw_horizont=24") == ("aw_horizont", 24)
    assert mb.aw_wert("aw_brutto=true") == ("aw_brutto", True)
    assert mb.aw_wert("aw_chart=reserve") == ("aw_chart", "reserve")


def test_bildschirmfoto_in_statusleiste():
    assert [p.ziel for p in mb.STATUSLEISTE[:2]] == [mb.A("foto"), mb.A("foto:ausschnitt")]


def test_anteil_einstellung_bereinigt():
    assert dk.bereinigen({"dg_anteil": "quatsch"})["dg_anteil"] == "ring"
    assert dk.bereinigen({"dg_anteil": "saeule100"})["dg_anteil"] == "saeule100"


# ---- Anteile ------------------------------------------------------------------------------------------------------------
def _anteile(**kw):
    reihen = {"Alpha": [50, 40, 30, 20], "Beta": [10, 20, 30, 40], "Gamma": [5, 5, 5, 5], "Delta": [1, 1, 1, 1],
              "Epsilon": [0, 0, 0, 0]}
    return ank.berechnen(reihen, ["W24", "S24", "W25", "S25"], [False, False, True, True], **kw)


def test_anteile_sortiert_leere_raus_kleine_zu_uebrige():
    a = _anteile(oben=2)
    assert a.namen == ["Alpha", "Beta", ank.UEBRIGE]
    assert a.zusammengefasst == ["Gamma", "Delta"]
    assert a.summe["Alpha"] == 90 and a.summe[ank.UEBRIGE] == 12        # Fenster = Ist-Perioden


def test_ein_einzelnes_uebrige_wird_nicht_gebildet():
    a = _anteile(oben=3)
    assert ank.UEBRIGE not in a.namen and "Delta" in a.namen


def test_prozent_je_periode_summiert_100():
    a = _anteile()
    for i in range(4):
        assert abs(sum(a.prozent(k)[i] for k in a.namen) - 100) < .5


def test_aussage_groesster_anteil_und_verschiebung():
    a = _anteile()
    assert a.satz.startswith("Den größten Anteil hat Alpha mit")
    assert "Beta" in a.satz and "gewachsen" in a.satz


def test_option_ring_kreis_und_100():
    a = _anteile()
    farben = {"Alpha": "#111111", "Beta": "#222222"}
    ring = ank.option(a, "ring", HELL, farben)
    assert ring["series"][0]["type"] == "pie" and ring["series"][0]["radius"][0] == "48%" and ring["graphic"]
    kreis = ank.option(a, "kreis", HELL, farben)
    assert kreis["series"][0]["radius"][0] == 0 and "graphic" not in kreis
    s100 = ank.option(a, "saeule100", HELL, farben)
    assert s100["yAxis"]["max"] == 100 and all(se["stack"] == "100" for se in s100["series"])
    assert s100["xAxis"]["data"][-1].endswith("(P)") and s100["series"][0]["data"][-1]["itemStyle"]["borderType"] == "dashed"
    assert "borderType" not in s100["series"][0]["data"][0]["itemStyle"]
    f100 = ank.option(a, "flaeche100", HELL, farben)
    assert f100["series"][0]["areaStyle"]


def test_monate_buendeln_tage():
    tage = ["30.01.", "31.01.", "01.02.", "02.02."]
    achse, w, prog = ank.monate_buendeln(tage, {"X": [1, 2, 3, 4]}, [True, True, True, False])
    assert achse == ["Jan", "Feb"] and w["X"] == [3, 7] and prog == [False, True]


def test_anteile_ohne_werte():
    a = ank.berechnen({"A": [0, 0]}, ["x", "y"])
    assert a.namen == [] and "Keine Werte" in a.satz
