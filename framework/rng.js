import { randomUUID } from "node:crypto";

export function createRunId() {
  return `${new Date().toISOString().replaceAll(/[-:.TZ]/g, "")}-${randomUUID().slice(0, 8)}`;
}
