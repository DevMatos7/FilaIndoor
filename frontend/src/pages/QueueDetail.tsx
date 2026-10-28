import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { QueueStatus, Ticket } from "../services/api";

function formatWait(seconds: number) {
  const m = Math.round(seconds / 60);
  return `${m} min`;
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

export default function QueueDetail() {
  const { queueId } = useParams();
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [waiting, setWaiting] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!queueId) return;
    setError(null);
    try {
      const [st, wt] = await Promise.all([
        api.get<QueueStatus>(`/queues/${queueId}/status`),
        api.get<Ticket[]>(`/queues/${queueId}/waiting`),
      ]);
      setStatus(st.data);
      setWaiting(wt.data);
    } catch {
      setError("Falha ao carregar a fila.");
    } finally {
      setLoading(false);
    }
  }, [queueId]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(id);
  }, [load]);

  async function issue(type: "NORMAL" | "PRIORITY") {
    if (!queueId || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const key = crypto.randomUUID();
      const { data } = await api.post(
        `/queues/${queueId}/tickets`,
        { type, source: "ADMIN" },
        { headers: { "Idempotency-Key": key } },
      );
      setMessage(`Senha ${data.number} emitida.`);
      await load();
    } catch {
      setError("Não foi possível emitir a senha.");
    } finally {
      setBusy(false);
    }
  }

  async function callNext() {
    if (!queueId || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const key = crypto.randomUUID();
      const { data } = await api.post(
        `/queues/${queueId}/next`,
        { terminal_id: "ADMIN-1", auto_complete_current: true },
        { headers: { "Idempotency-Key": key } },
      );
      setMessage(`Chamada: ${data.number}`);
      await load();
      const detail = await api.get<Ticket>(`/tickets/${data.id}`);
      setSelected(detail.data);
    } catch {
      setError("Não há senha para chamar ou a operação falhou.");
    } finally {
      setBusy(false);
    }
  }

  async function openInspector(ticketId: string) {
    try {
      const { data } = await api.get<Ticket>(`/tickets/${ticketId}`);
      setSelected(data);
    } catch {
      setError("Falha ao abrir inspector.");
    }
  }

  if (loading) return <p className="text-sm text-ink/60">Carregando fila…</p>;
  if (error && !status) {
    return (
      <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
        {error}
      </p>
    );
  }
  if (!status) return <p>Fila não encontrada.</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/queues" className="text-sm text-brand-700 hover:underline">
          ← Filas
        </Link>
        <h1 className="mt-2 font-display text-3xl font-semibold text-brand-900">{status.name}</h1>
        <p className="mt-1 text-sm text-ink/70">
          {status.waiting_count} aguardando · {status.priority_waiting} prioritárias · espera ~{" "}
          {formatWait(status.estimated_wait_seconds)}
        </p>
        {queueId && (
          <div className="mt-3 flex flex-wrap gap-4 text-sm font-medium text-brand-700">
            <Link className="underline-offset-2 hover:underline" to={`/queues/${queueId}/settings`}>
              Configuração
            </Link>
            <a
              className="underline-offset-2 hover:underline"
              href={`/totem/${queueId}?token=kiosk-acougue-demo`}
              target="_blank"
              rel="noreferrer"
            >
              Abrir totem
            </a>
            <a className="underline-offset-2 hover:underline" href={`/operator/${queueId}`} target="_blank" rel="noreferrer">
              Abrir botoeira
            </a>
            <a
              className="underline-offset-2 hover:underline"
              href={`/display/${queueId}?token=display-acougue-audio`}
              target="_blank"
              rel="noreferrer"
            >
              Abrir TV (áudio)
            </a>
          </div>
        )}
      </div>

      {error && (
        <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900" role="status">
          {message}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void issue("NORMAL")}
          className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Emitir normal
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void issue("PRIORITY")}
          className="border border-brand-700 px-4 py-2 text-sm font-semibold text-brand-700 disabled:opacity-50"
        >
          Emitir prioritária
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void callNext()}
          className="bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Chamar próxima
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="border border-brand-100 bg-white/80 p-4">
          <h2 className="font-display text-xl font-semibold">Fila de espera</h2>
          {waiting.length === 0 ? (
            <p className="mt-3 text-sm text-ink/60">Nenhuma senha aguardando.</p>
          ) : (
            <ul className="mt-3 divide-y divide-brand-50">
              {waiting.map((t) => (
                <li key={t.id} className="flex items-center justify-between py-2 text-sm">
                  <button type="button" className="font-semibold hover:underline" onClick={() => void openInspector(t.id)}>
                    {t.number}
                  </button>
                  <span className="text-ink/70">
                    {t.type === "PRIORITY" || t.type === "PRIORITY_PLUS" ? "Prioritária" : "Normal"} ·{" "}
                    {statusLabel(t.status)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="border border-brand-100 bg-white/80 p-4">
          <h2 className="font-display text-xl font-semibold">Inspector de senha</h2>
          {!selected ? (
            <p className="mt-3 text-sm text-ink/60">Selecione uma senha para ver a timeline.</p>
          ) : (
            <div className="mt-3 space-y-3 text-sm">
              <div>
                <p className="font-display text-3xl font-semibold">{selected.number}</p>
                <p className="text-ink/70">
                  {selected.type} · {statusLabel(selected.status)}
                </p>
              </div>
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

      <section className="border border-brand-100 bg-white/70 p-4 text-sm">
        <h2 className="font-medium">Regra de prioridade</h2>
        <p className="mt-1 text-ink/70">
          {status.priority_rule.normal_weight} normais / {status.priority_rule.priority_weight} prioritária · override
          após {Math.round(status.priority_rule.priority_max_wait_seconds / 60)} min
        </p>
        {status.current && (
          <p className="mt-2">
            Atual: <strong>{status.current.number}</strong> ({statusLabel(status.current.status)})
          </p>
        )}
      </section>
    </div>
  );
}
