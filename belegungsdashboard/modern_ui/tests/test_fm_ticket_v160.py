"""1.60: FM-Ticketnummern – fortlaufend je Jahr, in Betreff und Text, suchbar, Status aus den Mängeln."""

from datetime import datetime
from pathlib import Path

from modern import fm_ticket_kern as tk

MOD = Path(tk.__file__).parent


def _t(nr, maengel=(("GS-2-108", "heizung"),), zeit="2026-11-25T09:00:00"):
    return tk.Ticket(nr, zeit, "Alex", "fm@example.org", f"[{nr}] FM-Auftrag", [list(m) for m in maengel], ["2-108"])


def test_nummern_fortlaufend_je_jahr():
    alle = [_t("FM-2026-0001"), _t("FM-2026-0007"), _t("FM-2025-0099")]
    assert tk.naechste(alle, 2026) == "FM-2026-0008"
    assert tk.naechste(alle, 2027) == "FM-2027-0001"
    assert tk.naechste([], 2026) == "FM-2026-0001"


def test_nummer_in_betreff_und_text_einmal():
    b, t = tk.mit_nummer("FM-2026-0042", "FM-Auftrag: Zimmer 2-108", "Hallo,\n\nbitte …\n\nVielen Dank!\nAlex\n")
    assert b == "[FM-2026-0042] FM-Auftrag: Zimmer 2-108"
    assert "Ticket: FM-2026-0042 – bitte bei Rückfragen angeben.\n\nVielen Dank!" in t
    assert tk.mit_nummer("FM-2026-0042", b, t) == (b, t)          # kein zweites Mal


def test_suche_findet_varianten():
    alle = [_t("FM-2026-0042"), _t("FM-2025-0042", zeit="2025-03-01T10:00:00"), _t("FM-2026-0043")]
    for q in ("FM-42", "fm 42", "Ticket 42", "FM-0042"):
        assert [x.nr for x in tk.finden(q, alle)] == ["FM-2026-0042", "FM-2025-0042"], q
    assert [x.nr for x in tk.finden("FM-2025-0042", alle)] == ["FM-2025-0042"]
    assert tk.finden("2-108", alle) == [] and tk.suchbegriff("Zimmer 2-108") is None


def test_status_aus_maengeln():
    t = _t("FM-2026-0001", (("GS-2-108", "heizung"), ("GS-2-109", "bad")))
    assert tk.offen(t, {("GS-2-109", "bad")}) is True
    assert tk.offen(t, set()) is False
    t.erledigt_von_hand = "2026-11-25T10:00:00"
    assert tk.offen(t, {("GS-2-109", "bad")}) is False
    assert tk.je_mangel([_t("FM-2026-0001"), _t("FM-2026-0005", zeit="2026-11-26T08:00:00")]) == \
        {("GS-2-108", "heizung"): "FM-2026-0005"}


def test_anlegen_und_zuruecknehmen(monkeypatch):
    speicher = {"t": [_t("FM-2026-0003")]}
    monkeypatch.setattr(tk, "laden", lambda: list(speicher["t"]))
    monkeypatch.setattr(tk, "_speichern", lambda liste: speicher.update(t=list(liste)))
    monkeypatch.setattr(tk, "_gesperrt", lambda fn: fn)
    neu = tk.anlegen([("GS-2-108", "heizung")], ["2-108"], "FM-Auftrag", "fm@example.org", "Alex",
                     datetime(2026, 11, 25, 9, 30))
    assert neu.nr == "FM-2026-0004" and [t.nr for t in speicher["t"]] == ["FM-2026-0003", "FM-2026-0004"]
    tk.zuruecknehmen("FM-2026-0004")
    assert [t.nr for t in speicher["t"]] == ["FM-2026-0003"]


def test_oberflaeche_verdrahtet():
    h = (MOD / "seite_heute.py").read_text(encoding="utf-8")
    assert "ticket: list | None = None" in h and "zuruecknehmen(nr)" in h and "tk.mit_nummer" in h
    z = (MOD / "seite_zimmer.py").read_text(encoding="utf-8")
    assert "ticket=[(zimmer, art)]" in z and "ticket=list(eintraege)" in z and "FM-Tickets …" in z
    assert "ticket_treffer(q)" in (MOD / "suche_palette.py").read_text(encoding="utf-8")
