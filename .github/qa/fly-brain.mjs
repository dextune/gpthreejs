import { chromium } from 'playwright';
import fs from 'node:fs/promises';

const OUT = '/tmp/fly-brain-qa';
await fs.mkdir(OUT, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  args: ['--disable-dev-shm-usage', '--use-gl=swiftshader']
});

const errors = [];
const reports = [];

async function makePage(viewport, deviceScaleFactor = 1) {
  const context = await browser.newContext({ viewport, deviceScaleFactor, hasTouch: viewport.width < 600, isMobile: viewport.width < 600 });
  const page = await context.newPage();
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console: ${msg.text()}`);
  });
  await page.goto('http://127.0.0.1:4173/', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => Boolean(window.__FLY_BRAIN__));
  return { context, page };
}

async function record(label, page, fileName) {
  await page.waitForTimeout(250);
  const metrics = await page.evaluate(() => window.__FLY_BRAIN__.getMetrics());
  reports.push({ label, metrics });
  if (metrics.drawCalls > 130) errors.push(`${label}: draw calls too high (${metrics.drawCalls})`);
  if (metrics.geometries > 90) errors.push(`${label}: geometry count too high (${metrics.geometries})`);
  await page.screenshot({ path: `${OUT}/${fileName}`, fullPage: true });
}

// Render 1 — desktop title composition.
{
  const { context, page } = await makePage({ width: 1440, height: 900 }, 1);
  await page.waitForTimeout(650);
  await record('render-1-desktop-ready', page, '01-desktop-ready.png');
  await context.close();
}

// Render 2 — live gameplay, desktop high-DPI.
{
  const { context, page } = await makePage({ width: 1440, height: 900 }, 1.5);
  await page.mouse.click(450, 460);
  for (let i = 0; i < 5; i += 1) {
    await page.waitForTimeout(240);
    await page.keyboard.press('Space');
  }
  await record('render-2-desktop-running', page, '02-desktop-running.png');
  await context.close();
}

// Render 3 — later difficulty / meme HUD state.
{
  const { context, page } = await makePage({ width: 1280, height: 800 }, 1);
  await page.mouse.click(420, 400);
  await page.evaluate(() => window.__FLY_BRAIN__.debugScore(12));
  for (let i = 0; i < 4; i += 1) {
    await page.waitForTimeout(210);
    await page.keyboard.press('Space');
  }
  await record('render-3-score-12', page, '03-score-12.png');
  await context.close();
}

// Render 4 — mobile portrait touch layout.
{
  const { context, page } = await makePage({ width: 390, height: 844 }, 2);
  await page.touchscreen.tap(130, 430);
  await page.evaluate(() => window.__FLY_BRAIN__.debugScore(5));
  for (let i = 0; i < 5; i += 1) {
    await page.waitForTimeout(210);
    await page.touchscreen.tap(130, 430);
  }
  await record('render-4-mobile-running', page, '04-mobile-running.png');
  await context.close();
}

// Render 5 — comedic collision / game-over presentation.
{
  const { context, page } = await makePage({ width: 1440, height: 900 }, 1);
  await page.mouse.click(450, 460);
  await page.evaluate(() => {
    window.__FLY_BRAIN__.debugScore(8);
    window.__FLY_BRAIN__.debugCrash();
  });
  await page.waitForTimeout(700);
  await record('render-5-game-over', page, '05-game-over.png');
  await context.close();
}

await browser.close();
await fs.writeFile(`${OUT}/report.json`, JSON.stringify({ reports, errors }, null, 2));
console.log(JSON.stringify({ reports, errors }, null, 2));

if (errors.length) process.exit(1);
