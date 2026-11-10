"""Diagramme bedienen (0.75) – gilt für JEDES Diagramm der Oberfläche.

* **Größe ziehen:** Unter jedem Diagramm liegt eine Leiste; an ihr zieht man das Diagramm höher oder flacher.
  Die Höhe wird je Ansicht gemerkt (Doppelklick: zurück auf Standard). Das Detailpanel rechts lässt sich an seiner
  linken Kante breiter oder schmaler ziehen.
* **Diagramm ⇄ Tabelle:** dieselben Zahlen als Tabelle (für Vorleseprogramme, zum Nachlesen) und „Kopieren“ für Excel.
* **Klick auf eine Stelle** (Monat, Woche …) öffnet rechts das Detailpanel mit allen Werten dieser Stelle und der
  Berechnung dahinter.
* **ƒx Berechnung:** blendet unter dem Diagramm ein, wie die Zahlen gerechnet werden (Kennzahlen-Katalog) – in Worten,
  als Formel mit echten Werten und mit der Grundlage. Offen/zu wird gemerkt.
"""

from __future__ import annotations

from nicegui import ui

from . import kennzahlen_katalog as kk


def anbinden(a, chart, details=None) -> None:
    """Klick auf eine Stelle der x-Achse → Detailpanel. ``details(index)`` liefert optional die Berechnung mit
    Werten: Liste aus (Schlüssel, Werte, [(Text, Aktion)])."""
    chart.classes(add="m-dg")
    chart.on("m_achse", lambda e: _geklickt(a, chart, e.args, details), ["index"])


def _geklickt(a, chart, args, details) -> None:
    try:
        index = int((args or {}).get("index"))
    except (TypeError, ValueError):
        return
    opt = chart.options
    werte = kk.werte_an(opt, index)
    if not werte:
        return
    stelle = kk.kategorie(opt, index)

    def bauen():
        with ui.element("div").classes("m-dg-werte"):
            for name, text in werte:
                ui.label(name).classes("m-zweite")
                ui.label(text).classes("m-name")
        bloecke = details(index) if details else [(kk.REIHE[n], {}, []) for n, _t in werte if n in kk.REIHE]
        gesehen = set()
        for schluessel, w, aktionen in bloecke:
            if schluessel in gesehen or schluessel not in kk.KATALOG:
                continue
            gesehen.add(schluessel)
            block(schluessel, w, aktionen)
    a.panel(f"{stelle} · Werte und Berechnung", bauen)


def block(schluessel: str, werte: dict | None = None, aktionen: list | None = None) -> None:
    """Eine Kennzahl in drei Ebenen; Aktionen als anklickbare Werte („12 nicht nutzbar“ → Liste)."""
    k = kk.KATALOG[schluessel]
    with ui.element("section").classes("m-fxk"):
        with ui.element("div").classes("m-fxk-kopf"):
            ui.html('<b class="m-fx-zeichen">ƒx</b>', sanitize=False)
            ui.label(k.name).classes("m-name")
        with ui.element("div").classes("m-fxk-raster"):
            ui.label("In Worten").classes("m-zweite")
            ui.label(k.satz)
            ui.label("Formel").classes("m-zweite")
            with ui.element("div"):
                ui.label(k.formel)
                if werte:
                    ui.label("→ " + kk.einsetzen(schluessel, werte)).classes("m-fx-werte")
            ui.label("Grundlage").classes("m-zweite")
            ui.label(k.grundlage).classes("m-zweite")
        if aktionen:
            with ui.element("div").classes("m-fx-pillen"):
                for text, fn in aktionen:
                    b = ui.element("button").classes("m-fx-pille")
                    with b:
                        ui.label(text)
                    b.on("click", fn)


def fx_kasten(eintraege: list) -> None:
    """„ƒx Berechnung“-Kasten unter einem Diagramm (zu, bis man ƒx anklickt). ``eintraege``: (Schlüssel, Werte,
    Aktionen)."""
    with ui.element("div").classes("m-fx"):
        with ui.element("div").classes("m-fx-raster"):
            for schluessel, w, akt in eintraege:
                if schluessel in kk.KATALOG:
                    block(schluessel, w, akt)


def zimmer_liste_panel(a, titel: str, zeilen: list[tuple[str, str, str]]) -> None:
    """Liste hinter einer Zahl im Detailpanel: (Zimmer, Zustand, Text)."""
    def bauen():
        if not zeilen:
            ui.label("Keine Einträge.").classes("m-ptext")
        for zimmer, art, text in zeilen:
            with ui.element("div").classes("m-dg-liste"):
                ui.label(zimmer).classes("m-name")
                ui.label(art).classes("m-zweite")
                ui.label(text).classes("m-zweite")
    a.panel(titel, bauen)


CSS = r"""
/* ---------- 0.75 Diagramme: Leiste unter jedem Diagramm (Griff, Tabelle, ƒx, Kopieren) ---------- */
.m-dg-fuss { display: flex; align-items: center; gap: 6px; height: 30px; padding: 0 2px; font-size: 12px; color: var(--text3);
  user-select: none; flex: none; }
.m-dg-griff { flex: 1; display: flex; align-items: center; gap: 6px; height: 100%; cursor: ns-resize; border-top: 2px solid transparent; }
.m-dg-griff:hover { color: var(--akzent); border-top-color: color-mix(in srgb, var(--akzent) 45%, transparent); }
.m-dg-griff i { font-family: "Material Icons Outlined"; font-style: normal; font-size: 16px; font-feature-settings: "liga"; }
.m-dg-knopf { height: 24px; padding: 0 8px; border: 1px solid var(--rand); border-radius: 4px; background: var(--fl);
  color: var(--text2); font: inherit; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
.m-dg-knopf i { font-family: "Material Icons Outlined"; font-style: normal; font-size: 15px; font-feature-settings: "liga"; }
.m-dg-knopf:hover { border-color: var(--akzent); color: var(--akzent); }
.m-dg-knopf.an { background: color-mix(in srgb, var(--akzent) 12%, var(--fl)); border-color: var(--akzent); color: var(--akzent); font-weight: 600; }
.m-dg-knopf b { font-family: Georgia, serif; font-style: italic; }
.m-dg-gruppe { display: inline-flex; }
.m-dg-gruppe .m-dg-knopf:first-child { border-radius: 4px 0 0 4px; } .m-dg-gruppe .m-dg-knopf:last-child { border-radius: 0 4px 4px 0; margin-left: -1px; }
.m-dg-tab { overflow: auto; border: 1px solid var(--rand); border-radius: 6px; background: var(--fl); }
.m-dg-tab table { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }
.m-dg-tab th { position: sticky; top: 0; background: var(--fl2, var(--fl)); text-align: right; padding: 6px 10px; font-weight: 600;
  border-bottom: 1px solid var(--rand); white-space: nowrap; }
.m-dg-tab th:first-child, .m-dg-tab td:first-child { text-align: left; }
.m-dg-tab td { padding: 4px 10px; text-align: right; border-bottom: 1px solid var(--rand); white-space: nowrap; }
.m-dg-tab tr:hover td { background: color-mix(in srgb, var(--akzent) 6%, transparent); }
.m-chart.m-dg { cursor: pointer; }
/* ƒx Berechnung */
.m-fx { display: none; margin-top: 8px; }
.m-fx.offen { display: block; }
.m-fx-raster { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; }
.m-fxk { border: 1px solid var(--rand); border-radius: 8px; background: var(--fl); padding: 10px 14px; display: flex; flex-direction: column; gap: 6px; }
.m-fxk-kopf { display: flex; align-items: center; gap: 8px; }
.m-fx-zeichen { font-family: Georgia, serif; font-style: italic; color: var(--akzent); }
.m-fxk-raster { display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 4px 12px; font-size: 13px; line-height: 18px; }
.m-fx-werte { font-weight: 600; margin-top: 2px; }
.m-fxk-raster > * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
.m-fx-pillen { display: flex; flex-wrap: wrap; gap: 6px; }
.m-fx-pille { height: 26px; padding: 0 10px; border-radius: 13px; border: 1px solid color-mix(in srgb, var(--akzent) 45%, transparent);
  background: color-mix(in srgb, var(--akzent) 10%, var(--fl)); color: var(--akzent); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.m-fx-pille:hover { background: var(--akzent); color: var(--akzent-text, #fff); }
.m-dg-werte { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px 12px; padding-bottom: 10px; border-bottom: 1px solid var(--rand); }
.m-dg-werte .m-name { text-align: right; font-variant-numeric: tabular-nums; }
.m-dg-liste { display: grid; grid-template-columns: 76px 110px minmax(0, 1fr); gap: 8px; align-items: center; min-height: 34px;
  border-bottom: 1px solid var(--rand); }
/* Engpässe: Heatmap Woche × Art */
.m-heat-block { margin-bottom: 12px; }
.m-heat-kopf { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.m-heat-kopf .m-dg-knopf { margin-left: auto; }
.m-heat { display: grid; gap: 3px; font-size: 13px; overflow-x: auto; }
.m-heat-kw { text-align: center; color: var(--text2); font-size: 12px; white-space: nowrap; }
.m-heat-name { color: var(--text2); align-self: center; white-space: nowrap; }
.m-heat-zelle { height: 32px; border: 0; border-radius: 4px; font: inherit; font-weight: 600; cursor: pointer; display: flex;
  align-items: center; justify-content: center; gap: 3px; color: var(--text);
  background: color-mix(in srgb, var(--akzent) calc(8% + var(--anteil, 0) * 42%), var(--fl)); font-variant-numeric: tabular-nums; }
.m-heat-zelle .q-icon { font-size: 14px; }
.m-heat-zelle.warn { background: #FFF3DD; color: #8A4B00; }
.m-heat-zelle.krit { background: #FDE7E7; color: #A4161A; }
.m-heat-zelle:hover, .m-heat-zelle:focus-visible { outline: 2px solid var(--akzent); outline-offset: 1px; }
/* Detailpanel: Breite an der linken Kante ziehen */
.m-panel-griff { position: absolute; left: -3px; top: 0; bottom: 0; width: 7px; cursor: ew-resize; z-index: 6; }
.m-panel-griff:hover { background: color-mix(in srgb, var(--akzent) 35%, transparent); }
/* Office: Diagramme groß – der Prognose-Graph füllt fast die ganze Höhe, die Kennzahlen darunter erreicht man per Scrollen */
body.lay-office .m-chart { height: 380px !important; }
body.lay-office .m-mn-kachel .m-chart { height: 220px !important; }
body.lay-office .m-ex.b-dashboard { height: auto !important; }
body.lay-office .m-ex.b-dashboard > .m-xg { flex: none !important; }
body.lay-office .m-ex.b-dashboard .m-chart.m-xg-chart, body.lay-office .m-xsz .m-xg .m-chart.m-xg-chart {
  flex: none !important; height: max(320px, calc(100vh - var(--af-oben, 216px) - 390px)) !important; }
/* 0.78: Dashboard wieder auf EINEN Blick – Graph + kompakte Kennzahl-Karten ohne Scrollen (Erklärtext als Tooltip) */
body.lay-office .m-ex.b-dashboard .m-xk-hinweis { display: none; }
body.lay-office .m-ex.b-dashboard .m-xk-karte { cursor: help; }
/* ---------- 0.87 Diagramm-Karte ---------- */
.m-dk { container-type: inline-size; position: relative; display: flex; flex-direction: column; gap: 8px; min-width: 0;
  border: 1px solid var(--rand); border-radius: 10px; background: var(--fl); padding: 12px 14px 12px; }
.m-dk-kopf { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.m-dk-titelblock { flex: 1 1 260px; min-width: 0; }
.m-dk-titel { font-size: 15px; font-weight: 600; color: var(--text); line-height: 20px; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.m-dk-titel [data-titel] { display: none; }
.m-xg[data-tab="trend"][data-ansicht="kurve"] .m-dk-titel [data-titel="trend"],
.m-xg[data-tab="trend"][data-ansicht="status"] .m-dk-titel [data-titel="trend-status"],
.m-xg[data-tab="trend"][data-ansicht="standorte"] .m-dk-titel [data-titel="trend-standorte"],
.m-xg[data-tab="reserve"] .m-dk-titel [data-titel="reserve"], .m-xg[data-tab="jahr"] .m-dk-titel [data-titel="jahr"] { display: inline; }
/* 0.87: Schalter „inkl. UWTler und Mieter“ / „Standorte einzeln“ statt Segment + Hinweis-Chip */
.m-xg-schalter { height: 32px; padding: 0 12px; border: 1px solid var(--rand); border-radius: 16px; background: var(--fl);
  color: var(--text2); font: inherit; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.m-xg-schalter .q-icon { font-size: 17px; }
.m-xg-schalter:hover { border-color: var(--akzent); color: var(--akzent); }
.m-xg-schalter.an { background: color-mix(in srgb, var(--akzent) 14%, var(--fl)); border-color: var(--akzent); color: var(--akzent);
  font-weight: 600; }
.m-xg-schalter.an::before { content: "✓"; font-weight: 700; }
.m-dk-unter { font-size: 12px; color: var(--text3); line-height: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: block; }
.m-dk-knoepfe { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; justify-content: flex-end; margin-left: auto; }
.m-dk-knoepfe .m-dg-knopf { height: 28px; font-size: 13px; }
.m-dk-koerper { display: grid; grid-template-columns: minmax(0, 3fr) minmax(240px, 300px); gap: 14px; align-items: stretch; }
.m-dk.blick-zu .m-dk-koerper { grid-template-columns: minmax(0, 1fr) 34px; }
.m-dk-flaeche { position: relative; min-width: 0; }
.m-dk-flaeche .m-chart { width: 100%; }
.m-dk-griff { position: absolute; right: 0; bottom: 0; width: 18px; height: 18px; cursor: nwse-resize; opacity: .55;
  background: linear-gradient(135deg, transparent 0 55%, var(--text3) 55% 62%, transparent 62% 72%, var(--text3) 72% 79%, transparent 79%); }
.m-dk-griff:hover { opacity: 1; }
.m-dk-blick { min-width: 0; border-left: 1px solid var(--rand); padding-left: 14px; display: flex; flex-direction: column; gap: 6px;
  font-size: 13px; line-height: 1.45; color: var(--text); }
.m-dk-blick-kopf { display: flex; align-items: center; gap: 6px; }
.m-dk-blick-titel { font-size: 13px; font-weight: 600; color: var(--text2); }
.m-dk-zu { margin-left: auto; width: 26px; height: 26px; border: 0; border-radius: 6px; background: transparent; color: var(--text3);
  cursor: pointer; display: inline-flex; align-items: center; justify-content: center; }
.m-dk-zu:hover { background: var(--fl2, var(--bg)); color: var(--text); }
.m-dk-saetze { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.m-dk-satz { padding: 6px 8px; border-radius: 6px; cursor: pointer; border-left: 3px solid transparent; }
.m-dk-satz.still { cursor: default; }
.m-dk-satz:not(.still):hover { background: color-mix(in srgb, var(--akzent) 7%, transparent); }
.m-dk-satz.an { background: color-mix(in srgb, var(--akzent) 13%, transparent); border-left-color: var(--akzent); }
.m-dk-satz:focus-visible { outline: 2px solid var(--akzent); outline-offset: 1px; }
.m-dk-monat:empty { display: none; }
.m-dk-monat { border-top: 1px solid var(--rand); padding-top: 8px; display: flex; flex-direction: column; gap: 8px; }
.m-dk-monat-kopf { display: flex; align-items: center; }
.m-dk-monat .m-fxk-raster { grid-template-columns: 76px minmax(0, 1fr); }
.m-dk-stand { margin-top: auto; padding-top: 8px; border-top: 1px solid var(--rand); font-size: 12px; color: var(--text3);
  white-space: normal !important; }
.m-dk.blick-zu .m-dk-blick > :not(.m-dk-blick-kopf) { display: none; }
.m-dk.blick-zu .m-dk-blick-titel { writing-mode: vertical-rl; transform: rotate(180deg); }
.m-dk.blick-zu .m-dk-blick-kopf { flex-direction: column-reverse; gap: 10px; }
.m-dk.blick-zu .m-dk-blick { padding-left: 4px; }
.m-dk.blick-zu .m-dk-zu .q-icon { transform: rotate(180deg); }
.m-dk-fx .m-fx { margin-top: 0; }
@container (max-width: 760px) {
  .m-dk-koerper, .m-dk.blick-zu .m-dk-koerper { grid-template-columns: minmax(0, 1fr); }
  .m-dk-blick { border-left: 0; border-top: 1px solid var(--rand); padding: 8px 0 0; }
  .m-dk.blick-zu .m-dk-blick-titel { writing-mode: horizontal-tb; transform: none; }
  .m-dk.blick-zu .m-dk-blick-kopf { flex-direction: row; }
  .m-dk-zu .q-icon { transform: rotate(90deg); } .m-dk.blick-zu .m-dk-zu .q-icon { transform: rotate(-90deg); }
}
.m-dk.voll { position: fixed; inset: 0; z-index: 4000; border-radius: 0; margin: 0; overflow: auto; padding: 16px 20px; }
body .m-dk.voll .m-chart, body.lay-office .m-dk.voll .m-chart { height: calc(100vh - 120px) !important; }
body.m-dk-vollbild { overflow: hidden; }
/* Kacheln: kompakte Karte */
.m-dk.klein { padding: 10px 12px; }
.m-dk.klein .m-dk-titel { font-size: 14px; }
.m-dk.klein .m-dk-knoepfe .m-dg-knopf { height: 26px; padding: 0 6px; font-size: 12px; }
.m-dk.klein .m-dk-knoepfe .m-dg-knopf > :not(i):not(b) { }
"""

JS = r"""<script>
(() => {
  const SP = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} };
  const LS = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const inst = (el) => { try { return getElement(el)?.chart || null; } catch (e) { return null; } };
  const schluessel = (el) => {
    const t = (document.querySelector('.m-kopf .m-titel')?.innerText || '').trim();
    const alle = [...document.querySelectorAll('.m-inhalt .m-chart')];
    return 'dg-hoehe:' + t + '#' + Math.max(0, alle.indexOf(el));
  };
  const zahl = (v) => v == null || v === '' || isNaN(v) ? '' : Number(v).toLocaleString('de-DE', {maximumFractionDigits: 1});
  function tabelle(c) {
    const o = c.getOption(); const x = (Array.isArray(o.xAxis) ? o.xAxis[0] : o.xAxis) || {};
    const kat = x.data || []; const reihen = (o.series || []);
    const spalten = [], unten = {};
    reihen.forEach((s) => {
      const vers = (s.tooltip && s.tooltip.show === false) || !s.name;
      if (s.stack && vers) { unten[s.stack] = s; return; }
      if (vers || !(s.data || []).some(v => v != null)) return;
      spalten.push({ s, u: s.stack ? unten[s.stack] : null });
    });
    const wert = (d) => (d && typeof d === 'object' && !Array.isArray(d)) ? d.value : (Array.isArray(d) ? d[d.length - 1] : d);
    const zeilen = [['', ...spalten.map(p => p.s.name)]];
    if (kat.length) {
      kat.forEach((k, i) => {
        const z = [typeof k === 'object' ? (k.value ?? '') : k];
        spalten.forEach(p => { const v = wert(p.s.data?.[i]); const lo = p.u ? wert(p.u.data?.[i]) : null;
          z.push(v == null ? '' : (lo != null ? zahl(lo) + ' – ' + zahl(lo + v) : zahl(v))); });
        if (z.slice(1).some(v => v !== '')) zeilen.push(z);
      });
    } else {
      spalten.forEach(p => (p.s.data || []).forEach(d => zeilen.push([p.s.name, ...(Array.isArray(d) ? d : [wert(d)]).map(zahl)])));
    }
    return zeilen;
  }
  function knopf(text, symbol, titel) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'm-dg-knopf'; b.title = titel || text;
    b.innerHTML = (symbol ? `<i>${symbol}</i>` : '') + text; return b;
  }

  // ---- 0.87 Diagramm-Karte: Knöpfe im Kopf, Ziehgriff unten rechts, Vollbild, „Auf einen Blick“ ----
  const akzent = () => (getComputedStyle(document.body).getPropertyValue('--akzent') || '#0B6E66').trim();
  function fokus(el, li) {
    const c = inst(el); if (!c) return;
    const o = c.getOption(); const x = (Array.isArray(o.xAxis) ? o.xAxis[0] : o.xAxis) || {}; const kat = x.data || [];
    const namen = kat.map(k => typeof k === 'object' ? String(k.value ?? '') : String(k));
    let i = parseInt(li.dataset.i, 10);
    for (const alt of (li.dataset.xs || '').split('|').filter(Boolean)) { const j = namen.indexOf(alt); if (j >= 0) { i = j; break; } }
    if (isNaN(i) || i < 0 || i >= namen.length) return;
    const w = li.dataset.w === '' ? null : parseFloat(li.dataset.w);
    const karte = el.closest('.m-dk');
    karte.querySelectorAll('.m-dk-satz.an').forEach(x => x.classList.remove('an')); li.classList.add('an');
    if (w == null) return;
    c.setOption({ series: [{ id: 'm-fokus', type: 'line', data: [], markPoint: { symbol: 'pin', symbolSize: 46, animation: true,
      itemStyle: { color: akzent() }, label: { show: true, color: '#fff', fontWeight: 'bold', fontSize: 12,
      formatter: () => Math.round(w).toLocaleString('de-DE') }, data: [{ coord: [namen[i], w] }] } }] });
    const si = (o.series || []).findIndex(s => s.name === li.dataset.r);
    if (si >= 0) c.dispatchAction({ type: 'showTip', seriesIndex: si, dataIndex: i });
  }
  function karteAusstatten(el, karte) {
    const flaeche = el.closest('.m-dk-flaeche') || el.parentElement;
    const k = schluessel(el); const h = LS(k);
    if (h) { el.style.setProperty('height', h + 'px', 'important'); el.style.setProperty('flex', 'none', 'important'); }
    if (karte.dataset.dkOk) return; karte.dataset.dkOk = '1';
    if (LS('dk-blick-zu') === '1') karte.classList.add('blick-zu');
    const tab = document.createElement('div'); tab.className = 'm-dg-tab'; tab.style.display = 'none'; el.after(tab);
    const griff = document.createElement('div'); griff.className = 'm-dk-griff';
    griff.title = 'Ziehen: Diagramm höher oder flacher · Doppelklick: Standardhöhe'; flaeche.append(griff);
    const b = (n) => karte.querySelector(`.m-dk-kopf [data-dk="${n}"]`);
    const fx = karte.querySelector('.m-fx');
    if (!fx) { const f = b('fx'); if (f) f.style.display = 'none'; }
    else if (LS('dg-fx') === '1') { fx.classList.add('offen'); b('fx')?.classList.add('an'); }
    const neuZeichnen = () => setTimeout(() => { const c = inst(el); if (c) c.resize(); }, 60);
    const zeigen = (alsTabelle) => {
      b('diagramm')?.classList.toggle('an', !alsTabelle); b('tabelle')?.classList.toggle('an', alsTabelle);
      if (alsTabelle) { const c = inst(el); if (!c) return; const z = tabelle(c);
        tab.innerHTML = '<table><thead><tr>' + z[0].map(x => `<th>${x}</th>`).join('') + '</tr></thead><tbody>' +
          z.slice(1).map(r => '<tr>' + r.map(x => `<td>${x}</td>`).join('') + '</tr>').join('') + '</tbody></table>';
        tab.style.height = el.offsetHeight + 'px'; tab.style.display = ''; el.style.display = 'none';
      } else { tab.style.display = 'none'; el.style.display = ''; neuZeichnen(); }
    };
    karte.addEventListener('click', async (ev) => {
      const k_ = ev.target.closest('[data-dk]'); const satz = ev.target.closest('.m-dk-satz:not(.still)');
      if (satz && karte.contains(satz)) { fokus(el, satz); return; }
      if (!k_ || !karte.contains(k_)) return;
      const was = k_.dataset.dk;
      if (was === 'diagramm') zeigen(false);
      else if (was === 'tabelle') zeigen(true);
      else if (was === 'fx' && fx) { const an = fx.classList.toggle('offen'); k_.classList.toggle('an', an); SP('dg-fx', an ? '1' : null); }
      else if (was === 'kopieren') { const c = inst(el); if (!c) return;
        const tsv = tabelle(c).map(r => r.join('\t')).join('\n'); const alt = k_.innerHTML;
        try { await navigator.clipboard.writeText(tsv); k_.innerHTML = '<i>check</i>Kopiert'; }
        catch (e) { k_.innerHTML = '<i>error_outline</i>Nicht kopiert'; }
        setTimeout(() => { k_.innerHTML = alt; }, 1800); }
      else if (was === 'voll') vollbild(karte, el, !karte.classList.contains('voll'));
      else if (was === 'blick') { const zu = karte.classList.toggle('blick-zu'); SP('dk-blick-zu', zu ? '1' : null); neuZeichnen(); }
    });
    karte.addEventListener('keydown', (ev) => { const s = ev.target.closest && ev.target.closest('.m-dk-satz:not(.still)');
      if (s && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); fokus(el, s); } });
    griff.addEventListener('mousedown', (ev) => {
      ev.preventDefault(); const y0 = ev.clientY, h0 = el.offsetHeight;
      const zieh = (e) => { const h = Math.max(160, Math.min(2400, h0 + e.clientY - y0));
        el.style.setProperty('height', h + 'px', 'important'); el.style.setProperty('flex', 'none', 'important'); };
      const los = () => { document.removeEventListener('mousemove', zieh); document.removeEventListener('mouseup', los);
        SP(k, String(el.offsetHeight)); neuZeichnen(); };
      document.addEventListener('mousemove', zieh); document.addEventListener('mouseup', los);
    });
    griff.addEventListener('dblclick', () => { el.style.removeProperty('height'); el.style.removeProperty('flex'); SP(k, null); neuZeichnen(); });
  }
  function vollbild(karte, el, an) {
    karte.classList.toggle('voll', an); document.body.classList.toggle('m-dk-vollbild', an);
    const knopf = karte.querySelector('.m-dk-kopf [data-dk="voll"]');
    if (knopf) { knopf.classList.toggle('an', an); knopf.innerHTML = an ? '<i>fullscreen_exit</i>Schließen' : '<i>fullscreen</i>Vollbild'; }
    if (an) { el.dataset.hoehe = el.style.getPropertyValue('height'); el.style.removeProperty('height'); }
    else if (el.dataset.hoehe) el.style.setProperty('height', el.dataset.hoehe, 'important');
    setTimeout(() => { const c = inst(el); if (c) c.resize(); }, 80);
  }
  document.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Escape') return; const k = document.querySelector('.m-dk.voll'); if (!k) return;
    ev.stopPropagation(); vollbild(k, k.querySelector('.m-chart'), false);
  }, true);
  function ausstatten(el) {
    if (el.dataset.dg) return; el.dataset.dg = '1';
    if (el.closest('.m-opt, .q-dialog')) return;            // Vorschau in den Optionen: ohne Leiste
    const karte = el.closest('.m-dk'); if (karte) { karteAusstatten(el, karte); return; }
    const k = schluessel(el); const h = LS(k);
    if (h) { el.style.setProperty('height', h + 'px', 'important'); el.style.setProperty('flex', 'none', 'important'); }
    const tab = document.createElement('div'); tab.className = 'm-dg-tab'; tab.style.display = 'none';
    const fuss = document.createElement('div'); fuss.className = 'm-dg-fuss';
    const griff = document.createElement('div'); griff.className = 'm-dg-griff';
    griff.title = 'Ziehen: Diagramm höher oder flacher · Doppelklick: Standardhöhe';
    griff.innerHTML = '<i>drag_handle</i>';                  // 0.87: kein Hinweistext mehr – Tooltip genügt
    if (el.classList.contains('m-dg')) griff.title += ' · Klick ins Diagramm: Werte und Berechnung';
    const gruppe = document.createElement('span'); gruppe.className = 'm-dg-gruppe';
    const bD = knopf('Diagramm', 'show_chart'), bT = knopf('Tabelle', 'table_rows', 'Dieselben Zahlen als Tabelle');
    bD.classList.add('an'); gruppe.append(bD, bT);
    const bK = knopf('Kopieren', 'content_copy', 'Zahlen für Excel kopieren (Strg+V)');
    fuss.append(griff, gruppe);
    const fx = el.parentElement && [...el.parentElement.children].find(x => x.classList && x.classList.contains('m-fx'));
    let bF = null;
    if (fx) {
      bF = knopf('<b>ƒx</b> Berechnung', '', 'Wie werden die Zahlen gerechnet?');
      if (LS('dg-fx') === '1') { fx.classList.add('offen'); bF.classList.add('an'); }
      bF.onclick = () => { const an = fx.classList.toggle('offen'); bF.classList.toggle('an', an); SP('dg-fx', an ? '1' : null); };
      fuss.append(bF);
    }
    fuss.append(bK);
    el.after(tab); tab.after(fuss);
    const zeigen = (alsTabelle) => {
      bD.classList.toggle('an', !alsTabelle); bT.classList.toggle('an', alsTabelle);
      if (alsTabelle) {
        const c = inst(el); if (!c) return;
        const z = tabelle(c);
        tab.innerHTML = '<table><thead><tr>' + z[0].map(x => `<th>${x}</th>`).join('') + '</tr></thead><tbody>' +
          z.slice(1).map(r => '<tr>' + r.map(x => `<td>${x}</td>`).join('') + '</tr>').join('') + '</tbody></table>';
        tab.style.height = el.offsetHeight + 'px'; tab.style.display = ''; el.style.display = 'none';
      } else { tab.style.display = 'none'; el.style.display = ''; }
    };
    bD.onclick = () => zeigen(false); bT.onclick = () => zeigen(true);
    bK.onclick = async () => {
      const c = inst(el); if (!c) return;
      const tsv = tabelle(c).map(r => r.join('\t')).join('\n');
      try { await navigator.clipboard.writeText(tsv); bK.innerHTML = '<i>check</i>Kopiert'; }
      catch (e) { bK.innerHTML = '<i>error_outline</i>Nicht kopiert'; }
      setTimeout(() => { bK.innerHTML = '<i>content_copy</i>Kopieren'; }, 1800);
    };
    griff.addEventListener('mousedown', (ev) => {
      ev.preventDefault(); const y0 = ev.clientY, h0 = el.offsetHeight;
      const zieh = (e) => { const h = Math.max(160, Math.min(2400, h0 + e.clientY - y0));
        el.style.setProperty('height', h + 'px', 'important'); el.style.setProperty('flex', 'none', 'important'); };
      const los = () => { document.removeEventListener('mousemove', zieh); document.removeEventListener('mouseup', los);
        SP(k, String(el.offsetHeight)); };
      document.addEventListener('mousemove', zieh); document.addEventListener('mouseup', los);
    });
    griff.addEventListener('dblclick', () => { el.style.removeProperty('height'); el.style.removeProperty('flex'); SP(k, null); });
  }
  function klickbar(el) {
    if (!el.classList.contains('m-dg')) return;
    const c = inst(el); if (!c || c.__dgKlick) return; c.__dgKlick = true;
    c.getZr().on('click', (ev) => {
      const p = [ev.offsetX, ev.offsetY];
      try { if (!c.containPixel({gridIndex: 0}, p)) return; } catch (e) { return; }
      const x = c.convertFromPixel({gridIndex: 0}, p); if (!x) return;
      const i = Math.round(Array.isArray(x) ? x[0] : x); if (isNaN(i) || i < 0) return;
      const karte = el.closest('.m-dk');                       // 0.87: zugehörige Sätze im Panel hervorheben
      if (karte) karte.querySelectorAll('.m-dk-satz').forEach(s => s.classList.toggle('an', s.dataset.i === String(i)));
      getElement(el)?.$emit('m_achse', {index: i});
    });
  }
  function panelGriff() {
    const p = document.querySelector('.m-center'); if (!p || p.querySelector(':scope > .m-panel-griff')) return;
    const g = document.createElement('div'); g.className = 'm-panel-griff'; g.title = 'Ziehen: Panel breiter oder schmaler · Doppelklick: Standard';
    p.prepend(g);
    g.addEventListener('mousedown', (ev) => {
      ev.preventDefault(); const x0 = ev.clientX, b0 = p.offsetWidth;
      const zieh = (e) => { const b = Math.max(320, Math.min(window.innerWidth * .7, b0 + x0 - e.clientX));
        document.documentElement.style.setProperty('--af-pb', Math.round(b) + 'px'); };
      const los = () => { document.removeEventListener('mousemove', zieh); document.removeEventListener('mouseup', los);
        SP('af-pb', document.documentElement.style.getPropertyValue('--af-pb')); };
      document.addEventListener('mousemove', zieh); document.addEventListener('mouseup', los);
    });
    g.addEventListener('dblclick', () => { document.documentElement.style.removeProperty('--af-pb'); SP('af-pb', null); });
  }
  const pb = LS('af-pb'); if (pb) document.documentElement.style.setProperty('--af-pb', pb);
  setInterval(() => { document.querySelectorAll('.m-chart').forEach(el => { ausstatten(el); klickbar(el); }); panelGriff(); }, 500);
})();
</script>"""
