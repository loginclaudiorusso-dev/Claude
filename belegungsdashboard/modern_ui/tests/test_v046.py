"""0.46: Steuerung nach Fragen gegliedert, Tabellenvorlage, Festpreis solange ein Angebot gilt, nie nur zum Ausschöpfen,
Gästezimmer nicht in der Auslastung, Leiste anheften / Dock anpassen. Erfundene Daten und Beträge."""

from datetime import date
from types import SimpleNamespace

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def test_steuerung_fuenf_bereiche_und_alte_namen():
    from modern import seite_steuerung as ss

    assert list(ss.ANSICHTEN.values()) == ["Cockpit", "Vorhaben", "Zeitplan & Kapazität", "Finanzen", "Grundlagen"]
    for alt, neu in (("uebersicht", "cockpit"), ("renovierung", "vorhaben"), ("prognose", "zeitplan"),
                     ("szenarien", "finanzen"), ("kennzahlen", "grundlagen"), ("quatsch", "cockpit")):
        assert ss.ansicht(SimpleNamespace(ansicht_von=lambda s, d, v=alt: v)) == neu
    assert [ss.horizont(j, 2031) for j in (2031, 2032, 2033, 2035)] == ["belastbar", "wahrscheinlich", "Orientierung",
                                                                          "Orientierung"]


def test_festpreis_solange_das_angebot_gilt(leer):
    from modern import renovierung_kern as rk

    p = {**rk.parameter(), "preisstand": 2030, "preis_pct": 10, "puffer_bau_pct": 0, "neben_pct": 0, "vorsteuer_pct": 100}
    p = rk.angebot_uebernehmen(p, {"haus": "6", "art": "bau", "netto": 10000, "datum": "2030-02-01", "gueltig_bis": "2031-06-30"})
    assert p["kosten"]["6"]["gueltig_bau"] == "2031-06-30" and p["angebote"][-1]["gueltig_bis"] == "2031-06-30"
    assert round(rk.kosten(p, "6", 9, 2031).bau) == 10000                       # gilt noch → kein Aufschlag
    assert round(rk.kosten(p, "6", 9, 2032).bau) == 11000                       # ab dem Jahr nach Ablauf +10 %
    assert any("Festpreis" in t for t, _b in rk.kosten(p, "6", 9, 2031).herleitung)
    ohne = rk.angebot_uebernehmen(p, {"haus": "6", "art": "bau", "netto": 10000, "datum": "2030-02-01"})
    assert "gueltig_bau" not in ohne["kosten"]["6"] and round(rk.kosten(ohne, "6", 9, 2031).bau) == 11000


def test_gueltig_bis_wird_im_angebot_erkannt():
    from modern import renovierung_kern as rk

    erg = rk.angebot_auswerten("Objekt: Musterbau, Gebäude 2, Etage 1\nNettosumme   EUR 12.345,67\n"
                               "Dieses Angebot ist gültig bis 31.03.2031.")
    assert erg["gueltig_bis"] == "2031-03-31" and erg["netto"] == 12345.67
    assert "gueltig_bis" not in rk.angebot_auswerten("Nettosumme EUR 1.000,00")


def test_gaestezimmer_zaehlen_nicht_zur_auslastung():
    from modern import zimmer_kern as zk

    def r(status, gaeste=False):
        return SimpleNamespace(status=status, zimmer=SimpleNamespace(gaeste=gaeste))
    zs = [r("belegt"), r("frei"), r("gesperrt"), r("belegt", True), r("belegt", True), r("frei", True)]
    assert zk.auslastung_basis(zs) == (1, 2)
    t = zk.kennzahl_text(zs)
    assert "Auslastung 50 %" in t and "ohne 3 Gästezimmer" in t and t.startswith("6 Zimmer")


def test_design_dock_und_anheften_bleiben_gespeichert():
    from modern import themes

    d = themes.bereinigen({"layout": "showcase", "theme": "inn", "dock": ["heute", "steuerung"], "dock_fest": False})
    assert d["dock"] == ["heute", "steuerung"] and d["dock_fest"] is False
    assert "dock-auto" in themes.klassen(d) and "dock-auto" not in themes.klassen({**d, "dock_fest": True})
    assert themes.bereinigen({})["dock"] is None and themes.bereinigen({})["dock_fest"] is True
    assert "m-nav:hover" in themes.CSS and "subgrid" in __import__("modern.stil", fromlist=["CSS"]).CSS


def test_optimierer_nimmt_bei_gleichem_bedarf_die_guenstigere(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    z = next(x for x in st.zimmer if x.haus == "6" and x.aktiv and not x.gaeste)
    maengel.setzen(z.id, "renovierung", True, date(2029, 1, 1))
    st = zp.laden()
    p = {**rk.parameter(), "preisstand": 2031, "preis_pct": 0, "vorsteuer_pct": 100, "budget_bau": 500000, "modus": "budget"}
    fl = rk.flure(st, date(2030, 1, 1), p)
    wahl, rest = rk.optimieren(fl, p, 2031, 500000, None)
    assert wahl and rest > 100000                         # Rest bleibt frei – nichts nur zum Ausschöpfen
    assert {f.schluessel for f, _z, _a in wahl} <= {f.schluessel for f in fl if f.wert > 0}
