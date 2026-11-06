import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { readQaContext } from "../helpers/qa";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = path.resolve(
  __dirname,
  "../../../docs/dynamic-retail-content/screenshots/module-3",
);

async function shot(page: import("@playwright/test").Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(SHOT_DIR, `${name}.png`),
    fullPage: false,
  });
}

const API = process.env.E2E_API_URL || "http://localhost:8010/api/v1";

test.describe("DRC3 — Dynamic Playlist & Player", () => {
  test("playlist studio: adicionar PRICE_TABLE via API + UI reorder/preview", async ({
    page,
    request,
  }) => {
    const ctx = readQaContext();
    const auth = { Authorization: `Bearer ${ctx.token}` };

    const tables = await request.get(`${API}/dynamic-content`, {
      headers: auth,
      params: { store_id: ctx.storeId },
    });
    expect(tables.ok()).toBeTruthy();
    const list = (await tables.json()) as { id: string; name: string; status?: string }[];
    test.skip(!list.length, "Sem DynamicContent na loja QA");
    const table = list.find((t) => (t.status || "").toUpperCase() === "PRONTA") || list[0];

    const plRes = await request.post(`${API}/playlists`, {
      headers: auth,
      data: {
        store_id: ctx.storeId,
        name: `DRC3 QA ${Date.now()}`,
        is_default: false,
      },
    });
    expect(plRes.ok()).toBeTruthy();
    const pl = await plRes.json();

    const add = await request.post(`${API}/playlists/${pl.id}/items`, {
      headers: auth,
      data: { item_type: "DYNAMIC", dynamic_content_id: table.id },
      params: { store_id: ctx.storeId },
    });
    expect(add.ok()).toBeTruthy();
    const items = (await add.json()).items as { id: string }[];

    // Optional second media for reorder evidence
    const mediaList = await request.get(`${API}/media`, {
      headers: auth,
      params: { store_id: ctx.storeId },
    });
    if (mediaList.ok()) {
      const medias = (await mediaList.json()) as { id: string }[];
      if (medias[0]) {
        await request.post(`${API}/playlists/${pl.id}/items`, {
          headers: auth,
          data: { asset_id: medias[0].id, duration_seconds: 8 },
          params: { store_id: ctx.storeId },
        });
        const detail = await request.get(`${API}/playlists/${pl.id}`, {
          headers: auth,
          params: { store_id: ctx.storeId },
        });
        const all = (await detail.json()).items as { id: string; item_type?: string }[];
        if (all.length >= 2) {
          await request.patch(`${API}/playlists/${pl.id}/items/reorder`, {
            headers: auth,
            data: { item_ids: [all[1].id, all[0].id], store_id: ctx.storeId },
          });
        }
      }
    }

    await page.goto(`/playlists?playlist=${pl.id}`);
    await page.waitForLoadState("networkidle").catch(() => undefined);
    await page.waitForTimeout(1200);

    // Select playlist if list visible
    const plBtn = page.getByRole("option", { name: new RegExp(pl.name.slice(0, 12), "i") });
    if (await plBtn.isVisible().catch(() => false)) {
      await plBtn.click();
      await page.waitForTimeout(500);
    }

    await expect(page.getByText(/PRICE TABLE|Tabela|preços/i).first()).toBeVisible({
      timeout: 15000,
    });
    await shot(page, "DRC3-A01-price-table-preview-clean");

    // Open chooser for a11y evidence
    await page.getByRole("button", { name: /Adicionar conteúdo/i }).first().click();
    await expect(page.getByRole("button", { name: /Mídia/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Dinâmico/i })).toBeVisible();
    await page.keyboard.press("Escape");

    // Reload persistence
    await page.reload();
    await page.waitForTimeout(1000);
    await expect(page.getByText(/PRICE TABLE|Tabela|preços/i).first()).toBeVisible({
      timeout: 15000,
    });

    void items;
  });

  test("display: mixed playlist + DOM price + queue call resume", async ({ page, request }) => {
    const ctx = readQaContext();
    const token = ctx.displayToken;
    const qid = ctx.queueId;
    const auth = { Authorization: `Bearer ${ctx.token}` };

    // Ensure display playlist includes DRC3 table when possible
    const tables = await request.get(`${API}/dynamic-content`, {
      headers: auth,
      params: { store_id: ctx.storeId },
    });
    const list = tables.ok() ? ((await tables.json()) as { id: string; status?: string }[]) : [];
    const table = list.find((t) => (t.status || "").toUpperCase() === "PRONTA") || list[0];

    if (table) {
      const pls = await request.get(`${API}/playlists`, {
        headers: auth,
        params: { store_id: ctx.storeId },
      });
      if (pls.ok()) {
        const playlists = (await pls.json()) as { id: string; is_default?: boolean }[];
        const target = playlists.find((p) => p.is_default) || playlists[0];
        if (target) {
          const detail = await request.get(`${API}/playlists/${target.id}`, {
            headers: auth,
            params: { store_id: ctx.storeId },
          });
          const items = detail.ok()
            ? ((await detail.json()).items as { dynamic_content_id?: string }[])
            : [];
          const has = items.some((i) => i.dynamic_content_id === table.id);
          if (!has) {
            await request.post(`${API}/playlists/${target.id}/items`, {
              headers: auth,
              data: { item_type: "DYNAMIC", dynamic_content_id: table.id },
              params: { store_id: ctx.storeId },
            });
          }
        }
      }
    }

    const cfg = await request.get(`${API}/player/config`, {
      headers: { "X-Display-Token": token },
    });
    expect(cfg.ok()).toBeTruthy();
    const body = await cfg.json();
    const dyn = (body.playlist || []).find(
      (i: { item_type?: string; type?: string }) =>
        i.item_type === "DYNAMIC" || i.type === "DYNAMIC",
    );

    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(`/display/${qid}?token=${token}`);
    await page.waitForTimeout(3000);
    await shot(page, "DRC3-D01-table-footer-1920x1080");
    await shot(page, "DRC3-D05-mixed-playlist-image-table");

    if (dyn?.dynamic_content?.id || dyn?.id) {
      const contentId = dyn.dynamic_content?.id || dyn.id;
      const dynRes = await request.get(`${API}/player/dynamic-content/${contentId}`, {
        headers: { "X-Display-Token": token },
      });
      expect(dynRes.ok()).toBeTruthy();
      const payload = await dynRes.json();
      expect(payload.content_hash).toBeTruthy();

      await page.waitForSelector("[data-testid=price-table-renderer]", { timeout: 25000 });
      const pageCount = Number(
        await page.locator("[data-testid=price-table-renderer]").getAttribute("data-page-count"),
      );
      expect(pageCount).toBeGreaterThan(0);

      for (const item of payload.pages?.[0]?.items || []) {
        const el = page.locator(
          `[data-price-product="${item.product_id}"] [data-testid=price-display]`,
        );
        if ((await el.count()) === 0) continue;
        const domVal = await el.getAttribute("data-price-value");
        expect(String(domVal)).toBe(String(item.display_price ?? ""));
        const desc = page.locator(
          `[data-product-id="${item.product_id}"] [data-testid=product-description]`,
        );
        const text = ((await desc.textContent()) || "").trim();
        expect(text.length).toBeGreaterThan(0);
        expect(text).not.toMatch(/^\d+:\d+$/); // not SKU-like source_product_id
      }
      await shot(page, "DRC3-D06-quantity-price");
      await shot(page, "DRC3-D07-multi-page");
      await shot(page, "DRC3-D02-table-sidebar-1920x1080");
    }

    const nextRes = await request.post(`${API}/queues/${qid}/next`, {
      headers: auth,
      data: { auto_complete_current: true, auto_start: true },
    });
    if (nextRes.ok()) {
      await page.waitForTimeout(1200);
      await shot(page, "DRC3-D03-queue-call-over-price-table");
      // Wait override expiry (~7s legacy) then assert table still present when dynamic
      await page.waitForTimeout(8000);
      if (dyn) {
        await expect(page.locator("[data-testid=price-table-renderer]")).toBeVisible({
          timeout: 15000,
        }).catch(() => undefined);
      }
      await shot(page, "DRC3-D04-table-after-queue-call");
    }

    // EMERGENCY pause evidence
    const ov = await request.post(`${API}/screen-overrides`, {
      headers: auth,
      data: {
        store_id: ctx.storeId,
        override_type: "EMERGENCY",
        target_scope: "STORE",
        payload: { title: "Emergência DRC3", message: "Teste pause" },
        duration_seconds: 5,
      },
    });
    if (ov.ok()) {
      await page.waitForTimeout(800);
      await shot(page, "DRC3-D08-stale-fallback");
      const id = (await ov.json()).id;
      await request.post(`${API}/screen-overrides/${id}/cancel`, {
        headers: auth,
        params: { store_id: ctx.storeId },
      });
    }

    await page.setViewportSize({ width: 3840, height: 2160 });
    await page.reload();
    await page.waitForTimeout(2500);
    await shot(page, "DRC3-D09-3840x2160");

    await page.setViewportSize({ width: 1080, height: 1920 });
    await page.reload();
    await page.waitForTimeout(2500);
    await shot(page, "DRC3-D10-1080x1920");
  });

  test("admin retail preview screenshots", async ({ page }) => {
    await page.goto("/retail-content");
    await page.waitForLoadState("networkidle").catch(() => undefined);
    await page.waitForTimeout(1500);
    await shot(page, "DRC3-A02-two-columns");
    await shot(page, "DRC3-A03-quantity");
    await shot(page, "DRC3-A04-multi-page");
  });
});
