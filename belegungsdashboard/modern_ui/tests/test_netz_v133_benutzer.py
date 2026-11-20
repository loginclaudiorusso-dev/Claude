"""1.33 – Benutzerkonten für die gemeinsame Installation: Anmelden (Windows-Konto oder Passwort), Rollen, Standorte,
Schutz vor Aussperren. Erfundene Namen."""

import json

import pytest

from modern import benutzer_kern as bk
from modern import netz_kern


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    (tmp_path / "daten").mkdir()
    standort_kern.waehlen("GS", merken_=False)
    bk.abmelden()
    bk._FEHL.clear()
    yield tmp_path / "daten"
    bk.abmelden()


def _admin():
    return bk.ersten_admin_anlegen("chef", "Alex Admin", "geheim123", "geheim123", "alexw")


def test_ohne_konten_alles_wie_bisher(ordner):
    assert not bk.eingerichtet() and bk.ist_admin() and bk.erlaubte_standorte() == ["GS", "BP", "WE"]
    assert bk.anzeige() == ""


def test_erster_admin_nur_einmal_und_passwort_nur_als_hash(ordner):
    k = _admin()
    assert bk.eingerichtet() and bk.aktuell().kennung == "chef" and k.admin
    roh = (ordner / bk.DATEI).read_text(encoding="utf-8")
    assert "geheim123" not in roh and json.loads(roh)["konten"][0]["pw"].startswith("pbkdf2$")
    with pytest.raises(ValueError, match="schon einen Administrator"):
        bk.ersten_admin_anlegen("zwei", "Zweit", "geheim123", "geheim123")


def test_notfalldatei_erlaubt_neuen_admin_und_wird_entfernt(ordner):
    _admin()
    bk.abmelden()
    (ordner / bk.NOTFALL).write_text("", encoding="utf-8")
    assert bk.notfall()
    bk.ersten_admin_anlegen("ersatz", "Ersatz Admin", "neuesPW99", "neuesPW99")
    assert not (ordner / bk.NOTFALL).exists() and {k.kennung for k in bk.konten()} == {"chef", "ersatz"}


def test_anmelden_mit_passwort_und_fehlversuche(ordner):
    _admin()
    bk.anlegen("m.muster", "Mia Muster", "mitarbeiter", ["BP"], "", "start-pass-1")
    bk.abmelden()
    with pytest.raises(ValueError, match="stimmt nicht"):
        bk.anmelden("m.muster", "falsch")
    k = bk.anmelden(" M.Muster ", "start-pass-1")
    assert k.name == "Mia Muster" and k.muss_aendern
    for i in range(bk.FEHL_MAX):
        with pytest.raises(ValueError):
            bk.anmelden("m.muster", "falsch", jetzt=1000.0 + i)
    with pytest.raises(ValueError, match="warten"):
        bk.anmelden("m.muster", "start-pass-1", jetzt=1005.0)        # auch das richtige Passwort wartet
    assert bk.anmelden("m.muster", "start-pass-1", jetzt=1000.0 + bk.FEHL_PAUSE + 5).kennung == "m.muster"


def test_startpasswort_muss_geaendert_werden(ordner):
    _admin()
    bk.anlegen("m.muster", "Mia Muster", "mitarbeiter", ["BP"], "", "start-pass-1")
    bk.angemeldet(bk.anmelden("m.muster", "start-pass-1"))
    with pytest.raises(ValueError, match="verschieden"):
        bk.passwort_aendern("", "eigenes-pw-1", "eigenes-pw-2")
    with pytest.raises(ValueError, match="mindestens"):
        bk.passwort_aendern("", "kurz", "kurz")
    bk.passwort_aendern("", "eigenes-pw-1", "eigenes-pw-1")
    assert not bk.aktuell().muss_aendern and bk.finden("m.muster").zuletzt
    with pytest.raises(ValueError, match="bisherige"):                 # jetzt wird das alte Passwort verlangt
        bk.passwort_aendern("falsch", "noch-eins-1", "noch-eins-1")


def test_windows_konto_meldet_automatisch_an(ordner, monkeypatch):
    _admin()
    bk.anlegen("p.probe", "Pat Probe", "mitarbeiter", ["GS", "WE"], "FIRMA\\patp")
    monkeypatch.setenv("USERNAME", "PATP")
    k = bk.windows_konto()
    assert k.kennung == "p.probe" and k.windows == "patp" and not k.pw
    assert bk.windows_konto("niemand") is None
    with pytest.raises(ValueError, match="schon einem anderen"):
        bk.anlegen("dopp", "Doppelt", "mitarbeiter", ["GS"], "patp")


def test_standorte_und_rollen(ordner):
    _admin()
    bk.anlegen("bp.eins", "Bo Pyr", "mitarbeiter", ["BP"], "", "start-pass-1")
    with pytest.raises(ValueError, match="Standort"):
        bk.anlegen("ohne", "Ohne Ort", "mitarbeiter", [], "", "start-pass-1")
    with pytest.raises(ValueError, match="Startpasswort"):
        bk.anlegen("nix", "Nix", "mitarbeiter", ["GS"], "", "")
    with pytest.raises(ValueError, match="gibt es schon"):
        bk.anlegen("BP.Eins", "Bo Pyr", "mitarbeiter", ["BP"], "", "start-pass-1")
    bk.setzen(bk.finden("bp.eins"))
    assert bk.erlaubte_standorte() == ["BP"] and not bk.ist_admin()
    with pytest.raises(ValueError, match="Nur ein Administrator"):
        bk.anlegen("x.y", "X Y", "mitarbeiter", ["BP"], "", "start-pass-1")
    assert "Bo Pyr an" in netz_kern.wer()                               # Verlauf zeigt das Konto


def test_letzter_admin_bleibt_und_selbst_aussperren_geht_nicht(ordner):
    _admin()
    with pytest.raises(ValueError, match="selbst"):
        bk.bearbeiten("chef", "Alex Admin", "mitarbeiter", ["GS"], "alexw", True)
    with pytest.raises(ValueError, match="eigenes Konto"):
        bk.loeschen("chef")
    bk.anlegen("zwei", "Zweit Admin", "admin", [], "", "start-pass-1")
    bk.setzen(bk.finden("zwei"))
    bk.bearbeiten("chef", "Alex Admin", "admin", [], "alexw", False)      # gesperrt, aber „zwei“ bleibt Admin
    with pytest.raises(ValueError, match="mindestens ein aktiver Administrator"):
        bk.setzen(bk.finden("chef")) or bk.loeschen("zwei")


def test_gesperrtes_konto_und_zuruecksetzen(ordner):
    _admin()
    bk.anlegen("m.muster", "Mia Muster", "mitarbeiter", ["GS"], "", "start-pass-1")
    bk.bearbeiten("m.muster", "Mia Muster", "mitarbeiter", ["GS"], "", False)
    with pytest.raises(ValueError, match="gesperrt"):
        bk.anmelden("m.muster", "start-pass-1")
    bk.bearbeiten("m.muster", "Mia Muster", "mitarbeiter", ["GS"], "", True)
    bk.passwort_zuruecksetzen("m.muster", "zweites-pw-1")
    assert bk.anmelden("m.muster", "zweites-pw-1").muss_aendern
    bk.loeschen("m.muster")
    assert bk.finden("m.muster") is None


def test_hash_und_startpasswort():
    h = bk.hash_bilden("abc12345", runden=1000)
    assert bk.hash_pruefen("abc12345", h) and not bk.hash_pruefen("abc12346", h) and not bk.hash_pruefen("x", "kaputt")
    p = bk.start_passwort()
    assert len(p) == 14 and not set(p) & set("01lIoO")


def test_kaputte_benutzerdatei_sperrt_niemanden_still_aus(ordner):
    (ordner / "importe").mkdir(exist_ok=True)
    (ordner / bk.DATEI).write_text("{kaputt", encoding="utf-8")
    with pytest.raises(ValueError, match="beschädigt"):
        bk.eingerichtet()
