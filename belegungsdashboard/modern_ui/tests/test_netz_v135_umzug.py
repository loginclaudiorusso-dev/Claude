"""1.35 – Umzug in den EINEN Netzwerkordner: Daten auch dann übernehmen, wenn dort beim ersten Start schon etwas
angelegt wurde (gesichert, Benutzerkonten bleiben), und den richtigen Ordner finden. Erfundene Daten."""

import json

import pytest

from modern import netz_kern
from test_netz_v054_netzwerkordner import _alter_ordner, ordner  # noqa: F401 – Fixture und Beispielordner


def test_ersetzen_sichert_vorher_und_behaelt_konten(ordner, tmp_path):  # noqa: F811
    from belegung import datensicherung

    alt = _alter_ordner(tmp_path)
    (ordner / "zuweisungen.json").write_text('[{"person": "erster Start"}]', encoding="utf-8")
    (ordner / "nur_neu.json").write_text("{}", encoding="utf-8")
    (ordner / "importe").mkdir(exist_ok=True)
    (ordner / "importe" / "modern_benutzer.json").write_text('{"konten": [{"kennung": "chef"}]}', encoding="utf-8")
    u = netz_kern.uebernahme_pruefen(alt)
    assert u.vorhanden and not u.ok and "ersetzt" in u.probleme[0]
    assert netz_kern.uebernahme_pruefen(alt, None, True).ok
    netz_kern.uebernehmen(alt, None, True)
    assert json.loads((ordner / "zuweisungen.json").read_text(encoding="utf-8")) == []          # aus dem alten Ordner
    assert not (ordner / "nur_neu.json").exists()                                                 # nur Daten der Quelle
    assert "chef" in (ordner / "importe" / "modern_benutzer.json").read_text(encoding="utf-8")   # Konten bleiben
    s = [x for x in datensicherung.liste(ordner) if "Übernahme" in x.anlass]
    assert s and (s[0].pfad / "zuweisungen.json").read_text(encoding="utf-8").count("erster Start") == 1


def test_nur_konten_zaehlen_nicht_als_daten(ordner, tmp_path):  # noqa: F811
    (ordner / "importe").mkdir(exist_ok=True)
    (ordner / "importe" / "modern_benutzer.json").write_text("{}", encoding="utf-8")
    assert not netz_kern.hat_daten(ordner)
    assert netz_kern.uebernahme_pruefen(_alter_ordner(tmp_path)).ok


@pytest.mark.parametrize("unter", ["modern_ui", "Daten"])
def test_richtiger_ordner_wird_gefunden(ordner, tmp_path, unter):  # noqa: F811
    alt = _alter_ordner(tmp_path)
    if unter == "Daten":                                    # bisherige Netzwerk-/Testinstallation: Daten liegen darunter
        neu = tmp_path / "Testprogramm"
        neu.mkdir()
        alt.rename(neu / "Daten")
        u = netz_kern.uebernahme_pruefen(neu)
        assert u.ok and u.quelle == neu / "Daten"
    else:                                                   # aus Versehen der Ordner mit Start.bat (modern_ui)
        u = netz_kern.uebernahme_pruefen(alt / "modern_ui")
        assert u.ok and u.quelle == alt
