import { useCallback, useEffect, useState } from "react";
import api, { QueueSummary, Ticket } from "../services/api";

type HistoryResponse = {
  total: number;
  limit: number;
  offset: number;
  items: Array<
    Ticket & {
      wait_seconds?: number | null;
      service_seconds?: number | null;
    }
  >;
};

type TicketDetail = Ticket & {
  timings?: {
    wait_seconds?: number | null;
    service_seconds?: number | null;
    total_seconds?: number | null;
  };
  events?: Array<{ id: string; event_type: string; event_at: string }>;
};

function fmtSec(v?: number | null) {
  if (v == null) return "—";
  const m = Math.floor(v / 60);
  const s = v % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    WAITING: "Aguardando",
    CALLED: "Chamada",
    SERVING: "Em atendimento",
    COMPLETED: "Concluída",
    NO_SHOW: "Ausente",
    CANCELLED: "Cancelada",
    EXPIRED: "Expirada",
  };
  return map[status] || status;
}

export default function History() {
  const [queues, setQueues] = useState<QueueSummary[]>([]);
  const [queueId, setQueueId] = useState("");
  const [status, setStatus] = useState("");
  const [ticketType, setTicketType] = useState("");
  const [search, setSearch] = useState("");
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [selected, setSelected] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: res } = await api.get<HistoryResponse>("/tickets", {
        params: {
          queue_id: queueId || undefined,
          status: status || undefined,
          ticket_type: ticketType || undefined,
          search: search || undefined,
          limit,
          offset,
        },
      });
      setData(res);
    } catch {
      setError("Não foi possível carregar o histórico.");
    } finally {
      setLoading(false);
    }
  }, [queueId, status, ticketType, search, offset]);

  useEffect(() => {
    (async () => {
      try {
        const { data: qs } = await api.get<QueueSummary[]>("/queues");
        setQueues(qs);
      } catch {
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openInspector(id: string) {
    try {
      const { data: detail } = await api.get<TicketDetail>(`/tickets/${id}`);
      setSelected(detail);
    } catch {
      setError("Falha ao abrir inspector.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">Histórico</h1>
        <p className="mt-1 text-ink/70">Senhas emitidas com timeline e tempos auditáveis.</p>
      </div>

      <div className="grid gap-3 rounded-lg border border-brand-100 bg-white/80 p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-sm">
          Fila
          <select className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={queueId} onChange={(e) => { setOffset(0); setQueueId(e.target.value); }}>
            <option value="">Todas</option>
            {queues.map((q) => (
              <option key={q.id} value={q.id}>{q.name}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Status
          <select className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
            <option value="">Todos</option>
            {["WAITING", "CALLED", "SERVING", "COMPLETED", "NO_SHOW", "CANCELLED"].map((s) => (
              <option key={s} value={s}>{statusLabel(s)}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Tipo
          <select className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2" value={ticketType} onChange={(e) => { setOffset(0); setTicketType(e.target.value); }}>
            <option value="">Todos</option>
            <option value="NORMAL">Normal</option>
            <option value="PRIORITY">Prioritária</option>
          </select>
        </label>
        <label className="text-sm sm:col-span-2 lg:col-span-2">
          Buscar senha
          <input
            className="mt-1 w-full border border-brand-100 bg-sand px-2 py-2"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (setOffset(0), void load())}
            placeholder="Ex.: A023"
          />
        </label>
      </div>

      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {loading && <p className="text-sm text-ink/60">Carregando…</p>}

      {!loading && data && data.items.length === 0 && (
        <div className="border border-dashed border-brand-500/40 bg-white/60 p-6">
          <p className="font-medium">Nenhuma senha encontrada</p>
          <p className="mt-1 text-sm text-ink/70">Ajuste os filtros ou emita senhas no totem.</p>
        </div>
      )}

      {!loading && data && data.items.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="overflow-x-auto border border-brand-100 bg-white/80">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-brand-100 bg-brand-50">
                <tr>
                  <th className="px-3 py-2 font-medium">Senha</th>
                  <th className="px-3 py-2 font-medium">Tipo</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Emitida</th>
                  <th className="px-3 py-2 font-medium">Espera</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((t) => (
                  <tr key={t.id} className="cursor-pointer border-b border-brand-50 hover:bg-brand-50/60" onClick={() => void openInspector(t.id)}>
                    <td className="px-3 py-2 font-semibold">{t.number}</td>
                    <td className="px-3 py-2">{t.type}</td>
                    <td className="px-3 py-2">{statusLabel(t.status)}</td>
                    <td className="px-3 py-2">{t.issued_at ? new Date(t.issued_at).toLocaleString("pt-BR") : "—"}</td>
                    <td className="px-3 py-2">{fmtSec(t.wait_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between border-t border-brand-100 px-3 py-2 text-sm">
              <span>{data.total} registro(s)</span>
              <div className="flex gap-2">
                <button type="button" disabled={offset === 0} className="underline disabled:opacity-40" onClick={() => setOffset(Math.max(0, offset - limit))}>Anterior</button>
                <button type="button" disabled={offset + limit >= data.total} className="underline disabled:opacity-40" onClick={() => setOffset(offset + limit)}>Próxima</button>
              </div>
            </div>
          </div>

          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Inspector</h2>
            {!selected ? (
              <p className="mt-3 text-sm text-ink/60">Selecione uma senha na tabela.</p>
            ) : (
              <div className="mt-3 space-y-3 text-sm">
                <div>
                  <p className="font-display text-4xl font-semibold">{selected.number}</p>
                  <p className="text-ink/70">{selected.type} · {statusLabel(selected.status)}</p>
                </div>
                <dl className="grid grid-cols-2 gap-2">
                  <div><dt className="text-ink/60">Emitida</dt><dd>{selected.issued_at ? new Date(selected.issued_at).toLocaleTimeString("pt-BR") : "—"}</dd></div>
                  <div><dt className="text-ink/60">Chamada</dt><dd>{selected.called_at ? new Date(selected.called_at).toLocaleTimeString("pt-BR") : "—"}</dd></div>
                  <div><dt className="text-ink/60">Início</dt><dd>{selected.service_started_at ? new Date(selected.service_started_at).toLocaleTimeString("pt-BR") : "—"}</dd></div>
                  <div><dt className="text-ink/60">Finalizada</dt><dd>{selected.completed_at ? new Date(selected.completed_at).toLocaleTimeString("pt-BR") : "—"}</dd></div>
                  <div><dt className="text-ink/60">Espera</dt><dd>{fmtSec(selected.timings?.wait_seconds)}</dd></div>
                  <div><dt className="text-ink/60">Atendimento</dt><dd>{fmtSec(selected.timings?.service_seconds)}</dd></div>
                  <div className="col-span-2"><dt className="text-ink/60">Total</dt><dd>{fmtSec(selected.timings?.total_seconds)}</dd></div>
                </dl>
                <ol className="space-y-2 border-l-2 border-brand-100 pl-4">
                  {(selected.events || []).map((e) => (
                    <li key={e.id}>
                      <span className="font-medium">{e.event_type}</span>
                      <span className="ml-2 text-ink/60">{new Date(e.event_at).toLocaleString("pt-BR")}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
