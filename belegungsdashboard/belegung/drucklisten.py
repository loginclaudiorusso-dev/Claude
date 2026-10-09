"""Druckvorlagen (HTML für QTextDocument): Wochenblatt, Zimmerschilder und Schlüsselliste. Rein, ohne Qt."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape

from . import zimmerplan as zp

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

_STIL = """
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.5pt; color: #1f2a2a; }
h1 { font-size: 15pt; margin: 0 0 2px 0; }
h2 { font-size: 11pt; margin: 12px 0 4px 0; color: #0f5e57; }
.klein { color: #5b6b6b; font-size: 8.5pt; }
table.liste { border-collapse: collapse; width: 100%; }
table.liste th { background: #e3efed; text-align: left; padding: 4px 6px; font-size: 8.5pt; }
table.liste td { padding: 4px 6px; border-bottom: 1px solid #d5dede; vertical-align: top; }
.leer { color: #8a9898; }
</style>
"""


def _kurz(zid: str) -> str:
    return zid.removeprefix("GS-")


def _personen_text(bs: list[zp.Belegung], namen: bool) -> str:
    teile = []
    for b in bs:
        wer = escape(b.name) if namen else escape(zp.GRUPPE_LABEL.get(zp.belegung_gruppe(b) or "", "") or "Person")
        if b.massnahme and namen:
            wer += f" <span class='klein'>({escape(b.massnahme)})</span>"
        if b.art == "geplant":
            wer += " <span class='klein'>· geplant</span>"
        teile.append(wer)
    return "<br>".join(teile)


def wochenblatt_html(lage: zp.Lage, reinigungen: list[zp.Reinigung], montag: date, namen: bool = True,
                     stand: str = "") -> str:
    """Je Tag eine Tabelle: Zimmer | Abreise | Anreise | Reinigung – für Hausmeister und Reinigung."""
    sonntag = montag + timedelta(days=6)
    teile = [_STIL, f"<h1>Wochenblatt KW {montag.isocalendar()[1]} · {montag:%d.%m.} – {sonntag:%d.%m.%Y}</h1>",
             "<div class='klein'>Internat Goslar · An- und Abreisen, Reinigungen"
             + (f" · Gebäudeplan Stand {escape(stand)}" if stand else "") + "</div>"]
    rein: dict[tuple[date, str], zp.Reinigung] = {(r.tag, r.zimmer.id): r for r in reinigungen}
    for i in range(7):
        tag = montag + timedelta(days=i)
        zeilen: dict[str, dict] = {}
        for zid, bs in lage.belegungen.items():
            for b in bs:
                if b.art not in ("belegt", "geplant") or b.name == zp.PIVOT_NAME:
                    continue
                if b.von == tag:
                    zeilen.setdefault(zid, {"an": [], "ab": []})["an"].append(b)
                if b.bis == tag:
                    zeilen.setdefault(zid, {"an": [], "ab": []})["ab"].append(b)
        for (t, zid), r in rein.items():
            if t == tag:
                zeilen.setdefault(zid, {"an": [], "ab": []})
        teile.append(f"<h2>{WOCHENTAGE[i]}, {tag:%d.%m.%Y}</h2>")
        if not zeilen:
            teile.append("<div class='leer'>keine An- oder Abreisen, keine Reinigung</div>")
            continue
        teile.append("<table class='liste' width='100%' cellspacing='0'><tr><th width='10%'>Zimmer</th>"
                     "<th width='30%'>Abreise</th><th width='30%'>Anreise</th><th>Reinigung</th></tr>")
        for zid in sorted(zeilen, key=lambda k: (zp._haus_sort(k.split("-")[1]), k)):
            r = rein.get((tag, zid))
            reinigung = ""
            if r:
                reinigung = escape(r.art)
                if r.frist is not None:
                    frist = f"{WOCHENTAGE[r.frist.weekday()][:2]} {r.frist:%d.%m.}"
                    reinigung += (" – <b>sofort</b>" if r.frist <= tag else f" – sauber bis {frist}")
            teile.append(f"<tr><td><b>{_kurz(zid)}</b></td><td>{_personen_text(zeilen[zid]['ab'], namen)}</td>"
                         f"<td>{_personen_text(zeilen[zid]['an'], namen)}</td><td>{reinigung}</td></tr>")
        teile.append("</table>")
    return "".join(teile)


@dataclass
class Schild:
    zimmer: str                      # Zimmer-ID
    lage: str                        # „Haus 3.2 · 2. OG · West“
    namen: list[str] = field(default_factory=list)
    gruppe: str = ""                 # z. B. „UWT CUK25“
    von: date | None = None
    bis: date | None = None


def schilder(zuteilungen: list[zp.Zuteilung]) -> list[Schild]:
    """Zuteilungen je Zimmer zusammenfassen (Doppelzimmer: beide Namen auf ein Schild)."""
    je: dict[str, Schild] = {}
    for zt in zuteilungen:
        if zt.zimmer is None:
            continue
        s = je.setdefault(zt.zimmer.id, Schild(zt.zimmer.id, zp.flur_text(zt.zimmer), gruppe=zt.bedarf.massnahme,
                                               von=zt.bedarf.von, bis=zt.bedarf.bis))
        s.namen.append(zt.bedarf.name)
        s.von, s.bis = min(s.von, zt.bedarf.von), max(s.bis, zt.bedarf.bis)
    return sorted(je.values(), key=lambda s: (zp._haus_sort(s.zimmer.split("-")[1]), s.zimmer))


def zimmerschilder_html(liste: list[Schild]) -> str:
    """Ein Schild je Seite: große Zimmernummer, Namen, Gruppe, Zeitraum."""
    teile = ["<style>body { font-family: 'Segoe UI', Arial, sans-serif; color: #1f2a2a; }</style>"]
    for i, s in enumerate(liste):
        umbruch = " style='page-break-before: always'" if i else ""
        namen = "<br>".join(escape(_name_lesbar(n)) for n in s.namen)
        zeit = f"{s.von:%d.%m.} – {s.bis:%d.%m.%Y}" if s.von and s.bis else ""
        teile.append(f"<div{umbruch}><p align='center' style='font-size: 80pt; font-weight: 700; margin: 30px 0 0 0'>"
                     f"{_kurz(s.zimmer)}</p>"
                     f"<p align='center' style='font-size: 14pt; color: #5b6b6b; margin: 0 0 30px 0'>{escape(s.lage)}</p>"
                     f"<p align='center' style='font-size: 36pt; font-weight: 600; margin: 0'>{namen}</p>"
                     f"<p align='center' style='font-size: 16pt; color: #5b6b6b; margin: 24px 0 0 0'>"
                     f"{escape(s.gruppe)}{' · ' if s.gruppe and zeit else ''}{zeit}</p></div>")
    return "".join(teile)


def _name_lesbar(name: str) -> str:
    """„Meier, Anna“ → „Anna Meier“."""
    if "," in name:
        nach, vor = (t.strip() for t in name.split(",", 1))
        return f"{vor} {nach}".strip()
    return name


def schluesselliste_html(liste: list[Schild], titel: str) -> str:
    teile = [_STIL, f"<h1>Schlüsselliste · {escape(titel)}</h1>",
             "<div class='klein'>Ausgabe und Rückgabe bitte abzeichnen.</div><br>",
             "<table class='liste' width='100%' cellspacing='0'><tr><th width='8%'>Zimmer</th><th width='22%'>Name</th>"
             "<th width='10%'>Zeitraum</th><th width='9%'>Schlüssel</th><th width='9%'>Ausgabe</th>"
             "<th width='15%'>Unterschrift</th><th width='9%'>Rückgabe</th><th>Unterschrift</th></tr>"]
    for s in liste:
        zeit = f"{s.von:%d.%m.}–{s.bis:%d.%m.}" if s.von and s.bis else ""
        for n in s.namen:
            teile.append(f"<tr><td><b>{_kurz(s.zimmer)}</b></td><td>{escape(n)}</td><td>{zeit}</td>"
                         "<td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;<br>&nbsp;</td></tr>")
    teile.append("</table>")
    return "".join(teile)


def anreiseliste_html(zuteilungen: list[zp.Zuteilung], titel: str) -> str:
    """Anreiseliste zum Ausdrucken: Name, Maßnahme, Zimmer, Anreise bis Abreise – nach Namen sortiert."""
    zeilen = sorted(zuteilungen, key=lambda zt: zt.bedarf.name.lower())
    ohne = sum(1 for zt in zeilen if zt.zimmer is None)
    teile = [_STIL, f"<h1>Anreiseliste · {escape(titel)}</h1>",
             f"<div class='klein'>Internat Goslar · {len(zeilen)} Personen"
             + (f" · <b>{ohne} noch ohne Zimmer</b>" if ohne else "")
             + " · ≈ = Abreise angenommen</div><br>",
             "<table class='liste' width='100%' cellspacing='0'><tr><th width='5%'>Nr</th><th width='28%'>Name</th>"
             "<th width='21%'>Maßnahme</th><th width='10%'>Zimmer</th><th width='24%'>Zeitraum</th><th>Notiz</th></tr>"]
    for i, zt in enumerate(zeilen, start=1):
        b = zt.bedarf
        zimmer = f"<b>{_kurz(zt.zimmer.id)}</b>" if zt.zimmer else "<i>noch keins</i>"
        zeit = f"{b.von:%d.%m.%Y} – {'≈ ' if b.bis_angenommen else ''}{b.bis:%d.%m.%Y}"
        teile.append(f"<tr><td>{i}</td><td>{escape(b.name)}</td><td>{escape(b.massnahme)}</td><td>{zimmer}</td>"
                     f"<td nowrap>{zeit}</td><td>&nbsp;</td></tr>")
    teile.append("</table>")
    return "".join(teile)
