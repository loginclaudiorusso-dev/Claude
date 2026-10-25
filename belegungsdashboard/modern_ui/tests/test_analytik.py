"""0.11: Executive-Analytics – KPIs, Erkenntnisse, Szenario, Vorjahr, Summary, Diagramm-Optionen (erfundene Zahlen)."""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class _Lage:
    belegt: float


class _Ds:
    """Minimaler Datenstand: Stichtag, Belegung heute und vor 52 Wochen."""

    stichtag = date(2026, 10, 25)
    erster_tag = date(2024, 1, 1)

    def aufschluesselung(self, standort, tag, brutto):
        return _Lage(120.0)

    def verlauf(self, standort, von, bis, brutto):
        return pd.DataFrame({"wert": [110.0]})


def _pg(kap: int = 150, rueckblick=None):
    from modern import auswertung_kern as ak

    zeilen = [ak.PZeile(date(2025, m, 1), "ist", 100.0 + m, 0, 0, 0, 0, None, 100.0 + m) for m in range(1, 13)]
    zeilen += [ak.PZeile(date(2026, m, 1), "ist", 105.0 + m, 0, 0, 0, 0, None, 105.0 + m) for m in range(1, 10)]
    zeilen.append(ak.PZeile(date(2026, 10, 1), "laufend", 116.0, 114.0, 118.0, 112.0, 120.0, 110.0, 115.0))
    zeilen += [ak.PZeile(date(2026 + (m > 12), (m - 1) % 12 + 1, 1), "prognose", 110.0 + m, 105.0 + m, 115.0 + m,
                         100.0 + m, 120.0 + m, 90.0, None) for m in range(11, 23)]
    return ak.Prognose(zeilen, kap, "M", "Testmodell", 2.0, 4.0, .8, [("M", 2.0)], rueckblick or [])


def test_executive_kpis_mit_bezug_und_vergleich():
    from modern import analytik_kern as an

    ex = an.executive(_Ds(), "BFW GS", False, _pg())
    k = {x.schluessel: x for x in ex.kpis}
    assert list(k) == ["aktuell", "ziel", "reserve", "risiko", "guete"]
    assert k["aktuell"].wert == "120" and "Stichtag 25.10.2026" in k["aktuell"].bezug
    assert k["aktuell"].vergleich.startswith("+10 ggü. 26.10.2025") and k["aktuell"].richtung == 1
    assert ex.zielmonat == date(2026, 11, 1) and k["ziel"].wert == "121"          # nächster voller Monat, nicht der laufende
    assert "Ist Nov 2025" in k["ziel"].vergleich                                     # gleicher Kalendermonat ein Jahr früher
    assert k["reserve"].wert == "29" and k["guete"].wert == "± 2,0"
    arten = {a for a, _t in ex.erkenntnisse}
    assert arten <= {"Fakt", "Prognose", "Einschätzung", "Hinweis"} and "Fakt" in arten and "Prognose" in arten


def test_executive_szenario_kennzeichnung_und_risiko():
    from modern import analytik_kern as an

    pg = _pg()
    ex = an.executive(_Ds(), "BFW GS", False, pg, kap=120, offset=5)
    assert ex.erkenntnisse[0][0] == "Hinweis" and "Szenario aktiv" in ex.erkenntnisse[0][1]
    risiko = next(k for k in ex.kpis if k.schluessel == "risiko")
    assert int(risiko.wert) > 0 and risiko.stufe == "krit"
    assert pg.kapazitaet == 150 and pg.zeilen[-1].erwartet == 132.0                 # Simulation ändert keine Daten


def test_backtest_auffaelligkeit_nur_bei_deutlicher_abweichung():
    from modern import analytik_kern as an

    klein = an.executive(_Ds(), "BFW GS", False, _pg(rueckblick=[(date(2026, 9, 1), 114.0, 115.0)]))
    gross = an.executive(_Ds(), "BFW GS", False, _pg(rueckblick=[(date(2026, 9, 1), 114.0, 130.0)]))
    assert not any("Auffällige" in t for _a, t in klein.erkenntnisse)
    assert any("Auffällige" in t for _a, t in gross.erkenntnisse)


def test_szenario_vergleich_ausgang_gegen_szenario():
    from modern import analytik_kern as an

    pg = _pg()
    gleich = an.szenario_vergleich(pg, 150, 0)
    assert all(z.ausgang == z.szenario and not z.schlechter for z in gleich)
    eng = {z.titel: z for z in an.szenario_vergleich(pg, 110, 10)}
    assert eng["Kapazität"].schlechter and eng["Auslastungsannahme"].szenario == "+10 %"
    assert eng["Monate mit Kapazitätsrisiko"].schlechter


def test_vorjahr_ordnet_kalendermonate_zu_und_zeigt_luecken():
    from modern import analytik_kern as an

    vj = an.vorjahr(_pg())
    assert vj.monate[0] == date(2026, 4, 1) and vj.monate[-1] == date(2027, 3, 1) and len(vj.monate) == 12
    i = vj.monate.index(date(2026, 11, 1))
    assert vj.vorjahr[i] == 111.0 and not vj.aktuell_ist[i] and vj.aktuell[i] == 121.0
    assert vj.aktuell_ist[0] and vj.vorjahr[0] == 104.0
    assert vj.vorvorjahr[i] is None                                                  # kein Wert 2024 → Lücke, nichts erfunden


def test_summary_html_enthaelt_kpis_erkenntnisse_und_szenariohinweis():
    from modern import analytik_kern as an

    pg = _pg()
    ex = an.executive(_Ds(), "BFW GS", False, pg, kap=130)
    html = an.summary_html(ex, pg, "BFW GS", False, 130, 0.0)
    assert "Goslar" in html and "Aktuelle Belegung" in html and "Szenario" in html and "<table" in html


def test_diagramm_optionen_drei_modi_und_feste_achse():
    from modern import seite_prognose as sp

    pg = _pg()
    basis = {"pg": pg, "kap": 150, "offset": 0.0, "standort": "BFW GS", "brutto": False, "b95": True, "backtest": False,
             "animation": False, "pg_lang": None, "stichtag": date(2026, 10, 25)}
    achsen = []
    for schritt in (1, 2, 3, 4):
        o = sp.option({**basis, "art": "trend", "schritt": schritt})
        achsen.append((o["yAxis"]["min"], o["yAxis"]["max"]))
        namen = {s["name"]: s for s in o["series"]}
        hat = lambda n: any(v is not None for v in namen[n]["data"])  # noqa: E731
        assert hat("Ist") and hat("Prognose (erwartet)") == (schritt >= 2) and hat("80 %-Band") == (schritt >= 3)
        assert hat("Kapazität") == (schritt >= 4)
    assert len(set(achsen)) == 1                                                     # Aufbau ohne Achsensprung
    r = sp.option({**basis, "art": "reserve", "schritt": 4, "kap": 115})
    werte = [d["value"] for d in r["series"][0]["data"]]
    assert min(werte) < 0 and r["yAxis"]["scale"] is False                           # negative Reserve unter der Nulllinie
    j = sp.option({**basis, "art": "jahr", "schritt": 4})
    assert [s["name"] for s in j["series"]] == ["Vorvorjahr (Ist)", "Vorjahr (Ist)", "Aktuell (Ist)", "Aktuell (Prognose)"]
    sz = sp.option({**basis, "art": "trend", "schritt": 4, "kap": 120})
    assert "SZENARIO" in sz["title"]["text"]


class _DsStatus(_Ds):
    """Wie _Ds, dazu Tageswerte je Kategorie: UWT 10 Plätze (nur gerade Monate), Mieter 4 Plätze."""

    def kategorien(self, standort, von, bis, brutto=False):
        tage = pd.date_range(von, bis, freq="D")
        return pd.DataFrame({"Reha": 50.0, "UWT": [10.0 if t.month % 2 == 0 else 0.0 for t in tage], "Mieter": 4.0}, index=tage)

    def aufschluesselung(self, standort, tag, brutto):
        from belegung.datenstand import Aufschluesselung

        return Aufschluesselung({"Reha": 50.0, "UWT": 10.0, "Mieter": 4.0}, 64.0, 80)


def test_status_monate_uwt_mieter_rest_ergeben_gesamt():
    from modern import analytik_kern as an

    pg = _pg()
    sm = an.status_monate(_DsStatus(), "BFW GS", False, pg)
    assert len(sm) == len(pg.zeilen)
    for m, z in zip(sm, pg.zeilen):
        assert abs(m.uwt + m.mieter + m.uebrige - (z.ist if z.art == "ist" else z.erwartet)) < 1e-6
    nov = next(m for m in sm if m.monat == date(2026, 11, 1))
    assert nov.uwt == 0 and nov.mieter == 4 and nov.art == "prognose"           # UWT nur in geraden Monaten gebucht
    sl = an.status_lage(_DsStatus(), "BFW GS", False, sm)
    assert sl.heute == {"UWT": 10.0, "Mieter": 4.0, "uebrige": 50.0, "frei": 16.0} and sl.fest_max == 14
    assert any("UWTler 10 und Mieter 4" in s for s in sl.saetze)


def test_kontingente_vorschlag_pruefung_und_saetze():
    from modern import analytik_kern as an

    sm = an.status_monate(_DsStatus(), "BFW GS", False, _pg())
    vorschlag = an.kontingent_vorschlag(sm, 150)
    assert vorschlag == {"UWT": 7.0, "Mieter": 3.0}                               # höchster gebuchter Anteil, aufgerundet
    zeilen = an.kontingent_pruefung(sm, 150, {"UWT": 5, "Mieter": 10})
    assert len(zeilen) == 12 and zeilen[0].k_uwt == 7.5 and zeilen[0].k_uebrige == 127.5
    assert any(z.stufe["UWT"] == "ueber" for z in zeilen) and all(z.stufe["Mieter"] == "ok" for z in zeilen)
    assert an.kontingent_saetze(zeilen, {"UWT": 5, "Mieter": 10})[0].startswith("UWT: Kontingent in")
    assert "innerhalb" in an.kontingent_saetze(an.kontingent_pruefung(sm, 150, vorschlag), vorschlag)[0]


def test_kontingent_speichern_nur_in_eigener_datei(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from modern import kern

    assert kern.kontingent_lesen("BFW GS") is None
    kern.kontingent_setzen("BFW GS", {"UWT": 20, "Mieter": 10})
    assert kern.kontingent_lesen("BFW GS") == {"UWT": 20.0, "Mieter": 10.0}
    assert [p.name for p in tmp_path.iterdir()] == ["modern_ui.json"]
    kern.kontingent_setzen("BFW GS", None)
    assert kern.kontingent_lesen("BFW GS") is None


def test_sanierung_nur_mit_grundlage():
    from types import SimpleNamespace as N

    from modern import analytik_kern as an

    lage = N(zimmer={"a": N(betten=2, aktiv=True), "b": N(betten=1, aktiv=False), "c": N(betten=1, aktiv=True)},
             unbewohnbar={"a": "Schimmel", "b": "Lager"})
    assert an.sanierung_plaetze(lage, "BFW GS") == 2 and an.sanierung_plaetze(lage, "Gesamt") == 2
    assert an.sanierung_plaetze(lage, "BFW BP") is None and an.sanierung_plaetze(None, "BFW GS") is None


def test_backtest_gesamt_ist_summe_der_standorte():
    from types import SimpleNamespace as N

    from modern import auswertung_kern as ak

    m = lambda r: N(rueckblick=r)  # noqa: E731
    ds = N(prognose=N(modelle={"BFW BP": m([(date(2026, 8, 1), 10, 11), (date(2026, 9, 1), 12, 12)]),
                               "BFW GS": m([(date(2026, 9, 1), 20, 19)]),
                               "BFW WE": m([(date(2026, 9, 1), 30, 33), (date(2026, 7, 1), 1, 1)])}))
    assert ak._rueckblick_summe(ds) == [(date(2026, 9, 1), 62.0, 64.0)]          # nur gemeinsame Monate


def test_szenario_als_schatten_und_status_stapel():
    from modern import analytik_kern as an
    from modern import seite_prognose as sp

    pg = _pg()
    basis = {"pg": pg, "kap": 140, "offset": 10.0, "standort": "BFW GS", "brutto": False, "b95": True, "backtest": False,
             "animation": False, "pg_lang": None, "stichtag": date(2026, 10, 25), "art": "trend", "schritt": 4}
    o = sp.option(basis)
    namen = {s["name"]: s for s in o["series"]}
    echt = [v for v in namen["Prognose (erwartet)"]["data"] if v is not None]
    geist = [v for v in namen["Szenario (Simulation)"]["data"] if v is not None]
    assert echt[-1] == 132.0 and geist[-1] == round(132.0 * 1.1, 1)              # echte Prognose bleibt, Szenario daneben
    assert namen["Kapazität"]["data"][0] == 150 and namen["Kapazität Szenario"]["data"][0] == 140
    sm = an.status_monate(_DsStatus(), "BFW GS", False, pg)
    st = sp.option({**basis, "offset": 0.0, "kap": 150, "status": True, "sm": sm, "kontingent": {"UWT": 10, "Mieter": 5}})
    gestapelt = [s for s in st["series"] if s.get("stack") == "status"]
    assert [s["name"] for s in gestapelt] == ["UWTler", "Mieter", "Teilnehmende & Sonstige"]
    assert {s["name"] for s in st["series"]} >= {"Kontingent UWT", "Kontingent UWT + Mieter", "Kapazität"}
