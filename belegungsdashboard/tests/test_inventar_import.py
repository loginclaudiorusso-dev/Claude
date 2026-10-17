"""6.17.1: Inventur (neue Lampen, Bett1-Matratzen) einmalig ins Inventar übernehmen – nichts Vorhandenes überschreiben."""


BEKANNT = {"GS-2-101", "GS-3.2-108", "GS-6-304"}
TEXT = "# Kommentar\n2\t101\tNachttischlampe\t\n3.3\t108\tNachttischlampe\tBett1\n6\t304\t\tBett1\n9\t999\tBett1\n"


def test_lesen_ordnet_zu_und_meldet_unbekannte():
    from belegung import inventar

    erg, fehler = inventar.import_lesen(TEXT, BEKANNT)
    assert ("GS-3.2-108", "Matratze Bett1", "Bett & Wäsche") in erg       # 3.3-108 gibt es nur in 3.2
    assert sum(1 for _z, n, _k in erg if n == "Nachttischlampe (neu)") == 2
    assert fehler == ["9\t999\tBett1"]


def test_anwenden_legt_an_und_ueberschreibt_nichts():
    from belegung import inventar

    inv = inventar.Inventar()
    alt = inventar.Gegenstand("Matratze Bett1", "Bett & Wäsche")
    inv.gegenstand_speichern(alt)
    inv.setzen("GS-6-304", alt.id, 2)                       # schon gezählt: bleibt 2
    erg, _ = inventar.import_lesen(TEXT, BEKANNT)
    assert inventar.import_anwenden(inv, erg) == 3
    assert inv.anzahl("GS-6-304", alt.id) == 2
    assert len(inv.gegenstaende) == 2
    assert inventar.import_anwenden(inv, erg) == 0          # zweimal = einmal


def test_auto_import_nur_einmal(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung import inventar

    (tmp_path / inventar.IMPORT_DATEI).write_text(TEXT, encoding="utf-8")
    n, je, fehler = inventar.auto_import(BEKANNT)
    assert (n, je["Nachttischlampe (neu)"], je["Matratze Bett1"], len(fehler)) == (4, 2, 2, 1)
    assert inventar.auto_import(BEKANNT) is None
    assert inventar.laden().kurztext("GS-3.2-108") == "Matratze Bett1, Nachttischlampe (neu)"
