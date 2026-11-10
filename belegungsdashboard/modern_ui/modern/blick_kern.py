"""„Auf einen Blick“ (0.87) – 3 bis 5 Sätze zu einem Diagramm aus festen Vorlagen. Rein, ohne NiceGUI, ohne KI.

Jeder Satz trägt den Punkt, auf den er sich bezieht (Index auf der x-Achse, Wert, Reihe) – ein Klick auf den Satz hebt
ihn im Diagramm hervor. Regeln:

* Zahlen deutsch und ganzzahlig („1.234“).
* Ein Unterschied, der kleiner ist als die übliche Abweichung der Prognose (``schwelle``), heißt „etwa wie im Vorjahr“ –
  nicht „mehr“ oder „weniger“. Ohne bekannte Abweichung gelten 2 % des Werts, mindestens 1,5.
* Die letzte Zeile (``Blick.stand``) nennt immer den Datenstand und ab wann die Prognose beginnt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

MONATE_LANG = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
               "November", "Dezember"]
MONATE_KURZ = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


@dataclass
class Satz:
    text: str
    index: int | None = None        # Stelle auf der x-Achse
    wert: float | None = None
    reihe: str = ""                 # Name der Reihe, auf die sich der Punkt bezieht


@dataclass
class Blick:
    saetze: list[Satz] = field(default_factory=list)
    stand: str = ""                 # letzte Zeile: Datenstand und Prognosebeginn


def zahl(x: float | None) -> str:
    if x is None:
        return "–"
    return f"{round(x):,}".replace(",", ".")


def kurz(m: date) -> str:
    return f"{MONATE_KURZ[m.month - 1]} {str(m.year)[2:]}"


def lang(m: date, heute: date | None = None) -> str:
    """„Juli“ im laufenden Jahr bzw. für die nächsten 12 Monate – sonst mit Jahr („Juli 2025“)."""
    if heute is not None and abs((m.year - heute.year) * 12 + m.month - heute.month) > 9:
        return f"{MONATE_LANG[m.month - 1]} {m.year}"
    return MONATE_LANG[m.month - 1]


def schwelle_fuer(wert: float | None, abweichung: float | None) -> float:
    """Die übliche Abweichung der Prognose – ist sie unbekannt: 2 % des Werts, mindestens 1,5 (ein Unterschied von 1
    ist bei Zählwerten nie eine Aussage)."""
    if abweichung:
        return max(1.0, abweichung)
    return max(1.5, 0.02 * abs(wert) if wert is not None else 0.0)


def vergleich(diff: float, schwelle: float, bezug: str = "im Vorjahr") -> str:
    """„20 weniger als im Vorjahr“ · „etwa wie im Vorjahr“ (innerhalb der üblichen Abweichung)."""
    if abs(diff) < schwelle:
        return f"etwa wie {bezug}"
    return f"{zahl(abs(diff))} {'mehr' if diff > 0 else 'weniger'} als {bezug}"


def _stand(stand: date, prognose_ab: date | None, einheit: str = "Monat") -> str:
    t = f"Datenstand {stand:%d.%m.%Y}"
    if prognose_ab is None:
        return t + " · alle Werte sind Ist."
    return t + f" · ab {kurz(prognose_ab) if einheit == 'Monat' else f'{prognose_ab:%d.%m.%Y}'} Prognose."


# ---- Zeitdiagramm mit Monatswerten: Vorjahresvergleich / Belegungsprognose ---------------------------------------

def monate(monate_: list[date], aktuell: list[float | None], ist: list[bool], vorjahr: list[float | None],
           stand: date, kapazitaet: float | None = None, abweichung: float | None = None,
           obere80: list[float | None] | None = None, einheit: str = "belegt",
           reihe_ist: str = "Aktuell (Ist)", reihe_prog: str = "Aktuell (Prognose)") -> Blick:
    """Sätze zum Verlauf in Monaten (Ist, dann Prognose) gegen das Vorjahr."""
    b = Blick()
    n = len(monate_)
    letzte = max((i for i in range(n) if ist[i] and aktuell[i] is not None), default=None)
    prog = [i for i in range(n) if not ist[i] and aktuell[i] is not None]
    prognose_ab = monate_[prog[0]] if prog else None
    b.stand = _stand(stand, prognose_ab)
    if letzte is not None:
        w = aktuell[letzte]
        t = f"Aktuell {zahl(w)} {einheit} ({kurz(monate_[letzte])})"
        if vorjahr[letzte] is not None:
            t += f", {vergleich(w - vorjahr[letzte], schwelle_fuer(w, abweichung))} ({zahl(vorjahr[letzte])})"
        b.saetze.append(Satz(t + ".", letzte, w, reihe_ist))
    ist_idx = [i for i in range(n) if ist[i] and aktuell[i] is not None]
    if ist_idx and prog:
        tief = min(ist_idx, key=lambda i: aktuell[i])
        hoch = max(prog, key=lambda i: aktuell[i])
        b.saetze.append(Satz(f"Tiefpunkt war {lang(monate_[tief], stand)} mit {zahl(aktuell[tief])}, der Höchstwert wird "
                             f"im {lang(monate_[hoch], stand)} erwartet ({zahl(aktuell[hoch])}).", hoch, aktuell[hoch],
                             reihe_prog))
    elif ist_idx:
        tief = min(ist_idx, key=lambda i: aktuell[i])
        hoch = max(ist_idx, key=lambda i: aktuell[i])
        b.saetze.append(Satz(f"Tiefpunkt war {lang(monate_[tief], stand)} mit {zahl(aktuell[tief])}, der Höchstwert "
                             f"{lang(monate_[hoch], stand)} mit {zahl(aktuell[hoch])}.", tief, aktuell[tief], reihe_ist))
    if prog:
        sechs = prog[:6]
        lo, hi = min(aktuell[i] for i in sechs), max(aktuell[i] for i in sechs)
        paare = [(aktuell[i], vorjahr[i]) for i in sechs if vorjahr[i] is not None]
        t = f"Nächste {len(sechs)} Monate: {zahl(lo)} bis {zahl(hi)} erwartet"
        if paare:
            d = sum(a - v for a, v in paare) / len(paare)
            s = schwelle_fuer(sum(a for a, _v in paare) / len(paare), abweichung)
            t += (", im Schnitt etwa wie im Vorjahr" if abs(d) < s else
                  f", im Schnitt {zahl(abs(d))} {'über' if d > 0 else 'unter'} Vorjahr")
        hoch6 = max(sechs, key=lambda i: aktuell[i])
        b.saetze.append(Satz(t + ".", hoch6, aktuell[hoch6], reihe_prog))
    if kapazitaet:
        bereich = prog[:6] or ist_idx[-6:]
        if bereich:
            oben = [(obere80[i] if obere80 and obere80[i] is not None else aktuell[i]) for i in bereich]
            k = max(range(len(bereich)), key=lambda j: oben[j])
            reserve = kapazitaet - oben[k]
            i = bereich[k]
            if reserve >= 0:
                t = f"Kapazität {zahl(kapazitaet)}: Reserve mindestens {zahl(reserve)} Plätze."
            else:
                t = (f"Kapazität {zahl(kapazitaet)}: im {lang(monate_[i], stand)} möglicherweise überschritten "
                     f"(bis {zahl(oben[k])}).")
            b.saetze.append(Satz(t, i, aktuell[i], reihe_prog if not ist[i] else reihe_ist))
    return _begrenzen(b)


# ---- Tagesverlauf ------------------------------------------------------------------------------------------------

def tage(tage_: list[date], werte: list[float | None], ist: list[bool], stand: date,
         kapazitaet: float | None = None, abweichung: float | None = None, reihe: str = "Belegt") -> Blick:
    """Sätze zum Tagesverlauf (Summe je Tag)."""
    b = Blick()
    idx = [i for i, w in enumerate(werte) if w is not None]
    prog = [i for i in idx if not ist[i]]
    b.stand = _stand(stand, tage_[prog[0]] if prog else None, "Tag")
    if not idx:
        return b
    mittel = sum(werte[i] for i in idx) / len(idx)
    hoch = max(idx, key=lambda i: werte[i])
    tief = min(idx, key=lambda i: werte[i])
    b.saetze.append(Satz(f"Im Zeitraum im Schnitt {zahl(mittel)} belegt ({len(idx)} Tage).", None, None, reihe))
    b.saetze.append(Satz(f"Höchststand {zahl(werte[hoch])} am {tage_[hoch]:%d.%m.%Y}"
                         + (" (Prognose)" if not ist[hoch] else "") + ".", hoch, werte[hoch], reihe))
    b.saetze.append(Satz(f"Tiefststand {zahl(werte[tief])} am {tage_[tief]:%d.%m.%Y}"
                         + (" (Prognose)" if not ist[tief] else "") + ".", tief, werte[tief], reihe))
    ist_idx = [i for i in idx if ist[i]]
    if ist_idx and prog:
        a, e = werte[ist_idx[-1]], werte[prog[-1]]
        t = f"Bis zum {tage_[prog[-1]]:%d.%m.%Y} erwartet: {zahl(e)}, "
        t += vergleich(e - a, schwelle_fuer(a, abweichung), "heute") + f" ({zahl(a)})."
        b.saetze.append(Satz(t, prog[-1], e, reihe))
    if kapazitaet:
        reserve = kapazitaet - werte[hoch]
        b.saetze.append(Satz(f"Kapazität {zahl(kapazitaet)}: Reserve mindestens {zahl(reserve)} Plätze."
                             if reserve >= 0 else
                             f"Kapazität {zahl(kapazitaet)}: am {tage_[hoch]:%d.%m.%Y} um {zahl(-reserve)} überschritten.",
                             hoch, werte[hoch], reihe))
    return _begrenzen(b)


# ---- Maßnahmen: Neuanmeldungen je Startwelle (Zählwerte) ----------------------------------------------------------

def wellen(namen: list[str], werte: list[float | None], ist: list[bool], stand: date,
           klein: list[float | None] | None = None, gross: list[float | None] | None = None,
           treffer: tuple[int, int] | None = None, naechstes_jahr: float | None = None,
           abweichung: float | None = None, reihe_ist: str = "Ist", reihe_prog: str = "erwartet") -> Blick:
    """Sätze zu Neuanmeldungen je Halbjahres-Welle. Das Vorjahr derselben Welle liegt zwei Stellen davor."""
    b = Blick()
    n = len(namen)
    prog = [i for i in range(n) if not ist[i] and werte[i] is not None]
    ist_idx = [i for i in range(n) if ist[i] and werte[i] is not None]
    b.stand = f"Datenstand {stand:%d.%m.%Y}" + (f" · ab {namen[prog[0]]} Prognose." if prog else " · alle Werte sind Ist.")
    if ist_idx:
        i = ist_idx[-1]
        t = f"Letzte Welle {namen[i]}: {zahl(werte[i])} Neuanmeldungen"
        if i >= 2 and werte[i - 2] is not None:
            t += f", {vergleich(werte[i] - werte[i - 2], schwelle_fuer(werte[i], abweichung), 'ein Jahr zuvor')}" \
                 f" ({zahl(werte[i - 2])})"
        b.saetze.append(Satz(t + ".", i, werte[i], reihe_ist))
    if prog:
        i = prog[0]
        t = f"Nächste Welle {namen[i]}: "
        if klein and gross and klein[i] is not None and gross[i] is not None:
            t += f"{zahl(klein[i])} bis {zahl(gross[i])} erwartet (Planwert {zahl(werte[i])})."
        else:
            t += f"{zahl(werte[i])} erwartet."
        b.saetze.append(Satz(t, i, werte[i], reihe_prog))
    if naechstes_jahr is not None:
        letzte12 = sum(werte[i] for i in ist_idx[-2:]) if len(ist_idx) >= 2 else None
        t = f"Nächstes Jahr zusammen ≈ {zahl(naechstes_jahr)}"
        if letzte12 is not None:
            t += f", {vergleich(naechstes_jahr - letzte12, schwelle_fuer(letzte12, abweichung), 'in den letzten 12 Monaten')}"
            t += f" ({zahl(letzte12)})"
        b.saetze.append(Satz(t + ".", prog[1] if len(prog) > 1 else (prog[0] if prog else None),
                             werte[prog[1]] if len(prog) > 1 else (werte[prog[0]] if prog else None), reihe_prog))
    if treffer and treffer[1]:
        b.saetze.append(Satz(f"Rückwärtstest: {treffer[0]} von {treffer[1]} vergangenen "
                             f"{'Welle lag' if treffer[1] == 1 else 'Wellen lagen'} in der 80-%-Spanne."))
    return _begrenzen(b)


# ---- Belegung inkl. UWTler und Mieter (0.87) ----------------------------------------------------------------------

def vertrags_grenze(gruppen: list[float], letzter_ist: int | None, anteil: float = .5) -> int | None:
    """Erster Prognosemonat, in dem weniger als die Hälfte der heutigen UWT-/Mieter-Plätze noch gebucht ist – ab hier
    sind die Verträge großteils noch nicht bekannt (kein echter Rückgang, sondern das Ende der bekannten Verträge)."""
    if letzter_ist is None or not 0 <= letzter_ist < len(gruppen) or gruppen[letzter_ist] <= 0:
        return None
    heute = gruppen[letzter_ist]
    return next((i for i in range(letzter_ist + 1, len(gruppen)) if gruppen[i] < anteil * heute), None)


def gruppen(monate_: list[date], ist: list[bool], gesamt: list[float], uwt: list[float], mieter: list[float],
            stand: date, kapazitaet: float | None = None, kont_uwt: float | None = None,
            kont_beide: float | None = None, grenze: int | None = None, reihe: str = "Alle Bewohner") -> Blick:
    """Sätze zur Belegung inkl. UWTler und Mieter: Gesamt gegen Kapazität, je Kontingent, Ende der bekannten Verträge."""
    b = Blick()
    n = len(monate_)
    li = max((i for i in range(n) if ist[i]), default=None)
    prog = [i for i in range(n) if not ist[i]]
    b.stand = _stand(stand, monate_[prog[0]] if prog else None)
    if li is None:
        return b
    g, u, mi = gesamt[li], uwt[li], mieter[li]
    t = f"Heute {zahl(g)} belegt"
    if kapazitaet:
        t += f" von {zahl(kapazitaet)} Plätzen ({round(100 * g / kapazitaet)} %)"
    b.saetze.append(Satz(t + f", davon {zahl(u)} UWTler und {zahl(mi)} Mieter.", li, g, reihe))
    zwoelf = prog[:12]
    for name, kont, werte in (("UWT", kont_uwt, uwt), ("UWT + Mieter", kont_beide, [x + y for x, y in zip(uwt, mieter)])):
        if not kont:
            continue
        drueber = [i for i in zwoelf if werte[i] > kont + .5]
        t = f"Kontingent {name} {zahl(kont)}: heute {zahl(werte[li])} ({round(100 * werte[li] / kont)} %)"
        if drueber:
            t += (f", in {len(drueber)} der nächsten {len(zwoelf)} Monate darüber (zuerst "
                  f"{kurz(monate_[drueber[0]])})")
            b.saetze.append(Satz(t + ".", drueber[0], werte[drueber[0]], "UWTler" if name == "UWT" else "Mieter"))
        else:
            b.saetze.append(Satz(t + f", in den nächsten {len(zwoelf)} Monaten nicht darüber.", li, werte[li],
                                 "UWTler" if name == "UWT" else "Mieter"))
    if grenze is not None:
        b.saetze.append(Satz(f"Bekannte Verträge reichen großteils bis {kurz(monate_[grenze - 1])} – danach sind nur "
                             "Teilnehmende prognostiziert, der Abfall ist kein echter Rückgang.", grenze, gesamt[grenze], reihe))
    return _begrenzen(b)


def _begrenzen(b: Blick) -> Blick:
    b.saetze = b.saetze[:5]
    return b
