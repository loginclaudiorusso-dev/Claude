"""0.27: Gruppen beim Anlegen und in den Personenangaben (ohne Feld „Maßnahme“) – erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield date.today()
    aenderungen.verlauf_leeren()


@pytest.mark.parametrize("gruppe, haus, etage", [("Reha", "3.1", "1"), ("RVT", "3.2", None), ("Mieter", "6", None)])
def test_anlegen_nur_mit_gruppe(leer, gruppe, haus, etage):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import zimmer_kern as zk

    st = zp.laden()
    z = next(z for z in st.zimmer if z.aktiv and z.haus == haus and (etage is None or z.etage == etage) and z.betten == 1)
    zk.person_ins_zimmer(z.id, "Beispiel, Berta", "", gruppe, leer + timedelta(days=1), leer + timedelta(days=40), "w",
                         bemerkung="Maßnahme FIAE")
    p = next(x for x in anreiseliste.laden()[0] if x.name == "Beispiel, Berta")
    assert p.massnahme == zk.GRUPPEN_NEU[gruppe] and p.bemerkung == "Maßnahme FIAE"
    st = zp.laden()
    b = next(x for x in st.bedarf if x.schluessel == p.schluessel)
    assert b.gruppe == gruppe and (st.zugewiesen(p.schluessel) or {}).get("zimmer") == z.id
    zeile = next(x for x in kern.zeilen(st, b.von.isoformat(), leer) if x.schluessel == p.schluessel)
    assert zeile.gruppe == kern.GRUPPE_KURZ[gruppe]
    with pytest.raises(ValueError, match="Gruppe"):
        zk.person_ins_zimmer(z.id, "Probe, Paul", "", "", leer, leer + timedelta(days=3))


def test_gruppenauswahl_personenangaben():
    from modern import anreisen_kern as ank

    assert set(ank.GRUPPEN) == {"EMR", "ASS", "RVT", "Reha", "UWT", "Gast", "Mieter"}
    assert ank.GRUPPEN["RVT"] == "Vorbereitende Maßnahme" and ank.GRUPPEN["Reha"] == "Hauptmaßnahme"
    assert ank.gruppe_auswahl("RVL") == "RVT" and ank.gruppe_auswahl("Gast") == "Gast" and ank.gruppe_auswahl("?") is None
