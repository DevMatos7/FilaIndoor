import { useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Queue = { id: string; name: string; status: string };
type VirtualRow = {
  id: string;
  tracking_token: string;
  presence_status: string;
  ticket_number: string | null;
  ticket_status: string | null;
  customer_label: string | null;
  checked_in_at: string | null;
  created_at: string;
};

export default function RealPlusAdmin() {
  const [queues, setQueues] = useState<Queue[]>([]);
  const [queueId, setQueueId] = useState("");
  const [rows, setRows] = useState<VirtualRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<VirtualRow[]>("/real-plus/virtual-tickets", {
        params: queueId ? { queue_id: queueId } : {},
      });
      setRows(data);
    } catch {
      setError("Falha ao listar senhas virtuais (REAL+ habilitado?).");
    } finally {
      setLoading(false);
    }
  }, [queueId]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Queue[]>("/queues");
        setQueues(data);
        setQueueId((prev) => prev || data[0]?.id || "");
      } catch {
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const publicUrl = queueId ? `${window.location.origin}/real-plus/${queueId}` : "";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">REAL+</h1>
        <p className="mt-1 text-ink/70">Fila virtual: retirada remota, posição, check-in e avisos.</p>
      </div>

      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-ink/70">Fila</span>
          <select className="border border-brand-100 bg-white px-3 py-2" value={queueId} onChange={(e) => setQueueId(e.target.value)}>
            {queues.map((q) => (
              <option key={q.id} value={q.id}>
                {q.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900" onClick={() => void load()}>
          Atualizar
        </button>
        {publicUrl && (
          <a className="border border-brand-700 px-4 py-2 text-sm font-semibold text-brand-700" href={publicUrl} target="_blank" rel="noreferrer">
            Abrir app cliente
          </a>
        )}
      </div>

      {publicUrl && (
        <p className="text-sm text-ink/60">
          Link público: <code className="break-all">{publicUrl}</code>
        </p>
      )}

      <section className="border border-brand-100 bg-white/80 p-4">
        <h2 className="font-display text-xl font-semibold">Senhas virtuais</h2>
        {loading ? (
          <p className="mt-3 text-sm text-ink/60">Carregando…</p>
        ) : rows.length === 0 ? (
          <p className="mt-3 text-sm text-ink/60">Nenhuma senha REAL+ ainda.</p>
        ) : (
          <ul className="mt-3 divide-y divide-brand-50 text-sm">
            {rows.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="font-semibold">
                    {r.ticket_number || "—"} <span className="font-normal text-ink/50">· {r.presence_status}</span>
                  </p>
                  <p className="text-ink/60">
                    ticket {r.ticket_status || "—"}
                    {r.checked_in_at ? ` · check-in ${new Date(r.checked_in_at).toLocaleString()}` : ""}
                  </p>
                </div>
                <a className="text-brand-700 underline-offset-2 hover:underline" href={`/real-plus/${queueId}?t=${r.tracking_token}`} target="_blank" rel="noreferrer">
                  Acompanhar
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
