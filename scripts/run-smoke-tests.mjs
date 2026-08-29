import path from "node:path";
import { pathToFileURL } from "node:url";
import { jsonFiles, moduleNames, modulesRoot, readJson } from "./lib.mjs";

const unknownFlags = process.argv.slice(2).filter((arg) => arg !== "--FRESH");
if (unknownFlags.length > 0) {
  throw new Error(`Unknown argument(s): ${unknownFlags.join(", ")}`);
}

const mode = process.argv.includes("--FRESH") ? "fresh" : "replay";
let count = 0;

for (const moduleName of await moduleNames()) {
  const moduleDirectory = path.join(modulesRoot, moduleName);
  const { run } = await import(pathToFileURL(path.join(moduleDirectory, "index.js")));
  const tests = await jsonFiles(path.join(moduleDirectory, "runner", "tests"));

  for (const testFile of tests) {
    const input = await readJson(testFile);
    const testName = path.basename(testFile, ".json");
    const { runId } = await run(input, { mode, testName });
    console.log(`PASS ${moduleName}/${testName} (${mode}, ${runId})`);
    count += 1;
  }
}

if (count === 0) {
  throw new Error("No smoke-test inputs found.");
}

console.log(`\n${count} smoke test(s) passed.`);
