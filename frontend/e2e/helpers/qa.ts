import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import type { QaContext } from "./api";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function readQaContext(): QaContext {
  const p = path.join(__dirname, "../.auth/qa-context.json");
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export async function gotoAdmin(
  page: import("@playwright/test").Page,
  route: string,
) {
  await page.goto(route);
  await page.waitForLoadState("networkidle").catch(() => undefined);
}
