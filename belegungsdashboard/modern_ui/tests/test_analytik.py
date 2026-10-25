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
