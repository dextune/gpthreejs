import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const demoRoot = resolve(__dirname, "..");
const host = "127.0.0.1";
const port = Number(process.env.GPTHREEJS_RUNTIME_PORT || 4173);
const baseUrl = `http://${host}:${port}`;
const fixtureMarker = "[gpthreejs-smoke-fixture]";
const fixturePath = "/tests/runtime-error.html";
const fixtureConsoleMessage = `${fixtureMarker} intentional console error`;
const fixturePageErrorMessage = `${fixtureMarker} intentional page error`;
const requiredNodeIds = ["hips", "torso", "head", "hand_l", "hand_r", "weapon_hip"];
const requiredPivotIds = ["hips", "spine", "head", "leftHand", "rightHand"];
const requiredSocketIds = ["weapon_r", "weapon_hip"];

function startVite() {
  const viteBin = resolve(demoRoot, "node_modules", "vite", "bin", "vite.js");
  const child = spawn(
    process.execPath,
    [viteBin, "--host", host, "--port", String(port), "--strictPort"],
    {
      cwd: demoRoot,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, BROWSER: "none" },
    },
  );

  child.stdout.on("data", (chunk) => process.stdout.write(`[vite] ${chunk}`));
  child.stderr.on("data", (chunk) => process.stderr.write(`[vite] ${chunk}`));
  return child;
}

async function stopVite(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  const exited = await new Promise((resolveExit) => {
    const timeout = setTimeout(() => resolveExit(false), 3_000);
    child.once("exit", () => {
      clearTimeout(timeout);
      resolveExit(true);
    });
  });
  if (!exited && child.exitCode === null && child.signalCode === null) {
    child.kill("SIGKILL");
  }
}

async function withTimeout(promise, ms, message) {
  let timeout;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timeout = setTimeout(() => reject(new Error(message)), ms);
      }),
    ]);
  } finally {
    clearTimeout(timeout);
  }
}

async function closeBrowser(browserServer, browser) {
  try {
    if (browser) {
      await withTimeout(browser.close(), 3_000, "Timed out closing Playwright browser");
    }
  } finally {
    const process = browserServer?.process();
    if (process && process.exitCode === null && process.signalCode === null) {
      process.kill("SIGKILL");
    }
  }
}

async function waitForServer(child) {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Vite exited before serving: ${child.exitCode}`);
    }
    try {
      const res = await fetch(baseUrl);
      if (res.ok) return;
    } catch {
      // Server is still starting.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 150));
  }
  throw new Error(`Timed out waiting for ${baseUrl}`);
}

function installProblemCollectors(page, label) {
  const problems = [];
  page.on("pageerror", (error) => {
    problems.push({ type: "pageerror", label, message: error.message });
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      problems.push({ type: "console.error", label, message: message.text() });
    }
  });
  page.on("requestfailed", (request) => {
    const resourceType = request.resourceType();
    if (["document", "script", "stylesheet", "image"].includes(resourceType)) {
      problems.push({
        type: "requestfailed",
        label,
        url: request.url(),
        message: request.failure()?.errorText || "request failed",
      });
    }
  });
  return problems;
}

async function verifyFailureFixture(browser) {
  const page = await browser.newPage();
  const problems = installProblemCollectors(page, "intentional-fixture");
  const response = await page.goto(`${baseUrl}${fixturePath}`, { waitUntil: "load" });
  await page.waitForTimeout(250);
  await page.close();

  if (!response || response.status() !== 200 || response.url() !== `${baseUrl}${fixturePath}`) {
    throw new Error(`Runtime smoke fixture failed to load: ${response?.status()}`);
  }
  const sawConsoleError = problems.some(
    (problem) => problem.type === "console.error" && problem.message === fixtureConsoleMessage,
  );
  const sawPageError = problems.some(
    (problem) => problem.type === "pageerror" && problem.message === fixturePageErrorMessage,
  );
  if (!sawConsoleError || !sawPageError) {
    throw new Error(
      `Runtime smoke failed to detect intentional fixture errors: ${JSON.stringify(problems)}`,
    );
  }
  return problems;
}

async function verifyApp(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const problems = installProblemCollectors(page, "app");
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() => {
    const canvas = document.querySelector("canvas");
    return canvas instanceof HTMLCanvasElement && canvas.width > 0 && canvas.height > 0;
  });
  await page.waitForFunction(() => window.__gpthreejsRuntimeSmoke?.ready === true);
  await page.waitForTimeout(500);

  const appState = await page.evaluate(() => {
    const canvas = document.querySelector("canvas");
    if (!(canvas instanceof HTMLCanvasElement)) {
      return { canvas: { present: false }, runtime: window.__gpthreejsRuntimeSmoke || null };
    }
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    return {
      canvas: {
        present: true,
        width: canvas.width,
        height: canvas.height,
        webgl: Boolean(gl),
        contextLost: gl ? gl.isContextLost() : true,
      },
      runtime: window.__gpthreejsRuntimeSmoke || null,
    };
  });
  await page.close();

  if (problems.length) {
    throw new Error(`Runtime smoke found app errors: ${JSON.stringify(problems, null, 2)}`);
  }
  if (!appState.canvas.present || !appState.canvas.webgl || appState.canvas.contextLost) {
    throw new Error(`Runtime smoke found invalid canvas state: ${JSON.stringify(appState)}`);
  }
  const runtime = appState.runtime;
  const missingNodeIds = requiredNodeIds.filter((id) => !runtime?.nodeIds?.includes(id));
  const missingPivotIds = requiredPivotIds.filter((id) => !runtime?.pivotIds?.includes(id));
  const missingSocketIds = requiredSocketIds.filter((id) => !runtime?.socketIds?.includes(id));
  if (!runtime || runtime.rootChildren <= 0 || missingNodeIds.length || missingPivotIds.length || missingSocketIds.length) {
    throw new Error(
      `Runtime smoke found invalid formHandles: ${JSON.stringify({
        runtime,
        missingNodeIds,
        missingPivotIds,
        missingSocketIds,
      })}`,
    );
  }
  return appState;
}

async function main() {
  const vite = startVite();
  let browserServer;
  let browser;
  try {
    await waitForServer(vite);
    browserServer = await chromium.launchServer();
    browser = await chromium.connect(browserServer.wsEndpoint());
    const fixtureProblems = await verifyFailureFixture(browser);
    const canvasState = await verifyApp(browser);
    console.log(
      JSON.stringify(
        {
          ok: true,
          fixtureProblems: fixtureProblems.map(({ type }) => type),
          appState: canvasState,
        },
        null,
        2,
      ),
    );
  } finally {
    try {
      await closeBrowser(browserServer, browser);
    } finally {
      await stopVite(vite);
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
