import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import { flushLocalOutbox, readOutbox } from "../services/edgeOffline";

type Store = { id: string; name: string };
type SyncStatus = {
  store_id: string | null;
  pending: number;
  failed: number;
  synced: number;
  counts: Record<string, number>;
};
type OutboxEvent = {
  event_id: string;
  event_type: string;
  sync_status: string;
  occurred_at: string | null;
  origin_device: string | null;
  attempts: number;
  last_error: string | null;
};
type Health = {
  status: string;
  mode: string;
  edge: string;
  outbox: { pending: number; failed: number };
};

export default function Edge() {
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [events, setEvents] = useState<OutboxEvent[]>([]);
  const [localPending, setLocalPending] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, s, ev] = await Promise.all([
        api.get<Health>("/edge/health"),
        api.get<SyncStatus>("/edge/sync/status", { params: storeId ? { store_id: storeId } : {} }),
        api.get<OutboxEvent[]>("/edge/outbox", {
          params: { ...(storeId ? { store_id: storeId } : {}), limit: 30 },
        }),
      ]);
      setHealth(h.data);
      setSync(s.data);
      setEvents(ev.data);
      setLocalPending(readOutbox().length);
    } catch {
      setError("Falha ao carregar status do edge.");
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Store[]>("/stores");
        setStores(data);
        const campo = data.find((s) => s.name.includes("Campo Novo")) || data[0];
        setStoreId((prev) => prev || campo?.id || "");
      } catch {
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function doSync() {
    setMessage(null);
    try {
      const local = await flushLocalOutbox().catch(() => ({ flushed: 0 }));
      const { data } = await api.post("/edge/sync", null, { params: storeId ? { store_id: storeId } : {} });
      setMessage(`Sync: ${data.synced} ok, ${data.failed} falha · outbox local ${local.flushed}`);
      await load();
    } catch {
      setError("Falha ao sincronizar.");
    }
  }

  async function doRetry() {
    setMessage(null);
    try {
      const { data } = await api.post("/edge/sync/retry", null, { params: storeId ? { store_id: storeId } : {} });
      setMessage(`Retry: ${data.synced} ok, ${data.failed} falha`);
      await load();
    } catch {
      setError("Falha no retry.");
    }
  }

  async function refreshSnapshot() {
    if (!storeId) return;
    setMessage(null);
    try {
      const { data } = await api.get(`/edge/snapshot`, { params: { store_id: storeId } });
      localStorage.setItem(
        `filaindoor_edge_cache:snapshot:${storeId}`,
        JSON.stringify({ saved_at: Date.now(), data }),
      );
      setMessage(`Snapshot em cache: ${data.queues?.length || 0} filas, ${data.assets?.length || 0} mídias`);
    } catch {
      setError("Falha ao gerar snapshot.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">Edge / Offline</h1>
        <p className="mt-1 text-ink/70">Cache local, outbox de eventos, sync e recuperação.</p>
      </div>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}
      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-ink/70">Loja</span>
          <select
            className="border border-brand-100 bg-white px-3 py-2"
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
          >
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900" onClick={() => void doSync()}>
          Sincronizar agora
        </button>
        <button type="button" className="border border-brand-700 px-4 py-2 text-sm font-semibold text-brand-700" onClick={() => void doRetry()}>
          Retry falhas
        </button>
        <button type="button" className="border border-brand-100 px-4 py-2 text-sm text-ink/80" onClick={() => void refreshSnapshot()}>
          Atualizar cache snapshot
        </button>
      </div>

      {health && sync && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Edge</p>
            <p className="mt-1 font-display text-2xl font-semibold">{health.edge}</p>
            <p className="text-sm text-ink/60">{health.mode} · {health.status}</p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Pending</p>
            <p className="mt-1 font-display text-2xl font-semibold">{sync.pending}</p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Failed</p>
            <p className="mt-1 font-display text-2xl font-semibold">{sync.failed}</p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Synced / local outbox</p>
            <p className="mt-1 font-display text-2xl font-semibold">
              {sync.synced} <span className="text-base text-ink/50">/ {localPending}</span>
            </p>
          </div>
        </div>
      )}

      <section className="border border-brand-100 bg-white/80 p-4">
        <h2 className="font-display text-xl font-semibold">Outbox recente</h2>
        {events.length === 0 ? (
          <p className="mt-3 text-sm text-ink/60">Nenhum evento. Emita uma senha no totem para gerar TICKET_ISSUED.</p>
        ) : (
          <ul className="mt-3 divide-y divide-brand-50 text-sm">
            {events.map((e) => (
              <li key={e.event_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div>
                  <p className="font-semibold">
                    {e.event_type} <span className="font-normal text-ink/50">· {e.event_id.slice(0, 8)}…</span>
                  </p>
                  <p className="text-ink/60">
                    {e.origin_device || "—"} · {e.occurred_at ? new Date(e.occurred_at).toLocaleString() : "—"}
                    {e.last_error ? ` · ${e.last_error}` : ""}
                  </p>
                </div>
                <span
                  className={`px-2 py-0.5 text-xs font-semibold uppercase ${
                    e.sync_status === "SYNCED"
                      ? "bg-emerald-100 text-emerald-900"
                      : e.sync_status === "FAILED"
                        ? "bg-red-100 text-red-800"
                        : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {e.sync_status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
