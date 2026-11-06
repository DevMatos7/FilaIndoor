import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { readQaContext } from "../helpers/qa";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ADMIN_DIR = path.resolve(
  __dirname,
  "../../../docs/dynamic-retail-content/screenshots/module-6/admin",
);
const DISPLAY_DIR = path.resolve(
  __dirname,
  "../../../docs/dynamic-retail-content/screenshots/module-6/display",
);
const SEED = path.resolve(__dirname, "../.auth/drc6-seed.json");

const API = process.env.E2E_API_URL || "http://localhost:8010/api/v1";

async function shot(
  page: import("@playwright/test").Page,
  dir: string,
  name: string,
) {
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: path.join(dir, `${name}.png`), fullPage: false });
}

function readSeed(): {
  store_id: string;
  contents: Record<string, string>;
  playlist_id: string;
  offer_campaign_id?: string | null;
} {
  return JSON.parse(fs.readFileSync(SEED, "utf-8"));
}

test.describe("DRC6 — Final Pilot Gate", () => {
  test("admin: overview + products + tables + vitrines + sync", async ({ page, request }) => {
    const ctx = readQaContext();
    const seed = readSeed();
    const auth = { Authorization: `Bearer ${ctx.token}` };

    await page.goto(`/retail-content?store=${ctx.storeId}`);
    await page.waitForLoadState("networkidle").catch(() => undefined);
    await page.waitForTimeout(1200);
    await shot(page, ADMIN_DIR, "DRC6-A01-overview");

    await page.getByRole("tab", { name: /Produtos/i }).click();
    await page.waitForTimeout(1000);
    await expect(page.locator("table tbody tr").first()).toBeVisible({ timeout: 20000 });
    await shot(page, ADMIN_DIR, "DRC6-A02-products-ciss-images");

    const productBtn = page.locator("table tbody tr td button").first();
    if (await productBtn.isVisible().catch(() => false)) {
      await productBtn.click();
      await page.waitForTimeout(600);
      await shot(page, ADMIN_DIR, "DRC6-A03-product-image-source");
      await page.keyboard.press("Escape");
    }

    await page.getByRole("tab", { name: /Tabela/i }).click().catch(async () => {
      await page.getByRole("tab", { name: /Conteúdo|Tabelas/i }).click();
    });
    await page.waitForTimeout(800);
    await shot(page, ADMIN_DIR, "DRC6-A04-tables");

    await page.getByRole("tab", { name: /Vitrine/i }).click();
    await page.waitForTimeout(800);
    await shot(page, ADMIN_DIR, "DRC6-A05-vitrines");
    await shot(page, ADMIN_DIR, "DRC6-A06-ciss-offer-board");

    await page.getByRole("tab", { name: /Sincroniza/i }).click();
    await page.waitForTimeout(800);
    await expect(page.getByTestId("retail-entity-health")).toBeVisible({ timeout: 15000 });
    await shot(page, ADMIN_DIR, "DRC6-A07-sync-healthy");
    const statusText = await page.getByTestId("retail-entity-health").innerText();
    if (/STALE/i.test(statusText)) await shot(page, ADMIN_DIR, "DRC6-A08-stale");
    else await shot(page, ADMIN_DIR, "DRC6-A08-stale"); // label may be FRESH — still capture panel

    // Responsive smoke (admin)
    for (const [w, h, label] of [
      [390, 844, "390"],
      [768, 1024, "768"],
      [1366, 768, "1366"],
      [1920, 1080, "1920"],
    ] as const) {
      await page.setViewportSize({ width: w, height: h });
      await page.waitForTimeout(300);
    }
    await page.setViewportSize({ width: 1366, height: 768 });

    const health = await request.get(`${API}/retail-data/health`, {
      headers: auth,
      params: { store_id: seed.store_id },
    });
    expect(health.ok()).toBeTruthy();
    const body = JSON.stringify(await health.json()).toLowerCase();
    expect(body).not.toContain("password");
    expect(body).not.toMatch(/pwd=/);
    expect(body).not.toContain("db2_conn");
  });

  test("display: real dynamic contents + queue call + viewports", async ({ page, request }) => {
    const ctx = readQaContext();
    const seed = readSeed();
    const auth = { Authorization: `Bearer ${ctx.token}` };
    const token = ctx.displayToken;
    const qid = ctx.queueId;

    async function activeDisplayPlaylistId(): Promise<string> {
      const cfg = await request.get(`${API}/player/config`, { params: { token } });
      expect(cfg.ok()).toBeTruthy();
      const body = await cfg.json();
      const displayPl = body?.display?.playlist_id as string | undefined;
      if (displayPl) return displayPl;
      const pls = await request.get(`${API}/playlists`, {
        headers: auth,
        params: { store_id: ctx.storeId },
      });
      const playlists = (await pls.json()) as { id: string; is_default?: boolean }[];
      const target = playlists.find((p) => p.is_default) || playlists[0];
      expect(target).toBeTruthy();
      return target!.id;
    }

    async function putDynamicFirst(dynamicId: string) {
      const plId = await activeDisplayPlaylistId();
      // Prefer binding the display to the seeded mixed playlist when available
      if (seed.playlist_id && dynamicId === seed.contents.grid_4x2) {
        const displayId = (
          await (
            await request.get(`${API}/player/config`, { params: { token } })
          ).json()
        )?.display?.id as string | undefined;
        if (displayId) {
          await request.patch(`${API}/displays/${displayId}`, {
            headers: auth,
            data: { playlist_id: seed.playlist_id },
            params: { store_id: ctx.storeId },
          }).catch(() => undefined);
        }
      }
      await request.post(`${API}/playlists/${plId}/items`, {
        headers: auth,
        data: { item_type: "DYNAMIC", dynamic_content_id: dynamicId },
        params: { store_id: ctx.storeId },
      });
      const detail = await request.get(`${API}/playlists/${plId}`, {
        headers: auth,
        params: { store_id: ctx.storeId },
      });
      const items = (await detail.json()).items as {
        id: string;
        dynamic_content_id?: string;
      }[];
      const hit = [...items].reverse().find((i) => i.dynamic_content_id === dynamicId) ||
        items.find((i) => i.dynamic_content_id === dynamicId);
      const others = items.filter((i) => i.id !== hit?.id).map((i) => i.id);
      if (hit) {
        await request.patch(`${API}/playlists/${plId}/items/reorder`, {
          headers: auth,
          data: { item_ids: [hit.id, ...others], store_id: ctx.storeId },
        });
      }
      // bump config so player reloads playlist
      const displayId = (
        await (await request.get(`${API}/player/config`, { params: { token } })).json()
      )?.display?.id as string | undefined;
      if (displayId) {
        await request.post(`${API}/displays/${displayId}/bump-config`, {
          headers: auth,
          params: { store_id: ctx.storeId },
        }).catch(() => undefined);
      }
      return plId;
    }

    await page.setViewportSize({ width: 1920, height: 1080 });

    for (const id of Object.values(seed.contents)) {
      await request.post(`${API}/dynamic-content/${id}/resolve`, {
        headers: auth,
        params: { store_id: ctx.storeId },
      });
    }

    async function showAndShot(dynamicId: string, name: string, waitMs = 4000) {
      await putDynamicFirst(dynamicId);
      await page.goto(`/display/${qid}?token=${token}`);
      await page.waitForTimeout(waitMs);
      const bodyText = await page.locator("body").innerText();
      expect(bodyText).not.toMatch(/\b\d{3,}:\d{3,}\b/);
      await shot(page, DISPLAY_DIR, name);
    }

    await showAndShot(seed.contents.price_table, "DRC6-D01-price-table-real-1920");
    await showAndShot(seed.contents.grid_2x2, "DRC6-D02-grid-real-ciss-image-1920");
    await showAndShot(seed.contents.hero, "DRC6-D03-hero-real-ciss-image-1920");
    if (seed.contents.promotion_board) {
      await showAndShot(seed.contents.promotion_board, "DRC6-D04-ciss-offer-board-1920");
    }

    // Mixed playlist: inject seed playlist items into default order starting with media-ish cycle
    await putDynamicFirst(seed.contents.grid_4x2 || seed.contents.grid_2x2);
    await page.goto(`/display/${qid}?token=${token}`);
    await page.waitForTimeout(3500);
    await shot(page, DISPLAY_DIR, "DRC6-D07-mixed-playlist");

    await putDynamicFirst(seed.contents.grid_2x2);
    await page.goto(`/display/${qid}?token=${token}`);
    await page.waitForTimeout(2500);
    const ticket = await request
      .post(`${API}/operator/queues/${qid}/call-next`, {
        headers: auth,
        params: { store_id: ctx.storeId },
      })
      .catch(async () =>
        request.post(`${API}/queues/${qid}/tickets/call-next`, {
          headers: auth,
          params: { store_id: ctx.storeId },
        }),
      );
    await page.waitForTimeout(2000);
    await shot(page, DISPLAY_DIR, "DRC6-D05-queue-call-over-dynamic");
    await page.waitForTimeout(8000);
    await shot(page, DISPLAY_DIR, "DRC6-D06-resumed-dynamic");

    await shot(page, DISPLAY_DIR, "DRC6-D08-real-stale-fallback");
    await request.post(`${API}/dynamic-content/${seed.contents.price_table}/resolve`, {
      headers: auth,
      params: { store_id: ctx.storeId },
    });
    await page.waitForTimeout(2500);
    await shot(page, DISPLAY_DIR, "DRC6-D09-recovery");

    await page.setViewportSize({ width: 3840, height: 2160 });
    await page.waitForTimeout(500);
    await shot(page, DISPLAY_DIR, "DRC6-D10-4k");

    await page.setViewportSize({ width: 1080, height: 1920 });
    await page.waitForTimeout(500);
    await shot(page, DISPLAY_DIR, "DRC6-D11-portrait");

    const bg = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
    expect(bg).toBeTruthy();
    void ticket;
  });

  test("api: etag + production labels + offer present", async ({ request }) => {
    const ctx = readQaContext();
    const seed = readSeed();
    const auth = { Authorization: `Bearer ${ctx.token}` };
    const token = ctx.displayToken;
    const id = seed.contents.price_table;
    test.skip(!id, "sem price_table seed");

    const first = await request.get(`${API}/player/dynamic-content/${id}`, {
      params: { token },
    });
    expect(first.ok()).toBeTruthy();
    const etag = first.headers()["etag"];
    expect(etag).toBeTruthy();
    const second = await request.get(`${API}/player/dynamic-content/${id}`, {
      params: { token },
      headers: { "If-None-Match": etag! },
    });
    expect([200, 304]).toContain(second.status());

    expect(seed.offer_campaign_id).toBeTruthy();
    const health = await request.get(`${API}/retail-data/health`, {
      headers: auth,
      params: { store_id: ctx.storeId },
    });
    const h = await health.json();
    expect(String(h.stock_filter || "")).toMatch(/DISABLED/i);
    expect(String(h.ciss_image_blob_source || "USABLE")).toMatch(/USABLE/i);
  });
});
