import { test as setup, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { discoverQaContext, loginApi } from "./helpers/api";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const authFile = path.join(__dirname, ".auth/admin.json");
const ctxFile = path.join(__dirname, ".auth/qa-context.json");

setup("authenticate admin", async ({ page, request }) => {
  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  const token = await loginApi(request);
  const ctx = await discoverQaContext(request, token);
  fs.writeFileSync(ctxFile, JSON.stringify(ctx, null, 2));

  await page.goto("/login");
  await page.getByLabel("E-mail").fill("admin@real.local");
  await page.getByLabel("Senha").fill("admin123");
  await page.getByRole("button", { name: /Entrar|Acessar|Login/i }).click();
  await expect(page).not.toHaveURL(/\/login/);
  await page.waitForTimeout(500);
  await page.context().storageState({ path: authFile });
});
