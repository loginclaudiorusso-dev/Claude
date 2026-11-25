"""1.61: Befunde aus dem Menü-Audit – Standort-neutral (nicht nur Goslar), Gäste-Filter, Druck überall, Rollen."""

from datetime import date
from types import SimpleNamespace

import pytest

from modern import befehle_kern as bk
from modern import benutzer_kern as bn
from modern import hilfe_kern as hk
from modern import seite_inventar, seiten
from modern.gaeste_kern import GZeile


def test_zimmerbefehl_goslar_bleibt():
    assert bk.zimmer_befehl("2-408 Mangel") == ("2-408", "Mangel melden")
    assert bk.zimmer_befehl("2-408") is None


def test_zimmerbefehl_anderer_standort():
    ids = ["BP-A 103", "WE-A 202 R", "BP-B 12"]
    assert bk.zimmer_befehl("A 103 Mangel", ids) == ("A 103", "Mangel melden")
    assert bk.zimmer_befehl("a103 Mangel", ids) == ("A 103", "Mangel melden")
    assert bk.zimmer_befehl("a 202 r Mangel", ids) == ("A 202 R", "Mangel melden")
    assert bk.zimmer_befehl("A 103", ids) is None
    assert bk.zimmer_befehl("Mangel melden", ids) is None


def test_inventar_haeuser_aus_gebaeudeplan():
    z = [SimpleNamespace(haus="A", aktiv=True), SimpleNamespace(haus="B", aktiv=True), SimpleNamespace(haus="C", aktiv=False)]
    assert seite_inventar._hs(SimpleNamespace(stand=SimpleNamespace(zimmer=z))) == ["A", "B"]
    assert seite_inventar._hs(SimpleNamespace(stand=None)) == seite_inventar.HAEUSER


def test_gaeste_filter_und_suche():
    h = date(2026, 11, 25)
    gs = [GZeile("1", "Beispiel, Erika", date(2026, 11, 20), date(2026, 11, 30), "GS-2-101", bemerkung="Hospitation"),
          GZeile("2", "Musterhoff, Kim", date(2026, 12, 2), date(2026, 12, 4), ""),
          GZeile("3", "Probehaus, Alex", date(2026, 11, 1), date(2026, 11, 3), "")]
    assert [g.schluessel for g in seiten.gaeste_filtern(gs, h, "da")] == ["1"]
    assert [g.schluessel for g in seiten.gaeste_filtern(gs, h, "kommen")] == ["2"]
    assert [g.schluessel for g in seiten.gaeste_filtern(gs, h, "ohne")] == ["2"]
    assert [g.schluessel for g in seiten.gaeste_filtern(gs, h, "", "hospit")] == ["1"]
    assert "Musterhoff, Kim" in seiten.gaeste_druck_html(gs)


def test_notfallliste_ueberall_druckbar():
    for seite, ansicht in [("heute", None), ("prognose", None), ("zimmer", "karten"), ("anreisen", "zuteilen")]:
        assert "notfall" in [k for _t, k in hk.druckausgaben(seite, ansicht)]
    assert "inventar" in [k for _t, k in hk.druckausgaben("inventar", "haeuser")]
    assert "gaeste" in [k for _t, k in hk.druckausgaben("mieter", "gaeste")]


def test_admin_pruefen(monkeypatch):
    monkeypatch.setattr(bn, "eingerichtet", lambda: False)
    bn.admin_pruefen("Test")                            # ohne Konten: erlaubt wie bisher
    monkeypatch.setattr(bn, "eingerichtet", lambda: True)
    monkeypatch.setattr(bn, "aktuell", lambda: SimpleNamespace(admin=False))
    with pytest.raises(ValueError, match="nur ein Administrator"):
        bn.admin_pruefen("Stammdaten ändern")
    monkeypatch.setattr(bn, "aktuell", lambda: SimpleNamespace(admin=True))
    bn.admin_pruefen("Stammdaten ändern")
