import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { allFiles, jsonFiles, moduleNames, modulesRoot, readJson } from "./lib.mjs";

const unknownFlags = process.argv.slice(2).filter((arg) => arg !== "--FRESH");
if (unknownFlags.length > 0) {
  throw new Error(`Unknown argument(s): ${unknownFlags.join(", ")}`);
}

const mode = process.argv.includes("--FRESH") ? "fresh" : "replay";
let count = 0;
const names = await moduleNames();

async function replaySideEffectState(currentModule) {
  const watched = [];
  for (const moduleName of names) {
    const moduleDirectory = path.join(modulesRoot, moduleName);
    const inputFiles = await allFiles(path.join(moduleDirectory, "input", "data"));
    watched.push(...inputFiles.filter((file) => file.split(path.sep).includes("calls")));
    if (moduleName !== currentModule) {
      watched.push(...(await allFiles(path.join(moduleDirectory, "runner", "runs"))).filter((file) => file.endsWith(".json")));
    }
  }
  const state = [];
  for (const file of watched.sort()) {
    state.push([path.relative(modulesRoot, file), await readFile(file, "utf8")]);
  }
  return JSON.stringify(state);
}

for (const moduleName of names) {
  const moduleDirectory = path.join(modulesRoot, moduleName);
  const { run } = await import(pathToFileURL(path.join(moduleDirectory, "index.js")));
  const tests = await jsonFiles(path.join(moduleDirectory, "runner", "tests"));

  for (const testFile of tests) {
    const input = await readJson(testFile);
    const testName = path.basename(testFile, ".json");
    const before = mode === "replay" ? await replaySideEffectState(moduleName) : undefined;
    const { runId } = await run(input, { mode, testName });
    const after = mode === "replay" ? await replaySideEffectState(moduleName) : undefined;
    if (before !== after) {
      throw new Error(`${moduleName}/${testName} replay caused an adapter call or entered another module`);
    }
    console.log(`PASS ${moduleName}/${testName} (${mode}, ${runId})`);
    count += 1;
  }
}

if (count === 0) {
  throw new Error("No smoke-test inputs found.");
}

console.log(`\n${count} smoke test(s) passed.`);
