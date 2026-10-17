"""6.18: Zimmerzustand (Renovierung, Boden, Mängel) einmalig übernehmen – nach dem festen Standard. Erfundene Befunde."""

from datetime import date

import pytest

TEXT = """# Test
2-101\treno\t2026-08\t\tReno
2-102\treno\t2024-07\t\t
2-103\treno\t2019-02\t\t
2-101\tboden\tPVC\t\t
2-102\tboden\tPVC\t\t
2-103\tboden\tTeppich\t\t
2-101\tmangel\twand\t2026-03-17\tTeilstreichen
2-101\tmangel\trenovierung\t\tReno2
2-102\tmangel\tmatratze\t\t
9-999\treno\t2026-01\t\t
2-104\tmangel\tgibtsnicht\t\t
2-104\treno\tirgendwann\t\t
"""


@pytest.fixture
def stand(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung import zimmerplan as zp

    st = zp.laden()
    z = {x.id: x for x in st.zimmer}
    z["GS-2-102"].renoviert, z["GS-2-102"].boden, z["GS-2-102"].boden_vermutet = "2024-06-03", "Vinyl", True   # genauer
    z["GS-2-103"].renoviert, z["GS-2-103"].boden = "2021-05-10", "Vinyl"                                      # sicher, neuer
    zp.stammdaten_speichern(st.zimmer, st.plan)
    return zp.laden()


def test_lesen_meldet_unbekanntes(stand):
    from belegung import zimmerzustand as zz

    befunde, fehler = zz.lesen(TEXT, {z.id for z in stand.zimmer})
    assert len(befunde) == 9 and len(fehler) == 3


def test_anwenden_nach_standard(stand):
    from belegung import maengel, zimmerliste as zl, zimmerplan as zp, zimmerzustand as zz

    befunde, _ = zz.lesen(TEXT, {z.id for z in stand.zimmer})
    erg = zz.anwenden(stand, befunde, heute=date(2026, 10, 17))
    z = {x.id: x for x in zp.laden().zimmer}
    assert z["GS-2-101"].renoviert == "2026-08" and zl.reno_text(z["GS-2-101"]) == "08/2026"
    assert zl.reno_datum(z["GS-2-101"]) == date(2026, 8, 1)
    assert z["GS-2-102"].renoviert == "2024-06-03"              # gleiche Renovierung, genaues Datum bleibt
    assert z["GS-2-103"].renoviert == "2021-05-10"              # älterer Befund ändert nichts
    assert (z["GS-2-102"].boden, z["GS-2-102"].boden_vermutet) == ("PVC", False)   # vermutet → ersetzt
    assert z["GS-2-103"].boden == "Vinyl" and erg.boden_abweichend == ["2-103: Vinyl (Quelle: Teppich)"]
    offen = {(m.zimmer, m.art): m for m in maengel.offen()}
    assert offen[("GS-2-101", "wand")].seit == date(2026, 3, 17)
    assert offen[("GS-2-102", "matratze")].seit == date(2026, 10, 17)
    assert maengel.NAMEN["renovierung"] == "Renovierung nötig"
    assert (erg.reno, erg.boden, erg.maengel) == (1, 2, 3)


def test_auto_import_einmal_und_ohne_doppelte_maengel(stand, tmp_path):
    from belegung import maengel, zimmerplan as zp, zimmerzustand as zz

    maengel.setzen("GS-2-102", "matratze", True, date(2026, 9, 1))      # schon offen: nicht doppelt
    (tmp_path / zz.IMPORT_DATEI).write_text(TEXT, encoding="utf-8")
    erg = zz.auto_import(stand)
    assert erg.maengel == 2 and len(erg.fehler) == 3
    assert zz.auto_import(zp.laden()) is None
    assert len([m for m in maengel.offen() if m.zimmer == "GS-2-102"]) == 1
