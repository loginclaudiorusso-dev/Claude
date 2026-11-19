"""0.99 – ein Gruppen-Farbschema überall, zweifarbige Menüband-Symbole (Microsoft 365), Werkzeuge der Seite im
Menüband (Kontext-Registerkarte). Ohne echte Daten."""

from modern import analytik_kern as an
from modern import darstellung_kern as dk
from modern import diagramm_stil as ds
from modern import menueband as mb
from modern import themes


def test_gruppenfarben_ein_schema():
    assert ds.gruppen_farbe("UWT", dunkel_=False) == ds.gruppen_farbe("Umschüler", dunkel_=False) == "#1e3a5f"
    assert ds.gruppen_farbe("Mieter", dunkel_=False) == "#0d9488"
    assert ds.gruppen_farbe("Reha", dunkel_=False) == "#94a3b8"
    assert ds.gruppen_farbe("andere", 1, ["#111111", "#222222"], dunkel_=False) == "#222222"
    assert an.STATUS_FARBEN[True]["UWT"] == "#1e3a5f" and an.STATUS_FARBEN[True]["Mieter"] == "#0d9488"


def test_gruppenfarben_im_dunkeln_sichtbar():
    dunkel = ds.gruppen_farbe("UWT", dunkel_=True)
    assert dunkel != "#1e3a5f" and ds.kontrast(dunkel, "#15171C") >= 3
    assert an.STATUS_FARBEN[False]["UWT"] == dunkel


def _punkt(seite, ansicht=None, **z):
    return mb.Punkt("x", "chevron_right", mb.S(seite, ansicht, **z))


def test_symbole_fluent_wie_besprochen():
    # 1.00: Microsoft Fluent 2 – (Symbol, Bedeutungsfarbe)
    assert mb.symbol(_punkt("heute", heute_ansicht="zentrale")) == ("weather_sunny", mb.AMBER)
    assert mb.symbol(_punkt("anreisen", "zuteilen"))[0] == "conference_room"
    assert mb.symbol(_punkt("anreisen", "abreisen"))[0] == "door_arrow_right"
    assert mb.symbol(_punkt("anreisen", "eintragen"))[0] == "briefcase"
    assert mb.symbol(_punkt("mieter"))[0] == "key"
    assert mb.symbol(mb.Punkt("x", "y", mb.A("dg_modus:einfach")))[0] == "lightbulb"          # Variante A
    assert mb.symbol(mb.Punkt("x", "y", mb.A("dg_modus:karte")))[0] == "content_view"         # Variante A
    assert mb.symbol(mb.Punkt("x", "y", mb.A("aw:aw_chart=reserve")))[0] == "battery_charge"  # Variante A


def test_jedes_menueband_symbol_existiert_als_svg():
    from modern import menueband_ui as mu
    from modern import symbole

    for r in mb.reiter(mu._ansichten(), True, {"G": "Gesamt"}):
        for g in r.gruppen:
            for p in g.punkte:
                name, _farbe = mb.symbol(p)
                assert symbole.vorhanden(name), (r.key, p.text, name)


def test_keine_doppelten_symbole_je_reiter():
    from modern import menueband_ui as mu

    for r in mb.reiter(mu._ansichten(), True, {"G": "Gesamt"}):
        sym = [mb.symbol(p)[0] for g in r.gruppen for p in g.punkte]
        assert len(sym) == len(set(sym)), (r.key, sym)
        if r.key == "zimmer":
            assert all(p.gross for p in r.gruppen[0].punkte) and len(r.gruppen[0].punkte) == 4


def test_werkzeuge_oben_einstellung_und_klasse():
    assert dk.bereinigen({})["werkzeuge_oben"] is True
    assert dk.bereinigen({"werkzeuge_oben": False})["werkzeuge_oben"] is False
    d = themes.bereinigen({"layout": "office", "theme": "innternat"})
    assert "ob-oben" in themes.klassen(d)
    assert "ob-oben" not in themes.klassen({**d, "werkzeuge_oben": False})
    assert "ob-oben" not in themes.klassen({**d, "nav": "leiste"})
    assert "ob-oben" in themes.ALLE_KLASSEN
