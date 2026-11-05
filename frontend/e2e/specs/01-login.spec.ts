import { test, expect } from "@playwright/test";
import { saveShot } from "../helpers/api";

test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Login", () => {
  test("login inválido mostra erro", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail").fill("wrong@real.local");
    await page.getByLabel("Senha").fill("bad");
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(page.getByText(/Falha no login/i)).toBeVisible();
  });

  test("login válido e redirect protegido", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => localStorage.clear());
    await page.goto("/analytics");
    await expect(page).toHaveURL(/\/login/);
    await expect(page).toHaveURL(/next=/);
    await page.getByLabel("E-mail").fill("admin@real.local");
    await page.getByLabel("Senha").fill("admin123");
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(page).toHaveURL(/\/analytics/, { timeout: 20000 });
  });

  test("screenshot login desktop e mobile", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.setViewportSize({ width: 1920, height: 1080 });
    await saveShot(page, "admin/login-1920x1080.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "admin/login-390x844.png");
  });
});
