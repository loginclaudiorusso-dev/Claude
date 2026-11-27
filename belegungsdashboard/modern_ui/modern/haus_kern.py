"""1.63: Wer ist im Haus? – Abwesenheiten, Schlüsselausgaben und die Bildschirmliste „Aktuell im Haus“.

Abwesenheiten (Urlaub, Heimfahrt, Krankenhaus …)
* Name, Zimmer, von, bis, Grund. Wer heute abwesend ist, steht in „Aktuell im Haus“ und auf der Notfallliste getrennt
  („abwesend – nicht im Haus“) und zählt dort nicht als Person im Haus.

Schlüssel ausgeben und zurücknehmen
* Wer, welches Zimmer, wie viele Schlüssel (und Nummer/Bezeichnung), ausgegeben am, zurück am.
* „offen“ = nicht zurück; „überfällig“ = nicht zurück und laut Plan schon abgereist.

Je Standort gespeichert (``importe/modern_abwesenheiten.json``, ``importe/modern_schluessel.json``). Rein bis auf
Lesen und Schreiben (unter der Schreibsperre).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime

ABW_DATEI = "importe/modern_abwesenheiten.json"
SCHL_DATEI = "importe/modern_schluessel.json"
GRUENDE = {"heimfahrt": "Heimfahrt", "urlaub": "Urlaub", "krank": "Krankenhaus / krank", "praktikum": "Praktikum",
           "ferien": "Ferien / unterrichtsfrei", "sonst": "Sonstiges"}          # 1.75: Ferien (Kurs-Abwesenheit)


def _norm(name: str) -> str:
    return " ".join((name or "").replace(",", " ").lower().split())


def _gleich(a: str, b: str) -> bool:
    """Gleiche Person: alle Wörter gleich (Reihenfolge egal – „Beispiel, Erika“ = „Erika Beispiel“)."""
    return bool(a and b) and sorted(_norm(a).split()) == sorted(_norm(b).split())


# ---- Abwesenheiten -----------------------------------------------------------------------------------------------------

@dataclass
class Abwesenheit:
    id: str
    name: str
    zimmer: str              # Zimmer-ID (für die Zuordnung; leer erlaubt)
    von: str                 # ISO
    bis: str                 # ISO (letzter Tag der Abwesenheit)
    grund: str = "heimfahrt"
    notiz: str = ""
    erfasst: str = ""

    @property
    def von_d(self) -> date:
        return date.fromisoformat(self.von)

    @property
    def bis_d(self) -> date:
        return date.fromisoformat(self.bis)

    def am(self, tag: date) -> bool:
        return self.von_d <= tag <= self.bis_d

    @property
    def text(self) -> str:
        return f"{GRUENDE.get(self.grund, self.grund)} bis {self.bis_d:%d.%m.}"


def abw_laden() -> list[Abwesenheit]:
    from belegung import speicher

    d = speicher.lesen(ABW_DATEI, {})
    erg = []
    for x in (d or {}).get("abwesenheiten", []) if isinstance(d, dict) else []:
        try:
            a = Abwesenheit(**{f: x.get(f, "") for f in Abwesenheit.__dataclass_fields__})
            a.von_d, a.bis_d                               # noqa: B018 – Datum prüfen
            erg.append(a)
        except Exception:                                # noqa: BLE001 – kaputte Zeile überspringen
            continue
    return sorted(erg, key=lambda a: (a.von, a.name))


def _abw_speichern(liste: list[Abwesenheit]) -> None:
    from belegung import speicher

    speicher.schreiben(ABW_DATEI, {"abwesenheiten": [asdict(a) for a in liste]})


def abw_pruefen(name: str, von: date, bis: date) -> list[str]:
    fehler = []
    if not (name or "").strip():
        fehler.append("Bitte einen Namen angeben.")
    if bis < von:
        fehler.append("Das Ende liegt vor dem Beginn.")
    if (bis - von).days > 366:
        fehler.append("Länger als ein Jahr – bitte prüfen (eher Abreise als Abwesenheit?).")
    return fehler


def abw_anlegen(name: str, zimmer: str, von: date, bis: date, grund: str = "heimfahrt", notiz: str = "") -> str:
    from .kern import _schritt

    if f := abw_pruefen(name, von, bis):
        raise ValueError(" ".join(f))
    neu = Abwesenheit(uuid.uuid4().hex[:10], name.strip(), zimmer or "", von.isoformat(), bis.isoformat(),
                      grund if grund in GRUENDE else "sonst", notiz.strip(), datetime.now().isoformat(timespec="seconds"))
    _schritt(f"Abwesenheit {name.strip()}", lambda: _abw_speichern(abw_laden() + [neu]), [ABW_DATEI])
    return f"{name.strip()}: {neu.text} eingetragen"


def kurse(lage, von: date, bis: date) -> dict[str, list[tuple[str, str]]]:
    """1.75: Wer wohnt im Zeitraum im Haus – je Kurs/Maßnahme: {Maßnahme: [(Name, Zimmer-ID)]} (ohne Mieter,
    Kontingente und gehaltene Lücken)."""
    erg: dict[str, dict[str, str]] = {}
    for zid, bs in (getattr(lage, "belegungen", None) or {}).items():
        for b in bs:
            if b.art not in ("belegt", "geplant") or not (b.name or "").strip() or not (b.massnahme or "").strip():
                continue
            if (b.person or "").startswith(("kontingent:", "mv:")) or (b.grund or "").startswith("gehalten"):
                continue
            if (b.massnahme or "").lower().startswith("mieter") or not (b.von <= bis and b.bis >= von):
                continue
            erg.setdefault(b.massnahme.strip(), {}).setdefault(b.name.strip(), zid)
    return {k: sorted(v.items(), key=lambda x: x[0].lower()) for k, v in sorted(erg.items(), key=lambda x: x[0].lower())}


def abw_sammel_anlegen(eintraege: list[tuple[str, str]], von: date, bis: date, grund: str = "sonst", notiz: str = "",
                       kurs: str = "") -> str:
    """1.75: Eine Abwesenheit für viele (z. B. ganzer Kurs im Außenpraktikum, Ferienwoche) – ein Schritt, ein
    „Rückgängig“. Wer im Zeitraum schon abwesend eingetragen ist, wird nicht doppelt eingetragen."""
    from .kern import _schritt

    eintraege = [(n.strip(), z or "") for n, z in eintraege if (n or "").strip()]
    if not eintraege:
        raise ValueError("Bitte mindestens eine Person auswählen.")
    if f := abw_pruefen(eintraege[0][0], von, bis):
        raise ValueError(" ".join(f))
    jetzt = datetime.now().isoformat(timespec="seconds")
    notiz = (notiz.strip() + (f" (Kurs {kurs})" if kurs else "")).strip()
    n = {"neu": 0, "schon": 0}

    def tun():
        alle = abw_laden()
        for name, zid in eintraege:
            if any(_gleich(x.name, name) and x.von_d <= bis and x.bis_d >= von for x in alle):
                n["schon"] += 1
                continue
            alle.append(Abwesenheit(uuid.uuid4().hex[:10], name, zid, von.isoformat(), bis.isoformat(),
                                    grund if grund in GRUENDE else "sonst", notiz, jetzt))
            n["neu"] += 1
        _abw_speichern(alle)
    _schritt(f"Abwesenheit für {kurs or 'mehrere'} ({len(eintraege)})", tun, [ABW_DATEI])
    return (f"{n['neu']} Abwesenheit(en) eingetragen ({von:%d.%m.} – {bis:%d.%m.%Y})"
            + (f" · {n['schon']} waren schon eingetragen" if n["schon"] else ""))


def kursliste_html(kurs: str, personen: list[tuple[str, str]], titel: str = "Anwesenheit", unter: str = "") -> str:
    """1.75: Liste eines Kurses zum Drucken – Name, Zimmer, Spalte zum Unterschreiben."""
    from html import escape

    zeilen = "".join(f"<tr><td>{i}</td><td>{escape(n)}</td><td>{escape(z)}</td><td></td></tr>"
                     for i, (n, z) in enumerate(personen, 1))
    return ("<!doctype html><html lang='de'><meta charset='utf-8'><title>Kursliste</title><style>"
            "@page{size:A4;margin:14mm}body{font-family:Segoe UI,Arial,sans-serif;color:#1f2a33}"
            "h1{font-size:18pt;margin:0}.u{color:#45525c;margin:2mm 0 6mm}table{width:100%;border-collapse:collapse}"
            "th,td{border-bottom:0.3mm solid #bbb;padding:2.5mm 2mm;text-align:left;font-size:11pt}"
            "th{font-size:9pt;color:#45525c;text-transform:uppercase}td:last-child{width:45%}"
            f"</style><body><h1>{escape(titel)} · {escape(kurs)}</h1><div class='u'>{escape(unter)}</div>"
            "<table><tr><th>#</th><th>Name</th><th>Zimmer</th><th>Unterschrift</th></tr>" + zeilen
            + "</table></body></html>")


def abw_entfernen(aid: str) -> str:
    from .kern import _schritt

    alle = abw_laden()
    a = next((x for x in alle if x.id == aid), None)
    if a is None:
        raise ValueError("Diese Abwesenheit gibt es nicht mehr.")
    _schritt(f"Abwesenheit {a.name} entfernt", lambda: _abw_speichern([x for x in abw_laden() if x.id != aid]), [ABW_DATEI])
    return f"Abwesenheit von {a.name} entfernt"


def abwesend_am(liste: list[Abwesenheit], name: str, zimmer: str, tag: date) -> Abwesenheit | None:
    """Die heutige Abwesenheit einer Person (über Namen; das Zimmer muss passen, wenn beide eins nennen)."""
    for a in liste:
        if a.am(tag) and _gleich(a.name, name) and (not a.zimmer or not zimmer or a.zimmer == zimmer):
            return a
    return None


# ---- Schlüssel ---------------------------------------------------------------------------------------------------------

@dataclass
class Ausgabe:
    id: str
    name: str
    zimmer: str              # Zimmer-ID
    anzahl: int = 1
    bezeichnung: str = ""    # Schlüsselnummer, „Haustür + Zimmer“ …
    aus: str = ""            # ISO-Datum
    zurueck: str = ""        # ISO-Datum, leer = noch draußen
    bis: str = ""            # ISO-Datum: Abreise laut Plan beim Ausgeben (für „überfällig“)
    notiz: str = ""

    @property
    def offen(self) -> bool:
        return not self.zurueck

    def ueberfaellig(self, heute: date) -> bool:
        return self.offen and bool(self.bis) and date.fromisoformat(self.bis) < heute


def schl_laden() -> list[Ausgabe]:
    from belegung import speicher

    d = speicher.lesen(SCHL_DATEI, {})
    erg = []
    for x in (d or {}).get("ausgaben", []) if isinstance(d, dict) else []:
        try:
            erg.append(Ausgabe(**{f: x.get(f, Ausgabe.__dataclass_fields__[f].default)
                                  for f in Ausgabe.__dataclass_fields__}))
        except Exception:                                # noqa: BLE001
            continue
    return sorted(erg, key=lambda a: (a.zurueck != "", a.aus), reverse=False)


def _schl_speichern(liste: list[Ausgabe]) -> None:
    from belegung import speicher

    speicher.schreiben(SCHL_DATEI, {"ausgaben": [asdict(a) for a in liste]})


def ausgeben(name: str, zimmer: str, anzahl: int = 1, bezeichnung: str = "", am: date | None = None,
             bis: date | None = None, notiz: str = "") -> str:
    from .kern import _schritt

    if not (name or "").strip():
        raise ValueError("Bitte einen Namen angeben.")
    if int(anzahl or 0) < 1:
        raise ValueError("Mindestens ein Schlüssel.")
    am = am or date.today()
    neu = Ausgabe(uuid.uuid4().hex[:10], name.strip(), zimmer or "", int(anzahl), bezeichnung.strip(), am.isoformat(), "",
                  bis.isoformat() if bis else "", notiz.strip())
    _schritt(f"Schlüssel an {name.strip()}", lambda: _schl_speichern(schl_laden() + [neu]), [SCHL_DATEI])
    return f"{neu.anzahl} Schlüssel an {name.strip()} ausgegeben"


def zuruecknehmen(aid: str, am: date | None = None) -> str:
    from .kern import _schritt

    am = am or date.today()
    alle = schl_laden()
    a = next((x for x in alle if x.id == aid), None)
    if a is None:
        raise ValueError("Diese Ausgabe gibt es nicht mehr.")
    if not a.offen:
        raise ValueError(f"Schon zurück am {date.fromisoformat(a.zurueck):%d.%m.%Y}.")

    def tun():
        liste = schl_laden()
        for x in liste:
            if x.id == aid:
                x.zurueck = am.isoformat()
        _schl_speichern(liste)
    _schritt(f"Schlüssel von {a.name} zurück", tun, [SCHL_DATEI])
    return f"{a.anzahl} Schlüssel von {a.name} zurück"


def offen_von(liste: list[Ausgabe], name: str, zimmer: str = "") -> list[Ausgabe]:
    return [a for a in liste if a.offen and _gleich(a.name, name) and (not zimmer or not a.zimmer or a.zimmer == zimmer)]


# ---- Aktuell im Haus ---------------------------------------------------------------------------------------------------

@dataclass
class HausZeile:
    haus: str
    etage: str
    zimmer: str              # Kurzform
    zimmer_id: str
    name: str
    gruppe: str
    bis: date | None
    art: str                 # im_haus | geplant | mieter | unbekannt | abwesend
    abwesend: str = ""       # Text, wenn abwesend
    abw_id: str = ""
    schluessel: int = 0      # offene Schlüssel
    hinweis: str = ""


def im_haus(notfall_zeilen: list, abw: list[Abwesenheit], schl: list[Ausgabe], tag: date,
            zimmer_id=lambda kurz: kurz) -> list[HausZeile]:
    """Notfall-Zeilen (wer laut Plan im Haus ist) + Abwesenheiten + offene Schlüssel."""
    erg = []
    for z in notfall_zeilen:
        zid = zimmer_id(z.zimmer)
        a = abwesend_am(abw, z.name, zid, tag) if z.art in ("im_haus", "geplant", "mieter") else None
        offen = offen_von(schl, z.name, zid)
        erg.append(HausZeile(z.haus, z.etage, z.zimmer, zid, z.name, z.gruppe, z.bis, "abwesend" if a else z.art,
                             a.text if a else "", a.id if a else "", sum(x.anzahl for x in offen), z.hinweis))
    return erg


def filtern(zs: list[HausZeile], art: str = "", text: str = "") -> list[HausZeile]:
    q = (text or "").lower().strip()
    erg = []
    for z in zs:
        if art == "im_haus" and z.art not in ("im_haus", "mieter", "unbekannt"):
            continue
        if art and art != "im_haus" and z.art != art:
            continue
        if q and q not in f"{z.name} {z.zimmer} {z.gruppe} {z.haus}".lower():
            continue
        erg.append(z)
    return erg


def zaehlen(zs: list[HausZeile]) -> dict[str, int]:
    return {"im_haus": sum(1 for z in zs if z.art in ("im_haus", "mieter", "unbekannt")),
            "abwesend": sum(1 for z in zs if z.art == "abwesend"),
            "geplant": sum(1 for z in zs if z.art == "geplant")}
