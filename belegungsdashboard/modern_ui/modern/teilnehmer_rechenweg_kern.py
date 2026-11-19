"""1.25: Rechenweg der Teilnehmer-Prognose – Schritt für Schritt mit den echten Zahlen. Rein, ohne Oberfläche.

Die Teilnehmer-Prognose ist eine Simulation (``bestand_prognose``): 1000 mögliche Verläufe, je Monat der mittlere
(Median) und die Spanne. Der Rechenweg legt jede Zutat offen – mit den Werten, die das Modell aus den eigenen Daten
gemessen hat:

1. Datenbasis, 2. wer heute schon da ist und wie lange er bleibt (Kaplan-Meier-Verbleibskurve, vorzeitige
Abgangsquote, geplantes Ende), 3. fest angemeldet (künftige Tage im Pivot), 4. Übergänge aus Assessment/Vorbereitung
(Quote, Verzögerung, Zielarten, Szenario), 5. weitere Zugänge aus der Erfahrung (Saisonrate je Kalendermonat ×
Szenario × gemeinsamer Jahresfaktor, Poisson, Kappe), 6. Simulation (Median, Quantile, Mittel ≠ Median), 7. Ergebnis.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from . import bestand_prognose as bp
from .rechenweg_kern import Schritt, _k, _z

MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
Z80 = 1.2816


def _m(d: date) -> str:
    return f"{MONATE[d.month - 1]} {d.year}"


def _p(x: float | None) -> str:
    return "–" if x is None else f"{_z(100 * x, 0)} %"


def rechenweg(md: bp.Modell, e: bp.Ergebnis, art: str | None, k: int, faktor_prozent: float = 0.0) -> list[Schritt]:
    """Alle Schritte für den Messtag ``k`` (1 = erster Monat nach dem Stichtag) und eine Art bzw. alle (None/„Alle“)."""
    if not 1 <= k < len(e.monate):
        return []
    alle = art in (None, "", "Alle")
    arten = list(md.arten) if alle else [art]
    if not alle and art not in md.arten:
        return []
    z = e.zeile(None if alle else art)
    tag = e.monate[k]
    name = "alle Maßnahmen" if alle else bp.kurzname(art)
    faktor = max(0.0, 1 + faktor_prozent / 100)
    fs = [f for f in md.faelle if f.art in arten]
    laufend = [f for f in fs if f.laufend and f.ein <= md.letzter]
    erg: list[Schritt] = []

    # 1 Datenbasis
    erg.append(Schritt(
        "Datenbasis",
        "Aufenthalte aus dem Maßnahmen-Pivot (je Person und Kurs: Eintritt, Ende, geplantes Ende) bis zum Stichtag",
        f"{name}: {len(fs)} Aufenthalte · heute {len(laufend)} in der Maßnahme · Stichtag {md.letzter:%d.%m.%Y} · "
        f"gerechnet für den {tag:%d.%m.%Y} ({k} Monat(e) voraus)",
        [f"Weitere Zugänge werden aus den letzten {bp.JAHRE_HISTORIE} Jahren gemessen."]))

    # 2 Bestand heute → am Messtag
    b_mittel = float(e.zerlegung[0, z, k])
    plan_ende = sum(1 for f in laufend if f.geplant and f.geplant < tag)
    det = []
    for a in arten[:6] if alle else arten:
        kv = md.kurven.get(a)
        if kv is None:
            continue
        q = bp.abgangsquote(md, a)
        s30, s90, s180 = (float(kv.verbleib(t)) for t in (30, 90, 180))
        det.append(f"{bp.kurzname(a)}: Verbleibskurve aus {kv.n} Aufenthalten ({md.kurve_quelle.get(a, '')}, "
                   f"{kv.ereignisse} vorzeitige Abgänge) · noch da nach 30/90/180 Tagen: {_p(s30)} / {_p(s90)} / {_p(s180)}"
                   + (f" · vorzeitige Abgangsquote bis 30 Tage vor dem Soll-Ende ({md.soll.get(a)} Tage): {_p(q)}"
                      if q is not None else ""))
    if alle and len(arten) > 6:
        det.append(f"… und {len(arten) - 6} weitere Arten, je mit eigener Kurve.")
    erg.append(Schritt(
        "Wer heute da ist – und wie lange er bleibt",
        "Kaplan-Meier: S(t) = Π (1 − dᵢ ÷ nᵢ) über alle Tage tᵢ ≤ t mit vorzeitigem Abgang (dᵢ Abgänge, nᵢ noch "
        "beobachtet); laufende Fälle zählen bis heute mit (zensiert). Je Person wird ein vorzeitiges Ende aus der "
        "Kurve gezogen – es gilt das frühere aus geplantem Ende (Pivot, sonst Solldauer) und gezogenem Abgang.",
        f"{len(laufend)} heute da → am {tag:%d.%m.} im Mittel noch {_z(b_mittel)} da"
        + (f" · {plan_ende} enden vorher planmäßig (Pivot)" if plan_ende else ""),
        det))

    # 3 fest angemeldet
    kuenftig = [f for f in fs if f.ein > md.letzter]
    bis = [f for f in kuenftig if f.ein <= tag]
    bek = float(e.zerlegung[1, z, k])
    erg.append(Schritt(
        "Fest angemeldet",
        "Künftige Eintritte mit geplanten Tagen im Maßnahmen-Pivot – mit derselben Verbleibskurve wie oben",
        f"{len(kuenftig)} angemeldet, davon {len(bis)} mit Beginn bis {tag:%d.%m.} → am Messtag im Mittel {_z(bek)} da",
        [", ".join(f"{f.ein:%d.%m.}" for f in sorted(bis, key=lambda f: f.ein)[:12])
         + (" …" if len(bis) > 12 else "")] if bis else []))

    # 4 Übergänge aus Vorstufen
    pip = float(e.zerlegung[2, z, k])
    det = []
    for von, u in md.uebergaenge.items():
        if u.quote is None:
            continue
        ziel_n = sum(u.ziele.values()) or 1
        anteil = 1.0 if alle else u.ziele.get(art, 0) / ziel_n
        if not alle and not anteil:
            continue
        offen = sum(1 for i, f in enumerate(md.faelle) if f.gruppe == von and i not in md.folge and f.ein <= md.letzter
                    and (md.letzter - f.ein).days <= bp.UEBERGANG_TAGE)
        q = min(0.98, u.quote * faktor)
        v = u.verzoegerung
        det.append(f"{von} → {'weiter' if alle else bp.kurzname(art)}: Quote {_z(u.quote, 2)} (aus {u.basis} Fällen mit "
                   f"abgelaufenem Jahr){f' × Szenario {faktor:.2f}' if faktor != 1 else ''} = {_z(q, 2)}"
                   + ("" if alle else f" · davon in diese Art {_p(anteil)}")
                   + (f" · Wartezeit Median {int(np.median(v))} Tage (10–90 %: {int(np.percentile(v, 10))}–"
                      f"{int(np.percentile(v, 90))})" if len(v) else "")
                   + f" · offen (noch ohne Folge): {offen} → erwartet ≈ {offen} × {_z(q, 2)}"
                   + ("" if alle else f" × {_z(anteil, 2)}") + f" = {_z(offen * q * anteil)} (gesamter Horizont)")
    if not alle and art in getattr(md, "startmonate", {}):
        det.append("Startwellen: " + ", ".join(MONATE[m - 1] for m in md.startmonate[art])
                   + " – Wechsler kommen zum nächsten Starttermin.")
    erg.append(Schritt(
        "Übergänge aus Assessment und Vorbereitung",
        "Quote = Anteil der Vorstufen-Fälle, die binnen 365 Tagen in die nächste Stufe wechselten · für Fälle, die "
        "schon eine Weile warten: p = q·(1 − F(gewartet)) ÷ (1 − q·F(gewartet)), F = Verteilung der Wartezeit",
        f"am Messtag im Mittel {_z(pip)} aus der Pipeline da", det))

    # 5 weitere Zugänge (Erfahrung)
    ueb = float(e.zerlegung[3, z, k])
    raten = np.sum([md.raten[a] for a in arten], axis=0) if arten else np.zeros(12)
    mon = [e.monate[i] for i in range(1, k + 1)]
    lam = [float(raten[m.month - 1]) * faktor for m in mon]
    lo_j, hi_j = np.exp(-bp.JAHR_STREUUNG ** 2 / 2 - Z80 * bp.JAHR_STREUUNG), np.exp(-bp.JAHR_STREUUNG ** 2 / 2 + Z80 * bp.JAHR_STREUUNG)
    det = ["Rate je Kalendermonat (Ø je Jahr, ohne Wechsler aus Vorstufen): "
           + ", ".join(f"{MONATE[m.month - 1]} {_z(r_)}" for m, r_ in zip(mon, lam))]
    kap = {a: md.kappe[a] for a in arten if a in md.kappe}
    if kap:
        det.append("Kappe je Startmonat (Kursgröße): " + ", ".join(f"{bp.kurzname(a)} {n}" for a, n in kap.items())
                   + " – darüber gilt es als „Nachfrage über Kapazität“.")
    erg.append(Schritt(
        "Weitere Zugänge aus der Erfahrung",
        "Zugänge im Monat ~ Poisson(λ × Szenario × Jahresfaktor) − schon fest angemeldete Eintritte des Monats · "
        f"λ = Ø der letzten {bp.JAHRE_HISTORIE} Jahre im selben Kalendermonat · Jahresfaktor lognormal, σ = "
        f"{_z(bp.JAHR_STREUUNG, 2)} (Mittel 1) – in einem Lauf für alle Arten gleich: gute und schwache Jahre",
        f"Σλ bis {tag:%d.%m.} = {_z(sum(lam))} Zugänge · Jahresfaktor in 8 von 10 Läufen {_z(lo_j, 2)}–{_z(hi_j, 2)} → "
        f"am Messtag im Mittel noch {_z(ueb)} da (abzüglich vorzeitiger und regulärer Abgänge)", det))

    # 6 Simulation
    med, p10, p90 = float(e.median[z, k]), float(e.p10[z, k]), float(e.p90[z, k])
    p025 = float(e.p025[z, k]) if e.p025 is not None else None
    p975 = float(e.p975[z, k]) if e.p975 is not None else None
    mittel = float(e.zerlegung[:, z, k].sum())
    erg.append(Schritt(
        "Simulation",
        f"{bp.DURCHLAEUFE} Verläufe mit festem Startwert (wiederholbar): jede Zutat wird je Lauf zufällig gezogen und am "
        "Messtag gezählt (anwesend, wenn Eintritt ≤ Tag < Ende) · Planwert = Median, Spanne = 10./90. bzw. 2,5./97,5. "
        "Perzentil",
        f"Mittel = {_z(b_mittel)} + {_z(bek)} + {_z(pip)} + {_z(ueb)} = {_z(mittel)} · Median = {_z(med, 0)} · "
        f"80 %: {_z(p10, 0)}–{_z(p90, 0)}" + (f" · 95 %: {_z(p025, 0)}–{_z(p975, 0)}" if p025 is not None else ""),
        ["Mittel und Median weichen leicht ab, weil die Verteilung schief ist (Zugänge können nicht unter 0 fallen, "
         "nach oben schon). Der Planwert ist der Median: die Hälfte der Läufe liegt darunter, die Hälfte darüber."]))

    # 7 Ergebnis
    sicher = b_mittel + bek
    erg.append(Schritt(
        "Ergebnis",
        "Planwert = Median · „bekannt“ = schon da + fest angemeldet (Mittel)",
        f"{name}, {_m(tag)}: Planwert {_z(med, 0)} · davon bekannt {_z(sicher, 0)} · erwartet dazu "
        f"{_k(max(0.0, med - sicher), 0)}"))
    return erg
