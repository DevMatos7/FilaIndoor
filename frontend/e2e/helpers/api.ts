import { APIRequestContext, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const API = process.env.E2E_API_URL || "http://localhost:8010/api/v1";

export type QaContext = {
  token: string;
  storeId: string;
  storeName: string;
  queueId: string;
  displayToken: string;
  kioskToken: string;
  channelId?: string;
};

export async function loginApi(
  request: APIRequestContext,
  email = "admin@real.local",
  password = "admin123",
): Promise<string> {
  const res = await request.post(`${API}/auth/login`, {
    form: { username: email, password },
  });
  expect(res.ok(), `login failed: ${res.status()}`).toBeTruthy();
  const body = await res.json();
  return body.access_token as string;
}

export async function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function discoverQaContext(request: APIRequestContext, token: string): Promise<QaContext> {
  const headers = await authHeaders(token);
  const stores = await (await request.get(`${API}/stores`, { headers })).json();
  expect(Array.isArray(stores) && stores.length > 0).toBeTruthy();
  const store = stores.find((s: { name: string }) => /Campo Novo/i.test(s.name)) || stores[0];

  const queues = await (await request.get(`${API}/queues`, { headers })).json();
  expect(Array.isArray(queues) && queues.length > 0).toBeTruthy();
  const queue = queues.find((q: { name: string }) => /Açougue|Acougue/i.test(q.name)) || queues[0];

  // display / kiosk tokens from seed (see backend/scripts/seed_data.py + settings)
  const displayToken = "display-acougue-audio";
  const kioskToken = "kiosk-acougue-demo";

  const channels = await request.get(`${API}/channels`, {
    headers,
    params: { store_id: store.id },
  });
  let channelId: string | undefined;
  if (channels.ok()) {
    const list = await channels.json();
    channelId = list[0]?.id;
  }

  return {
    token,
    storeId: store.id,
    storeName: store.name,
    queueId: queue.id,
    displayToken,
    kioskToken,
    channelId,
  };
}

export async function ensureMinimalIndoor(request: APIRequestContext, ctx: QaContext) {
  const headers = await authHeaders(ctx.token);
  // ensure channel exists
  if (!ctx.channelId) {
    const created = await request.post(`${API}/channels`, {
      headers,
      data: { store_id: ctx.storeId, name: "Canal QA UX12" },
    });
    if (created.ok()) {
      ctx.channelId = (await created.json()).id;
    }
  }
  return ctx;
}

export function finalShotDir(...parts: string[]) {
  const root = path.resolve(__dirname, "../../../docs/productization/screenshots/final");
  const dir = path.join(root, ...parts);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export async function saveShot(page: import("@playwright/test").Page, relativePath: string) {
  const full = path.join(
    path.resolve(__dirname, "../../../docs/productization/screenshots/final"),
    relativePath,
  );
  fs.mkdirSync(path.dirname(full), { recursive: true });
  await page.screenshot({ path: full, fullPage: false });
  return full;
}
