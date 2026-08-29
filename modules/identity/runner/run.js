import { createModuleRunner } from "../../../framework/create-module-runner.js";
import { createAdapters } from "../input/create-adapters.js";
import { execute } from "../src/index.js";
import { createRunId } from "./rng.js";

export const run = createModuleRunner({
  moduleDirectory: new URL("..", import.meta.url),
  createAdapters,
  createRunId,
  execute,
});
