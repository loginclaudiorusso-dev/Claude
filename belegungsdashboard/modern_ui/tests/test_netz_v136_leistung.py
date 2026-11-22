"""1.36 – schneller: Zimmer-Vergleich über die Kennung, „nach Planung“ nur einmal je Stand, Seitenwechsel ohne
Neuladen, solange sich nichts geändert hat."""

import inspect

from belegung import eintragen
from belegung import zimmerplan as zp
from modern import kern, leistung_kern  # noqa: F401 – kern installiert die Beschleunigung


def test_zimmer_vergleich_gleiches_ergebnis():
    a, b = zp.Zimmer("GS-1-101", "1", "EG", "101"), zp.Zimmer("GS-1-101", "1", "EG", "101")
    c = zp.Zimmer("GS-1-102", "1", "EG", "102")
    d = zp.Zimmer("GS-1-101", "1", "EG", "101", betten=2)
    assert a == b and a != c and a != d and a == a and (a == "x") is False
    assert zp.Zimmer._eq_original(a, b) and not zp.Zimmer._eq_original(a, d)


def test_vorschlagen_ausnahmen_ueber_kennungen():
    from modern import regeln_kern

    f = regeln_kern._MIETER.get("vorschlagen") or zp.vorschlagen
    assert "_alt_ids" in f.__code__.co_varnames + f.__code__.co_cellvars


def test_nach_planung_je_stand_nur_einmal(monkeypatch):
    zaehler = []
    orig = eintragen.nach_planung.__wrapped__
    monkeypatch.setattr(eintragen.nach_planung, "__wrapped__", orig)

    class Stand:
        pass
    s1, s2 = Stand(), Stand()
    import modern.leistung_kern as lk

    lk._STAND["ok"] = False
    monkeypatch.setattr(eintragen, "nach_planung", lambda st, h=None, w=12: zaehler.append((st, w)) or (st, w))
    lk.installieren()
    assert eintragen.nach_planung(s1, None, 5) == (s1, 5) and eintragen.nach_planung(s1, None, 5) == (s1, 5)
    assert eintragen.nach_planung(s1, None, 12) == (s1, 12)
    assert eintragen.nach_planung(s2, None, 5) == (s2, 5)
    assert len(zaehler) == 3


def test_seitenwechsel_laedt_nur_bei_aenderung():
    from modern import oberflaeche

    q = inspect.getsource(oberflaeche.Ansicht._laden)
    assert "voll" in q and "stempel ==" in q and "WIEDER_S" in q
    assert "voll=False" in inspect.getsource(oberflaeche.Ansicht.oeffnen)
