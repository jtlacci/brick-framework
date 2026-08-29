import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import YAML from "yaml";
import { moduleNames, modulesRoot } from "./lib.mjs";

const errors = [];
const bannedBuiltins = new Set([
  "node:child_process", "child_process", "node:cluster", "cluster",
  "node:dgram", "dgram", "node:dns", "dns", "node:fs", "fs",
  "node:http", "http", "node:http2", "http2", "node:https", "https",
  "node:net", "net", "node:process", "process", "node:tls", "tls",
  "node:worker_threads", "worker_threads"
]);

async function exists(target) {
  try { await access(target); return true; } catch { return false; }
}

async function walk(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(target));
    else files.push(target);
  }
  return files;
}

function importsIn(source) {
  const imports = [];
  const pattern = /(?:from\s*|import\s*(?:\(\s*)?|require\s*\(\s*)["']([^"']+)["']/g;
  for (const match of source.matchAll(pattern)) imports.push(match[1]);
  return imports;
}

function directIoIn(source) {
  const checks = [
    [/(^|[^.\w])fetch\s*\(/m, "global fetch()"],
    [/(^|[^.\w])WebSocket\s*\(/m, "global WebSocket()"],
    [/(^|[^.\w])XMLHttpRequest\s*\(/m, "global XMLHttpRequest()"],
    [/(^|[^.\w])process\s*\./m, "global process"],
    [/(^|[^.\w])Deno\s*\./m, "global Deno"],
    [/(^|[^.\w])Bun\s*\./m, "global Bun"],
  ];
  return checks.filter(([pattern]) => pattern.test(source)).map(([, label]) => label);
}

for (const moduleName of await moduleNames()) {
  const moduleDirectory = path.join(modulesRoot, moduleName);
  for (const required of [
    "index.js", "input/config.yml", "input/adapters", "input/data",
    "runner/run.js", "runner/rng.js", "runner/runs", "runner/tests", "src"
  ]) {
    if (!await exists(path.join(moduleDirectory, required))) {
      errors.push(`${moduleName}: missing ${required}`);
    }
  }

  if (!await exists(path.join(moduleDirectory, "input", "config.yml"))) continue;
  const config = YAML.parse(await readFile(path.join(moduleDirectory, "input", "config.yml"), "utf8"));
  const allowedLibraries = new Set(config.srcLibraries ?? []);
  const srcDirectory = path.join(moduleDirectory, "src");
  if (!await exists(srcDirectory)) continue;

  for (const file of (await walk(srcDirectory)).filter((item) => item.endsWith(".js"))) {
    const source = await readFile(file, "utf8");
    for (const directIo of directIoIn(source)) {
      errors.push(`${path.relative(modulesRoot, file)}: banned direct I/O via ${directIo}`);
    }
    for (const specifier of importsIn(source)) {
      if (bannedBuiltins.has(specifier)) {
        errors.push(`${path.relative(modulesRoot, file)}: banned I/O import '${specifier}'`);
      } else if (specifier.startsWith(".")) {
        const resolved = path.resolve(path.dirname(file), specifier);
        if (!(resolved === srcDirectory || resolved.startsWith(`${srcDirectory}${path.sep}`))) {
          errors.push(`${path.relative(modulesRoot, file)}: relative import escapes src/`);
        }
      } else if (!allowedLibraries.has(specifier)) {
        errors.push(`${path.relative(modulesRoot, file)}: library '${specifier}' is not listed in config.yml srcLibraries`);
      }
    }
  }

  for (const file of (await walk(moduleDirectory)).filter((item) => item.endsWith(".js"))) {
    if (file.startsWith(`${path.join(moduleDirectory, "runner")}${path.sep}`)) continue;
    if (file.startsWith(`${srcDirectory}${path.sep}`)) continue;
    const source = await readFile(file, "utf8");
    for (const specifier of importsIn(source)) {
      if (specifier.includes("/src/") || specifier === "./src" || specifier === "../src") {
        errors.push(`${path.relative(modulesRoot, file)}: only runner/ may import src/`);
      }
    }
  }

  const publicEntry = (await readFile(path.join(moduleDirectory, "index.js"), "utf8")).trim();
  if (publicEntry !== 'export { run } from "./runner/run.js";') {
    errors.push(`${moduleName}/index.js: public entry must export only run() from runner/run.js`);
  }
}

if (errors.length) {
  console.error(errors.map((error) => `- ${error}`).join("\n"));
  process.exitCode = 1;
} else {
  console.log("Module boundaries are valid.");
}
