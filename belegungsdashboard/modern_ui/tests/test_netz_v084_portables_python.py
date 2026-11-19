"""0.84 – Installationspaket mit portablem Python: der PC braucht kein installiertes Python."""

import subprocess
import zipfile
from importlib import util
from pathlib import Path

import pytest

NETZ = Path(__file__).resolve().parent.parent / "netz"


def test_startdatei_nimmt_portables_python():
    t = (NETZ / "INNternat starten.bat").read_bytes()
    assert b"\r\n" in t and all(c < 128 for c in t)
    t = t.decode()
    assert 'if exist "%INN%Python\\pythonw.exe" (' in t and 'set "PYW=%INN%Python\\pythonw.exe"' in t
    assert t.index("goto verknuepfung") < t.index("Erster Start auf diesem PC") < t.index(":verknuepfung")
    assert 'set "PYW=%VENV%\\Scripts\\pythonw.exe"' in t and '"%PYW%" "%PROG%\\modern_ui\\app.py"' in t
    assert "PYTHONNOUSERSITE" in t


def test_installationspaket_mit_python(tmp_path):
    spec = util.spec_from_file_location("installation_bauen", NETZ / "installation_bauen.py")
    ib = util.module_from_spec(spec)
    spec.loader.exec_module(ib)
    py = tmp_path / "Python"
    (py / "Lib" / "site-packages" / "demo").mkdir(parents=True)
    (py / "Lib" / "site-packages" / "demo" / "__pycache__").mkdir()
    for n in ("python.exe", "pythonw.exe", "Lib/site-packages/demo/__init__.py", "Lib/site-packages/demo/__pycache__/x.pyc"):
        (py / n).write_bytes(b"x")
    try:
        ib.bauen(tmp_path / "i.zip", py, "Test")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("kein git-Stand")
    alle = set(zipfile.ZipFile(tmp_path / "i.zip").namelist())
    assert {"INNternat_Test/Python/pythonw.exe", "INNternat_Test/Python/Lib/site-packages/demo/__init__.py"} <= alle
    assert not any("__pycache__" in n for n in alle) and not any("/Pakete/" in n for n in alle)
    assert "Python muss NICHT installiert sein" in (NETZ / "INSTALLATION.txt").read_text(encoding="utf-8")
