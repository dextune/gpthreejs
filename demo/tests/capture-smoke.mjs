import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import profile from "../src/capture/m0-profile.json" with { type: "json" };

const __dirname = dirname(fileURLToPath(import.meta.url));
const demoRoot = resolve(__dirname, "..");
const host = "127.0.0.1";
const port = Number(process.env.GPTHREEJS_CAPTURE_PORT || 4174);
const baseUrl = `http://${host}:${port}`;
const passes = ["beauty", "alpha"];

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
  let childExited = false;
  let lastBody = "";
  child.once("exit", () => {
    childExited = true;
  });
  while (Date.now() < deadline) {
    if (child.exitCode !== null || childExited) {
      throw new Error(`Vite exited before serving: ${child.exitCode}`);
    }
    try {
      const remainingMs = Math.max(1, deadline - Date.now());
      const res = await fetch(baseUrl, {
        signal: AbortSignal.timeout(Math.min(1_000, remainingMs)),
      });
      lastBody = await res.text();
      if (res.ok && lastBody.includes("/main.ts")) {
        await new Promise((resolveDelay) => setTimeout(resolveDelay, 150));
        if (child.exitCode !== null || childExited) {
          throw new Error(`Vite exited before serving: ${child.exitCode}`);
        }
        return;
      }
    } catch {
      // Server is still starting.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 150));
  }
  throw new Error(`Timed out waiting for owned Vite server at ${baseUrl}: ${lastBody.slice(0, 120)}`);
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

async function capturePass(browser, passId, runId) {
  const page = await browser.newPage({
    deviceScaleFactor: profile.viewport.deviceScaleFactor,
    viewport: { width: profile.viewport.width, height: profile.viewport.height },
  });
  const problems = installProblemCollectors(page, `${passId}-${runId}`);
  await page.goto(`${baseUrl}/?capture=${passId}`, { waitUntil: "networkidle" });
  await page.waitForFunction(
    (expectedMode) => window.__gpthreejsCaptureReady?.mode === expectedMode,
    passId,
  );
  const result = await page.evaluate(() => {
    const ready = window.__gpthreejsCaptureReady;
    if (!ready?.ready) return { ok: false, reason: "capture not ready" };
    return {
      ok: true,
      ready,
      width: ready.width,
      height: ready.height,
      pixelHash: ready.pixelHash,
      hashKind: ready.hashKind,
      stats: ready.stats,
    };
  });
  await page.close();
  if (problems.length) {
    throw new Error(`Capture ${passId}/${runId} found browser errors: ${JSON.stringify(problems)}`);
  }
  if (!result.ok) {
    throw new Error(`Capture ${passId}/${runId} failed: ${result.reason}`);
  }
  return {
    passId,
    runId,
    hash: result.pixelHash,
    width: result.width,
    height: result.height,
    hashKind: result.hashKind,
    ready: result.ready,
    stats: result.stats,
  };
}

function compareCaptures(first, second) {
  const mismatches = [];
  if (first.hash !== second.hash) mismatches.push("pixel hash");
  if (first.width !== second.width || first.height !== second.height) mismatches.push("dimensions");
  if (JSON.stringify(first.stats) !== JSON.stringify(second.stats)) mismatches.push("pixel stats");
  return mismatches;
}

function validatePassEvidence(capture, alphaCapture) {
  if (capture.ready?.profileId !== profile.id) {
    throw new Error(`Unexpected capture profile: ${JSON.stringify(capture.ready)}`);
  }
  if (JSON.stringify(capture.ready?.viewport) !== JSON.stringify(profile.viewport)) {
    throw new Error(`Unexpected capture viewport: ${JSON.stringify(capture.ready)}`);
  }
  if (capture.width !== profile.viewport.width || capture.height !== profile.viewport.height) {
    throw new Error(`Unexpected capture size: ${capture.width}x${capture.height}`);
  }
  if (
    capture.passId === "beauty"
    && (
      capture.hashKind !== "rgba"
      || !alphaCapture
      || capture.ready.rootChildren <= 0
      || capture.stats.foregroundPixels < alphaCapture.stats.opaquePixels
    )
  ) {
    throw new Error(`Beauty capture has insufficient foreground: ${JSON.stringify(capture)}`);
  }
  if (
    capture.passId === "alpha"
    && (
      capture.hashKind !== "alpha"
      || capture.stats.transparentPixels === 0
      || capture.stats.opaquePixels === 0
    )
  ) {
    throw new Error(`Alpha capture lacks silhouette separation: ${JSON.stringify(capture.stats)}`);
  }
}

async function main() {
  const vite = startVite();
  let browserServer;
  let browser;
  let shuttingDown = false;
  const shutdown = async (signal) => {
    if (shuttingDown) return;
    shuttingDown = true;
    try {
      await closeBrowser(browserServer, browser);
    } finally {
      await stopVite(vite);
    }
    if (signal) {
      process.kill(process.pid, signal);
    }
  };
  process.once("SIGINT", () => {
    void shutdown("SIGINT");
  });
  process.once("SIGTERM", () => {
    void shutdown("SIGTERM");
  });
  try {
    await waitForServer(vite);
    browserServer = await chromium.launchServer();
    browser = await chromium.connect(browserServer.wsEndpoint());
    const results = [];
    for (const passId of passes) {
      const first = await capturePass(browser, passId, "a");
      const second = await capturePass(browser, passId, "b");
      const mismatches = compareCaptures(first, second);
      if (mismatches.length) {
        throw new Error(`Capture ${passId} was not deterministic: ${mismatches.join(", ")}`);
      }
      results.push(first);
    }
    const alphaCapture = results.find((capture) => capture.passId === "alpha");
    for (const capture of results) {
      validatePassEvidence(capture, alphaCapture);
    }
    console.log(
      JSON.stringify(
        {
          ok: true,
          profile,
          passes: results.map(({ passId, hash, hashKind, stats }) => ({
            passId,
            hash,
            hashKind,
            stats,
          })),
        },
        null,
        2,
      ),
    );
  } finally {
    if (!shuttingDown) {
      await shutdown();
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
