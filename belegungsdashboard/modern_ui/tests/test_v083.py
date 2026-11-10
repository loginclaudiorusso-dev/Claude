"""0.83 – Komplettes Installationspaket: Pakete ohne Internet, eigene Instanz (INSTANZ.txt), kein Briefing von selbst."""

import subprocess
import zipfile
from datetime import datetime
from importlib import util
from pathlib import Path

import pytest

NETZ = Path(__file__).resolve().parent.parent / "netz"


def test_startdatei_instanz_und_offline():
    t = (NETZ / "INNternat starten.bat").read_bytes()
    assert b"\r\n" in t and all(c < 128 for c in t)
    t = t.decode()
    for teil in ('if exist "%INN%INSTANZ.txt" set /p INST=<"%INN%INSTANZ.txt"', r"%LOCALAPPDATA%\INNternat-%INST%",
                 '--no-index --find-links "%INN%Pakete"', ":pakete_fertig", ":pakete_ok", "$env:VERKNUEPFUNG",
                 'set "INNTERNAT_INSTANZ=%INST%"', r"%LOCALAPPDATA%\INNternat"):
        assert teil in t, teil
    assert t.index(":pakete_fertig") < t.index(":pakete_ok")


def test_autostart_je_instanz(monkeypatch):
    from modern import melder

    monkeypatch.delenv("INNTERNAT_INSTANZ", raising=False)
    assert melder._autostart_datei() == melder.AUTOSTART_DATEI
    monkeypatch.setenv("INNTERNAT_INSTANZ", "Test")
    assert melder._autostart_datei() == "INNternat_Test.cmd"


def test_kein_briefing_in_test_instanz(monkeypatch):
    from modern import briefing_kern

    monkeypatch.setenv("INNTERNAT_INSTANZ", "Test")
    monkeypatch.setattr(briefing_kern, "faellig", lambda j: pytest.fail("darf nicht geprüft werden"))
    assert briefing_kern.pruefen(datetime(2026, 11, 10, 8, 0)) is None


def test_installationspaket(tmp_path):
    spec = util.spec_from_file_location("installation_bauen", NETZ / "installation_bauen.py")
    ib = util.module_from_spec(spec)
    spec.loader.exec_module(ib)
    pakete = tmp_path / "wheels"
    pakete.mkdir()
    (pakete / "demo_paket-1.0-py3-none-any.whl").write_bytes(b"PK")
    try:
        namen = ib.bauen(tmp_path / "i.zip", pakete, "Test")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("kein git-Stand")
    with zipfile.ZipFile(tmp_path / "i.zip") as z:
        alle = set(z.namelist())
        assert z.read("INNternat_Test/INSTANZ.txt") == b"Test\r\n"
    for n in ("INNternat starten.bat", "LIESMICH.txt", "INSTALLATION.txt", "Pakete/demo_paket-1.0-py3-none-any.whl",
              "Programm/modern_ui/app.py"):
        assert f"INNternat_Test/{n}" in alle, n
    assert all(n.startswith("INNternat_Test/") for n in alle)
    assert not any("/Daten/" in n or "/tests/" in n for n in alle) and len(namen) == len(alle)
