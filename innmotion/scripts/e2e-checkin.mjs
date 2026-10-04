// End-to-End-Test des Check-ins:
// 1) Betreuung zeigt den QR-Code des Fitnessraums → daraus wird ein Kamera-Video (Y4M) erzeugt.
// 2) Teilnehmende scannen ihn mit der (simulierten) Kamera → Punkte + Wochenziel.
// 3) Zweiter Scan am selben Ort wird durch die 3-Stunden-Sperre abgelehnt.
// 4) Manuelle Code-Eingabe für die Sporthalle funktioniert.
// Aufruf: node scripts/e2e-checkin.mjs [baseUrl] [outDir]
import { chromium } from 'playwright-core';
import { writeFileSync, mkdirSync } from 'node:fs';

const base = process.argv[2] ?? 'http://localhost:5173';
const out = process.argv[3] ?? 'screenshots';
mkdirSync(out, { recursive: true });
const exe = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium';
const W = 640, H = 480;
const assert = (cond, msg) => { if (!cond) { console.error('FEHLER:', msg); process.exit(1); } console.log('ok –', msg); };

const setRole = (role, pid) => `(() => { localStorage.setItem('innmotion-session', JSON.stringify({ state: { role: '${role}', personByRole: { participant: 'p-gs-01', staff: 's-gs', lead: 'lead', ${role}: '${pid}' } }, version: 1 })); })()`;

// --- 1) Betreuung: QR-Code holen
let b = await chromium.launch({ executablePath: exe });
let page = await b.newPage({ viewport: { width: 390, height: 844 } });
await page.goto(base);
await page.evaluate(() => localStorage.clear());
await page.goto(base);
await page.evaluate(setRole('staff', 's-gs'));
await page.goto(base + '/betreuung/code', { waitUntil: 'networkidle' });
await page.getByRole('tab', { name: 'Fitnessraum' }).click();
await page.waitForTimeout(300);
const hallCodeText = await (async () => {
  await page.getByRole('tab', { name: 'Sporthalle' }).click();
  await page.waitForTimeout(200);
  const t = await page.locator('p.font-mono').first().innerText();
  await page.getByRole('tab', { name: 'Fitnessraum' }).click();
  await page.waitForTimeout(300);
  return t.replace(/\s/g, '');
})();
const yPlane = await page.evaluate(async ([W, H]) => {
  const svg = document.querySelector('[role="img"][aria-label^="QR-Code"] svg').outerHTML;
  const img = new Image();
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  await img.decode();
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);
  ctx.drawImage(img, (W - 380) / 2, (H - 380) / 2, 380, 380);
  const d = ctx.getImageData(0, 0, W, H).data;
  const y = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) y[i] = Math.round(0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]);
  return Array.from(y);
}, [W, H]);
const dbJson = await page.evaluate(() => localStorage.getItem('innmotion-db'));
await b.close();

const frame = Buffer.concat([Buffer.from('FRAME\n'), Buffer.from(yPlane), Buffer.alloc((W / 2) * (H / 2) * 2, 128)]);
const y4m = `${out}/qr-fitnessraum.y4m`;
writeFileSync(y4m, Buffer.concat([Buffer.from(`YUV4MPEG2 W${W} H${H} F10:1 Ip A1:1 C420jpeg\n`), ...Array(20).fill(frame)]));
assert(hallCodeText.length === 6, `Tagescode Sporthalle gelesen (${hallCodeText})`);

// --- 2) Teilnehmende scannen mit der Kamera
b = await chromium.launch({ executablePath: exe, args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-video-capture=${y4m}`] });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, permissions: ['camera'], deviceScaleFactor: 2 });
await ctx.addInitScript(([db]) => { if (!sessionStorage.getItem('seeded')) { localStorage.setItem('innmotion-db', db); sessionStorage.setItem('seeded', '1'); } }, [dbJson]);
page = await ctx.newPage();
await page.goto(base);
await page.evaluate(setRole('participant', 'p-gs-01'));
await page.goto(base + '/', { waitUntil: 'networkidle' });
const before = await page.locator('section[aria-labelledby="week-title"] p.tnum').innerText();
await page.getByRole('button', { name: 'Einchecken' }).first().click();
await page.getByRole('heading', { name: 'Eingecheckt!' }).waitFor({ timeout: 15000 }).catch(async (e) => { await page.screenshot({ path: `${out}/e2e-fehler.png` }); console.error(await page.locator('body').innerText()); throw e; });
const celebration = await page.locator('body').innerText();
await page.waitForTimeout(1200);
await page.screenshot({ path: `${out}/e2e-1-kamera-erfolg.png`, fullPage: true });
assert(/Wochenziel geschafft/.test(celebration), 'Kamera-Scan erfolgreich, Wochenziel erreicht');
await page.getByRole('button', { name: 'Fertig' }).click();
const after = await page.locator('section[aria-labelledby="week-title"] p.tnum').innerText();
assert(Number(after) > Number(before), `Wochenpunkte gestiegen (${before} → ${after})`);

// --- 3) Zweiter Scan am selben Ort → Sperre
await page.getByRole('button', { name: 'Einchecken' }).first().click();
await page.getByRole('alert').filter({ hasText: 'schon seit' }).waitFor({ timeout: 15000 });
await page.screenshot({ path: `${out}/e2e-2-sperre.png` });
assert(true, '3-Stunden-Sperre greift beim zweiten Scan');

// --- 4) Manuelle Eingabe Sporthalle
await page.getByRole('tab', { name: 'Code eingeben' }).click();
await page.getByLabel(/6-stelligen Code/).fill(hallCodeText.toLowerCase());
await page.getByRole('button', { name: 'Einchecken' }).click();
await page.getByRole('heading', { name: 'Eingecheckt!' }).waitFor({ timeout: 5000 });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${out}/e2e-3-code-erfolg.png`, fullPage: true });
assert(true, 'Manuelle Code-Eingabe erfolgreich');

// --- 5) Falscher Code
await page.getByRole('button', { name: 'Fertig' }).click();
await page.getByRole('button', { name: 'Einchecken' }).first().click();
await page.getByRole('tab', { name: 'Code eingeben' }).click();
await page.getByLabel(/6-stelligen Code/).fill('AAAAAA');
await page.getByRole('button', { name: 'Einchecken' }).click();
await page.getByRole('alert').waitFor();
assert(true, 'Unbekannter Code wird abgelehnt');
await b.close();
console.log('Alle Check-in-Tests bestanden.');
