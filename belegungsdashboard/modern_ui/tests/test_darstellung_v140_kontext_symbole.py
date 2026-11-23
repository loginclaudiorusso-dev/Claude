"""1.40 – Kontext- und Werkzeug-Registerkarten mit eigenen Piktogrammen, ruhigeres Cockpit, robuster Start mit
portablem Python (fremde PYTHONHOME/PYTHONPATH, unvollständige Kopie). Ohne echte Daten."""

import inspect
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from modern import menueband as mb
from modern import menueband_ui as mbu
from modern import piktogramme as pk
from modern import seite_heute as sh
from modern import symbole as sy

NETZ = Path(mb.__file__).resolve().parent.parent / "netz"


def test_ersatz_zeigt_auf_vorhandene_bilder():
    assert len(pk.ERSATZ) >= 70
    for fluent, ziel in pk.ERSATZ.items():
        assert pk.vorhanden(ziel), (fluent, ziel)
        assert sy.vorhanden(fluent), fluent                          # nur echte Fluent-Namen werden ersetzt
    assert len(set(pk.SYMBOLE.values())) == len(pk.SYMBOLE)
    for name in pk.SYMBOLE:
        ET.fromstring(pk.svg(name))


def test_kontextkarten_ganz_eigen():
    for r in mb.reiter(mbu._ansichten(), True, {"G": "Gesamt"}):
        if not r.kontext:
            continue
        for g in r.gruppen:
            for p in g.punkte:
                name, _f = mb.symbol(p)
                h = sy.html(name, _f)
                assert "pikto" in h, (r.titel, p.text, name)


def test_bedeutungsfarbe_bleibt_sonst_ein_akzent():
    gruen = sy.html("checkmark_circle", sy.GRUEN)
    assert "pikto" in gruen and "--pk-a:#10b981" in gruen
    assert "--pk-a" in sy.html("prohibited", sy.ROT) and "--pk-a" in sy.html("warning", sy.AMBER)
    for farbe in (sy.BLAU, sy.TEAL, sy.VIOLETT, sy.BASIS):
        assert "--pk-a" not in sy.html("people", farbe), farbe
    # dieselbe Bedeutung = dasselbe Bild
    assert pk.ERSATZ["print"] == "drucken" and pk.ERSATZ["qr_code"] == "qr" and pk.ERSATZ["location"] == "standort"


def test_cockpit_ruhiger():
    q = inspect.getsource(sh._postfach)
    assert "_woche_tabelle(a, t)" in q and "_frei_saeulen(a, t)" in q
    assert "_tagesblock" not in inspect.getsource(sh)                     # Abreisen/Reinigung stehen oben als Zahl
    kopf = inspect.getsource(sh._liste_kopf)
    assert "if ns:" in kopf and "zeigen(POSTFACH)" in kopf
    a = type("A", (), {"karten": [], "pf_auswahl": sh.POSTFACH})()
    assert sh.auswahl(a) == sh.POSTFACH
    assert ".m-cockpit-kopf" in sh.CSS and "padding: 0 20px" in sh.CSS


def test_start_ignoriert_fremdes_python_und_prueft_kopie():
    t = (NETZ / "INNternat starten.bat").read_bytes()
    assert b"\r\n" in t and all(c < 128 for c in t)
    t = t.decode()
    for zeile in ('set "PYTHONHOME="', 'set "PYTHONPATH="'):
        assert t.index(zeile) < t.index("if defined PYNETZ (")
    assert 'if not defined PYNETZ if exist "%INN%Python\\Python\\pythonw.exe" set "PYNETZ=%INN%Python\\Python"' in t
    assert ":python_testen" in t and '-c "import nicegui, encodings"' in t and 'set "PYTHONHOME=%~1"' in t
    lokal = t[t.index("\r\n:python_lokal"):t.index("\r\n:python_testen")]
    assert lokal.index('call :python_testen "%INNTERNAT_LOKAL%\\Python"') < lokal.index("robocopy")
    assert lokal.index(":python_netz") < lokal.index('call :python_testen "%PYNETZ%"') < lokal.index("exit /b 1")
    assert "call :python_lokal\r\n    if errorlevel 1 exit /b 1" in t


def test_keine_doppelten_bilder_in_einer_kontextkarte():
    for r in mb.reiter(mbu._ansichten(), True, {"G": "Gesamt"}):
        if r.kontext:
            namen = [mb.symbol(p)[0] for g in r.gruppen for p in g.punkte]
            namen = ["p:" + pk.ERSATZ.get(n, n) if not n.startswith("p:") else n for n in namen]
            assert [n for n, k in Counter(namen).items() if k > 1] == [], r.titel
