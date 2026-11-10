"""0.85 – Installationspaket: Edge-Fenster statt eigenem Fenster (Netzlaufwerk), Fehlersuche.bat mit sichtbarer Konsole."""

from pathlib import Path

NETZ = Path(__file__).resolve().parent.parent / "netz"
APP = Path(__file__).resolve().parent.parent / "app.py"


def test_startdatei_browser_und_konsole():
    t = (NETZ / "INNternat starten.bat").read_bytes()
    assert b"\r\n" in t and all(c < 128 for c in t)
    t = t.decode()
    portabel = t[t.index('if exist "%INN%Python\\pythonw.exe" ('):t.index("goto verknuepfung")]
    assert 'set "INNTERNAT_BROWSER=1"' in portabel
    assert 'if /i "%~1"=="--konsole" (' in t and '"%PYW:pythonw.exe=python.exe%"' in t and "pause" in t
    assert t.index('"--konsole"') < t.index('start "" /D "%INNTERNAT_LOKAL%" "%PYW%"')


def test_fehlersuche_bat():
    t = (NETZ / "Fehlersuche.bat").read_bytes()
    assert b"\r\n" in t and all(c < 128 for c in t)
    assert b'call "%~dp0INNternat starten.bat" --konsole' in t
    assert '"Fehlersuche.bat"' in (NETZ / "installation_bauen.py").read_text(encoding="utf-8")
    assert "Fehlersuche.bat" in (NETZ / "INSTALLATION.txt").read_text(encoding="utf-8")


def test_app_schalter():
    q = APP.read_text(encoding="utf-8")
    assert 'not os.environ.get("INNTERNAT_BROWSER")' in q and 'KONSOLE = "--konsole" in sys.argv' in q
    assert "traceback.print_exception" in q
