"""1.21.1 – Austausch: Zimmerplanung kommt an. Eintrag hier unverändert seit dem letzten Austausch → die Datei gilt
(auch beim „ganzen Stand“); UWT-Blöcke, Klassen/DZ-Liste und „Doppelzimmer einzeln“ werden mit übertragen."""

import inspect
from datetime import datetime

from modern import austausch_kern as ak
from test_teilnehmer_v105_monat_austausch import START, Ablage, _export, _gleich, _import

Z = "zimmer_zuweisungen.json"


def _zimmer(ab, person, zimmer):
    z = ab.lesen(Z, {})
    for r in z["zuweisungen"]:
        if r["person"] == person:
            r["zimmer"] = zimmer
    ab.schreiben(Z, z)


def _ganzer_stand(ab):
    st = ak.stand(ab.lesen)
    return ak.datei_bauen(ak.aenderungen(st, None), "neu", "Test", datetime(2026, 11, 17, 9, 0))


def test_ganzer_stand_ueberschreibt_unveraenderte_planung():
    a, b = Ablage(START), Ablage()
    _import(b, _export(a, "neu"))                         # erster Austausch – beide haben jetzt eine Basis
    _zimmer(a, "id:900001", "GS-2-105")                   # A plant um und schickt den ganzen Stand
    punkte = _import(b, _ganzer_stand(a))
    p = next(p for p in punkte if p.aenderung.bereich == "zuweisungen")
    assert p.status == "uebernehmen"                      # vorher: Konflikt, eigener Stand blieb
    assert _gleich(a, b)


def test_beide_geaendert_bleibt_konflikt():
    a, b = Ablage(START), Ablage()
    _import(b, _export(a, "neu"))
    _zimmer(a, "id:900001", "GS-2-105")
    _zimmer(b, "id:900001", "GS-2-107")                   # auch hier umgeplant → nicht still überschreiben
    p = next(p for p in _import(b, _ganzer_stand(a)) if p.aenderung.bereich == "zuweisungen")
    assert p.status == "konflikt"
    assert b.lesen(Z, {})["zuweisungen"][0]["zimmer"] == "GS-2-107"


def test_uwt_und_dz_liste_reisen_mit():
    start = {**START,
             "importe/uwt.json": {"bloecke": [{"klasse": "K9", "anreise": "2026-12-07", "abreise": "2027-06-30", "anzahl": 2,
                                               "datei": "x.pdf", "importiert_am": "2026-11-01T10:00:00",
                                               "personen": [{"tn_id": "901", "name": "Erfunden, Eins", "zimmer": ""}]}]},
             "importe/uwt_klassen.json": {"klassen": {"K9": [{"tn_id": "901", "name": "Erfunden, Eins", "dz": "K9:1"}]},
                                          "datei": "k.xlsx", "importiert_am": "2026-11-01T10:00:00"},
             "importe/modern_dz_einzeln.json": {"2026-12-07": True}}
    a, b = Ablage(start), Ablage()
    _import(b, _export(a, "neu"))
    assert _gleich(a, b)
    assert b.lesen("importe/uwt_klassen.json", {})["klassen"]["K9"][0]["dz"] == "K9:1"
    assert "importiert_am" not in b.lesen("importe/uwt.json", {})["bloecke"][0]        # örtliches Feld bleibt zu Hause
    assert b.lesen("importe/modern_dz_einzeln.json", {}) == {"2026-12-07": True}


def test_dz_einzeln_liest_alte_liste():
    from belegung import speicher
    from modern import dz_einzeln_kern as dze

    alt = speicher.lesen
    try:
        speicher.lesen = lambda name, standard=None: ["2026-12-07"]                       # Format aus 1.21.0
        assert dze.tage() == {"2026-12-07"}
        speicher.lesen = lambda name, standard=None: {"2026-12-07": True, "2026-12-14": False}
        assert dze.tage() == {"2026-12-07"}
    finally:
        speicher.lesen = alt


def test_oberflaeche_alle_konflikte():
    from modern import austausch_dienst, seite_daten

    q = inspect.getsource(seite_daten._austausch_lesen)
    assert "Konflikte aus der Datei übernehmen" in q and "meinen Stand behalten" in q
    assert "basis_lesen" in inspect.getsource(austausch_dienst.lesen)
    assert "eigener Stand behalten" in inspect.getsource(austausch_dienst.uebernehmen)
