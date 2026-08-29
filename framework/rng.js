import { randomUUID } from "node:crypto";

export function createRunId() {
  return `${new Date().toISOString().replaceAll(/[-:.TZ]/g, "")}-${randomUUID()}`;
}
