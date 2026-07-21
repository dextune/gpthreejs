import { cpSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const demoRoot = resolve(process.env.GPTHREEJS_CLEAN_INSTALL_SOURCE_ROOT || resolve(__dirname, ".."));
const preflightScript = resolve(__dirname, "dependency-preflight.mjs");
const cleanRoot = mkdtempSync(resolve(tmpdir(), "gpthreejs-demo-clean-"));

function quoteArg(value) {
  if (/^[A-Za-z0-9_./:@%+=,-]+$/.test(value)) return value;
  return `"${value.replace(/(["\\$`])/g, "\\$1")}"`;
}

function npmCommand() {
  return process.platform === "win32" ? "npm.cmd" : "npm";
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || cleanRoot,
    env: options.env || process.env,
    encoding: "utf8",
    stdio: "pipe",
  });
  if (result.status !== 0) {
    throw new Error(
      [
        `Command failed: ${command} ${args.join(" ")}`,
        `exit=${result.status}`,
        result.error ? `error=${result.error.message}` : "",
        result.stdout,
        result.stderr,
      ].join("\n"),
    );
  }
  return result;
}

try {
  const sourcePackageJson = resolve(demoRoot, "package.json");
  const sourcePackageLock = resolve(demoRoot, "package-lock.json");
  if (!existsSync(sourcePackageJson)) {
    throw new Error(`Missing ${sourcePackageJson}`);
  }
  if (!existsSync(sourcePackageLock)) {
    throw new Error(
      `Missing ${sourcePackageLock}; restore it from git or regenerate it with npm --prefix ${quoteArg(demoRoot)} install --package-lock-only before running clean-install smoke.`,
    );
  }
  cpSync(sourcePackageJson, resolve(cleanRoot, "package.json"));
  cpSync(sourcePackageLock, resolve(cleanRoot, "package-lock.json"));

  const installEnv = {
    ...process.env,
    NODE_ENV: "development",
    npm_config_production: "false",
    npm_config_omit: "",
  };
  run(npmCommand(), ["ci", "--include=dev"], { env: installEnv });
  run(npmCommand(), ["run", "provision:browser"]);
  const preflight = run(process.execPath, [preflightScript], {
    env: { ...process.env, GPTHREEJS_PREFLIGHT_ROOT: cleanRoot },
  });

  console.log(
    JSON.stringify(
      {
        ok: true,
        root: cleanRoot,
        install: "npm ci --include=dev",
        browserProvisioning: "npm run provision:browser",
        preflight: JSON.parse(preflight.stdout),
      },
      null,
      2,
    ),
  );
} catch (error) {
  console.error("gpthreejs demo clean-install smoke failed:");
  console.error(`- ${error.message}`);
  process.exitCode = 1;
} finally {
  rmSync(cleanRoot, { recursive: true, force: true });
}
