"""1.47 – Nach einem Update läuft die alte Version unsichtbar weiter: der Start erkennt sie und beendet sie."""

import subprocess
import sys
import threading
import time

import start_pruefen as sp
from modern import __version__
from modern import start_kern as sk


def _fremd():
    """Ein Prozess wie die alte Instanz; ein Faden holt ihn nach dem Ende ab (sonst bliebe unter Linux ein Zombie)."""
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    threading.Thread(target=p.wait, daemon=True).start()
    return p


def test_veraltet_nur_bei_anderer_version():
    assert sk.veraltet({"version": "1.40"}, "1.47")
    assert not sk.veraltet({"version": "1.47"}, "1.47")
    assert not sk.veraltet({}, "1.47") and not sk.veraltet(None, "1.47")     # Lebenszeichen ohne Version: nicht anfassen


def test_beenden_beendet_den_prozess():
    p = _fremd()
    try:
        assert sk.pid_lebt(p.pid)
        assert sk.beenden(p.pid)
        p.wait(timeout=5)
    finally:
        if p.poll() is None:
            p.kill()
    assert not sk.beenden("x") and not sk.beenden(0)


def test_start_beendet_alte_version_und_startet_neu(tmp_path):
    p = _fremd()
    try:
        sk.schreiben(tmp_path, "bereit", port=1234, version="0.99")
        d = sk.lesen(tmp_path)
        d["pid"] = p.pid
        (tmp_path / "laeuft.json").write_text(__import__("json").dumps(d), encoding="utf-8")
        assert sk.lebt(sk.lesen(tmp_path))
        assert sp.vorher([], tmp_path) == 0                   # weiter: neue Version starten
        time.sleep(0.2)
        assert p.poll() is not None and sk.lesen(tmp_path) is None
    finally:
        if p.poll() is None:
            p.kill()


def test_gleiche_version_bleibt():
    assert sp._version() == __version__
