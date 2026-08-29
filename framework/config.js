import { readFile } from "node:fs/promises";
import path from "node:path";
import YAML from "yaml";

export async function loadConfig(moduleDirectory) {
  const file = path.join(moduleDirectory, "input", "config.yml");
  const config = YAML.parse(await readFile(file, "utf8"));
  if (!config?.module) throw new Error(`${file} must define module`);
  if (!Number.isInteger(config?.retention?.runs) || config.retention.runs < 1) {
    throw new Error(`${file} retention.runs must be a positive integer`);
  }
  if (!Number.isInteger(config?.retention?.adapterCalls) || config.retention.adapterCalls < 1) {
    throw new Error(`${file} retention.adapterCalls must be a positive integer`);
  }
  return config;
}
