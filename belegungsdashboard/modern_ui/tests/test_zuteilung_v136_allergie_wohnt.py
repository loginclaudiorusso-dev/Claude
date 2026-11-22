"""1.36 – Allergiker-Meldung: wer laut Gebäudeplan schon im Zimmer auf der Etage wohnt, wird nicht gemeldet; „Passt
so“ blendet einen Fall für alle aus (mit Rückgängig). Erfundene Namen und Zimmer."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from belegung.gebaeudeplan import Belegung
from belegung.zimmerplan import Zimmer
from modern import hinweise_kern as hk

HEUTE = date(2026, 11, 23)


def _stand(belegungen, zugewiesen=None):
    z_etage = Zimmer("GS-2-104", hk.ALLERGIE_HAUS, hk.ALLERGIE_ETAGE, "104")
    z_anders = Zimmer("GS-3-201", "3", "2. OG", "201")
    b = SimpleNamespace(schluessel="p1", name="Muster, Mia Lea", von=HEUTE - timedelta(days=33),
                        bis=HEUTE + timedelta(days=200), bemerkung="Allergie (Hausstaub)")
    return SimpleNamespace(bedarf=[b], lage=SimpleNamespace(zimmer={z.id: z for z in (z_etage, z_anders)},
                                                           belegungen=belegungen),
                           zugewiesen=lambda s: zugewiesen)


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path


def test_wohnt_laut_gebaeudeplan_auf_der_etage(ordner):
    bel = {"GS-2-104": [Belegung("GS-2-104", HEUTE - timedelta(days=33), HEUTE + timedelta(days=200), "belegt",
                                 "Muster, Mia Lea")]}
    f = hk.allergie_faelle(_stand(bel), HEUTE)
    assert len(f) == 1 and f[0].zimmer == "GS-2-104" and f[0].auf_etage and not f[0].bestaetigt


def test_ohne_zimmer_bleibt_gemeldet_und_passt_so_blendet_aus(ordner):
    st = _stand({})
    assert not hk.allergie_faelle(st, HEUTE)[0].auf_etage
    hk.bestaetigen("p1", "Muster, Mia Lea")
    f = hk.allergie_faelle(st, HEUTE)[0]
    assert f.auf_etage and f.bestaetigt                       # gilt als erledigt, sichtbar als „bestätigt“
    hk.bestaetigen("p1", "Muster, Mia Lea", an=False)
    assert not hk.allergie_faelle(st, HEUTE)[0].auf_etage


def test_anderer_name_zaehlt_nicht(ordner):
    bel = {"GS-2-104": [Belegung("GS-2-104", HEUTE, HEUTE + timedelta(days=9), "belegt", "Muster, Max")]}
    assert hk.wohnt_in(_stand(bel), _stand(bel).bedarf[0], HEUTE) == ""


def test_geplante_zuweisung_auf_der_etage_gilt_weiter(ordner):
    st = _stand({}, {"zimmer": "GS-2-104"})
    assert hk.allergie_faelle(st, HEUTE)[0].auf_etage
