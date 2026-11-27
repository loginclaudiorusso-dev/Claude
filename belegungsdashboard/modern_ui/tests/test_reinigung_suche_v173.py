"""1.73: Reinigungsliste ohne überholte Doppelzeilen, schnelles Abhaken, Suche ohne doppelte Person (erfundene Daten)."""

from datetime import date
from types import SimpleNamespace as NS

import modern.kern  # noqa: F401
from belegung import reinigungsliste as rl

from modern import seiten_kern as sk
from modern import suche_kern

H = date(2026, 11, 27)


def _r(zid, prio):
    return NS(zimmer=NS(kurz=zid, id="GS-" + zid, haus="3.2", etage="2"), art="Vorbereiten", manuell_id="", prio=prio)


def test_ueberholte_vorbereiten_nicht_doppelt(monkeypatch):
    rs = [_r("3.2-204", 4), _r("3.2-204", 5), _r("3.2-205", 1)]
    monkeypatch.setattr(sk, "_reinigungen", lambda stand, von, bis: rs)
    monkeypatch.setattr(rl, "erledigt", lambda: {})
    monkeypatch.setattr(rl, "sortiert", lambda r, h, f: r)
    monkeypatch.setattr(rl, "prioritaet", lambda r, h, f: r.prio)
    for name in ("schluessel", "auszug_datum", "frist_text", "notiz"):
        monkeypatch.setattr(rl, name, lambda r, *a, **k: "")
    monkeypatch.setattr(rl, "einzug_text", lambda r, *a: "")
    monkeypatch.setattr(rl, "prio_text", lambda r, h, f: "")
    monkeypatch.setattr(rl, "details", lambda r, *a: "")
    monkeypatch.setattr(sk.zp, "flur_text", lambda z: "")
    monkeypatch.setattr(sk, "_zustand_heute", lambda *a: "")
    zeilen = sk.reinigung(None, H, H, H)
    assert [z.zimmer for z in zeilen] == ["3.2-204", "3.2-205"]          # „Anreise vorbei, nicht abgehakt“ fällt weg


def test_abhaken_nutzt_geladenen_stand(monkeypatch):
    r = NS(zimmer=NS(kurz="3.2-204"))
    monkeypatch.setattr(sk, "_reinigungen", lambda stand, von, bis: [r] if stand == "geladen" else [])
    monkeypatch.setattr(rl, "schluessel", lambda x: "k1")
    geladen = {"n": 0}
    monkeypatch.setattr(sk.zp, "laden", lambda: geladen.__setitem__("n", geladen["n"] + 1) or "frisch")
    gesetzt = []
    monkeypatch.setattr(rl, "erledigt_setzen", lambda x, an=True: gesetzt.append((x, an)))
    import modern.kern as kern
    monkeypatch.setattr(kern, "_schritt", lambda t, fn, d=None: fn())
    from modern import netz_kern
    import contextlib
    monkeypatch.setattr(netz_kern, "sperre", lambda *a, **k: contextlib.nullcontext())
    assert "3.2-204" in sk.reinigung_setzen(["k1"], True, H, H, "geladen")
    assert geladen["n"] == 0 and gesetzt == [(r, True)]                  # kein erneutes Laden des Zimmerplans


def _t(name, zimmer, von, bis):
    return NS(name=name, zimmer_id=zimmer, von=von, bis=bis, frei=False, gesperrt=False)


def test_suche_ohne_doppelte_person_ohne_zimmer():
    mit = _t("Beispiel, Erika", "GS-2-213", date(2026, 11, 4), date(2026, 12, 8))
    alt = _t("Beispiel, Erika", "", date(2026, 10, 28), date(2026, 11, 24))           # alter Eintrag, abgereist
    spaeter = _t("Beispiel, Erika", "", date(2027, 3, 1), date(2027, 4, 1))          # neuer Aufenthalt – bleibt
    fremd = _t("Probehaus, Kim", "", date(2026, 10, 28), date(2026, 11, 24))
    erg = [t for t, _h in suche_kern.nur_aktuell([(mit, ""), (alt, ""), (spaeter, ""), (fremd, "")], H)]
    assert erg == [mit, spaeter, fremd]
