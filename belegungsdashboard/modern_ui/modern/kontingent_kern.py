"""1.75: Zimmer für eine Gruppe blockieren (Kontingent) – auch wenn die Namen noch nicht feststehen.

Beispiel: „Kurs Elektro, 12 Personen, 03.03.–28.03.“ – die Zimmer sollen nicht anderweitig vergeben werden, obwohl
noch niemand namentlich bekannt ist.

* Ein Kontingent: Bezeichnung, Zeitraum, Zimmer (Auswahl), Notiz. Gespeichert je Standort in
  ``importe/modern_kontingente.json`` (mit gesichert, alle PCs sehen es).
* Beim Laden (eingehängt in ``zimmerplan.lage_bauen``, nur neue Oberfläche) bekommt jedes Bett der Zimmer im Zeitraum
  eine Belegung „Kontingent: …“. Damit zählt es überall wie belegt: Zimmerplan, Zuteilen (das Zimmer wird nicht
  vorgeschlagen), Belegung, Engpässe, Auswertung.
* **Füllt sich von selbst:** Steht im Zeitraum schon jemand namentlich im Zimmer (Gebäudeplan oder Zuteilung), wird
  sein Bett nicht mehr blockiert – kommen die Namen aus RIOS, verschwindet die Blockierung Bett für Bett.
* Zum Zuteilen in INNternat: das Zimmer aus dem Kontingent freigeben (oder das Kontingent auflösen).
* Gebäudeplan und Hauptprogramm bleiben unverändert.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

DATEI = "importe/modern_kontingente.json"
GRUND = "Kontingent"
PERSON = "kontingent:"
_ORIG: dict = {}


@dataclass
class Kontingent:
    id: str
    titel: str
    von: date
    bis: date
    zimmer: list[str] = field(default_factory=list)
    notiz: str = ""
    angelegt: str = ""
    wer: str = ""

    def zu_dict(self) -> dict:
        d = asdict(self)
        d["von"], d["bis"] = self.von.isoformat(), self.bis.isoformat()
        return d

    @staticmethod
    def aus_dict(d: dict) -> "Kontingent":
        return Kontingent(str(d["id"]), str(d.get("titel") or ""), date.fromisoformat(d["von"]),
                          date.fromisoformat(d["bis"]), [str(z) for z in d.get("zimmer") or []],
                          str(d.get("notiz") or ""), str(d.get("angelegt") or ""), str(d.get("wer") or ""))

    @property
    def text(self) -> str:
        return f"{self.titel} · {self.von:%d.%m.%Y} – {self.bis:%d.%m.%Y} · {len(self.zimmer)} Zimmer"


def laden() -> list[Kontingent]:
    from belegung import speicher

    try:
        roh = speicher.lesen(DATEI, {}) or {}
    except Exception:                              # noqa: BLE001 – beschädigt: lieber ohne Blockierung laden
        return []
    erg = []
    for d in roh.get("kontingente") or [] if isinstance(roh, dict) else []:
        try:
            erg.append(Kontingent.aus_dict(d))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(erg, key=lambda k: (k.von, k.titel))


def _speichern(ks: list[Kontingent]) -> None:
    from belegung import speicher

    speicher.schreiben(DATEI, {"kontingente": [k.zu_dict() for k in ks]})


def _wer() -> str:
    try:
        from . import netz_kern

        return netz_kern.wer()
    except Exception:                              # noqa: BLE001
        return ""


def _pruefen(titel: str, von: date, bis: date, zimmer: list[str]) -> str:
    titel = re.sub(r"\s+", " ", (titel or "").strip())[:80]
    if not titel:
        raise ValueError("Bitte eine Bezeichnung eingeben (z. B. „Kurs Elektro März“).")
    if bis < von:
        raise ValueError("Das Ende liegt vor dem Beginn.")
    if (bis - von).days > 400:
        raise ValueError("Ein Kontingent darf höchstens gut ein Jahr dauern.")
    if not zimmer:
        raise ValueError("Bitte mindestens ein Zimmer auswählen.")
    return titel


def anlegen(titel: str, von: date, bis: date, zimmer: list[str], notiz: str = "") -> str:
    from .kern import _schritt

    titel = _pruefen(titel, von, bis, zimmer)

    def tun():
        ks = laden()
        ks.append(Kontingent(f"k{datetime.now():%Y%m%d%H%M%S%f}", titel, von, bis, sorted(set(zimmer)),
                             (notiz or "").strip()[:300], datetime.now().isoformat(timespec="minutes"), _wer()))
        _speichern(ks)
    _schritt(f"Kontingent „{titel}“ angelegt", tun, [DATEI])
    return f"{len(set(zimmer))} Zimmer für „{titel}“ blockiert ({von:%d.%m.} – {bis:%d.%m.%Y})"


def bearbeiten(kid: str, titel: str, von: date, bis: date, zimmer: list[str], notiz: str = "") -> str:
    from .kern import _schritt

    titel = _pruefen(titel, von, bis, zimmer)

    def tun():
        ks = laden()
        k = next((k for k in ks if k.id == kid), None)
        if k is None:
            raise ValueError("Dieses Kontingent gibt es nicht mehr.")
        k.titel, k.von, k.bis, k.zimmer, k.notiz = titel, von, bis, sorted(set(zimmer)), (notiz or "").strip()[:300]
        _speichern(ks)
    _schritt(f"Kontingent „{titel}“ geändert", tun, [DATEI])
    return f"Kontingent „{titel}“ gespeichert"


def zimmer_freigeben(kid: str, zid: str) -> str:
    """Ein Zimmer aus dem Kontingent nehmen (z. B. um dort jemanden zuzuteilen). Letztes Zimmer → aufgelöst."""
    from .kern import _schritt

    def tun():
        ks = laden()
        k = next((k for k in ks if k.id == kid), None)
        if k is None:
            raise ValueError("Dieses Kontingent gibt es nicht mehr.")
        k.zimmer = [z for z in k.zimmer if z != zid]
        _speichern([x for x in ks if x.zimmer])
    _schritt("Zimmer aus Kontingent freigegeben", tun, [DATEI])
    return "Zimmer freigegeben – es kann jetzt zugeteilt werden"


def aufloesen(kid: str) -> str:
    from .kern import _schritt

    def tun():
        ks = laden()
        if not any(k.id == kid for k in ks):
            raise ValueError("Dieses Kontingent gibt es nicht mehr.")
        _speichern([k for k in ks if k.id != kid])
    _schritt("Kontingent aufgelöst", tun, [DATEI])
    return "Kontingent aufgelöst – die Zimmer sind wieder frei"


def ist_kontingent(b) -> bool:
    return (getattr(b, "person", "") or "").startswith(PERSON)


def _namentlich(bs: list, von: date, bis: date) -> int:
    """Wie viele Betten sind im Zeitraum schon namentlich belegt (höchste Zahl an einem Tag)?"""
    echte = [b for b in bs if b.art in ("belegt", "geplant") and not ist_kontingent(b) and b.von <= bis and b.bis >= von]
    if not echte:
        return 0
    tage = sorted({max(b.von, von) for b in echte})
    return max(sum(1 for b in echte if b.von <= t <= b.bis) for t in tage)


def anwenden(lage, ks: list[Kontingent] | None = None) -> int:
    """Blockier-Belegungen eintragen (je freies Bett eine). Rückgabe: Anzahl."""
    from belegung.gebaeudeplan import Belegung

    ks = laden() if ks is None else ks
    n = 0
    for k in ks:
        for zid in k.zimmer:
            z = lage.zimmer.get(zid)
            if z is None:
                continue
            bs = lage.belegungen.setdefault(zid, [])
            if any(b.art == "gesperrt" and b.von <= k.bis and b.bis >= k.von for b in bs):
                continue                           # gesperrt (Renovierung, Mangel) – nicht zusätzlich blockieren
            frei = max(0, int(z.betten or 1) - _namentlich(bs, k.von, k.bis))
            for i in range(frei):
                bs.append(Belegung(zid, k.von, k.bis, "belegt", name=f"{GRUND}: {k.titel}", massnahme=GRUND,
                                   grund=f"{GRUND} ({k.titel})", person=f"{PERSON}{k.id}:{i + 1}"))
                n += 1
    return n


def _lage_bauen(*args, **kwargs):
    lage = _ORIG["lage_bauen"](*args, **kwargs)
    try:
        anwenden(lage)
    except Exception:                              # noqa: BLE001 – darf das Laden nie verhindern
        pass
    return lage


def installieren() -> None:
    from belegung import zimmerplan as zp

    if _ORIG:
        return
    _ORIG["lage_bauen"] = zp.lage_bauen
    zp.lage_bauen = _lage_bauen


def frei_im_zeitraum(lage, von: date, bis: date, zimmer: list) -> list:
    """Zimmer, die im Zeitraum ganz frei sind (für die Auswahl beim Anlegen)."""
    erg = []
    for z in zimmer:
        if not getattr(z, "aktiv", True):
            continue
        try:
            if lage.freie_betten(z.id, von, bis) >= (z.betten or 1):
                erg.append(z)
        except Exception:                          # noqa: BLE001
            continue
    return erg
