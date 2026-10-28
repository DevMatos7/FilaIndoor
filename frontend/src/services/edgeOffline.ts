/** Cache local + outbox client-side (Sprint 11). */

const CACHE_PREFIX = "filaindoor_edge_cache:";
const OUTBOX_KEY = "filaindoor_edge_outbox";

export type EdgeOutboxItem = {
  event_id: string;
  store_id: string;
  event_type: string;
  payload?: Record<string, unknown>;
  origin_device?: string;
  occurred_at: string;
};

const apiBase = () => import.meta.env.VITE_API_URL || "/api/v1";

export function cacheKey(kind: string, id: string) {
  return `${CACHE_PREFIX}${kind}:${id}`;
}

export function saveCache<T>(kind: string, id: string, data: T) {
  try {
    localStorage.setItem(
      cacheKey(kind, id),
      JSON.stringify({ saved_at: Date.now(), data }),
    );
  } catch {
    /* quota */
  }
}

export function loadCache<T>(kind: string, id: string, maxAgeMs = 5 * 60 * 1000): T | null {
  try {
    const raw = localStorage.getItem(cacheKey(kind, id));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { saved_at: number; data: T };
    if (Date.now() - parsed.saved_at > maxAgeMs) return null;
    return parsed.data;
  } catch {
    return null;
  }
}

export function readOutbox(): EdgeOutboxItem[] {
  try {
    return JSON.parse(localStorage.getItem(OUTBOX_KEY) || "[]") as EdgeOutboxItem[];
  } catch {
    return [];
  }
}

export function enqueueLocal(item: Omit<EdgeOutboxItem, "occurred_at" | "event_id"> & { event_id?: string }) {
  const list = readOutbox();
  const event: EdgeOutboxItem = {
    event_id: item.event_id || crypto.randomUUID(),
    store_id: item.store_id,
    event_type: item.event_type,
    payload: item.payload,
    origin_device: item.origin_device,
    occurred_at: new Date().toISOString(),
  };
  list.push(event);
  localStorage.setItem(OUTBOX_KEY, JSON.stringify(list.slice(-200)));
  return event;
}

export async function flushLocalOutbox(): Promise<{ flushed: number }> {
  const list = readOutbox();
  if (list.length === 0) return { flushed: 0 };
  const res = await fetch(`${apiBase()}/edge/outbox`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ events: list }),
  });
  if (!res.ok) throw new Error("Falha ao enviar outbox");
  localStorage.setItem(OUTBOX_KEY, "[]");
  return { flushed: list.length };
}

export function subscribeConnectivity(onChange: (online: boolean) => void) {
  const ping = async () => {
    if (!navigator.onLine) {
      onChange(false);
      return;
    }
    try {
      const res = await fetch(`${apiBase().replace(/\/api\/v1$/, "")}/health`, { cache: "no-store" });
      onChange(res.ok);
    } catch {
      onChange(false);
    }
  };
  const onOnline = () => {
    onChange(true);
    void flushLocalOutbox().catch(() => undefined);
  };
  const onOffline = () => onChange(false);
  window.addEventListener("online", onOnline);
  window.addEventListener("offline", onOffline);
  const id = window.setInterval(() => void ping(), 15000);
  void ping();
  return () => {
    window.removeEventListener("online", onOnline);
    window.removeEventListener("offline", onOffline);
    window.clearInterval(id);
  };
}
