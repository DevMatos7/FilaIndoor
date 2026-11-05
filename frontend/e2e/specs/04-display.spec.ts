import { test, expect } from "@playwright/test";
import { saveShot } from "../helpers/api";
import { readQaContext } from "../helpers/qa";

test.describe("Display 2.0", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("player layouts e overrides screenshots", async ({ page, request }) => {
    const ctx = readQaContext();
    const token = ctx.displayToken;
    const qid = ctx.queueId;
    const API = "http://localhost:8010/api/v1";

    // resolve layouts via config
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(`/display/${qid}?token=${token}`);
    await page.waitForTimeout(2500);
    await expect(page.locator("body")).toBeVisible();
    await saveShot(page, "display/display-player-1920x1080.png");

    // try footer layout by assigning template if API available
    const cfg = await request.get(`${API}/player/config`, {
      headers: { "X-Display-Token": token },
    });
    expect(cfg.ok()).toBeTruthy();
    const cfgBody = await cfg.json();
    expect(cfgBody.playlist || cfgBody.channel).toBeTruthy();

    // capture current as media_queue_footer candidate (seed default)
    await saveShot(page, "display/display-media-queue-footer-1920x1080.png");

    // create EMERGENCY override if possible
    const ov = await request.post(`${API}/screen-overrides`, {
      headers: { Authorization: `Bearer ${ctx.token}` },
      data: {
        store_id: ctx.storeId,
        override_type: "EMERGENCY",
        target_scope: "STORE",
        payload: { title: "Emergência QA", message: "Evacuação de teste UX-12" },
        duration_seconds: 90,
      },
    });
    if (ov.ok()) {
      await page.reload();
      await page.waitForTimeout(2000);
      await saveShot(page, "display/display-emergency-1920x1080.png");
      const id = (await ov.json()).id;
      await request.post(`${API}/screen-overrides/${id}/cancel`, {
        headers: { Authorization: `Bearer ${ctx.token}` },
        params: { store_id: ctx.storeId },
      });
    }

    // QUEUE_CALL real via NEXT (override auto, ~7s)
    await page.setViewportSize({ width: 1920, height: 1080 });
    const nextRes = await request.post(`${API}/queues/${qid}/next`, {
      headers: { Authorization: `Bearer ${ctx.token}` },
      data: { auto_complete_current: true, auto_start: true },
    });
    if (nextRes.ok()) {
      await page.reload();
      await page.waitForTimeout(1200);
      await saveShot(page, "display/display-queue-call-1920x1080.png");
      await page.waitForTimeout(8000); // deixa expirar
    }

    // MANUAL (campanha) — evidência separada
    const manual = await request.post(`${API}/screen-overrides`, {
      headers: { Authorization: `Bearer ${ctx.token}` },
      data: {
        store_id: ctx.storeId,
        override_type: "MANUAL",
        target_scope: "STORE",
        payload: { title: "Campanha QA", message: "Promoção controlada UX-12" },
        duration_seconds: 60,
      },
    });
    if (manual.ok()) {
      await page.reload();
      await page.waitForTimeout(1500);
      await saveShot(page, "display/display-manual-1920x1080.png");
      // keep file name used by matrix as alias evidence
      await saveShot(page, "display/display-queue-call-or-manual-1920x1080.png");
      const id = (await manual.json()).id;
      await request.post(`${API}/screen-overrides/${id}/cancel`, {
        headers: { Authorization: `Bearer ${ctx.token}` },
        params: { store_id: ctx.storeId },
      });
    }

    // sidebar / fullscreen — switch layout templates if list exists
    const layouts = await request.get(`${API}/layout-templates`, {
      headers: { Authorization: `Bearer ${ctx.token}` },
      params: { store_id: ctx.storeId },
    });
    if (layouts.ok() && ctx.channelId) {
      const list = (await layouts.json()) as Array<{ id: string; slug: string }>;
      const sidebar = list.find((l) => l.slug === "media_queue_sidebar");
      const full = list.find((l) => l.slug === "queue_fullscreen");
      const mediaFull = list.find((l) => l.slug === "fullscreen_media");

      async function applyLayout(slug: string, templateId: string, file: string) {
        await request.patch(`${API}/channels/${ctx.channelId}`, {
          headers: { Authorization: `Bearer ${ctx.token}` },
          data: { layout_template_id: templateId, store_id: ctx.storeId },
        });
        await page.reload();
        await page.waitForTimeout(2500);
        await saveShot(page, `display/${file}`);
      }

      if (sidebar) await applyLayout("media_queue_sidebar", sidebar.id, "display-media-queue-sidebar-1920x1080.png");
      if (full) await applyLayout("queue_fullscreen", full.id, "display-queue-fullscreen-1920x1080.png");
      if (mediaFull) await applyLayout("fullscreen_media", mediaFull.id, "display-fullscreen-media-1920x1080.png");

      // restore footer
      const footer = list.find((l) => l.slug === "media_queue_footer");
      if (footer) {
        await request.patch(`${API}/channels/${ctx.channelId}`, {
          headers: { Authorization: `Bearer ${ctx.token}` },
          data: { layout_template_id: footer.id, store_id: ctx.storeId },
        });
      }
    }

    // portrait sanity
    await page.setViewportSize({ width: 1080, height: 1920 });
    await page.reload();
    await page.waitForTimeout(1500);
    await saveShot(page, "display/display-portrait-1080x1920.png");

    // 4K
    await page.setViewportSize({ width: 3840, height: 2160 });
    await page.reload();
    await page.waitForTimeout(1500);
    await saveShot(page, "display/display-media-queue-footer-3840x2160.png");
  });
});
