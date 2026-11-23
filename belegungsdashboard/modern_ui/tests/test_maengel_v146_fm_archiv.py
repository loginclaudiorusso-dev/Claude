"""1.46 – QR-Meldungen an FM weiterleiten (Vorlage, Vermerk) und Erledigte archivieren. Erfundene Daten."""

from datetime import date
from pathlib import Path

import pytest

from modern import qr_meldungen_kern as qm

INHALT = "ID: {rid}\nZeit: 2026-11-23T13:41:54Z\nZimmer: {zimmer}\nArt: [\"Heizung\"]\nBeschreibung: {text}\nENDE\n"


@pytest.fixture
def stand(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    (tmp_path / "daten").mkdir()
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    qm._STAND.update(mtime=None, pfad="", gelesen=None, fehler="", neu=0)
    from belegung import zimmerplan as zp

    st = zp.laden()
    o = tmp_path / "qr"
    o.mkdir()
    zs = [z for z in st.zimmer if z.aktiv and "-" in z.kurz][:3]
    for i, z in enumerate(zs, 1):
        (o / f"qr-{i}.txt").write_text(INHALT.format(rid=i, zimmer=z.kurz, text=f"Heizung rauscht {i}"), encoding="utf-8")
    qm.einlesen("", ordner="", dateien=str(o))
    yield zs
    aenderungen.verlauf_leeren()


def _m(mid):
    return next(m for m in qm.meldungen() if m.id == mid)


def test_fm_vorlage_und_vermerk(stand):
    m = _m("pa|1")
    wo, art, notiz = qm.fm_vorlage(m, lambda z: z.removeprefix("GS-"))
    assert wo == stand[0].kurz and art                                  # Katalogname der vorgeschlagenen Art
    assert "QR-Code" in notiz and "Heizung rauscht 1" in notiz and m.zeit_text in notiz
    qm.uebernehmen("pa|1", m.art, stand[0].id, heute=date(2026, 11, 23))
    qm.fm_vermerken("pa|1", heute=date(2026, 11, 23))
    assert _m("pa|1").fm == "2026-11-23"


def test_archiv(stand):
    qm.uebernehmen("pa|1", _m("pa|1").art, stand[0].id)
    qm.verwerfen("pa|2")
    assert sorted(qm.erledigte_ids()) == ["pa|1", "pa|2"]
    assert qm.archivieren(["pa|3"]).startswith("Neue Meldungen")     # neue bleiben stehen
    assert qm.archivieren(qm.erledigte_ids()) == "2 Meldung(en) archiviert"
    assert [m.id for m in qm.meldungen(qm.ARCHIV)] and {m.id for m in qm.meldungen(qm.ARCHIV)} == {"pa|1", "pa|2"}
    assert qm.meldungen("uebernommen") == [] and qm.meldungen("verworfen") == []
    assert [m.id for m in qm.neue()] == ["pa|3"]
    qm.archivieren(["pa|2"], an=False)
    assert [m.id for m in qm.meldungen("verworfen")] == ["pa|2"]


def test_oberflaeche_bietet_fm_und_archiv():
    q = (Path(qm.__file__).parent / "qr_ui.py").read_text(encoding="utf-8")
    assert "Übernehmen & an FM" in q and "Erledigte archivieren" in q and "fm_mail(a, wo, art, notiz, nach=nach)" in q
    h = (Path(qm.__file__).parent / "seite_heute.py").read_text(encoding="utf-8")
    assert 'def fm_mail(a, zimmer: str = "", art: str = "", notiz: str = "", nach=None)' in h
