"""1.01 – Knöpfe ohne eigenes Symbol bekommen im Menüband ein passendes Fluent-Symbol; „RIOS-Daten“ statt
„Firmenprogramm“."""

from modern import menueband, symbole


def test_zeitraum_knoepfe_haben_kalender_symbole():
    for text in ("Heute", "Dieser Monat", "Letzter Monat", "Dieses Jahr", "Nächste 3 Monate"):
        name, _ = symbole.aus_text(text)
        assert name.startswith("calendar"), text


def test_alle_stichwort_symbole_vorhanden_und_unbekanntes_bleibt_mehr():
    assert all(symbole.vorhanden(z[0]) for _, z in symbole.TEXT)
    assert symbole.aus_text("Unbekannt")[0] == "more_horizontal"


def test_rios_daten_statt_firmenprogramm():
    import pathlib

    ordner = pathlib.Path(menueband.__file__).parent
    assert not [p.name for p in ordner.glob("*.py") if "Firmenprogramm" in p.read_text(encoding="utf-8")]
