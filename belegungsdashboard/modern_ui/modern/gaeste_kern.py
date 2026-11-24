"""1.49: Gäste – eigener Bereich „Gäste & Mieter“ und Doppelzimmer für Gäste.

* Ein Gast (Hospitant, Besuch …) wird hier angelegt: Name, An-/Abreise, Geschlecht, Bemerkung, auf Wunsch gleich mit
  Zimmer. Er steht danach auch in der Anreiseliste (Gruppe „Gast“).
* **Doppelzimmer:** Nur bei Gästen – sie dürfen dann in jedes Doppelzimmer (auch Haus 3.2/3.3). Mit Begleitperson werden beide angelegt und als Paar markiert (Angabe ``dz`` =
  ``gast:<Schlüssel des ersten>``) – nur so dürfen zwei Gäste ein Doppelzimmer teilen. Ohne Begleitperson wohnt der
  Gast allein im Doppelzimmer (Wunsch ``dz_wunsch``, Doppelzimmer stehen in der Auswahl oben).
* ``installieren``: Paar-Angabe in den Bedarf übernehmen, Zimmerregel für Gäste-Paare (nur in der neuen Oberfläche –
  das bisherige Programm kennt keine Gäste-Paare: dort wohnen Gäste allein).
Rein, ohne NiceGUI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from belegung import zimmerplan as zp

GRUPPE = "Gast"
PRAEFIX = "gast:"
DZ_TEXTE = ("Doppelzimmer – nur gemeinsam mit derselben UWT-Klasse", "Doppelzimmer – nur mit dem DZ-Partner laut Liste",
            "Doppelzimmer – laut DZ-Liste allein", "Doppelzimmer – anderes Geschlecht")
_ORIG: dict = {}


def gast_paar(b) -> bool:
    return b.gruppe == GRUPPE and str(b.dz).startswith(PRAEFIX)


_DZ: set[str] = set()                # Gäste mit Doppelzimmer (Wunsch oder Paar) – aus den Angaben, bei jedem Laden neu


def _angaben_anwenden(bedarf, angaben):
    erg = _ORIG["angaben"](bedarf, angaben)
    for b in erg:
        a = angaben.get(b.schluessel) or {}
        dz = a.get("dz", "")
        if b.gruppe == GRUPPE and str(dz).startswith(PRAEFIX):
            b.dz = dz
        if b.gruppe == GRUPPE and (gast_paar(b) or a.get("dz_wunsch")):
            _DZ.add(b.schluessel)
    return erg


def _paar_ok(lage, z, b, ohne) -> bool:
    mit = lage.mitbewohner(z.id, b.von, b.bis, ohne)
    return not mit or (gast_paar(b) and all(lage.dz.get(m.person, "") == b.dz for m in mit))


def _passt(lage, z, b, ohne=frozenset()):
    """Gäste mit Doppelzimmer dürfen in jedes Doppelzimmer (auch Haus 3.2/3.3, sonst UWT) – allein oder mit ihrer
    Begleitperson, nie mit Fremden. Alle übrigen Regeln (frei, gesperrt, unbewohnbar, Tier …) gelten weiter."""
    grund = _ORIG["passt"](lage, z, b, ohne)
    if grund is None or b.gruppe != GRUPPE or z.betten < 2 or not (b.schluessel in _DZ or gast_paar(b)):
        return grund
    if grund in DZ_TEXTE:
        return None if _paar_ok(lage, z, b, ohne) else grund
    # Flur-Regel („Gast nicht in Haus 3.2 …“): wie für ein Doppelzimmer prüfen – mit der Gruppe, die dort wohnen darf
    grund2 = _ORIG["passt"](lage, z, replace(b, gruppe="UWT", dz=""), ohne)
    if grund2 is None or grund2 in DZ_TEXTE:
        return None if _paar_ok(lage, z, b, ohne) else (grund2 or grund)
    return grund


def installieren() -> None:
    if _ORIG:
        return
    _ORIG["angaben"], _ORIG["passt"] = zp.angaben_anwenden, zp.passt
    zp.angaben_anwenden, zp.passt = _angaben_anwenden, _passt


def entfernen() -> None:
    if _ORIG:
        zp.angaben_anwenden, zp.passt = _ORIG.pop("angaben"), _ORIG.pop("passt")


# ---- Liste ----------------------------------------------------------------------------------------------------------

@dataclass
class GZeile:
    schluessel: str
    name: str
    von: date
    bis: date
    zimmer: str                # Zimmer-ID (geplant/gebucht) oder ""
    begleitung: str = ""       # Name der Begleitperson (Doppelzimmer-Paar)
    dz_wunsch: bool = False
    bemerkung: str = ""

    @property
    def doppelzimmer(self) -> bool:
        return bool(self.begleitung) or self.dz_wunsch


def _zimmer_von(stand, schluessel: str) -> str:
    for zid, bs in stand.lage.belegungen.items():
        if any(x.person == schluessel and x.art in ("belegt", "geplant") for x in bs):
            return zid
    return ""


def liste(stand, heute: date, tage_zurueck: int = 7) -> list[GZeile]:
    """Gäste, die noch kommen oder gerade da sind (und die der letzten ``tage_zurueck`` Tage)."""
    from datetime import timedelta

    angaben = zp.angaben_laden()
    gaeste = [b for b in stand.bedarf if b.gruppe == GRUPPE and b.bis >= heute - timedelta(days=tage_zurueck)]
    erg = []
    for b in gaeste:
        partner = [x.name for x in gaeste if gast_paar(b) and x is not b and x.dz == b.dz]
        erg.append(GZeile(b.schluessel, b.name, b.von, b.bis, _zimmer_von(stand, b.schluessel),
                          ", ".join(partner), bool((angaben.get(b.schluessel) or {}).get("dz_wunsch")), b.bemerkung))
    return sorted(erg, key=lambda g: (g.von, g.name))


# ---- Zimmerauswahl --------------------------------------------------------------------------------------------------

def zimmer_frei(von: date, bis: date, doppelzimmer: bool = False, zu_zweit: bool = False, geschlecht: str = "") -> dict[str, str]:
    """{Zimmer-ID: Text} – Zimmer, die für einen Gast im Zeitraum frei sind. ``zu_zweit``: nur Doppelzimmer mit zwei
    freien Betten; ``doppelzimmer``: Doppelzimmer zuerst."""
    from .kern import kurz

    stand = zp.laden()
    b = zp.Bedarf("gast:neu", "Gast, Neu", GRUPPE, GRUPPE, von, bis, geschlecht)
    if doppelzimmer or zu_zweit:
        _DZ.add(b.schluessel)
    else:
        _DZ.discard(b.schluessel)
    erg = []
    for z in stand.zimmer:
        if zp.passt(stand.lage, z, b) is not None:
            continue
        frei = stand.lage.freie_betten(z.id, von, bis)
        if zu_zweit and (z.betten < 2 or frei < 2):
            continue
        erg.append(((0 if (doppelzimmer or zu_zweit) and z.betten > 1 else 1, not z.gaeste, z.id),
                    z.id, f"{kurz(z.id)} · {'Doppelzimmer' if z.betten > 1 else 'Einzelzimmer'}"
                    + (" · Gästezimmer" if z.gaeste else "")))
    return {zid: text for _k, zid, text in sorted(erg)}


# ---- Anlegen --------------------------------------------------------------------------------------------------------

def _name(text: str) -> str:
    name = " ".join((text or "").split())
    if "," not in name or len(name) < 4:
        raise ValueError(f"Bitte den Namen als „Nachname, Vorname“ eingeben{f' ({name})' if name else ''}.")
    return name


def anlegen(*args, **kwargs) -> str:
    """Unter der Schreibsperre (mehrere PCs) – siehe ``_anlegen``."""
    from .kern import unter_sperre

    return unter_sperre(_anlegen)(*args, **kwargs)


def _anlegen(name: str, anreise: date, abreise: date, geschlecht: str = "", bemerkung: str = "",
             doppelzimmer: bool = False, begleitung: str = "", begleitung_geschlecht: str = "", zimmer: str = "") -> str:
    """Gast (und ggf. Begleitperson) anlegen, als Gast kennzeichnen, auf Wunsch gleich ins Zimmer setzen – ein Schritt."""
    from belegung import anreiseliste

    from . import kern

    name = _name(name)
    if abreise is None or abreise <= anreise:
        raise ValueError("Bitte eine Abreise nach der Anreise angeben.")
    begleitung = begleitung.strip()
    if begleitung and not doppelzimmer:
        raise ValueError("Mit Begleitperson bitte „Doppelzimmer“ anhaken – zwei Gäste teilen sich nur ein Doppelzimmer.")
    personen = [anreiseliste.Person(name, GRUPPE, anreise, True, abreise=abreise, geschlecht=geschlecht,
                                    bemerkung=bemerkung.strip(), abreise_quelle="hand")]
    if begleitung:
        personen.append(anreiseliste.Person(_name(begleitung), GRUPPE, anreise, True, abreise=abreise,
                                            geschlecht=begleitung_geschlecht,
                                            bemerkung=f"Begleitung von {name}", abreise_quelle="hand"))
    dz = f"{PRAEFIX}{personen[0].schluessel}" if begleitung else ""

    def aktion():
        for p in personen:
            anreiseliste.person_speichern(p)
            werte = {"gruppe": GRUPPE}
            if p.geschlecht:
                werte["geschlecht"] = p.geschlecht
            if dz:
                werte["dz"] = dz
            elif doppelzimmer:
                werte["dz_wunsch"] = True
            zp.angabe_setzen(p.schluessel, **werte)
        if zimmer:
            for p in personen:                      # nacheinander: die Begleitperson sieht den Gast schon im Zimmer
                st = zp.laden()
                zp.zuweisungen_speichern([kern._zuteilung(st, p.schluessel, zimmer)], "Gäste")
    kern._schritt(f"Gast {name}" + (f" + {begleitung}" if begleitung else ""), aktion,
                  [anreiseliste.DATEI, zp.PERSONEN_ANGABEN])
    wer = name + (f" und {begleitung}" if begleitung else "")
    wo = f" in {kern.kurz(zimmer)}" if zimmer else " – Zimmer unter Anreisen → Zuteilen wählen"
    return f"Gast {wer} angelegt ({anreise:%d.%m.} – {abreise:%d.%m.%Y}){wo}"
