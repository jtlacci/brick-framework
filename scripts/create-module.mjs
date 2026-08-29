import { cp, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { modulesRoot, root } from "./lib.mjs";

const name = process.argv[2];
if (!name || !/^[a-z][a-z0-9-]*$/.test(name)) {
  throw new Error("Usage: npm run module:new -- <lowercase-kebab-name>");
}

const source = path.join(root, "templates", "module");
const destination = path.join(modulesRoot, name);

await mkdir(destination);
await cp(source, destination, { recursive: true });

async function replacePlaceholders(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await replacePlaceholders(target);
    } else {
      const content = await readFile(target, "utf8");
      await writeFile(target, content.replaceAll("__MODULE_NAME__", name));
    }
  }
}

await replacePlaceholders(destination);
console.log(`Created modules/${name}`);
