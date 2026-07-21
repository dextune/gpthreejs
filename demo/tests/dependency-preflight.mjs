import { createRequire } from "node:module";
import { accessSync, constants, existsSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const demoRoot = resolve(scriptPath, "..", "..");
const root = resolve(process.env.GPTHREEJS_PREFLIGHT_ROOT || demoRoot);

const requiredBins = [
  ["tsc", "typescript"],
  ["vite", "vite"],
  ["playwright", "playwright"],
];

function binPath(name) {
  const base = resolve(root, "node_modules", ".bin", name);
  if (process.platform === "win32") return `${base}.cmd`;
  return base;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function quoteArg(value) {
  if (/^[A-Za-z0-9_./:@%+=,-]+$/.test(value)) return value;
  return `"${value.replace(/(["\\$`])/g, "\\$1")}"`;
}

function actionableInstallCommand() {
  return `npm --prefix ${quoteArg(root)} ci --include=dev`;
}

function packageDir(packageName) {
  const parts = packageName.split("/");
  return resolve(root, "node_modules", ...parts);
}

function readablePackageManifest(packageName) {
  const manifest = resolve(packageDir(packageName), "package.json");
  try {
    readJson(manifest);
    return true;
  } catch {
    return false;
  }
}

function executableFile(path) {
  try {
    const stat = statSync(path);
    if (!stat.isFile()) return false;
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function packageNames(packageJson) {
  return [
    ...Object.keys(packageJson.dependencies || {}),
    ...Object.keys(packageJson.devDependencies || {}),
  ].sort();
}

function withTimeout(promise, ms, message) {
  let timeout;
  return Promise.race([
    promise.finally(() => clearTimeout(timeout)),
    new Promise((_, reject) => {
      timeout = setTimeout(() => reject(new Error(message)), ms);
    }),
  ]);
}

async function probeChromium(requireFromDemo) {
  let browserServer;
  try {
    const { chromium } = requireFromDemo("playwright");
    browserServer = await chromium.launchServer({ timeout: 10_000 });
  } finally {
    const process = browserServer?.process();
    if (browserServer) {
      try {
        await withTimeout(browserServer.close(), 3_000, "Timed out closing Playwright Chromium");
      } catch (error) {
        if (process && process.exitCode === null && process.signalCode === null) {
          process.kill("SIGKILL");
        }
        throw error;
      }
    }
  }
}

async function collectProblems() {
  const problems = [];
  const packageJsonPath = resolve(root, "package.json");
  const packageLockPath = resolve(root, "package-lock.json");
  const nodeModulesPath = resolve(root, "node_modules");
  let packageJson;

  if (!existsSync(packageJsonPath)) {
    problems.push({
      code: "missing-package-json",
      message: `Missing ${packageJsonPath}`,
    });
    return problems;
  }

  if (!existsSync(packageLockPath)) {
    problems.push({
      code: "missing-package-lock",
      message: `Missing ${packageLockPath}; restore it from git or regenerate it with npm --prefix ${quoteArg(root)} install --package-lock-only before running npm ci.`,
    });
  }

  if (!existsSync(nodeModulesPath)) {
    problems.push({
      code: "missing-node-modules",
      message: existsSync(packageLockPath)
        ? `Dependencies are not installed. Run: ${actionableInstallCommand()}`
        : `Dependencies are not installed, but npm ci requires package-lock.json first.`,
    });
    return problems;
  }

  packageJson = readJson(packageJsonPath);
  const requireFromDemo = createRequire(packageJsonPath);
  for (const packageName of packageNames(packageJson)) {
    if (!readablePackageManifest(packageName)) {
      problems.push({
        code: "invalid-package",
        message: `Missing or unreadable npm package manifest for '${packageName}'. Run: ${actionableInstallCommand()}`,
      });
    }
  }

  for (const [binName, packageName] of requiredBins) {
    if (!executableFile(binPath(binName))) {
      problems.push({
        code: "invalid-binary",
        message: `Missing or non-executable ${binName} binary from '${packageName}'. Run: ${actionableInstallCommand()}`,
      });
    }
  }

  const canProbeBrowser =
    readablePackageManifest("playwright") && executableFile(binPath("playwright"));
  if (canProbeBrowser) {
    try {
      await probeChromium(requireFromDemo);
    } catch (error) {
      problems.push({
        code: "playwright-chromium-unavailable",
        message: `Playwright Chromium launch failed: ${error.message}. Run: npm --prefix ${quoteArg(root)} run provision:browser`,
      });
    }
  }

  return problems;
}

function validatePackageScripts() {
  const packageJson = readJson(resolve(root, "package.json"));
  const scripts = packageJson.scripts || {};
  const requiredScripts = [
    "preflight",
    "provision:browser",
    "typecheck",
    "build",
    "test:runtime",
    "capture:smoke",
    "verify:clean-install",
    "check",
  ];
  return requiredScripts
    .filter((script) => !scripts[script])
    .map((script) => ({
      code: "missing-script",
      message: `Missing package script '${script}' in ${resolve(root, "package.json")}`,
    }));
}

async function main() {
  const packageJsonPath = resolve(root, "package.json");
  const problems = [
    ...(await collectProblems()),
    ...(existsSync(packageJsonPath) ? validatePackageScripts() : []),
  ];
  if (problems.length) {
    console.error("gpthreejs demo dependency preflight failed:");
    for (const problem of problems) {
      console.error(`- [${problem.code}] ${problem.message}`);
    }
    console.error(`After fixing dependencies, run: npm --prefix ${quoteArg(root)} run check`);
    return 1;
  }

  console.log(
    JSON.stringify(
      {
        ok: true,
        root,
        packages: packageNames(readJson(resolve(root, "package.json"))),
        binaries: requiredBins.map(([binName]) => binName),
        browser: "playwright-chromium-launch",
      },
      null,
      2,
    ),
  );
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
