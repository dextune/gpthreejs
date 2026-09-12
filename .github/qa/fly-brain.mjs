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
  const mobile = viewport.width < 600;
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor,
    hasTouch: mobile,
    isMobile: mobile
  });
  const page = await context.newPage();
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console: ${msg.text()}`);
  });
  await page.goto('http://127.0.0.1:4173/', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => Boolean(window.__FLY_BRAIN__));
  return { context, page };
}

async function keepAlive(page, milliseconds) {
  const steps = Math.ceil(milliseconds / 80);
  for (let i = 0; i < steps; i += 1) {
    await page.waitForTimeout(80);
    const state = await page.evaluate(() => {
      const game = window.__FLY_BRAIN__;
      if (game.state !== 1) return game.state;
      const fly = game.fly;
      if (fly.root.position.y < 0.05 && fly.velocityY < -1.0) fly.flap();
      return game.state;
    });
    if (state !== 1) break;
  }
}

async function record(label, page, fileName, expected = {}) {
  await page.waitForTimeout(220);
  const metrics = await page.evaluate(() => {
    const game = window.__FLY_BRAIN__;
    return {
      ...game.getMetrics(),
      renderPixelRatio: game.rendererSystem.renderer.getPixelRatio()
    };
  });
  reports.push({ label, metrics });

  if (metrics.drawCalls > 90) errors.push(`${label}: draw calls too high (${metrics.drawCalls})`);
  if (metrics.geometries > 50) errors.push(`${label}: geometry count too high (${metrics.geometries})`);
  if (expected.state !== undefined && metrics.state !== expected.state) {
    errors.push(`${label}: expected state ${expected.state}, got ${metrics.state}`);
  }
  if (expected.minScore !== undefined && metrics.score < expected.minScore) {
    errors.push(`${label}: expected score >= ${expected.minScore}, got ${metrics.score}`);
  }
  if (expected.maxPixelRatio !== undefined && metrics.renderPixelRatio > expected.maxPixelRatio + 0.01) {
    errors.push(`${label}: pixel ratio ${metrics.renderPixelRatio} exceeds ${expected.maxPixelRatio}`);
  }

  await page.screenshot({ path: `${OUT}/${fileName}`, fullPage: true });
}

// Render 1 — desktop title composition.
{
  const { context, page } = await makePage({ width: 1440, height: 900 }, 1);
  await page.waitForTimeout(650);
  await record('render-1-desktop-ready', page, '01-desktop-ready.png', { state: 0 });
  await context.close();
}

// Render 2 — live gameplay, desktop high-DPI.
{
  const { context, page } = await makePage({ width: 1440, height: 900 }, 1.5);
  await page.mouse.click(450, 460);
  await keepAlive(page, 1350);
  await record('render-2-desktop-running', page, '02-desktop-running.png', { state: 1 });
  await context.close();
}

// Render 3 — later difficulty / meme HUD state.
{
  const { context, page } = await makePage({ width: 1280, height: 800 }, 1);
  await page.mouse.click(420, 400);
  await page.evaluate(() => window.__FLY_BRAIN__.debugScore(12));
  await keepAlive(page, 1200);
  await record('render-3-score-12', page, '03-score-12.png', { state: 1, minScore: 12 });
  await context.close();
}

// Render 4 — mobile portrait touch layout and adaptive render quality.
{
  const { context, page } = await makePage({ width: 390, height: 844 }, 2);
  await page.touchscreen.tap(130, 430);
  await page.evaluate(() => window.__FLY_BRAIN__.debugScore(5));
  await keepAlive(page, 900);
  await record('render-4-mobile-running', page, '04-mobile-running.png', {
    state: 1,
    minScore: 5,
    maxPixelRatio: 1.35
  });
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
  await record('render-5-game-over', page, '05-game-over.png', { state: 2, minScore: 8 });
  await context.close();
}

await browser.close();
await fs.writeFile(`${OUT}/report.json`, JSON.stringify({ reports, errors }, null, 2));
console.log(JSON.stringify({ reports, errors }, null, 2));

if (errors.length) process.exit(1);
