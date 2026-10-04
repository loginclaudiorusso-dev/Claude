// Prüft alle Screens im mobilen Viewport (390 × 844):
// Screenshots (hell + dunkel), kein horizontales Scrollen, keine Konsolenfehler, keine Anfragen an Drittanbieter.
// Aufruf: node scripts/check.mjs [baseUrl] [outDir] [filter]
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';

const base = process.argv[2] ?? 'http://localhost:5173';
const out = process.argv[3] ?? 'screenshots';
const filter = process.argv[4] ?? '';
mkdirSync(out, { recursive: true });

const ROUTES = {
  participant: ['/', '/challenges', '/events', '/events/ev-bouldern', '/liga', '/profil', '/profil/abzeichen', '/profil/ideen', '/profil/umfrage', '/profil/daten', '/checkin'],
  staff: ['/betreuung', '/betreuung/code', '/betreuung/events', '/betreuung/events/neu', '/betreuung/turnier', '/betreuung/turnier/t-herbstcup', '/betreuung/ankuendigung', '/betreuung/ideen', '/profil'],
  lead: ['/leitung', '/leitung/liga', '/leitung/umfrage', '/leitung/verwaltung', '/leitung/datenschutz', '/aushang/gs', '/profil'],
};
const PERSON = { participant: 'p-gs-01', staff: 's-gs', lead: 'lead' };

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium', args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] });
const problems = [];
const foreign = new Set();
for (const scheme of ['light', 'dark']) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, colorScheme: scheme, isMobile: true, hasTouch: true, permissions: ['camera'] });
  const page = await ctx.newPage();
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (!['localhost', '127.0.0.1'].includes(u.hostname) && !u.protocol.startsWith('data') && !u.protocol.startsWith('blob')) foreign.add(r.url());
  });
  page.on('console', (m) => m.type() === 'error' && problems.push(`[${scheme}] console: ${m.text()}`));
  page.on('pageerror', (e) => problems.push(`[${scheme}] pageerror: ${e.message}`));
  await page.goto(base);
  for (const [role, routes] of Object.entries(ROUTES)) {
    for (const route of routes) {
      const name = `${role}${route === '/' ? '_home' : route.replace(/\//g, '_')}`;
      if (filter && !filter.split(',').some((f) => (f.endsWith('*') ? name.startsWith(f.slice(0, -1)) : name === f))) continue;
      await page.evaluate(([role, pid]) => {
        const s = JSON.parse(localStorage.getItem('innmotion-session') || '{"state":{"personByRole":{}},"version":1}');
        s.state.role = role;
        s.state.personByRole = { participant: 'p-gs-01', staff: 's-gs', lead: 'lead', ...s.state.personByRole, [role]: pid };
        localStorage.setItem('innmotion-session', JSON.stringify(s));
      }, [role, PERSON[role]]);
      await page.goto(base + route, { waitUntil: 'networkidle' });
      await page.waitForTimeout(900);
      const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, w: window.innerWidth, path: location.pathname }));
      if (m.sw > 390 || m.w > 390) problems.push(`[${scheme}] ${route} (${role}): horizontales Scrollen ${m.sw}px > ${m.w}px`);
      if (m.path !== route) problems.push(`[${scheme}] ${route} (${role}): umgeleitet nach ${m.path}`);
      // Abgeschnittene Texte: Elemente, deren Inhalt breiter ist als sie selbst, ohne bewusstes truncate
      const clipped = await page.evaluate(() => {
        const bad = [];
        for (const el of document.querySelectorAll('body *')) {
          const cs = getComputedStyle(el);
          if (el.closest('.sr-only, [aria-hidden="true"]')) continue;
          if (el.children.length === 0 && el.textContent.trim() && el.scrollWidth > el.clientWidth + 1 && cs.overflow !== 'visible' && cs.textOverflow !== 'ellipsis' && el.clientWidth > 1) bad.push(el.textContent.trim().slice(0, 40));
          const r = el.getBoundingClientRect();
          let clippedByParent = false;
          for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) if (['hidden', 'clip', 'auto', 'scroll'].includes(getComputedStyle(a).overflowX)) { clippedByParent = true; break; }
          if (r.width > 0 && r.right > window.innerWidth + 1 && cs.position !== 'fixed' && !clippedByParent) bad.push('rechts raus: ' + (el.textContent || el.tagName).trim().slice(0, 40));
        }
        return [...new Set(bad)].slice(0, 5);
      });
      if (clipped.length) problems.push(`[${scheme}] ${route} (${role}): evtl. abgeschnitten: ${clipped.join(' | ')}`);
      await page.screenshot({ path: `${out}/${name}-${scheme}.png`, fullPage: true });
    }
  }
  await ctx.close();
}
await browser.close();
console.log(foreign.size ? `Anfragen an Drittanbieter:\n${[...foreign].join('\n')}` : 'Keine Anfragen an Drittanbieter.');
console.log(problems.length ? `Probleme:\n${problems.join('\n')}` : 'Keine Probleme gefunden.');
