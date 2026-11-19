"""1.22 – Vorjahresvergleich je Tag: Prognose beginnt am Stichtag (beim Ist-Wert), Tooltip mit Tageswerten,
95-%-Band wie im Trend. Erfundene Zahlen."""

from datetime import date, timedelta

import pandas as pd

from modern import analytik_kern as an
from modern import auswertung_kern as ak

STICH = date(2026, 11, 13)


class _Ds:
    stichtag = STICH
    erster_tag = date(2023, 1, 1)

    def verlauf(self, standort, von, bis, brutto):
        idx = pd.date_range(von, bis, freq="D")
        return pd.DataFrame({"wert": [100.0 + t.day for t in idx], "ist": [t.date() <= STICH for t in idx]}, index=idx)


def _pg():
    z = []
    for k in range(-12, 13):
        m = (pd.Timestamp(2026, 11, 1) + pd.DateOffset(months=k)).date()
        art = "ist" if k < 0 else ("laufend" if k == 0 else "prognose")
        z.append(ak.PZeile(m, art, 120.0, 115.0, 125.0, 110.0, 130.0, None, 118.0 if art == "ist" else None))
    return ak.Prognose(z, 200, "M", "Test", 1.0, 2.0, .8, [], [])


def test_tageswerte_mit_vorjahr_am_gleichen_wochentag():
    monate = an.vorjahr(_pg()).monate
    vt = an.vorjahr_tage(_Ds(), "X", False, monate)
    assert vt.tage[0] == monate[0] and vt.tage[-1].month == monate[-1].month
    i = vt.tage.index(STICH)
    assert vt.ist[i] == 100 + STICH.day and vt.ist[i + 1] is None             # nach dem Stichtag kein Ist
    vd = STICH - timedelta(days=364)
    assert vt.vorjahr[i] == 100 + vd.day and vd.weekday() == STICH.weekday()


def test_prognose_startet_am_stichtag_mit_spanne_null():
    pg = _pg()
    vt = an.vorjahr_tage(_Ds(), "X", False, an.vorjahr(pg).monate)
    pt = an.prognose_tage(vt, ak.szenario(pg, 200, 0))
    i = vt.tage.index(STICH)
    assert pt["erwartet"][i - 1] is None
    assert pt["erwartet"][i] == vt.ist[i] and pt["lo95"][i] == pt["hi95"][i] == vt.ist[i]
    j = vt.tage.index(date(2027, 1, 15))                                          # Monatsmitte = Monatswert
    assert pt["erwartet"][j] == 120.0 and pt["lo80"][j] == 115.0 and pt["hi95"][j] == 130.0


def test_diagramm_mit_95_band_und_tagestooltip():
    from modern import seite_prognose as sp

    pg = _pg()
    vt = an.vorjahr_tage(_Ds(), "X", False, an.vorjahr(pg).monate)
    c = {"pg": pg, "pg_lang": pg, "kap": 200, "offset": 0, "b95": True, "vj_tage": vt, "karte": False}
    t = sp._t()
    o = sp._vorjahr(sp._basis(t, False), t, c, "Test", "Netto", "")
    namen = [s_["name"] for s_ in o["series"]]
    assert "95-%-Spanne" in namen and "80-%-Spanne" in namen
    assert len(o["xAxis"]["data"]) == len(vt.tage) and o["xAxis"]["data"][vt.tage.index(STICH)] == an.tag_text(STICH)
    assert "Belegt (Ist)" in o["tooltip"][":formatter"] and "Vorjahr (" in o["tooltip"][":formatter"]
    ist = next(s_ for s_ in o["series"] if s_["name"] == "Aktuell (Ist)")
    assert "markLine" in ist and "Stichtag" in ist["markLine"]["label"]["formatter"]
    c95 = {**c, "b95": False}
    assert "95-%-Spanne" not in [s_["name"] for s_ in sp._vorjahr(sp._basis(t, False), t, c95, "T", "N", "")["series"]]
