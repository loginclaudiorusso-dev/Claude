"""0.49: Archiv früherer Anreisen über jeden Zeitraum – mit Zimmer aus Planung, Gebäudeplan oder Historie, Drucken und
Excel. Erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def test_archiv_findet_alte_anreisen_mit_zimmer(leer):
    from belegung import anreiseliste, gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import anreisen_kern as ank

    alt = date(2024, 3, 4)                                 # deutlich älter als 12 Monate
    P = anreiseliste.Person
    anreiseliste.speichern([P("Muster, Anna", "GS RVL", alt, True, tn_id="901", abreise=alt + timedelta(days=60)),
                            P("Beispiel, Ben", "GS EMR", alt, True, tn_id="902", abreise=alt + timedelta(days=20)),
                            P("Neu, Nora", "GS RVL", date(2031, 1, 6), True, tn_id="903")], {})
    st = zp.laden()
    anna = next(b for b in st.bedarf if b.name == "Muster, Anna")
    z1 = next(z for z in st.zimmer if z.aktiv and not z.gaeste)
    zp.zuweisung_setzen(st, anna.schluessel, z1.id)
    st = zp.laden()
    z2 = next(z for z in st.zimmer if z.aktiv and not z.gaeste and z.id != z1.id)
    st.lage.belegungen.setdefault(z2.id, []).append(gebaeudeplan.Belegung(z2.id, alt - timedelta(days=1), alt + timedelta(days=20),
                                                                         "belegt", "Beispiel, Ben", "GS EMR"))
    zs = ank.archiv(st, date(2024, 1, 1), date(2024, 12, 31))
    assert [z.name for z in zs] == ["Beispiel, Ben", "Muster, Anna"]          # Nora (2031) liegt außerhalb
    nach = {z.name: z for z in zs}
    assert nach["Muster, Anna"].quelle == "Planung" and nach["Muster, Anna"].zimmer
    assert nach["Beispiel, Ben"].quelle == "Gebäudeplan" and nach["Beispiel, Ben"].anreise == alt   # Anreise laut Liste
    assert [z.name for z in ank.archiv(st, date(2024, 1, 1), date(2024, 12, 31), "emr")] == ["Beispiel, Ben"]
    html = ank.archiv_html(zs, date(2024, 1, 1), date(2024, 12, 31))
    assert "Muster, Anna" in html and "Anreise Mo 04.03.2024 (2)" in html
    assert ank.archiv_excel(zs, leer / "a.xlsx") == 2 and (leer / "a.xlsx").exists()


def test_menue_hat_archiv():
    from modern import seite_anreisen

    assert "Archiv: frühere Anreisen" in open(seite_anreisen.__file__, encoding="utf-8").read()
