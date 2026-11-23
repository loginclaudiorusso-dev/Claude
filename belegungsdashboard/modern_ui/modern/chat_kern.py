"""1.43: Chat im Programm – kurze Unterhaltung zwischen allen, die gerade mit INNternat arbeiten.

* Eine Datei für alle Standorte im gemeinsamen Datenordner: ``importe/modern_chat.json`` (Basis, wie die Benutzer).
* Zwei Kanäle: „Alle Standorte“ (``alle``) und je Standort ein eigener (Kurzname, z. B. ``GS``).
* Eine Nachricht hat Zeit, Absender (Konto bzw. Windows-Name), Kanal und Text. Aufgehoben werden die letzten
  ``MAX`` Nachrichten, höchstens ``TAGE`` Tage.
* „Gelesen bis“ merkt sich jede Person selbst (``chat_gelesen`` je Kanal, über ``netz_kern.persoenlich``).
* Unterschied zu „Nachrichten“: Nachrichten sind Notizen mit Antworten und „erledigt“; der Chat ist das Gespräch
  zwischendurch – ohne Erledigt, ohne Rückgängig.
Rein, ohne NiceGUI.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

DATEI = "importe/modern_chat.json"
MAX = 800
TAGE = 60
MAX_TEXT = 1000
ALLE = "alle"


@dataclass
class Beitrag:
    id: str
    zeit: str              # ISO, Sekunden
    von: str
    kanal: str
    text: str

    @property
    def uhr(self) -> str:
        return self.zeit[11:16]

    @property
    def tag(self) -> str:
        return self.zeit[:10]


def _pfad() -> Path:
    from . import netz_kern

    return netz_kern.basis() / DATEI


def stempel() -> float:
    """Änderungszeit der Chatdatei (0 = gibt es nicht) – zum billigen Nachsehen, ob etwas Neues da ist."""
    try:
        return _pfad().stat().st_mtime
    except OSError:
        return 0.0


def _lesen() -> list[Beitrag]:
    from . import netz_kern

    p = _pfad()
    if not p.exists():
        return []
    try:
        d = json.loads(netz_kern.text_lesen(p))
    except (OSError, ValueError):
        return []
    erg = []
    for x in d.get("beitraege", []) if isinstance(d, dict) else []:
        try:
            erg.append(Beitrag(**{k: str(x[k]) for k in ("id", "zeit", "von", "kanal", "text")}))
        except (KeyError, TypeError):
            continue
    return erg


def _schreiben(bs: list[Beitrag], jetzt: datetime) -> None:
    from . import netz_kern

    grenze = (jetzt - timedelta(days=TAGE)).isoformat(timespec="seconds")
    bs = [b for b in bs if b.zeit >= grenze][-MAX:]
    p = _pfad()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"beitraege": [asdict(b) for b in bs]}, f, ensure_ascii=False, indent=1)
        netz_kern.ersetzen(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def ich() -> str:
    from . import nachrichten_kern

    return nachrichten_kern.ich()


def kanaele() -> dict[str, str]:
    """{Kanal: Anzeigename} – „Alle Standorte“ zuerst, dann der aktive Standort."""
    from . import standort_kern

    s = standort_kern.aktiv()
    return {ALLE: "Alle Standorte", s.kurz: s.name}


def beitraege(kanal: str, anzahl: int = 200) -> list[Beitrag]:
    return [b for b in _lesen() if b.kanal == kanal][-anzahl:]


def senden(kanal: str, text: str, von: str | None = None, jetzt: datetime | None = None) -> Beitrag:
    from . import netz_kern

    text = (text or "").strip()
    if not text:
        raise ValueError("Bitte etwas schreiben.")
    jetzt = jetzt or datetime.now()
    b = Beitrag(uuid.uuid4().hex[:10], jetzt.isoformat(timespec="seconds"), von or ich(), kanal, text[:MAX_TEXT])
    with netz_kern.sperre():
        bs = _lesen()
        bs.append(b)
        _schreiben(bs, jetzt)
    return b


def gelesen_bis(kanal: str) -> str:
    from . import netz_kern

    d = netz_kern.persoenlich("chat_gelesen", {}, je_standort=False) or {}
    return str(d.get(kanal, "")) if isinstance(d, dict) else ""


def gelesen(kanal: str, bis: str | None = None) -> None:
    from . import netz_kern

    d = dict(netz_kern.persoenlich("chat_gelesen", {}, je_standort=False) or {})
    d[kanal] = bis or datetime.now().isoformat(timespec="seconds")
    netz_kern.persoenlich_setzen("chat_gelesen", d, je_standort=False)


def ungelesen(wer: str | None = None, alle: list[Beitrag] | None = None) -> dict[str, list[Beitrag]]:
    """{Kanal: neue Beiträge anderer seit „gelesen bis“} – nur Kanäle, die man sehen darf (alle + aktiver Standort)."""
    wer = wer or ich()
    alle = _lesen() if alle is None else alle
    erg = {}
    for k in kanaele():
        seit = gelesen_bis(k)
        neu = [b for b in alle if b.kanal == k and b.von != wer and b.zeit > seit]
        if neu:
            erg[k] = neu
    return erg


def tagestrenner(bs: list[Beitrag], heute: str) -> list[tuple[str, Beitrag | None]]:
    """Für die Anzeige: vor dem ersten Beitrag eines Tages eine Zeile „Heute“ bzw. „Mo 23.11.“."""
    tage = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    erg: list[tuple[str, Beitrag | None]] = []
    zuletzt = ""
    for b in bs:
        if b.tag != zuletzt:
            d = datetime.fromisoformat(b.zeit)
            erg.append(("Heute" if b.tag == heute else f"{tage[d.weekday()]} {d:%d.%m.}", None))
            zuletzt = b.tag
        erg.append(("", b))
    return erg
