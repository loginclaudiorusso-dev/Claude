"""0.54: Netzwerkordner – Speichern mit Wiederholung, Schreibsperre, persönliche Einstellungen je PC, Tagessicherung,
Daten übernehmen, Paket. Nur erfundene Daten."""

from __future__ import annotations

import json
import os
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from modern import kern, netz_kern, standort_kern  # noqa: F401 – kern installiert die Erweiterungen


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    d = tmp_path / "Daten"
    d.mkdir()
    monkeypatch.setenv("BELEGUNG_DATEN", str(d))
    standort_kern.waehlen("GS", merken_=False)
    return d


# ---- Wiederholen -------------------------------------------------------------------------

def test_ersetzen_wiederholt_bei_sperre(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("neu")
    b.write_text("alt")
    echt, n = os.replace, {"x": 0}

    def zickig(q, z):
        n["x"] += 1
        if n["x"] < 3:
            raise PermissionError(13, "Zugriff verweigert")
        echt(q, z)

    monkeypatch.setattr(netz_kern.os, "replace", zickig)
    monkeypatch.setattr(netz_kern.time, "sleep", lambda s: None)
    netz_kern.ersetzen(a, b)
    assert n["x"] == 3 and b.read_text() == "neu"


def test_ersetzen_gibt_irgendwann_auf(tmp_path, monkeypatch):
    def immer(q, z):
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr(netz_kern.os, "replace", immer)
    monkeypatch.setattr(netz_kern.time, "sleep", lambda s: None)
    with pytest.raises(PermissionError):
        netz_kern.ersetzen(tmp_path / "a", tmp_path / "b", versuche=3)


def test_andere_fehler_nicht_wiederholt(tmp_path, monkeypatch):
    n = {"x": 0}

    def weg(q, z):
        n["x"] += 1
        raise FileNotFoundError(2, "weg")

    monkeypatch.setattr(netz_kern.os, "replace", weg)
    with pytest.raises(FileNotFoundError):
        netz_kern.ersetzen(tmp_path / "a", tmp_path / "b")
    assert n["x"] == 1


def test_speicher_nutzt_wiederholung(ordner):
    from belegung import aenderungen, speicher

    assert isinstance(speicher.os, netz_kern._OsMitWiederholung)
    assert isinstance(aenderungen.os, netz_kern._OsMitWiederholung)
    speicher.schreiben("probe.json", {"a": 1})
    assert speicher.lesen("probe.json", {}) == {"a": 1}
    assert speicher.os.path is os.path                 # alles andere wie gehabt


def test_gesperrte_datei_nicht_als_leer_lesen(ordner, monkeypatch):
    """Sonst würde mit {} weitergerechnet und die Datei danach überschrieben."""
    from belegung import speicher

    speicher.schreiben("probe.json", {"a": 1})

    def gesperrt(p, versuche=netz_kern.VERSUCHE):
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr(netz_kern, "text_lesen", gesperrt)
    with pytest.raises(OSError, match="gesperrt"):
        speicher.lesen("probe.json", {})


def test_kaputte_datei_bleibt_standard(ordner):
    from belegung import speicher

    (ordner / "probe.json").write_text("{kaputt", encoding="utf-8")
    assert speicher.lesen("probe.json", {"x": 0}) == {"x": 0}


def test_pivot_im_datenordner(ordner):
    from belegung import laden

    (ordner / "pivot_neu.xlsx").write_bytes(b"x")
    assert laden.excel_suchen() == ordner / "pivot_neu.xlsx"


# ---- Sperre ------------------------------------------------------------------------------

def test_sperre_exklusiv_und_frei(ordner):
    with netz_kern.sperre():
        info = netz_kern.sperre_info()
        assert info and info["pid"] == os.getpid()
        with netz_kern.sperre():                      # verschachtelt: kein Selbst-Blockieren
            pass
        assert (ordner / netz_kern.SPERRE).exists()
    assert not (ordner / netz_kern.SPERRE).exists()


def test_sperre_eines_anderen_pcs(ordner):
    (ordner / netz_kern.SPERRE).write_text(json.dumps({"wer": "Erika an PC-07"}), encoding="utf-8")
    t0 = time.monotonic()
    with pytest.raises(netz_kern.Besetzt, match="Erika an PC-07"):
        with netz_kern.sperre(warten=0.3):
            pass
    assert time.monotonic() - t0 < 3
    assert (ordner / netz_kern.SPERRE).exists()       # fremde Sperre bleibt


def test_verwaiste_sperre_wird_uebernommen(ordner):
    p = ordner / netz_kern.SPERRE
    p.write_text("{}", encoding="utf-8")
    alt = time.time() - 600
    os.utime(p, (alt, alt))
    with netz_kern.sperre(warten=0.5):
        assert netz_kern.sperre_info()["pid"] == os.getpid()


def test_sperre_wartet_auf_freigabe(ordner):
    p = ordner / netz_kern.SPERRE
    p.write_text("{}", encoding="utf-8")
    threading.Timer(0.3, lambda: p.unlink()).start()
    with netz_kern.sperre(warten=5):
        pass


def test_schritt_unter_sperre_und_notiert(ordner):
    from belegung import speicher

    gesehen = {}

    def aktion():
        gesehen["sperre"] = (ordner / netz_kern.SPERRE).exists()
        speicher.schreiben("modern_probe.json", {"n": 1})

    kern._schritt("Probe gespeichert", aktion, ["modern_probe.json"])
    assert gesehen["sperre"] and not (ordner / netz_kern.SPERRE).exists()
    d = netz_kern.letzte_aenderung()
    assert d["titel"] == "Probe gespeichert" and d["rechner"] == netz_kern.rechner()
    assert not netz_kern.von_anderem(d)
    assert netz_kern.von_anderem({**d, "rechner": "PC-99"})


def test_schritt_besetzt_meldet_und_schreibt_nichts(ordner, monkeypatch):
    from belegung import speicher

    (ordner / netz_kern.SPERRE).write_text(json.dumps({"wer": "Max an PC-02"}), encoding="utf-8")
    monkeypatch.setattr(netz_kern, "SPERRE_WARTEN", 0.2)
    with pytest.raises(ValueError, match="Gerade speichert Max an PC-02"):
        kern._schritt("Probe", lambda: speicher.schreiben("modern_probe.json", {"n": 1}), ["modern_probe.json"])
    assert not (ordner / "modern_probe.json").exists()


# ---- Persönlich je PC -----------------------------------------------------------------------

def test_design_je_pc_und_uebernahme(ordner, tmp_path):
    from belegung import speicher

    # bisher: gemeinsam in modern_ui.json
    speicher.schreiben(kern.ZUSTAND, {"design": {"theme": "innternat", "modus": "hell"}, "design_038": True})
    d = kern.design_lesen()
    assert d["modus"] == "hell"                       # übernommen
    lokal = netz_kern.lokal_lesen()
    assert lokal["design"]["modus"] == "hell"
    kern.design_setzen({**d, "modus": "dunkel"})
    assert kern.design_lesen()["modus"] == "dunkel"
    assert speicher.lesen(kern.ZUSTAND, {})["design"]["modus"] == "hell"   # gemeinsame Datei unberührt


def test_spaeter_und_willkommen_je_pc(ordner, monkeypatch, tmp_path):
    from datetime import date

    heute = date(2026, 3, 2)
    kern.spaeter_setzen("anreise:x", True, heute)
    assert kern.spaeter(heute) == {"anreise:x"}
    assert not (ordner / kern.ZUSTAND).exists()       # nichts im gemeinsamen Ordner
    assert kern.willkommen_zeigen()
    kern.willkommen_weg()
    assert not kern.willkommen_zeigen()
    monkeypatch.setenv(netz_kern.LOKAL_ENV, str(tmp_path / "anderer_pc"))
    assert kern.willkommen_zeigen() and kern.spaeter(heute) == set()       # anderer PC: eigene Einstellungen


def test_standort_je_pc(ordner, monkeypatch, tmp_path):
    standort_kern.merken("BP")
    assert standort_kern.gemerkt() == "BP"
    assert not (ordner / "importe" / "modern_standort.json").exists()
    monkeypatch.setenv(netz_kern.LOKAL_ENV, str(tmp_path / "pc2"))
    assert standort_kern.gemerkt() == "GS"
    (ordner / "importe").mkdir(exist_ok=True)
    (ordner / "importe" / "modern_standort.json").write_text('{"standort": "WE"}', encoding="utf-8")
    assert standort_kern.gemerkt() == "WE"            # bisherige gemeinsame Wahl als Vorgabe


# ---- Tagessicherung -----------------------------------------------------------------------

def test_tagessicherung_einmal_am_tag(ordner):
    from belegung import datensicherung, speicher

    speicher.schreiben("einstellungen.json", {"a": 1})
    jetzt = datetime(2026, 3, 2, 8, 0)
    assert len(netz_kern.tagessicherung(jetzt)) == 1  # erster Start dieser Version
    assert netz_kern.tagessicherung(jetzt.replace(hour=9)) == []          # gleicher Tag: nichts
    assert len(netz_kern.tagessicherung(datetime(2026, 3, 3, 8, 0))) == 1  # nächster Tag
    assert len(datensicherung.liste(ordner)) == 2


def test_tagessicherung_alle_standorte(ordner):
    from belegung import speicher

    speicher.schreiben("einstellungen.json", {"a": 1})
    bp = ordner / "Standorte" / "BP"
    bp.mkdir(parents=True)
    (bp / "zuweisungen.json").write_text("[]", encoding="utf-8")
    erg = netz_kern.tagessicherung(datetime(2026, 3, 2, 8, 0))
    assert len(erg) == 2 and (bp / "Sicherungen").is_dir()


def test_tagessicherung_leer_nichts(ordner):
    assert netz_kern.tagessicherung(datetime(2026, 3, 2, 8, 0)) == []


# ---- Daten übernehmen ----------------------------------------------------------------------

def _alter_ordner(tmp_path) -> Path:
    alt = tmp_path / "Belegung_alt"
    (alt / "belegung").mkdir(parents=True)
    (alt / "belegung" / "speicher.py").write_text("# Programm", encoding="utf-8")
    (alt / "modern_ui" / ".venv").mkdir(parents=True)
    (alt / "modern_ui" / "app.py").write_text("# Programm", encoding="utf-8")
    (alt / "Start.bat").write_text("@echo off", encoding="utf-8")
    (alt / "requirements.txt").write_text("x", encoding="utf-8")
    (alt / "einstellungen.json").write_text(json.dumps({"quelle": str(alt / "pivot_neu.xlsx")}), encoding="utf-8")
    (alt / "zuweisungen.json").write_text("[]", encoding="utf-8")
    (alt / "pivot_neu.xlsx").write_bytes(b"pivot")
    (alt / "importe").mkdir()
    (alt / "importe" / "anreisen.json").write_text("{}", encoding="utf-8")
    (alt / "Listen").mkdir()
    (alt / "Listen" / "UWT_Muster.xlsx").write_bytes(b"x")
    (alt / "Sicherungen" / "2026-01-01_080000_v1.0_Start").mkdir(parents=True)
    (alt / "Sicherungen" / "2026-01-01_080000_v1.0_Start" / "zuweisungen.json").write_text("[]", encoding="utf-8")
    (alt / "Standorte" / "BP" / "importe").mkdir(parents=True)
    (alt / "Standorte" / "BP" / "zuweisungen.json").write_text("[]", encoding="utf-8")
    (alt / "INNternat_Logo.png").write_bytes(b"png")
    (alt / "~$pivot_neu.xlsx").write_bytes(b"lock")
    return alt


def test_uebernahme_pruefen(ordner, tmp_path):
    alt = _alter_ordner(tmp_path)
    u = netz_kern.uebernahme_pruefen(f'"{alt}"')                     # mit Anführungszeichen aus dem Explorer
    namen = {str(p).replace("\\", "/") for p in u.dateien}
    assert u.ok, u.probleme
    assert {"einstellungen.json", "zuweisungen.json", "pivot_neu.xlsx", "importe/anreisen.json", "Listen/UWT_Muster.xlsx",
            "Standorte/BP/zuweisungen.json", "INNternat_Logo.png"} <= namen
    assert not any(n.startswith(("belegung/", "modern_ui/")) or n.endswith((".bat", ".py")) for n in namen)
    assert "requirements.txt" not in namen and "~$pivot_neu.xlsx" not in namen
    assert "Bad Pyrmont" not in u.text and "BP" in u.standorte


def test_uebernahme_probleme(ordner, tmp_path):
    assert netz_kern.uebernahme_pruefen("").probleme
    assert "gibt es nicht" in netz_kern.uebernahme_pruefen(tmp_path / "fehlt").probleme[0]
    leer = tmp_path / "leer"
    leer.mkdir()
    assert "keine INNternat-Daten" in netz_kern.uebernahme_pruefen(leer).probleme[0]
    assert "neue Datenordner selbst" in netz_kern.uebernahme_pruefen(ordner).probleme[0]


def test_uebernehmen_kopiert_und_stellt_pivot_um(ordner, tmp_path):
    alt = _alter_ordner(tmp_path)
    vorher = sorted(p.relative_to(alt) for p in alt.rglob("*"))
    text = netz_kern.uebernehmen(alt)
    assert "neu starten" in text
    assert (ordner / "Standorte" / "BP" / "zuweisungen.json").exists()
    assert (ordner / "Sicherungen").is_dir() and not (ordner / "belegung").exists()
    assert json.loads((ordner / "einstellungen.json").read_text(encoding="utf-8"))["quelle"] == str(ordner / "pivot_neu.xlsx")
    assert sorted(p.relative_to(alt) for p in alt.rglob("*")) == vorher                 # alter Ordner unverändert
    assert json.loads((alt / "einstellungen.json").read_text(encoding="utf-8"))["quelle"] == str(alt / "pivot_neu.xlsx")


def test_uebernehmen_nie_ueber_vorhandene_daten(ordner, tmp_path):
    alt = _alter_ordner(tmp_path)
    (ordner / "zuweisungen.json").write_text('[{"person": "neu"}]', encoding="utf-8")
    with pytest.raises(ValueError, match="schon Daten"):
        netz_kern.uebernehmen(alt)
    assert "neu" in (ordner / "zuweisungen.json").read_text(encoding="utf-8")


def test_hilfsdateien_zaehlen_nicht_als_daten(ordner):
    (ordner / netz_kern.LETZTE).write_text("{}", encoding="utf-8")
    (ordner / "modern_ui_neu.json").write_text("{}", encoding="utf-8")
    assert not netz_kern.hat_daten(ordner)
    (ordner / "zuweisungen.json").write_text("[]", encoding="utf-8")
    assert netz_kern.hat_daten(ordner)


# ---- Start, Version, Paket ------------------------------------------------------------------

def test_lokal_ordner(monkeypatch, tmp_path):
    monkeypatch.delenv(netz_kern.LOKAL_ENV)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    assert netz_kern.lokal_ordner() == tmp_path / "AppData" / "INNternat"
    assert not netz_kern.netzbetrieb()
    monkeypatch.setenv(netz_kern.START_ENV, r"\\server\INNternat\INNternat starten.bat")
    assert netz_kern.netzbetrieb()


def test_autostart_ueber_startdatei(monkeypatch, tmp_path):
    from modern import melder

    monkeypatch.setenv(netz_kern.START_ENV, r"\\server\INNternat\INNternat starten.bat")
    b = melder.autostart_befehl(tmp_path)
    assert r'call "\\server\INNternat\INNternat starten.bat" --minimiert' in b


def test_version_auf_platte():
    from modern import __version__

    assert netz_kern.version_auf_platte() == __version__


def test_startdatei():
    bat = (Path(netz_kern.__file__).resolve().parent.parent / "netz" / "INNternat starten.bat").read_bytes()
    assert b"\r\n" in bat and all(c < 128 for c in bat)          # Windows-Zeilenenden, nur ASCII (cmd)
    t = bat.decode()
    for teil in ('BELEGUNG_DATEN=%INN%Daten', "INNTERNAT_START=%~f0", r"%LOCALAPPDATA%\INNternat", "PYTHONPYCACHEPREFIX",
                 r'"%PROG%\modern_ui\app.py"', '/D "%INNTERNAT_LOKAL%"'):
        assert teil in t


def test_paket(tmp_path):
    import shutil
    import subprocess

    if shutil.which("git") is None:
        pytest.skip("ohne git")
    from importlib import util

    spec = util.spec_from_file_location("paket_bauen", Path(netz_kern.__file__).resolve().parent.parent / "netz" / "paket_bauen.py")
    pb = util.module_from_spec(spec)
    spec.loader.exec_module(pb)
    try:
        namen = pb.bauen(tmp_path / "INNternat.zip")
    except subprocess.CalledProcessError:
        pytest.skip("kein git-Stand")
    assert namen[:2] == ["INNternat starten.bat", "LIESMICH.txt"]
    with zipfile.ZipFile(tmp_path / "INNternat.zip") as z:
        alle = set(z.namelist())
    assert "Programm/modern_ui/app.py" in alle and "Programm/belegung/speicher.py" in alle
    assert "Programm/modern_ui/modern/netz_kern.py" in alle or "Programm/modern_ui/modern/kern.py" in alle
    assert not any(n.startswith(("Programm/tests/", "Programm/modern_ui/tests/", "Programm/belegung/ui/")) for n in alle)
    assert "Programm/Start.bat" not in alle and "Programm/modern_ui/Start.bat" not in alle
    assert not any(n.startswith("Daten/") for n in alle)
    assert pb.mitliefern("belegung/zimmerplan.py") and not pb.mitliefern("belegung/ui/hauptfenster.py")
