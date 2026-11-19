"""1.27 – Start absichern: Lebenszeichen, Doppelstart, Python-Version, Fehleranzeige."""

import os
import pathlib
import subprocess
import sys
import time

from modern import start_kern as sk

HIER = pathlib.Path(__file__).resolve().parents[1]


def test_python_version():
    assert sk.python_pruefen((3, 13))[0] == "ok" and sk.python_pruefen((3, 11))[0] == "ok"
    assert sk.python_pruefen((3, 10))[0] == "alt" and "mindestens Python 3.11" in sk.python_pruefen((3, 10))[1]
    assert sk.python_pruefen((3, 14))[0] == "neu"


def test_lebenszeichen_schreiben_lesen_entfernen(tmp_path):
    sk.schreiben(tmp_path, "bereit", port=8123)
    d = sk.lesen(tmp_path)
    assert d["zustand"] == "bereit" and d["port"] == 8123 and d["pid"] == os.getpid()
    assert not list(tmp_path.glob("*.tmp"))
    sk.entfernen(tmp_path)
    assert sk.lesen(tmp_path) is None


def test_fremde_datei_wird_beim_beenden_nicht_entfernt(tmp_path):
    (tmp_path / sk.DATEI).write_text('{"pid": 1, "zustand": "bereit", "zeit": 0}', encoding="utf-8")
    sk.entfernen(tmp_path)
    assert sk.lesen(tmp_path)["pid"] == 1


def test_lebt_nur_bei_frischem_lebenszeichen_eines_anderen_laufenden_prozesses():
    jetzt = time.time()
    andere = os.getppid()                                    # läuft sicher
    assert sk.lebt({"pid": andere, "zustand": "bereit", "zeit": jetzt}, jetzt)
    assert sk.lebt({"pid": andere, "zustand": "startet", "zeit": jetzt - 20}, jetzt)
    assert not sk.lebt({"pid": andere, "zustand": "bereit", "zeit": jetzt - 60}, jetzt)      # verwaist
    assert not sk.lebt({"pid": andere, "zustand": "fehler", "zeit": jetzt}, jetzt)
    assert not sk.lebt({"pid": os.getpid(), "zustand": "bereit", "zeit": jetzt}, jetzt)       # ich selbst
    assert not sk.lebt({"pid": 999_999_9, "zustand": "bereit", "zeit": jetzt}, jetzt)        # abgestürzt
    assert not sk.lebt(None) and not sk.lebt({"zustand": "bereit", "zeit": "x", "pid": andere})


def test_warten_meldet_bereit_fehler_und_zeitueberschreitung(tmp_path):
    uhr = {"t": 1000.0}

    def schlaf(s):
        uhr["t"] += s
    assert sk.warten(tmp_path, 995, 3, schlaf, lambda: uhr["t"])[0] == "zeitueberschreitung"
    (tmp_path / sk.DATEI).write_text('{"pid": 5, "zustand": "fehler", "zeit": 1001, "fehler": "X"}', encoding="utf-8")
    erg, d = sk.warten(tmp_path, 995, 3, schlaf, lambda: uhr["t"])
    assert erg == "fehler" and d["fehler"] == "X"
    (tmp_path / sk.DATEI).write_text('{"pid": 5, "zustand": "bereit", "zeit": 900}', encoding="utf-8")     # alt
    assert sk.warten(tmp_path, 995, 3, schlaf, lambda: uhr["t"])[0] == "zeitueberschreitung"


def test_protokoll_ende(tmp_path):
    (tmp_path / "x.log").write_text("\n".join(f"Zeile {i}" for i in range(50)), encoding="utf-8")
    assert sk.protokoll_ende(tmp_path / "x.log", 3).splitlines() == ["Zeile 47", "Zeile 48", "Zeile 49"]
    assert sk.protokoll_ende(tmp_path / "fehlt.log") == ""


def _pruefen(tmp_path, *args):
    env = dict(os.environ, INNTERNAT_LOKAL=str(tmp_path))
    return subprocess.run([sys.executable, str(HIER / "start_pruefen.py"), *args], env=env, capture_output=True,
                          text=True, timeout=60)


def test_startpruefung_laeuft_ohne_nicegui_und_erkennt_doppelstart(tmp_path):
    assert _pruefen(tmp_path, "vorher").returncode == 0
    (tmp_path / sk.DATEI).write_text(f'{{"pid": {os.getpid()}, "zustand": "bereit", "zeit": {time.time()}}}',
                                     encoding="utf-8")
    assert _pruefen(tmp_path, "vorher", "--minimiert").returncode == 2
    r = _pruefen(tmp_path, "vorher")
    assert r.returncode == 2 and "schon geöffnet" in r.stdout


def test_app_schreibt_lebenszeichen_und_fehler():
    s = (HIER / "app.py").read_text(encoding="utf-8")
    assert 'start_kern.schreiben(LOKAL, "fehler"' in s and "_lebenszeichen(port)" in s and "_lebenszeichen(None)" in s
    assert s.index("start_kern.lebt(") < s.index("from nicegui import")       # Doppelstart vor dem teuren Import
    bat = (HIER / "netz" / "INNternat starten.bat").read_text(encoding="utf-8")
    assert "start_pruefen.py\" vorher" in bat and "start_pruefen.py\" nachher" in bat
    assert bat.index("vorher") < bat.index('start "" /D') < bat.index("nachher")
