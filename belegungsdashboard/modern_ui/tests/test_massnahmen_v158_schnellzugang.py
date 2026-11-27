"""1.58: Maßnahme schnell finden – Suchfeld im Maßnahmen-Menü der Teilnehmer-Prognose, Schnellwahl über dem Diagramm,
Treffer in der Suche (Strg+K) und „Maßnahme ansehen“ im Menüband; „Diagrammtyp: Linie“ wirkt auch bei den Zugängen."""

from pathlib import Path
from types import SimpleNamespace

from modern import suche_palette as sp

MOD = Path(sp.__file__).parent


def test_suche_findet_massnahme(monkeypatch):
    a = SimpleNamespace(heute=None, _mn_namen=["GS KBM", "GS RVT", "GS KBM-T", "GS BFS"])
    t = sp.massnahmen_treffer(a, "kbm")
    assert [x[3] for x in t] == [("massnahme", "GS KBM"), ("massnahme", "GS KBM-T")]
    assert t[0][0] == "Neuanmeldungen GS KBM"
    assert sp.massnahmen_treffer(a, "k") == []                 # ein Buchstabe ist zu wenig
    assert len(sp.massnahmen_treffer(a, "gs")) == 3              # höchstens drei Treffer


def test_schnellzugang_je_monat_zwei_jahre():
    from modern import seite_massnahmen as sm

    assert sm.SCHNELL == {"mn_takt": "monat", "mn_darstellung": "ein", "mn_vor": 4}
    src = (MOD / "seite_massnahmen.py").read_text(encoding="utf-8")
    assert "Maßnahme ansehen – tippen, z. B. KBM" in src
    assert '"Maßnahme ansehen", "suche", A("mn_suche")' not in (MOD / "menueband.py").read_text(encoding="utf-8")  # 1.74: doppelt
    assert 'name == "mn_suche"' in (MOD / "menueband_ui.py").read_text(encoding="utf-8")


def test_teilnehmer_prognose_menue_mit_suche_und_linie():
    src = (MOD / "bestand_prognose_ui.py").read_text(encoding="utf-8")
    assert "Maßnahme suchen, z. B. KBM" in src and 'suche.on("keydown.enter", erster)' in src
    assert '"Diagrammtyp: Linie“ gilt auch hier' in src or "Diagrammtyp: Linie" in src
    assert 'if linie and r_["type"] == "bar"' in src or 'elif linie and r_["type"] == "bar"' in src
