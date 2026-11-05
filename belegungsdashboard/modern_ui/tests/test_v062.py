"""0.62: Leitstand-Workbench – umschaltbar je PC, gleiche Fachlogik. Ohne Browser: Einstellung, Klickregeln, Rahmen."""

from types import SimpleNamespace

from modern import kern  # noqa: F401
from modern import leitstand_ui as ls
from modern import oberflaeche


def test_einstellung_je_pc(tmp_path, monkeypatch):
    monkeypatch.setenv("INNTERNAT_LOKAL", str(tmp_path / "pc1"))
    assert not ls.an()
    ls.setzen(True)
    assert ls.an()
    monkeypatch.setenv("INNTERNAT_LOKAL", str(tmp_path / "pc2"))
    assert not ls.an()                                     # anderer PC: eigene Wahl


def test_klick_weist_nur_freie_passende_zimmer_zu():
    from modern.kern import Option

    z = SimpleNamespace(optionen=[Option("GS-2-201", "2-201", "vorschlag"), Option("GS-2-202", "2-202", "frei"),
                                  Option("GS-2-601", "2-601", "ausnahme"), Option("GS-2-301", "2-301", "aktuell")])
    assert ls._klickbar(z) == {"GS-2-201", "GS-2-202"}     # Gästezimmer/Ausnahme nur von Hand
    assert ls._klickbar(None) == set()


def test_leitstand_ist_eine_ansicht_mit_gleichen_handlungen():
    assert issubclass(ls.Leitstand, oberflaeche.Ansicht)
    for name in ("aendern", "rueckgaengig", "_zimmer_gewaehlt", "laden", "pruefen", "toast"):
        assert getattr(ls.Leitstand, name) is getattr(oberflaeche.Ansicht, name)   # nicht überschrieben
    for name in ("aufbauen", "zeichnen", "panel", "panel_zu", "oeffnen", "_extra_taste"):
        assert name in ls.Leitstand.__dict__


def test_buehnen_und_listen_zeigen_auf_vorhandene_seiten():
    from modern import register, seite_auswertung, seite_steuerung

    for _k, _t, seite, _a in ls.AKTEN:
        assert seite == "anreisen" or seite in register.SEITEN
    assert {k for k, _t in ls.RADAR} <= set(seite_auswertung.ANSICHTEN)
    assert {k for k, _t in ls.BAU} <= set(seite_steuerung.ANSICHTEN)
    assert list(ls.BUEHNEN) == ["dispo", "akten", "radar", "bau"]


def test_css_nur_unter_body_leitstand():
    import re

    regeln = [r.strip() for r in re.findall(r"([^{}]+)\{", ls.LS_CSS) if r.strip() and not r.strip().startswith("@")]
    assert all("leitstand" in r or r.startswith(".ls-") or ".ls-" in r for r in regeln)
