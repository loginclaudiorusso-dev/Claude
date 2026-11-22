"""1.36: Nachrichten im Programm – kurze Notizen an die Kolleginnen und Kollegen am Standort, ohne Outlook.

* Gespeichert je Standort (``importe/modern_nachrichten.json``), also für alle PCs gleich. Absender ist das angemeldete
  Konto (sonst Windows-Name und PC).
* Eine Nachricht hat Antworten (Verlauf wie bei einer Mail), „gelesen“ je Person und „erledigt“ (verschwindet aus der
  Liste, bleibt 90 Tage im Archiv).
* Rein, ohne NiceGUI. Geschrieben wird unter der Schreibsperre; danach wird notiert, damit andere PCs neu laden.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

DATEI = "importe/modern_nachrichten.json"
MAX_TEXT = 2000
AUFHEBEN_TAGE = 90


@dataclass
class Antwort:
    von: str
    zeit: str
    text: str


@dataclass
class Nachricht:
    id: str
    zeit: str
    von: str
    betreff: str
    text: str
    antworten: list[Antwort] = field(default_factory=list)
    gelesen: list[str] = field(default_factory=list)
    erledigt: str = ""                  # ISO-Zeit, "" = offen
    erledigt_von: str = ""

    @property
    def letzte(self) -> str:
        return self.antworten[-1].zeit if self.antworten else self.zeit

    def ungelesen_fuer(self, ich: str) -> bool:
        return ich not in self.gelesen


def ich() -> str:
    """Wer bin ich (für „gelesen“ und als Absender)? Das Konto, sonst Windows-Name."""
    from . import benutzer_kern, netz_kern

    return benutzer_kern.anzeige() or netz_kern.benutzer() or netz_kern.rechner()


def _lesen() -> list[Nachricht]:
    from belegung import speicher

    try:
        d = speicher.lesen(DATEI, {}) or {}
    except Exception:                                   # noqa: BLE001 – beschädigt: leer anzeigen, nicht abstürzen
        return []
    erg = []
    for x in d.get("nachrichten", []) if isinstance(d, dict) else []:
        try:
            erg.append(Nachricht(**{**{k: x.get(k) for k in ("id", "zeit", "von", "betreff", "text")},
                                    "antworten": [Antwort(**a) for a in x.get("antworten", [])],
                                    "gelesen": list(x.get("gelesen", [])), "erledigt": x.get("erledigt", ""),
                                    "erledigt_von": x.get("erledigt_von", "")}))
        except TypeError:
            continue
    return erg


def _schreiben(ns: list[Nachricht], titel: str) -> None:
    from dataclasses import asdict

    from belegung import speicher

    from . import netz_kern

    grenze = (datetime.now() - timedelta(days=AUFHEBEN_TAGE)).isoformat(timespec="minutes")
    ns = [n for n in ns if not n.erledigt or n.erledigt >= grenze]
    speicher.schreiben(DATEI, {"nachrichten": [asdict(n) for n in ns]})
    netz_kern.notieren(titel)


def _aendern(fn, titel: str):
    from . import netz_kern

    with netz_kern.sperre():
        ns = _lesen()
        erg = fn(ns)
        _schreiben(ns, titel)
    return erg


def offene() -> list[Nachricht]:
    """Offene Nachrichten, neueste Aktivität zuerst."""
    return sorted((n for n in _lesen() if not n.erledigt), key=lambda n: n.letzte, reverse=True)


def ungelesen(wer: str | None = None) -> int:
    w = wer or ich()
    return sum(1 for n in offene() if n.ungelesen_fuer(w))


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="minutes")


def _text(t: str) -> str:
    t = (t or "").strip()
    if not t:
        raise ValueError("Bitte einen Text eingeben.")
    return t[:MAX_TEXT]


def schreiben(betreff: str, text: str) -> str:
    von = ich()
    n = Nachricht(uuid.uuid4().hex[:10], _jetzt(), von, (betreff or "").strip()[:120] or _text(text)[:60],
                  _text(text), gelesen=[von])
    _aendern(lambda ns: ns.append(n), f"Nachricht: {n.betreff}")
    return "Nachricht gespeichert – alle am Standort sehen sie auf der Startseite"


def _finden(ns: list[Nachricht], nid: str) -> Nachricht:
    n = next((n for n in ns if n.id == nid), None)
    if n is None:
        raise ValueError("Diese Nachricht gibt es nicht mehr – bitte neu laden.")
    return n


def antworten(nid: str, text: str) -> str:
    von, t = ich(), _text(text)

    def f(ns):
        n = _finden(ns, nid)
        n.antworten.append(Antwort(von, _jetzt(), t))
        n.gelesen = [von]                          # neue Antwort: für alle anderen wieder ungelesen
        n.erledigt = n.erledigt_von = ""
    _aendern(f, "Antwort auf eine Nachricht")
    return "Antwort gespeichert"


def gelesen(nid: str) -> None:
    w = ich()

    def f(ns):
        n = _finden(ns, nid)
        if w not in n.gelesen:
            n.gelesen.append(w)
    if any(n.id == nid and n.ungelesen_fuer(w) for n in _lesen()):
        _aendern(f, "Nachricht gelesen")


def erledigen(nid: str, an: bool = True) -> str:
    w = ich()

    def f(ns):
        n = _finden(ns, nid)
        n.erledigt, n.erledigt_von = (_jetzt(), w) if an else ("", "")
    _aendern(f, "Nachricht erledigt" if an else "Nachricht wieder offen")
    return "Erledigt – die Nachricht ist aus der Liste" if an else "Wieder offen"


for _f in (schreiben, antworten, erledigen):        # kein „Rückgängig“ (das nähme sonst den letzten Planungsschritt zurück)
    _f.ohne_rueckgaengig = True
