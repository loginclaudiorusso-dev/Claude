"""0.36: Anreiselisten als PDF („Teilnehmer Beginn“) für Bad Pyrmont/Weser-Ems, Showcase-Dock. Erfundene Daten."""

from datetime import date

import pytest

TEXT = """Teilnehmer Beginn
Beginn vom 02.11.2030 bis 30.11.2030
                                                                     Stand 31.10.2030
Integration
02.11.2030
BP KBM 3011                            vom 02.11.2030 bis 01.11.2032
   02.11.30   Probe, Paula                              01.01.90   DRV Bund                       P  K
                                                                   Braunschweig-Hannover: H
   02.11.30   Muster, Max Moritz                        02.02.91   AA Musterstadt                 P
   05.11.30*  von Test, Tina                            03.03.92   DRV                                K
                                                                       Maßnahme BP KBM 3011: 3 TN
09.11.2030
BP EMR ASS 301109                      vom 09.11.2030 bis 11.11.2030
   09.11.30   Beispiel, Bert                            04.04.93   DRV Bund                           K
                                                                       Maßnahme BP EMR ASS 301109: 1 TN
                                                                                       Gesamt: 4
"""


def test_pdf_liste_lesen():
    from modern import pdf_anreise_kern as pk

    assert pk.ist_liste(TEXT)
    listen = pk.lesen_text(TEXT, "liste.pdf")
    assert [(l.datum, l.gruppe, len(l.personen)) for l in listen] == [
        (date(2030, 11, 2), "BP KBM 3011", 2), (date(2030, 11, 5), "BP KBM 3011", 1), (date(2030, 11, 9), "BP EMR ASS 301109", 1)]
    p = {x.name: x for l in listen for x in l.personen}
    assert p["Probe, Paula"].internat and not p["Muster, Max Moritz"].internat
    assert p["Probe, Paula"].abreise == date(2032, 11, 1) and p["Probe, Paula"].anreise == date(2030, 11, 2)
    assert p["von Test, Tina"].bemerkung == "verspäteter Einstieg" and p["von Test, Tina"].internat
    assert p["Beispiel, Bert"].gruppe == "EMR"
    assert all(x.liste == l.schluessel for l in listen for x in l.personen)
    assert not any("1990" in str(x.zu_dict()) or "01.01.90" in str(x.zu_dict()) for l in listen for x in l.personen)  # kein Geburtsdatum


@pytest.fixture
def standorte(tmp_path, monkeypatch):
    from modern import standort_kern as sk

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    sk.installieren()
    yield tmp_path
    sk.waehlen("GS", merken_=False)


def test_pdf_import_nur_ausserhalb_von_goslar(standorte, monkeypatch):
    from modern import daten_kern as dk
    from modern import pdf_anreise_kern as pk
    from modern import standort_kern as sk

    monkeypatch.setattr(pk, "text_lesen", lambda pfad: TEXT)
    pdf = standorte / "liste.pdf"
    pdf.write_bytes(b"%PDF")
    v = dk.anreisen_lesen([pdf], ["liste.pdf"])
    assert not v.listen and "Excel" in v.fehler[0]                 # Goslar bleibt bei den Excel-Listen (TN-ID)
    sk.waehlen("BP", merken_=False)
    v = dk.anreisen_lesen([pdf], ["liste.pdf"])
    assert not v.fehler and sum(len(l.personen) for l in v.listen) == 4
    dk.anreisen_uebernehmen(v)
    from belegung import zimmerplan as zp

    assert {b.name for b in zp.laden().bedarf} == {"Probe, Paula", "von Test, Tina", "Beispiel, Bert"}   # nur mit K
