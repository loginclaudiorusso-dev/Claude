// Prüft die PWA-Installierbarkeit am Produktions-Build (npm run build && npm run preview).
import { chromium } from 'playwright-core';
const base = process.argv[2] ?? 'http://localhost:4173';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
// Persistenter Kontext – im Inkognito-Modus meldet Chrome PWAs grundsätzlich als nicht installierbar.
const ctx = await chromium.launchPersistentContext(mkdtempSync(join(tmpdir(), 'innm-')), { executablePath: process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium' });
const b = ctx;
const page = await ctx.newPage();
const foreign = [];
page.on('request', (r) => { const h = new URL(r.url()).hostname; if (!['localhost', '127.0.0.1'].includes(h) && !r.url().startsWith('data:')) foreign.push(r.url()); });
await page.goto(base, { waitUntil: 'networkidle' });
const res = await page.evaluate(async () => {
  const link = document.querySelector('link[rel="manifest"]');
  const manifest = link ? await (await fetch(link.href)).json() : null;
  const reg = await Promise.race([navigator.serviceWorker.ready, new Promise((r) => setTimeout(() => r(null), 8000))]);
  return { manifest, sw: !!reg?.active, scope: reg?.scope };
});
const cdp = await ctx.newCDPSession(page);
const errs = await cdp.send('Page.getInstallabilityErrors').catch(() => ({ installabilityErrors: ['(nicht prüfbar)'] }));
console.log('Manifest:', res.manifest?.name, '| Icons:', res.manifest?.icons?.map((i) => i.sizes + (i.purpose ? ' ' + i.purpose : '')).join(', '), '| display:', res.manifest?.display);
console.log('Service Worker aktiv:', res.sw, res.scope);
console.log('Installierbarkeit:', errs.installabilityErrors.length ? JSON.stringify(errs.installabilityErrors) : 'keine Fehler');
await page.context().setOffline(true);
await page.reload({ waitUntil: 'load' }).catch(() => {});
console.log('Offline-Start:', (await page.title()) === 'INNmotion' && (await page.locator('nav').count()) > 0 ? 'ok' : 'fehlgeschlagen');
console.log(foreign.length ? 'Drittanbieter: ' + foreign.join(', ') : 'Keine Anfragen an Drittanbieter.');
await b.close();
