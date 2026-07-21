import { chmodSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(new URL("./dependency-preflight.mjs", import.meta.url));
const cleanInstallScriptPath = fileURLToPath(new URL("./clean-install-smoke.mjs", import.meta.url));
const demoRoot = resolve(dirname(scriptPath), "..");

function quoteArg(value) {
  if (/^[A-Za-z0-9_./:@%+=,-]+$/.test(value)) return value;
  return `"${value.replace(/(["\\$`])/g, "\\$1")}"`;
}

function runPreflight(root) {
  return spawnSync(process.execPath, [scriptPath], {
    env: { ...process.env, GPTHREEJS_PREFLIGHT_ROOT: root },
    encoding: "utf8",
  });
}

function assertIncludes(text, expected) {
  if (!text.includes(expected)) {
    throw new Error(`Expected output to include ${JSON.stringify(expected)}:\n${text}`);
  }
}

const root = mkdtempSync(resolve(tmpdir(), "gpthreejs preflight "));
const quotedRoot = quoteArg(root);
try {
  writeFileSync(
    resolve(root, "package.json"),
    JSON.stringify(
      {
        private: true,
        dependencies: {
          three: "^0.172.0",
        },
        devDependencies: {
          "@types/node": "^26.1.1",
          "@types/three": "^0.172.0",
          playwright: "^1.61.1",
          typescript: "^5.7.0",
          vite: "^6.0.0",
        },
        scripts: {
          preflight: "node tests/dependency-preflight.mjs",
          "provision:browser": "playwright install chromium",
          typecheck: "tsc --noEmit",
          build: "vite build",
          "test:runtime": "node tests/runtime-smoke.mjs",
          "capture:smoke": "node tests/capture-smoke.mjs",
          "verify:clean-install": "node tests/clean-install-smoke.mjs",
          check: "npm run preflight && npm run typecheck && npm run build && npm run test:runtime && npm run capture:smoke",
        },
      },
      null,
      2,
    ),
  );

  const missingLock = runPreflight(root);
  if (missingLock.status === 0) {
    throw new Error("Expected missing lock/node_modules preflight to fail");
  }
  assertIncludes(missingLock.stderr, "missing-package-lock");
  assertIncludes(missingLock.stderr, "missing-node-modules");
  assertIncludes(missingLock.stderr, `npm --prefix ${quotedRoot} install --package-lock-only`);
  assertIncludes(missingLock.stderr, "npm ci requires package-lock.json first");
  assertIncludes(missingLock.stderr, `npm --prefix ${quotedRoot} run check`);

  writeFileSync(resolve(root, "package-lock.json"), JSON.stringify({ lockfileVersion: 3 }, null, 2));
  const missingModules = runPreflight(root);
  if (missingModules.status === 0) {
    throw new Error("Expected missing node_modules preflight to fail");
  }
  assertIncludes(missingModules.stderr, "missing-node-modules");
  assertIncludes(missingModules.stderr, `npm --prefix ${quotedRoot} ci --include=dev`);

  const nodeModules = resolve(root, "node_modules");
  mkdirSync(resolve(nodeModules, ".bin"), { recursive: true });
  mkdirSync(resolve(nodeModules, "three"), { recursive: true });
  mkdirSync(resolve(nodeModules, "typescript"), { recursive: true });
  mkdirSync(resolve(nodeModules, "vite"), { recursive: true });
  mkdirSync(resolve(nodeModules, "playwright"), { recursive: true });
  mkdirSync(resolve(nodeModules, "@types", "node"), { recursive: true });
  for (const packageName of ["three", "typescript", "vite", "playwright", "@types/node"]) {
    writeFileSync(resolve(nodeModules, ...packageName.split("/"), "package.json"), "{}");
  }
  const tscBin = resolve(nodeModules, ".bin", process.platform === "win32" ? "tsc.cmd" : "tsc");
  const viteBin = resolve(nodeModules, ".bin", process.platform === "win32" ? "vite.cmd" : "vite");
  const playwrightBin = resolve(nodeModules, ".bin", process.platform === "win32" ? "playwright.cmd" : "playwright");
  writeFileSync(tscBin, "");
  writeFileSync(viteBin, "");
  mkdirSync(playwrightBin);
  chmodSync(tscBin, 0o755);
  chmodSync(viteBin, 0o755);

  const missingWorkflowDeps = runPreflight(root);
  if (missingWorkflowDeps.status === 0) {
    throw new Error("Expected missing workflow dependency preflight to fail");
  }
  assertIncludes(missingWorkflowDeps.stderr, "npm package manifest for '@types/three'");
  assertIncludes(missingWorkflowDeps.stderr, "non-executable playwright binary");
  assertIncludes(missingWorkflowDeps.stderr, `npm --prefix ${quotedRoot} ci --include=dev`);

  if (process.platform !== "win32") {
    mkdirSync(resolve(nodeModules, "@types", "three"), { recursive: true });
    writeFileSync(resolve(nodeModules, "@types", "three", "package.json"), "{}");
    rmSync(playwrightBin, { recursive: true, force: true });
    writeFileSync(playwrightBin, "");
    chmodSync(playwrightBin, 0o755);
    chmodSync(tscBin, 0o644);

    const nonExecutableBinary = runPreflight(root);
    if (nonExecutableBinary.status === 0) {
      throw new Error("Expected non-executable binary preflight to fail");
    }
    assertIncludes(nonExecutableBinary.stderr, "non-executable tsc binary");
    assertIncludes(nonExecutableBinary.stderr, `npm --prefix ${quotedRoot} ci --include=dev`);
  }

  const emptyBrowserCache = mkdtempSync(resolve(tmpdir(), "gpthreejs-empty-browser-cache-"));
  try {
    const missingBrowser = spawnSync(process.execPath, [scriptPath], {
      env: {
        ...process.env,
        GPTHREEJS_PREFLIGHT_ROOT: demoRoot,
        PLAYWRIGHT_BROWSERS_PATH: emptyBrowserCache,
      },
      encoding: "utf8",
    });
    if (missingBrowser.status === 0) {
      throw new Error("Expected empty browser cache preflight to fail");
    }
    assertIncludes(missingBrowser.stderr, "playwright-chromium-unavailable");
    assertIncludes(missingBrowser.stderr, `npm --prefix ${quoteArg(demoRoot)} run provision:browser`);
  } finally {
    rmSync(emptyBrowserCache, { recursive: true, force: true });
  }

  const missingSourceLockRoot = mkdtempSync(resolve(tmpdir(), "gpthreejs-missing-source-lock-"));
  try {
    writeFileSync(resolve(missingSourceLockRoot, "package.json"), JSON.stringify({ private: true }, null, 2));
    const missingSourceLock = spawnSync(process.execPath, [cleanInstallScriptPath], {
      env: {
        ...process.env,
        GPTHREEJS_CLEAN_INSTALL_SOURCE_ROOT: missingSourceLockRoot,
      },
      encoding: "utf8",
    });
    if (missingSourceLock.status === 0) {
      throw new Error("Expected missing source lock clean-install smoke to fail");
    }
    assertIncludes(missingSourceLock.stderr, "clean-install smoke failed");
    assertIncludes(missingSourceLock.stderr, "install --package-lock-only");
  } finally {
    rmSync(missingSourceLockRoot, { recursive: true, force: true });
  }

  console.log(
    JSON.stringify(
      {
        ok: true,
        checked: [
          "missing-lock",
          "missing-node-modules",
          "missing-workflow-dependency",
          ...(process.platform === "win32" ? [] : ["non-executable-binary"]),
          "missing-playwright-chromium",
          "missing-clean-install-source-lock",
        ],
      },
      null,
      2,
    ),
  );
} finally {
  rmSync(root, { recursive: true, force: true });
}
