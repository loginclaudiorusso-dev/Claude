"""0.48: Budget je Topf und Haushaltsjahr – verbraucht beim Auftrag (einstellbar), Ablauf über zwei Jahre, Budget je
Jahr, Freigabe in einer Stufe, Angebote gelten bis Jahresende. Erfundene Daten und Beträge."""

from datetime import date

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _vorhaben(vk):
    return vk.leer_vorhaben(titel="Flur streichen (Muster)", treiber="qualitaet", nachweis="Wände verschmutzt",
                            kosten=[{"id": "k1", "titel": "Maler", "betrag": 60000, "herkunft": "angebot", "jahr": 2031,
                                     "topf": "bau", "auftrag": {"betrag": 58000, "datum": "2031-11-20"},
                                     "rechnungen": [{"betrag": 20000, "datum": "2031-12-15", "bezahlt_am": "2031-12-28"},
                                                    {"betrag": 38000, "datum": "2032-01-20", "bezahlt_am": "2032-02-05"}]},
                                    {"id": "k2", "titel": "Böden", "betrag": 15000, "herkunft": "schaetzung", "jahr": 2031,
                                     "topf": "bau"}])


def test_auftrag_im_dezember_verbraucht_das_budget_des_auftragsjahres(leer):
    from modern import vorhaben_kern as vk

    v = _vorhaben(vk)
    e = vk.einstellungen()
    assert e["regel"]["bau"] == "auftrag" and e["entscheider"] == "Leitung"
    k31 = vk.konto([v], 2031, "bau", 100000, e)
    assert (k31.verbraucht, k31.offen, k31.gebunden, k31.abgerechnet, k31.bezahlt) == (58000, 15000, 58000, 20000, 20000)
    assert k31.frei == 100000 - 58000 - 15000
    k32 = vk.konto([v], 2032, "bau", 100000, e)
    assert (k32.verbraucht, k32.offen, k32.abgerechnet, k32.bezahlt) == (0, 0, 38000, 38000)   # Zahlung 2032 belastet 2032 nicht


@pytest.mark.parametrize("regel, v31, v32", [("rechnung", 20000, 38000), ("zahlung", 20000, 38000)])
def test_andere_regeln_verteilen_auf_die_jahre(leer, regel, v31, v32):
    from modern import vorhaben_kern as vk

    e = {**vk.einstellungen(), "regel": {"bau": regel, "moebel": "auftrag", "sonstiges": "auftrag"}}
    v = _vorhaben(vk)
    k31, k32 = vk.konto([v], 2031, "bau", None, e), vk.konto([v], 2032, "bau", None, e)
    assert (k31.verbraucht, k32.verbraucht) == (v31, v32)
    assert k31.offen == 2000 + 15000                     # Maler: 60.000 geplant − 58.000 abgerechnet; Böden ganz offen


def test_budget_je_jahr_und_einstellungen_mit_rueckgaengig(leer):
    from modern import kern
    from modern import vorhaben_kern as vk

    e = vk.einstellungen()
    e["budgets"] = {"2031": {"bau": 80000}}
    e["entscheider"] = "Leitung FM"
    vk.einstellungen_schritt(e)
    assert vk.budget(2031, "bau", 90000) == 80000 and vk.budget(2032, "bau", 90000) == 90000
    assert vk.budget(2031, "moebel") is None
    ok, _t = kern.rueckgaengig()
    assert ok and vk.budget(2031, "bau", 90000) == 90000


def test_freigabe_traegt_entscheider_und_datum_ein(leer):
    from modern import vorhaben_kern as vk

    v = {**_vorhaben(vk), "entscheidung": {"status": "freigegeben", "datum": "", "wer": ""}}
    vk.speichern_auto_schritt(v)
    g = vk.gespeichert()[0]["entscheidung"]
    assert g["wer"] == "Leitung" and g["datum"] == date.today().isoformat()
    assert vk.freigeben({**v, "entscheidung": {"status": "idee"}}, date(2031, 1, 1))["entscheidung"] == {"status": "idee"}


def test_abgelehnte_zaehlen_nicht_im_konto(leer):
    from modern import vorhaben_kern as vk

    v = {**_vorhaben(vk), "entscheidung": {"status": "abgelehnt", "datum": "", "wer": ""}}
    assert vk.konto([v], 2031, "bau").belastet == 0


def test_angebot_gilt_standardmaessig_bis_jahresende(leer):
    from modern import renovierung_kern as rk

    p = rk.angebot_uebernehmen(rk.parameter(), {"haus": "6", "art": "moebel", "netto": 4000, "zimmer": 4, "datum": "2031-03-01"})
    assert p["kosten"]["6"]["gueltig_moebel"] == "2031-12-31" and p["angebote"][-1]["gueltig_bis"] == "2031-12-31"


def test_beschluss_heisst_leitung():
    from modern import steuerung_kern as sk

    assert "Geschäftsführung" not in open(sk.__file__, encoding="utf-8").read()
