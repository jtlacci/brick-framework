import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig } from "./config.js";
import { pruneJsonFiles, writeJson } from "./files.js";

function serializeError(error) {
  return {
    name: error?.name ?? "Error",
    message: error?.message ?? String(error),
    stack: error?.stack,
  };
}

function sortAdapterCalls(adapterCalls) {
  adapterCalls.sort((left, right) => Number.parseInt(left.callId, 10) - Number.parseInt(right.callId, 10));
}

export function createModuleRunner({ moduleDirectory: directoryUrl, execute, createAdapters, createRunId }) {
  const moduleDirectory = fileURLToPath(directoryUrl);

  return async function run(input, options = {}) {
    const mode = options.mode ?? "replay";
    if (!['replay', 'fresh'].includes(mode)) throw new Error(`mode must be 'replay' or 'fresh'; received '${mode}'`);

    const runId = createRunId();
    const startedAt = new Date().toISOString();
    const startedClock = performance.now();
    const adapterCalls = [];
    const runFile = path.join(moduleDirectory, "runner", "runs", `${runId}.json`);
    let config;
    let baseRecord = {
      schemaVersion: 1,
      runId,
      module: path.basename(moduleDirectory),
      mode,
      kind: options.testName ? "test" : "run",
      testName: options.testName,
      parentRunId: options.parentRunId,
      startedAt,
      input,
      adapterCalls,
    };

    try {
      config = await loadConfig(moduleDirectory);
      baseRecord = { ...baseRecord, module: config.module };
      const adapters = await createAdapters({
        moduleDirectory, config, runId, mode, parentRunId: options.parentRunId, adapterCalls,
      });
      const result = await execute({ input, config, adapters, runId });
      sortAdapterCalls(adapterCalls);
      const finishedAt = new Date().toISOString();
      await writeJson(runFile, {
        ...baseRecord,
        finishedAt,
        durationMs: Math.round((performance.now() - startedClock) * 1000) / 1000,
        ok: true,
        result,
      });
      await pruneJsonFiles(path.dirname(runFile), config.retention.runs, "startedAt");
      return { runId, result };
    } catch (error) {
      sortAdapterCalls(adapterCalls);
      const finishedAt = new Date().toISOString();
      await writeJson(runFile, {
        ...baseRecord,
        finishedAt,
        durationMs: Math.round((performance.now() - startedClock) * 1000) / 1000,
        ok: false,
        error: serializeError(error),
      });
      await pruneJsonFiles(path.dirname(runFile), config?.retention?.runs ?? 10, "startedAt");
      error.runId = runId;
      throw error;
    }
  };
}
