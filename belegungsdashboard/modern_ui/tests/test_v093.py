"""0.93 – Belegung: Mieter aus Mietverträgen, Zeitraum-Knöpfe vom heutigen Tag aus („Heute“), eigene Einfach-Ansicht;
Maßnahmen: Diagramme je Maßnahme auch in „Einfach“. Erfundene Zahlen."""

from datetime import date
from pathlib import Path

MOD = Path(__file__).resolve().parent.parent / "modern"


def test_mieter_aus_vertraegen_ohne_doppelzaehlung():
    import pandas as pd

    from modern import auswertung_kern as ak

    tage = pd.date_range("2026-10-01", "2026-10-10", freq="D")
    kat = pd.DataFrame({"Reha": [100.0] * 10, "UWT": [5.0] * 10, "Mieter": [1.0] * 10}, index=tage)
    zr = [(date(2026, 10, 1), date(2026, 10, 10)), (date(2026, 10, 1), date(2026, 10, 10)), (date(2026, 10, 6), date(2026, 12, 31))]
    k, mehr = ak._mieter_dazu(kat, "BFW GS", zr)
    assert list(k["Mieter"]) == [2.0] * 5 + [3.0] * 5          # max(Liste 1, Verträge 2 bzw. 3)
    assert list(mehr) == [1.0] * 5 + [2.0] * 5 and list(k["Reha"]) == [100.0] * 10
    k2, mehr2 = ak._mieter_dazu(kat, "BFW BP", zr)               # Mieter nur in Goslar
    assert not mehr2.any() and list(k2["Mieter"]) == [1.0] * 10


def test_belegung_satz():
    from modern import blick_kern as bk

    s = bk.belegung_zeitraum(date(2026, 10, 1), date(2026, 10, 31), {"Reha": [180.0] * 31, "Mieter": [20.0] * 31}, 250)
    assert s.titel == "Vom 01.10. bis 31.10.2026 waren im Schnitt 200 von 250 Plätzen belegt (80 %)."
    assert [g[0] for g in s.gruppen] == ["Reha", "Mieter"] and round(s.gruppen[1][2], 2) == .1
    h = bk.belegung_zeitraum(date(2026, 11, 11), date(2026, 11, 11), {"Reha": [191.0]}, 250)
    assert h.titel == "Am 11.11.2026 waren 191 von 250 Plätzen belegt (76 %)."


def test_knoepfe_vom_heutigen_tag():
    t = (MOD / "seite_auswertung.py").read_text(encoding="utf-8")
    assert '("Heute", h, h)' in t and "h = a.heute" in t and '"Letzter Monat", ende_vormonat.replace(day=1)' in t
    assert "def _belegung_einfach" in t and "_mieter_zr(a)" in t
    m = (MOD / "seite_massnahmen.py").read_text(encoding="utf-8")
    assert "Diagramme je Maßnahme zeigen" in m
