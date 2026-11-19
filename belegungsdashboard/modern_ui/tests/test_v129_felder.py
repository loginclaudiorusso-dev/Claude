"""1.29 – Geschlecht einer Belegung an EINER Stelle lesen (Feld „grund“ des Hauptprogramms). Erfundene Namen."""

from datetime import date
from types import SimpleNamespace as NS

from belegung import zimmerplan as zp

from modern.belegung_felder import geschlecht


def test_eigene_planung_fuehrt_geschlecht_in_grund():
    b = zp.Belegung("GS-2-101", date(2026, 11, 1), date(2026, 11, 30), "geplant", "Muster, Erika", "", "w", "p1")
    assert b.grund == "w" and geschlecht(b) == "w"


def test_sperrgrund_ist_kein_geschlecht():
    b = NS(person="", grund="Mieter", name="")
    assert geschlecht(b) == zp.geschlecht_raten("")
    b2 = NS(person="p2", grund="Renovierung", name="Beispiel, Max")
    assert geschlecht(b2) == zp.geschlecht_raten("Beispiel, Max")


def test_eigenes_feld_hat_vorrang():
    assert geschlecht(NS(geschlecht="m", person="p3", grund="w", name="")) == "m"


def test_renovierung_nutzt_die_eine_stelle():
    import inspect

    from modern import renovierung_kern as rk
    assert "belegung_felder" in inspect.getsource(rk._geschlecht) and ".grund" not in inspect.getsource(rk._geschlecht)
