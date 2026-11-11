"""0.91 – Seitenleiste im Windows-Look (Menüband wählbar), Heute als eine Seite, „Diese Mail übernehmen“,
Leitungsansicht der Prognose nach Entwurf. Erfundene Zahlen."""

from datetime import date
from pathlib import Path

import pytest

from modern import blick_kern as bk
from modern import darstellung_kern as dk
from modern import menueband as mb
from modern import themes

MOD = Path(__file__).resolve().parent.parent / "modern"


def test_navigation_einstellung_und_klasse():
    # 0.92: Menüband wie in Office ist Standard und bleibt es; die Seitenleiste nur, wenn ausdrücklich gewählt
    assert dk.STANDARD["nav"] == "band" and set(dk.NAVIGATION) == {"leiste", "band"}
    assert dk.bereinigen({})["nav"] == "band"
    assert dk.bereinigen({"navigation": "leiste"})["nav"] == "band"        # Einstellung aus 0.91 gilt nicht mehr
    assert dk.bereinigen({"nav": "leiste"})["nav"] == "leiste"
    assert dk.bereinigen({"nav": "quatsch"})["nav"] == "band"
    assert "nav-leiste" in themes.klassen({"layout": "office", "theme": "innternat", "nav": "leiste"})
    assert "nav-leiste" not in themes.klassen({"layout": "office", "theme": "innternat"})
    assert ("aktion", "nav:leiste") in [p.ziel for p in mb.DATEI]


def test_seitenleiste_alle_ziele_sichtbar():
    from modern import menueband_ui as mbu

    e = mb.leiste(mbu._ansichten())
    gruppen = [g for g, _ in e]
    assert gruppen == ["", "Anreisen", "Zimmer und Haus", "Auswertung", "Verwalten"]
    texte = [p.text for _g, ps in e for p in ps]
    for t in ("Heute", "Zuteilen", "Firmenprogramm", "Reinigung", "Mängel und Prüfungen", "Belegung und Prognose",
              "Engpässe", "Steuerung", "Daten und Import"):
        assert t in texte, t
    assert "Steuerung" not in [p.text for _g, ps in mb.leiste(mbu._ansichten(), leitung=False) for p in ps]
    av = lambda s: {"zimmer": "liste"}.get(s, "")  # noqa: E731
    assert mb.leiste_aktiv(e, "zimmer", av, "zentrale").text == "Liste"
    assert mb.leiste_aktiv(e, "heute", av, "postfach").text == "Heute"
    assert mb.leiste_aktiv(e, "reinigung", lambda s: "facility", "zentrale").text == "Reinigung"   # erster der Seite


def _reihe():
    ms = [date(2025, m, 1) for m in range(11, 13)] + [date(2026, m, 1) for m in range(1, 13)] + \
         [date(2027, m, 1) for m in range(1, 11)]
    werte = [480 + (40 if m.month in (11, 12, 1, 2, 3) else 0) - (40 if m.month in (7, 8) else 0) for m in ms]
    ist = [m < date(2026, 11, 1) for m in ms]
    lo = [None if i else w - 15 for w, i in zip(werte, ist)]
    hi = [None if i else w + 15 for w, i in zip(werte, ist)]
    return ms, werte, ist, lo, hi


def test_leitungsansicht_reichlich_platz():
    ms, werte, ist, lo, hi = _reihe()
    g = bk.gf(ms, werte, ist, date(2026, 11, 10), 900, lo, hi, None, 11.0)
    assert g.titel.startswith("Es bleibt voraussichtlich reichlich Platz: rund ") and "von 900 Plätzen belegt" in g.titel
    assert "wird nicht erreicht" in g.untertitel and g.warn == pytest.approx(765)
    assert [z.titel for z in g.zahlen] == ["Heute belegt", "Nächster Monat erwartet", "Knappster Monat",
                                           "So gut lag die Prognose bisher"]
    assert g.zahlen[3].wert == "± 11" and g.zahlen[1].zusatz.startswith("wahrscheinlich zwischen")
    assert any("Sommertief" in m.unter for m in g.marken)
    assert g.luft is not None and g.luft > 0


def test_leitungsansicht_eng():
    ms, werte, ist, lo, hi = _reihe()
    g = bk.gf(ms, werte, ist, date(2026, 11, 10), 560, lo, hi)
    assert g.titel.startswith("Es wird ab ") and "eng" in g.titel and g.luft is None
    assert "kann ab" in g.untertitel


def test_offene_mail_ohne_outlook_verstaendlich():
    from modern import outlook_kern

    with pytest.raises(ValueError, match="Outlook"):
        outlook_kern.offene_mail()


def test_heute_eine_seite_und_ein_klick():
    h = (MOD / "seite_heute.py").read_text(encoding="utf-8")
    for teil in ("def _zeile(a, k, primaer: bool)", "Aufgaben sind dringend", "Zurück zur Übersicht",
                 "def _woche_tabelle", "def _frei_saeulen", "def _fall_vergleich", "Danach geht es weiter mit"):
        assert teil in h, teil
    k = (MOD / "kern.py").read_text(encoding="utf-8")
    assert 'Aktion(f"ausweich:{fs[0].schluessel}", f"{kurz(fs[0].vorschlag)} zuweisen")' in k
    assert 'startswith("ausweich:")' in (MOD / "oberflaeche.py").read_text(encoding="utf-8")
