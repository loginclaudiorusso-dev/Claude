"""1.21: Doppelzimmer einzeln vergeben – je Anreise per Knopfdruck, zur Laufzeit, das Hauptprogramm bleibt unverändert.

Stimmt die DZ-Liste (Klassenübersicht: wer mit wem im Doppelzimmer) nicht, wird für diese Anreise jede UWT-Person so
behandelt, als stünde in der DZ-Liste „allein“: kein gemeinsames Doppelzimmer, Einzelzimmer bevorzugt, sonst ein
Doppelzimmer für sich allein. Bereits gespeicherte Paare dieser Anreise werden beim Einschalten aufgelöst: die erste
Person (nach Namen) behält das Zimmer, die zweite steht danach „ohne Zimmer“ mit Vorschlag – „Alle übernehmen“.

Gespeichert im Datenordner (alle PCs im Netzwerkordner sehen dasselbe), mit Rückgängig. Das alte Programm kennt den
Schalter nicht – dort gilt weiter die DZ-Liste. Rein, ohne NiceGUI.
"""

from __future__ import annotations

from belegung import speicher
from belegung import zimmerplan as zp

DATEI = "importe/modern_dz_einzeln.json"          # Liste der Anreisetage (ISO), an denen DZ einzeln vergeben werden
GRUPPE = "UWT"
_ORIG: dict = {}


def tage() -> set[str]:
    try:
        return {str(t) for t in speicher.lesen(DATEI, [])}
    except Exception:                                   # noqa: BLE001 – beschädigte Datei: Schalter aus
        return set()


def an(kennung: str | None) -> bool:
    return bool(kennung) and kennung in tage()


def betroffen(bedarf, kennung: str) -> int:
    """Wie viele UWT reisen an diesem Tag an? (nur dann zeigt das Menüband den Schalter)"""
    return sum(1 for b in bedarf if b.gruppe == GRUPPE and b.von.isoformat() == kennung)


def anwenden(bedarf, an_tagen: set[str]):
    """UWT an den gewählten Anreisetagen: DZ-Liste durch „allein“ ersetzen."""
    for b in bedarf:
        if b.gruppe == GRUPPE and b.von.isoformat() in an_tagen:
            b.dz = "allein"
    return bedarf


def _angaben_anwenden(bedarf, angaben):
    erg = _ORIG["angaben"](bedarf, angaben)
    t = tage()
    return anwenden(erg, t) if t else erg


def installieren() -> None:
    if _ORIG:
        return
    _ORIG["angaben"] = zp.angaben_anwenden
    zp.angaben_anwenden = _angaben_anwenden


def entfernen() -> None:
    if _ORIG:
        zp.angaben_anwenden = _ORIG.pop("angaben")


def paare(stand, kennung: str) -> list[str]:
    """Gespeicherte gemeinsame Zimmer der UWT dieser Anreise: wer muss raus? (je Zimmer bleibt die erste Person)"""
    uwt = {b.schluessel: b for b in stand.bedarf if b.gruppe == GRUPPE and b.von.isoformat() == kennung}
    je_zimmer: dict[str, list[str]] = {}
    for z in stand.zuweisungen:
        if z["person"] in uwt and z.get("zimmer"):
            je_zimmer.setdefault(z["zimmer"], []).append(z["person"])
    raus = []
    for personen in je_zimmer.values():
        raus += sorted(personen, key=lambda s: (uwt[s].name, s))[1:]
    return raus


def setzen(kennung: str, wert: bool) -> str:
    from datetime import date

    from .kern import _schritt

    t = tage()
    t = (t | {kennung}) if wert else (t - {kennung})
    tag = date.fromisoformat(kennung)
    erg: dict = {}

    def aktion():
        speicher.schreiben(DATEI, sorted(t))
        if wert and (raus := paare(zp.laden(), kennung)):
            zp.zuweisungen_entfernen(set(raus), "Doppelzimmer einzeln")
            erg["n"] = len(raus)

    _schritt(f"Anreise {tag:%d.%m.}: Doppelzimmer " + ("einzeln" if wert else "laut DZ-Liste"), aktion, [DATEI])
    if wert:
        n = erg.get("n", 0)
        return (f"Anreise {tag:%d.%m.}: UWT wohnen allein – die DZ-Liste gilt hier nicht."
                + (f" {n} Person(en) aus gemeinsamen Zimmern genommen – „Alle übernehmen“ gibt ihnen ein eigenes Zimmer."
                   if n else ""))
    return (f"Anreise {tag:%d.%m.}: Doppelzimmer wieder laut DZ-Liste (gespeicherte Zimmer bleiben; zurück zu den alten "
            "Paaren mit Rückgängig)")
