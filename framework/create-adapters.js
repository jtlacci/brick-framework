import { readdir } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { hash, pruneJsonFiles, readJson, safeKey, writeJson } from "./files.js";

function errorRecord(error) {
  return {
    name: error?.name ?? "Error",
    message: error?.message ?? String(error),
  };
}

export async function createAdapters({ moduleDirectory, config, runId, mode, parentRunId, adapterCalls }) {
  const adaptersDirectory = path.join(moduleDirectory, "input", "adapters");
  const entries = await readdir(adaptersDirectory, { withFileTypes: true });
  const adapters = {};
  let nextCallNumber = 1;

  for (const entry of entries.filter((item) => item.isFile() && item.name.endsWith(".js")).sort((a, b) => a.name.localeCompare(b.name))) {
    const adapter = (await import(pathToFileURL(path.join(adaptersDirectory, entry.name)))).default;
    if (!adapter?.name || typeof adapter.fetch !== "function") {
      throw new Error(`${entry.name} must default-export { name, fetch(args, context), key?(args) }`);
    }
    if (adapters[adapter.name]) throw new Error(`Duplicate adapter name '${adapter.name}'`);

    adapters[adapter.name] = async (args = {}) => {
      const callNumber = nextCallNumber;
      nextCallNumber += 1;
      const key = safeKey(adapter.key ? await adapter.key(args) : hash(args).slice(0, 24));
      const callId = `${callNumber}-${hash({ runId, args, key }).slice(0, 8)}`;
      const dataDirectory = path.join(moduleDirectory, "input", "data", safeKey(adapter.name));
      const sampleFile = path.join(dataDirectory, "samples", `${key}.json`);

      if (mode === "replay") {
        let sample;
        try {
          sample = await readJson(sampleFile);
        } catch (error) {
          let replayError = error;
          if (error.code === "ENOENT") {
            replayError = new Error(`No saved sample for adapter '${adapter.name}' key '${key}'. Run the smoke test with --FRESH.`);
          }
          adapterCalls.push({
            callId, source: adapter.name, key, mode, observedAt: new Date().toISOString(),
            error: errorRecord(replayError),
          });
          throw replayError;
        }
        adapterCalls.push({
          callId, source: adapter.name, key, mode, sample: path.relative(moduleDirectory, sampleFile),
          sampleHash: hash(sample.value), capturedAt: sample.capturedAt, observedAt: new Date().toISOString(),
        });
        return sample.value;
      }

      const capturedAt = new Date().toISOString();
      const envelope = { source: adapter.name, key, runId, parentRunId, callId, capturedAt, args };
      try {
        const value = await adapter.fetch(args, { runId, parentRunId, mode });
        const record = { ...envelope, ok: true, value };
        const callFile = path.join(dataDirectory, "calls", `${runId}-${callId}.json`);
        await writeJson(callFile, record);
        await writeJson(sampleFile, record);
        await pruneJsonFiles(path.dirname(callFile), config.retention.adapterCalls, "capturedAt");
        adapterCalls.push({
          callId, source: adapter.name, key, mode, sample: path.relative(moduleDirectory, sampleFile),
          sampleHash: hash(value), capturedAt,
        });
        return value;
      } catch (error) {
        const callFile = path.join(dataDirectory, "calls", `${runId}-${callId}.json`);
        await writeJson(callFile, { ...envelope, ok: false, error: errorRecord(error) });
        await pruneJsonFiles(path.dirname(callFile), config.retention.adapterCalls, "capturedAt");
        adapterCalls.push({ callId, source: adapter.name, key, mode, capturedAt, error: errorRecord(error) });
        throw error;
      }
    };
  }

  return Object.freeze(adapters);
}
