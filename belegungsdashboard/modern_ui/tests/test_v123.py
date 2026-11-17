"""1.23 – Suche nach Zimmerwechsel: nur das neue Zimmer (altes als Hinweis). Erfundene Namen."""

from datetime import date

from belegung.suche import Treffer

from modern import suche_kern as sk

H = date(2026, 11, 17)


def _t(name, zimmer, von, bis, person=""):
    return Treffer(name, "GS RVT", "RVT", von, bis, zimmer, "Gebäudeplan", "", person)


def test_umzug_nur_im_gebaeudeplan_zeigt_nur_neues_zimmer():
    alt = _t("Muster, Max", "GS-2-101", date(2026, 9, 1), date(2026, 11, 10))
    neu = _t("Max Muster", "GS-2-205", date(2026, 11, 10), date(2027, 2, 28))
    erg = sk.nur_aktuell([(alt, ""), (neu, "")], H)
    assert [t.zimmer_id for t, _h in erg] == ["GS-2-205"]
    assert erg[0][1] == "vorher in 2-101 bis 10.11.2026"


def test_ehemalige_und_andere_bleiben():
    weg = _t("Probe, Paula", "GS-3-110", date(2026, 1, 5), date(2026, 6, 30))          # nur früher da
    andere = _t("Muster, Max", "GS-2-205", date(2026, 11, 10), date(2027, 2, 28))
    zwei = _t("Test, Tom", "GS-2-300", date(2027, 3, 1), None)                         # künftige Buchung …
    jetzt = _t("Test, Tom", "GS-2-301", date(2026, 10, 1), date(2027, 2, 28))          # … und aktuelle: beide bleiben
    erg = sk.nur_aktuell([(weg, ""), (andere, ""), (zwei, ""), (jetzt, "")], H)
    assert [t.zimmer_id for t, _h in erg] == ["GS-3-110", "GS-2-205", "GS-2-300", "GS-2-301"]


def test_eintrag_mit_umzug_hinweis_bleibt():
    alt = _t("Muster, Max", "GS-2-101", date(2026, 9, 1), date(2026, 11, 10))
    neu = _t("Muster, Max", "GS-2-205", date(2026, 11, 10), date(2027, 2, 28))
    erg = sk.nur_aktuell([(alt, ""), (neu, "umgezogen am 10.11.2026 aus 2-101")], H)
    assert erg == [(neu, "umgezogen am 10.11.2026 aus 2-101")]


def test_historie_nicht_fuer_aktuelle_bewohner():
    neu = _t("Muster, Max", "GS-2-205", date(2026, 11, 10), date(2027, 2, 28))
    da = sk.aktuelle_namen([(neu, "")], H)
    assert sk.ist_aktuell("Max Muster", da) and not sk.ist_aktuell("Probe, Paula", da)


def test_palette_nutzt_filter():
    import inspect

    from modern import canvas_kern, suche_palette

    q = inspect.getsource(suche_palette.treffer)
    assert "nur_aktuell" in q and "ist_aktuell" in q
    assert "nur_aktuell" in inspect.getsource(canvas_kern)
