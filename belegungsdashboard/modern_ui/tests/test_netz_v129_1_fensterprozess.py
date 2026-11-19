"""1.29.1 – Das eigene Fenster (pywebview) läuft unter Windows in einem KINDPROZESS, der app.py erneut lädt
(``__mp_main__``). Die Doppelstart-Prüfung aus 1.27 darf nur im Hauptprozess greifen – sonst beendet sich das
Fenster sofort, weil es das Lebenszeichen „startet“ des eigenen Programms sieht („zweiter Start beendet“)."""

import json
import multiprocessing as mp
import os
import pathlib
import runpy
import time

APP = pathlib.Path(__file__).resolve().parents[1] / "app.py"


def _kind(lokal: str, daten: str, marke: str) -> None:
    os.environ["INNTERNAT_LOKAL"], os.environ["BELEGUNG_DATEN"] = lokal, daten
    runpy.run_path(str(APP), run_name="__mp_main__")      # so lädt der Fensterprozess das Programm
    pathlib.Path(marke).write_text("durchgelaufen", encoding="utf-8")


def test_fensterprozess_haelt_sich_nicht_fuer_einen_doppelstart(tmp_path):
    lokal, daten = tmp_path / "lokal", tmp_path / "daten"
    lokal.mkdir(), daten.mkdir()
    eigen = {"pid": os.getpid(), "zustand": "startet", "zeit": time.time()}   # das Hauptprogramm startet gerade
    (lokal / "laeuft.json").write_text(json.dumps(eigen), encoding="utf-8")
    p = mp.get_context("spawn").Process(target=_kind, args=(str(lokal), str(daten), str(tmp_path / "marke")))
    p.start()
    p.join(120)
    assert (tmp_path / "marke").exists(), "Fensterprozess hat sich als zweiten Start beendet"
    assert json.loads((lokal / "laeuft.json").read_text(encoding="utf-8"))["pid"] == os.getpid()   # nicht überschrieben


def test_hintergrund_takte_vertragen_das_beenden():
    """Beim Beenden liefert NiceGUI aus run.io_bound None – die Takte dürfen dann nicht mit TypeError abbrechen."""
    import inspect

    from modern import outlook_kern, qr_ui
    for q in (inspect.getsource(outlook_kern), inspect.getsource(qr_ui.takt)):
        assert "if erg is None:" in q
