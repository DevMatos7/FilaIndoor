import { test, expect } from "@playwright/test";
import { saveShot } from "../helpers/api";
import { readQaContext } from "../helpers/qa";

test.describe("Totem 2.0", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("idle + double tap não duplica", async ({ page, request }) => {
    const ctx = readQaContext();
    const qid = ctx.queueId;

    // baseline waiting count via public/kiosk if available — use admin API
    const before = await request.get(`http://localhost:8010/api/v1/queues/${qid}/waiting`, {
      headers: { Authorization: `Bearer ${ctx.token}` },
    });
    const waitingBefore = before.ok() ? ((await before.json()) as unknown[]).length : 0;

    const totemUrl = `/totem/${qid}?token=${encodeURIComponent(ctx.kioskToken)}`;

    // unavailable (sem token) — evidência visual do estado
    await page.setViewportSize({ width: 800, height: 1280 });
    await page.goto(`/totem/${qid}`);
    await page.waitForTimeout(800);
    await saveShot(page, "totem/totem-unavailable-800x1280.png");

    await page.goto(totemUrl);
    await page.waitForTimeout(1200);
    await saveShot(page, "totem/totem-idle-800x1280.png");

    await page.setViewportSize({ width: 768, height: 1024 });
    await saveShot(page, "totem/totem-idle-768x1024.png");

    await page.setViewportSize({ width: 800, height: 1280 });
    const normalBtn = page.getByRole("button", { name: /Atendimento normal/i });
    await expect(normalBtn).toBeVisible({ timeout: 20000 });
    await normalBtn.dblclick({ delay: 40 });

    await page.waitForTimeout(2500);
    await saveShot(page, "totem/totem-success-or-processing-800x1280.png");
    // success / processing / printer_error — qualquer estado pós-emissão
    await expect(
      page.getByText(/sua senha|emitindo|impressora|não foi possível/i).first(),
    ).toBeVisible({ timeout: 10000 });

    const after = await request.get(`http://localhost:8010/api/v1/queues/${qid}/waiting`, {
      headers: { Authorization: `Bearer ${ctx.token}` },
    });
    if (after.ok()) {
      const waitingAfter = ((await after.json()) as unknown[]).length;
      // double tap should create at most +1 (not +2)
      expect(waitingAfter - waitingBefore).toBeLessThanOrEqual(1);
      expect(waitingAfter - waitingBefore).toBeGreaterThanOrEqual(0);
    }
  });
});

test.describe("Operator 2.0", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("operator ready / screenshots", async ({ page }) => {
    const ctx = readQaContext();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/operator/${ctx.queueId}`);
    await page.waitForTimeout(1500);

    // pick terminal if asked
    const term = page.getByRole("button", { name: /Balcão|ACOU|Terminal/i }).first();
    if (await term.isVisible().catch(() => false)) {
      await term.click();
    }
    const select = page.locator("select").first();
    if (await select.isVisible().catch(() => false)) {
      await select.selectOption({ index: 1 }).catch(() => undefined);
    }

    await saveShot(page, "operator/operator-390x844.png");
    await page.setViewportSize({ width: 768, height: 1024 });
    await saveShot(page, "operator/operator-768x1024.png");

    const next = page.getByRole("button", { name: /Próximo|NEXT|Chamar/i }).first();
    if (await next.isVisible().catch(() => false)) {
      await next.click();
      await page.waitForTimeout(1500);
      await page.setViewportSize({ width: 390, height: 844 });
      await saveShot(page, "operator/operator-serving-390x844.png");
    }
  });
});
