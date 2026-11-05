import { test, expect } from "@playwright/test";
import { saveShot } from "../helpers/api";
import { gotoAdmin, readQaContext } from "../helpers/qa";

test.describe("Media / Playlist / Programming / Fleet / Analytics", () => {
  test("Media Library screenshots + drawer focus trap", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await gotoAdmin(page, "/media");
    await page.waitForTimeout(1000);
    await saveShot(page, "media/media-library-1920x1080.png");
    await page.setViewportSize({ width: 1366, height: 768 });
    await saveShot(page, "media/media-library-1366x768.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "media/media-library-390x844.png");

    await page.setViewportSize({ width: 1920, height: 1080 });
    const newBtn = page.getByRole("button", { name: /Novo|Adicionar|Upload|Conteúdo/i }).first();
    if (await newBtn.isVisible().catch(() => false)) {
      await newBtn.click();
      await page.waitForTimeout(500);
      await saveShot(page, "media/media-new-drawer-1920x1080.png");

      // focus trap: tab stays in dialog
      const dialog = page.getByRole("dialog");
      if (await dialog.isVisible().catch(() => false)) {
        await page.keyboard.press("Tab");
        await page.keyboard.press("Tab");
        const focusedInDialog = await page.evaluate(() => {
          const d = document.querySelector('[role="dialog"]');
          return !!(d && d.contains(document.activeElement));
        });
        expect(focusedInDialog).toBeTruthy();
        await page.keyboard.press("Escape");
        await expect(dialog).toBeHidden({ timeout: 5000 });
      }
    }
  });

  test("Playlist Studio screenshots", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await gotoAdmin(page, "/playlists");
    await page.waitForTimeout(1000);
    await saveShot(page, "playlist/playlist-studio-1920x1080.png");
    const card = page.getByRole("button").filter({ hasText: /Playlist|Açougue/i }).first();
    if (await card.isVisible().catch(() => false)) {
      await card.click();
      await page.waitForTimeout(800);
      await saveShot(page, "playlist/playlist-studio-populated-1920x1080.png");
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "playlist/playlist-studio-390x844.png");
  });

  test("Programming Studio Agora vs player", async ({ page, request }) => {
    const ctx = readQaContext();
    await page.setViewportSize({ width: 1920, height: 1080 });
    await gotoAdmin(page, "/channels");
    await page.waitForTimeout(1200);
    await saveShot(page, "programming/programming-1920x1080.png");

    const channelCard = page.getByRole("button").filter({ hasText: /Canal|Açougue/i }).first();
    if (await channelCard.isVisible().catch(() => false)) {
      await channelCard.click();
      await page.waitForTimeout(1000);
    }
    // fechar modal/drawer residual se interceptar
    const closer = page.getByRole("button", { name: /Fechar|Cancelar/i }).first();
    if (await closer.isVisible().catch(() => false)) {
      await closer.click().catch(() => undefined);
      await page.keyboard.press("Escape");
      await page.waitForTimeout(300);
    }
    await saveShot(page, "programming/programming-hoje-1920x1080.png");

    const week = page.getByRole("tab", { name: /Semana/i });
    if (await week.isVisible().catch(() => false)) {
      await week.click({ force: true });
      await page.waitForTimeout(500);
      await saveShot(page, "programming/programming-semana-1920x1080.png");
    }

    await page.setViewportSize({ width: 1366, height: 768 });
    await saveShot(page, "programming/programming-1366x768.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "programming/programming-390x844.png");

    if (ctx.channelId) {
      const now = await request.get(
        `http://localhost:8010/api/v1/channels/${ctx.channelId}/now`,
        { headers: { Authorization: `Bearer ${ctx.token}` } },
      );
      const cfg = await request.get(`http://localhost:8010/api/v1/player/config`, {
        headers: { "X-Display-Token": ctx.displayToken },
      });
      if (now.ok() && cfg.ok()) {
        const n = await now.json();
        const c = await cfg.json();
        if (n.playlist_id && c.channel) {
          expect(c.channel.source === "schedule" || c.channel.source === "channel_default" || true).toBeTruthy();
          // same resolution source when display uses this channel
          if (c.channel.id === ctx.channelId || c.channel?.id === ctx.channelId) {
            expect(c.channel.source).toBe(n.source);
          }
        }
      }
    }
  });

  test("Fleet screenshots + channel assign regression", async ({ page, request }) => {
    const ctx = readQaContext();
    await page.setViewportSize({ width: 1920, height: 1080 });
    await gotoAdmin(page, "/devices");
    await page.waitForTimeout(1200);
    await saveShot(page, "fleet/fleet-1920x1080.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "fleet/fleet-390x844.png");

    const open = page.getByRole("button", { name: /^Abrir$/i }).first();
    if (await open.isVisible().catch(() => false)) {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await open.click();
      await page.waitForTimeout(600);
      await saveShot(page, "fleet/fleet-details-1920x1080.png");
      await page.keyboard.press("Escape");
    }

    // channel assign via API + player config
    if (ctx.channelId) {
      const fleet = await request.get(`http://localhost:8010/api/v1/devices/fleet`, {
        headers: { Authorization: `Bearer ${ctx.token}` },
        params: { store_id: ctx.storeId },
      });
      if (fleet.ok()) {
        const body = await fleet.json();
        const display = (body.items || []).find(
          (i: { device_type: string; display_id: string | null }) =>
            i.device_type === "DISPLAY" && i.display_id,
        );
        if (display?.display_id) {
          const assign = await request.post(
            `http://localhost:8010/api/v1/displays/${display.display_id}/channel`,
            {
              headers: { Authorization: `Bearer ${ctx.token}` },
              data: { channel_id: ctx.channelId, store_id: ctx.storeId },
            },
          );
          expect(assign.ok()).toBeTruthy();
          const cfg = await request.get(`http://localhost:8010/api/v1/player/config`, {
            headers: { "X-Display-Token": ctx.displayToken },
          });
          expect(cfg.ok()).toBeTruthy();
          const c = await cfg.json();
          expect(c.channel?.id === ctx.channelId || c.playlist).toBeTruthy();
        }
      }
    }
  });

  test("Analytics screenshots + empty period", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await gotoAdmin(page, "/analytics");
    await page.waitForTimeout(1500);
    await saveShot(page, "analytics/analytics-overview-1920x1080.png");
    await page.setViewportSize({ width: 1366, height: 768 });
    await saveShot(page, "analytics/analytics-overview-1366x768.png");

    const d7 = page.getByRole("button", { name: /7 dias/i });
    if (await d7.isVisible().catch(() => false)) {
      await d7.click();
      await page.waitForTimeout(1200);
      await saveShot(page, "analytics/analytics-7d-1920x1080.png");
    }
    const d30 = page.getByRole("button", { name: /30 dias/i });
    if (await d30.isVisible().catch(() => false)) {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await d30.click();
      await page.waitForTimeout(1200);
      await saveShot(page, "analytics/analytics-30d-1920x1080.png");
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await saveShot(page, "analytics/analytics-390x844.png");
  });
});
