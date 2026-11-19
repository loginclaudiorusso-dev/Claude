"""0.34: Ergebnisse der UX-Prüfung – Änderungsbericht nach dem Einlesen, Kontrast, Sortieren per Tastatur. Erfundene Daten."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    yield tmp_path


def _b(s, name, von, bis, gruppe="RVT"):
    return SimpleNamespace(schluessel=s, name=name, von=von, bis=bis, gruppe=gruppe)


def test_bericht_nach_dem_einlesen():
    from modern import daten_kern as dk

    h = date(2030, 5, 6)
    vorher = SimpleNamespace(bedarf=[_b("id:1", "Alt, Anna", h, h + timedelta(days=30)),
                                     _b("id:2", "Weg, Willi", h, h + timedelta(days=30)),
                                     _b("id:3", "Gleich, Gerd", h, h + timedelta(days=30))],
                             zuweisungen=[{"person": "id:1", "zimmer": "GS-3.2-111"}])
    nachher = SimpleNamespace(bedarf=[_b("id:1", "Alt, Anna", h, h + timedelta(days=37)),
                                      _b("id:3", "Gleich, Gerd", h, h + timedelta(days=30)),
                                      _b("id:4", "Neu, Nina", h + timedelta(days=7), h + timedelta(days=60), "Reha")],
                              zuweisungen=[{"person": "id:1", "zimmer": "GS-3.2-111"}])
    erg = dk.bedarf_aenderungen(vorher, nachher, h)
    assert [(x.art, x.name) for x in erg] == [("geaendert", "Alt, Anna"), ("entfernt", "Weg, Willi"), ("neu", "Neu, Nina")]
    assert erg[0].zimmer == "3.2-111" and "Abreise 05.06. → 12.06." in erg[0].text
    assert "13.05." in erg[2].text


def test_ohne_neue_dateien_kein_bericht(leer):
    from modern import daten_kern as dk

    assert dk.ordner_importieren_bericht() == ([], [])


def _kontrast(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_kleinschrift_kontrast_mindestens_4_5():
    from modern import stil

    for flaeche in ("bg", "fl", "fl2"):
        assert _kontrast(stil.T["text3"], stil.T[flaeche]) >= 4.5, flaeche


def test_sortieren_per_tastatur():
    from modern.oberflaeche import SORTIER_JS

    assert "tabindex" in SORTIER_JS and "columnheader" in SORTIER_JS and "keydown" in SORTIER_JS
