import { test, expect } from "@playwright/test";
import { saveShot } from "../helpers/api";
import { readQaContext, gotoAdmin } from "../helpers/qa";

test.describe("App Shell & route smoke", () => {
  test("shell carrega Command Center e StoreSwitcher", async ({ page }) => {
    await gotoAdmin(page, "/");
    await expect(page.getByRole("heading", { name: /Command Center|Operação|Visão/i }).or(page.locator("h1")).first()).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/Loja/i).first()).toBeVisible();
    await page.setViewportSize({ width: 1920, height: 1080 });
    await saveShot(page, "admin/command-center-1920x1080.png");
    await page.setViewportSize({ width: 1366, height: 768 });
    await saveShot(page, "admin/command-center-1366x768.png");
    await page.setViewportSize({ width: 768, height: 1024 });
    await saveShot(page, "admin/command-center-768x1024.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "admin/command-center-390x844.png");
  });

  test("rotas admin abrem sem crash", async ({ page }) => {
    const routes = [
      "/",
      "/analytics",
      "/queues",
      "/media",
      "/playlists",
      "/channels",
      "/devices",
      "/edge",
      "/integrations",
      "/history",
    ];
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const r of routes) {
      const res = await page.goto(r, { waitUntil: "domcontentloaded" });
      expect(res?.ok() || res?.status() === 304, `${r} status`).toBeTruthy();
      await expect(page.locator("body")).toBeVisible();
      expect(page.url()).not.toMatch(/\/login/);
    }
    const critical = errors.filter(
      (e) => !/ResizeObserver|Non-Error|chart|recharts/i.test(e),
    );
    expect(critical, critical.join("\n")).toEqual([]);
  });

  test("customer routes smoke", async ({ page }) => {
    const ctx = readQaContext();
    test.skip(!ctx.queueId, "queue id missing");
    await page.goto(`/totem/${ctx.queueId}`);
    await expect(page.locator("body")).toBeVisible();
    await page.goto(`/operator/${ctx.queueId}`);
    await expect(page.locator("body")).toBeVisible();
    await page.goto(`/display/${ctx.queueId}?token=display-acougue-audio`);
    await expect(page.locator("body")).toBeVisible();
    await page.goto("/pair");
    await expect(page.locator("body")).toBeVisible();
  });
});
