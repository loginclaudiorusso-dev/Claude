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


# ---- „Einfach“ für die Geschäftsführung (0.89): Aussage als Überschrift, höchstens drei Zahlen, Füllstand ---------

@dataclass
class Leitung:
    titel: str = ""                                   # die Aussage – sie IST die Überschrift
    zahlen: list = field(default_factory=list)        # (Bezeichnung, Zahl, Zusatz) – höchstens drei
    balken: list = field(default_factory=list)        # (Monat, Wert, Anteil an der Kapazität oder None, Ist?)
    unsicher: str = ""                                # Unsicherheit als Satz
    stand: str = ""


def leitung(ort: str, monate_: list[date], erwartet: list[float | None], ist: list[bool], stand: date,
            kapazitaet: float | None = None, unten80: list[float | None] | None = None,
            oben80: list[float | None] | None = None, kritisch: float = .85, monate_vor: int = 6,
            oben95: list[float | None] | None = None) -> Leitung:
    """Eine Aussage für die Leitung: reicht der Platz? Grundlage sind die geprüften Monate (bis 12 voraus); gezeigt
    werden heute und die nächsten ``monate_vor`` Monate als Füllstand gegen „voll“."""
    n = len(monate_)
    li = max((i for i in range(n) if ist[i] and erwartet[i] is not None), default=None)
    prog = [i for i in range(n) if not ist[i] and erwartet[i] is not None]
    lg = Leitung(stand=_stand(stand, monate_[prog[0]] if prog else None))
    if li is None and not prog:
        lg.titel = f"{ort}: noch keine Zahlen."
        return lg
    o = lambda i: (oben80[i] if oben80 and oben80[i] is not None else erwartet[i])  # noqa: E731
    u = lambda i: (unten80[i] if unten80 and unten80[i] is not None else erwartet[i])  # noqa: E731
    zwoelf = prog[:12]
    if kapazitaet:
        eng = next((i for i in zwoelf if o(i) >= kritisch * kapazitaet), None)
        gesamt = ort.strip().lower() in ("gesamt", "alle", "alle häuser")
        wo = "Insgesamt" if gesamt else f"In {ort}"
        spitze = max(o(i) for i in zwoelf) if zwoelf else None
        if eng is None:
            bis = monate_[zwoelf[-1]] if zwoelf else stand
            lg.titel = (f"Insgesamt gibt es bis {lang(bis, stand)} voraussichtlich genug freie Plätze." if gesamt
                        else f"{ort} hat bis {lang(bis, stand)} voraussichtlich genug freie Plätze.")
        elif eng == zwoelf[0]:
            lg.titel = (f"{wo} ist es schon jetzt eng – voraussichtlich bis zu {zahl(spitze)} von {zahl(kapazitaet)} "
                        "Plätzen belegt.")
        else:
            lg.titel = (f"{wo} wird es ab {lang(monate_[eng], stand)} eng – voraussichtlich bis zu {zahl(spitze)} von "
                        f"{zahl(kapazitaet)} Plätzen belegt.")
    elif zwoelf:
        lg.titel = (f"{ort}: in den nächsten {len(zwoelf[:monate_vor])} Monaten {zahl(min(erwartet[i] for i in zwoelf[:monate_vor]))} "
                    f"bis {zahl(max(erwartet[i] for i in zwoelf[:monate_vor]))} belegt erwartet.")
    else:
        lg.titel = f"{ort}: heute {zahl(erwartet[li])} belegt."
    if li is not None:
        lg.zahlen.append(("Heute belegt", zahl(erwartet[li]), f"von {zahl(kapazitaet)} Plätzen" if kapazitaet else kurz(monate_[li])))
    if zwoelf:
        hoch = max(zwoelf, key=lambda i: erwartet[i])
        lg.zahlen.append(("Höchstwert erwartet", zahl(erwartet[hoch]), lang(monate_[hoch], stand)))
        if kapazitaet:
            # 0.90: „mindestens“ nur mit der 95-%-Grenze (in 19 von 20 Monaten nicht überschritten); hi80 wäre in jedem
            # 10. Monat zu optimistisch – über 12 Monate noch öfter.
            o95 = lambda i: (oben95[i] if oben95 and oben95[i] is not None else o(i))  # noqa: E731
            frei = kapazitaet - max(o95(i) for i in zwoelf)
            sicher = "in 19 von 20 Fällen" if oben95 else "in 9 von 10 Fällen"
            lg.zahlen.append(("Freie Plätze, ungünstiger Fall", zahl(max(frei, 0)), f"{sicher} mindestens so viele"
                              if frei >= 0 else f"{zahl(-frei)} zu wenig möglich"))
    zeig = ([li] if li is not None else []) + prog[:monate_vor]
    lg.balken = [(kurz(monate_[i]) if i != li else "heute", erwartet[i], erwartet[i] / kapazitaet if kapazitaet else None,
                  i == li) for i in zeig]
    if prog:
        i = prog[min(monate_vor, len(prog)) - 1]
        lg.unsicher = (f"In 8 von 10 Fällen liegt die Belegung im {lang(monate_[i], stand)} zwischen {zahl(u(i))} und "
                       f"{zahl(o(i))} – je weiter voraus, desto breiter.")
    return lg


def _begrenzen(b: Blick) -> Blick:
    b.saetze = b.saetze[:5]
    return b


# ---- 0.91: Leitungsansicht der Belegungsprognose (Entwurf „Heute neu gedacht“, Seite 4) ---------------------------

@dataclass
class GfZahl:
    titel: str
    wert: str
    einheit: str
    zusatz: str


@dataclass
class GfMarke:
    index: int
    wert: float
    text: str
    unter: str = ""


@dataclass
class Gf:
    titel: str = ""
    untertitel: str = ""
    zahlen: list = field(default_factory=list)      # GfZahl – genau vier
    marken: list = field(default_factory=list)      # GfMarke – Beschriftungen im Diagramm
    warn: float | None = None                       # Warnschwelle in Plätzen
    luft: float | None = None                       # Abstand Höchstwert → Warnschwelle (gerundet)
    luft_index: int | None = None
    prognose_ab: int | None = None                  # erster Prognosemonat (Index)


def _rund(x: float, auf: int = 10) -> int:
    return int(round(x / auf) * auf)


def gf(monate_: list[date], werte: list[float | None], ist: list[bool], stand: date, kapazitaet: float | None = None,
       unten80: list | None = None, oben80: list | None = None, vorjahr: list | None = None, mae_1m: float | None = None,
       kritisch: float = .85, monate_vor: int = 12) -> Gf:
    """Eine Aussage, ein Untertitel, vier Zahlen und wenige Beschriftungen – alles aus den Rechenkernen, nur in Worten."""
    n = len(monate_)
    g = Gf()
    li = max((i for i in range(n) if ist[i] and werte[i] is not None), default=None)
    prog = [i for i in range(n) if not ist[i] and werte[i] is not None][:monate_vor]
    g.prognose_ab = prog[0] if prog else None
    o = lambda i: (oben80[i] if oben80 and oben80[i] is not None else werte[i])  # noqa: E731
    u = lambda i: (unten80[i] if unten80 and unten80[i] is not None else werte[i])  # noqa: E731
    if not prog:
        g.titel = f"Heute {zahl(werte[li])} Plätze belegt." if li is not None else "Noch keine Zahlen."
        return g
    hoch = max(prog, key=lambda i: werte[i])
    tief = min(prog, key=lambda i: werte[i])
    k = kapazitaet
    g.warn = kritisch * k if k else None
    eng = next((i for i in prog if g.warn is not None and o(i) >= g.warn), None)
    if k and eng is None:
        wort = "reichlich" if max(o(i) for i in prog) < .7 * k else "genug"
        g.titel = f"Es bleibt voraussichtlich {wort} Platz: rund {zahl(_rund(werte[hoch]))} von {zahl(k)} Plätzen belegt"
    elif k:
        g.titel = (f"Es wird ab {lang(monate_[eng], stand)} eng: voraussichtlich bis zu {zahl(max(o(i) for i in prog))} "
                   f"von {zahl(k)} Plätzen belegt")
    else:
        g.titel = f"Voraussichtlich rund {zahl(_rund(werte[hoch]))} Plätze belegt"
    satz = (f"In den nächsten {len(prog)} Monaten schwankt die Belegung zwischen {zahl(werte[tief])} im "
            f"{lang(monate_[tief], stand)} und {zahl(werte[hoch])} im {lang(monate_[hoch], stand)}.")
    if g.warn is not None:
        satz += (f" Die Warnschwelle von {round(100 * kritisch)} % wird nicht erreicht." if eng is None else
                 f" Die Warnschwelle von {round(100 * kritisch)} % ({zahl(g.warn)} Plätze) kann ab "
                 f"{lang(monate_[eng], stand)} erreicht werden.")
    g.untertitel = satz
    # vier Zahlen
    if li is not None:
        vj = werte[li - 12] if li >= 12 and werte[li - 12] is not None else (vorjahr[li] if vorjahr and vorjahr[li] is not None else None)
        d = None if vj is None else werte[li] - vj
        g.zahlen.append(GfZahl("Heute belegt", zahl(werte[li]), f"· {round(100 * werte[li] / k)} %" if k else "Plätze",
                               "" if d is None else (f"{zahl(abs(d))} {'mehr' if d > 0 else 'weniger'} als vor einem Jahr"
                                                     if round(d) else "so viele wie vor einem Jahr")))
    i0 = prog[0]
    g.zahlen.append(GfZahl("Nächster Monat erwartet", zahl(werte[i0]), f"· {round(100 * werte[i0] / k)} %" if k else "Plätze",
                           f"wahrscheinlich zwischen {zahl(u(i0))} und {zahl(o(i0))}"))
    if k:
        g.zahlen.append(GfZahl("Knappster Monat", zahl(max(k - werte[hoch], 0)), "frei",
                               f"{lang(monate_[hoch], stand)} · sonst immer mehr"))
    g.zahlen.append(GfZahl("So gut lag die Prognose bisher", f"± {zahl(mae_1m)}" if mae_1m is not None else "–", "Plätze",
                           "im Mittel, einen Monat voraus" if mae_1m is not None else "noch kein Rückblick möglich"))
    # Beschriftungen: nächster Monat, Tiefpunkt der Prognose (Sommertief?), letzter Monat
    g.marken.append(GfMarke(i0, werte[i0], f"{MONATE_LANG[monate_[i0].month - 1]} {monate_[i0].year}: {zahl(werte[i0])}"))
    if tief != i0:
        fenster = [werte[j] for j in range(max(0, tief - 18), tief - 6) if werte[j] is not None]
        sommer = (monate_[tief].month in (6, 7, 8) and tief >= 12 and werte[tief - 12] is not None and bool(fenster)
                  and werte[tief - 12] <= min(fenster))         # voriges Jahr lag der Tiefpunkt im selben Monat
        g.marken.append(GfMarke(tief, werte[tief], f"{MONATE_LANG[monate_[tief].month - 1]} {monate_[tief].year}: "
                                f"{zahl(werte[tief])}", "Sommertief wie jedes Jahr" if sommer else ""))
    letzt = prog[-1]
    if letzt not in (i0, tief):
        g.marken.append(GfMarke(letzt, werte[letzt], f"{MONATE_KURZ[monate_[letzt].month - 1]} {monate_[letzt].year}: "
                                f"rund {zahl(_rund(werte[letzt]))}"))
    if g.warn is not None and eng is None:
        g.luft = _rund(g.warn - werte[hoch])
        g.luft_index = i0 + (len(prog) - 1) // 3 if len(prog) > 3 else i0
    return g
