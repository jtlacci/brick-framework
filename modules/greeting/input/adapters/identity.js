import { run as runIdentity } from "../../../identity/index.js";

export default {
  name: "identity",
  async fetch(args, context) {
    return runIdentity(args, {
      mode: context.mode,
      parentRunId: context.runId,
    });
  },
};
