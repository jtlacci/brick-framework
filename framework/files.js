import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";

export async function readJson(file) {
  return JSON.parse(await readFile(file, "utf8"));
}

export async function writeJson(file, value) {
  await mkdir(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`);
  await rename(temporary, file);
}

export function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function hash(value) {
  return createHash("sha256").update(typeof value === "string" ? value : stableJson(value)).digest("hex");
}

export function safeKey(key) {
  const text = String(key);
  return /^[a-zA-Z0-9._-]{1,100}$/.test(text) ? text : hash(text).slice(0, 24);
}

export async function pruneJsonFiles(directory, keep, timestampField) {
  if (!Number.isInteger(keep) || keep < 1) throw new Error(`Retention must be a positive integer; received ${keep}`);
  const entries = await readdir(directory, { withFileTypes: true }).catch((error) => {
    if (error.code === "ENOENT") return [];
    throw error;
  });
  const records = [];
  for (const entry of entries.filter((item) => item.isFile() && item.name.endsWith(".json"))) {
    const file = path.join(directory, entry.name);
    try {
      const record = await readJson(file);
      records.push({ file, timestamp: record[timestampField] ?? "" });
    } catch {
      records.push({ file, timestamp: "" });
    }
  }
  records.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  await Promise.all(records.slice(keep).map(({ file }) => rm(file)));
}
