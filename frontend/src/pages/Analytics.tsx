import { useCallback, useEffect, useState } from "react";
import api, { QueueSummary } from "../services/api";

type TimingStats = {
  avg_seconds: number | null;
  median_seconds: number | null;
  p90_seconds: number | null;
  max_seconds: number | null;
};

type Summary = {
  date: string;
  queue_id: string | null;
  queue_name: string | null;
  kpis: {
    issued: number;
    completed: number;
    waiting: number;
    called: number;
    serving: number;
    no_show: number;
    cancelled: number;
    abandon_rate: number;
    wait: TimingStats;
    service: TimingStats;
  };
  by_type: Record<string, number>;
  hourly: Array<{ hour: number; issued: number; completed: number }>;
  sla: {
    green: number;
    yellow: number;
    red: number;
    unknown: number;
    target_wait_seconds: number;
    warning_wait_seconds: number;
  };
  current_waiting: Array<{
    id: string;
    number: string;
    type: string;
    status: string;
    wait_seconds: number | null;
  }>;
  by_operator: Array<{ operator_id: string; completed: number }>;
};

function fmtSec(v: number | null | undefined) {
  if (v == null) return "—";
  const m = Math.floor(v / 60);
  const s = Math.round(v % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border border-brand-100 bg-white/80 p-4">
      <p className="text-xs uppercase tracking-wide text-ink/55">{label}</p>
      <p className="mt-2 font-display text-3xl font-semibold text-brand-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink/50">{hint}</p>}
    </div>
  );
}

export default function Analytics() {
  const [queues, setQueues] = useState<QueueSummary[]>([]);
  const [queueId, setQueueId] = useState("");
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: res } = await api.get<Summary>("/analytics/summary", {
        params: { day, queue_id: queueId || undefined },
      });
      setData(res);
    } catch {
      setError("Não foi possível carregar o analytics.");
    } finally {
      setLoading(false);
    }
  }, [day, queueId]);

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

  const maxHourly = data ? Math.max(1, ...data.hourly.map((h) => Math.max(h.issued, h.completed))) : 1;
  const activeHours = data?.hourly.filter((h) => h.issued > 0 || h.completed > 0) ?? [];
  const chartHours = activeHours.length > 0 ? activeHours : data?.hourly.slice(8, 21) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-brand-900">Analytics</h1>
          <p className="mt-1 text-ink/70">KPIs do dia — espera, atendimento, abandono e pico horário.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm">
            Dia
            <input
              type="date"
              className="mt-1 block border border-brand-100 bg-sand px-2 py-2"
              value={day}
              onChange={(e) => setDay(e.target.value)}
            />
          </label>
          <label className="text-sm">
            Fila
            <select
              className="mt-1 block min-w-[12rem] border border-brand-100 bg-sand px-2 py-2"
              value={queueId}
              onChange={(e) => setQueueId(e.target.value)}
            >
              <option value="">Todas</option>
              {queues.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}
      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}

      {!loading && data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <Kpi label="Atendimentos hoje" value={String(data.kpis.completed)} hint={`${data.kpis.issued} emitidas`} />
            <Kpi label="Aguardando" value={String(data.kpis.waiting)} />
            <Kpi label="Tempo médio espera" value={fmtSec(data.kpis.wait.avg_seconds)} hint={`P90 ${fmtSec(data.kpis.wait.p90_seconds)}`} />
            <Kpi label="Tempo médio atendimento" value={fmtSec(data.kpis.service.avg_seconds)} hint={`P90 ${fmtSec(data.kpis.service.p90_seconds)}`} />
            <Kpi label="Maior espera" value={fmtSec(data.kpis.wait.max_seconds)} />
            <Kpi label="Ausências" value={String(data.kpis.no_show)} hint={`Canceladas ${data.kpis.cancelled} · abandono ${fmtPct(data.kpis.abandon_rate)}`} />
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <section className="border border-brand-100 bg-white/80 p-4">
              <h2 className="font-display text-xl font-semibold">Atendimentos / hora</h2>
              <p className="mt-1 text-sm text-ink/60">Emitidas vs concluídas ({data.date})</p>
              <div className="mt-4 flex h-48 items-end gap-1">
                {chartHours.map((h) => (
                  <div key={h.hour} className="flex flex-1 flex-col items-center justify-end gap-1">
                    <div className="flex w-full items-end justify-center gap-0.5" style={{ height: "100%" }}>
                      <div
                        className="w-1/2 bg-brand-300"
                        style={{ height: `${(h.issued / maxHourly) * 100}%`, minHeight: h.issued ? 4 : 0 }}
                        title={`Emitidas ${h.issued}`}
                      />
                      <div
                        className="w-1/2 bg-brand-700"
                        style={{ height: `${(h.completed / maxHourly) * 100}%`, minHeight: h.completed ? 4 : 0 }}
                        title={`Concluídas ${h.completed}`}
                      />
                    </div>
                    <span className="text-[10px] text-ink/50">{String(h.hour).padStart(2, "0")}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-4 text-xs text-ink/60">
                <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-3 bg-brand-300" /> Emitidas</span>
                <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-3 bg-brand-700" /> Concluídas</span>
              </div>
            </section>

            <section className="border border-brand-100 bg-white/80 p-4">
              <h2 className="font-display text-xl font-semibold">SLA de espera</h2>
              <p className="mt-1 text-sm text-ink/60">
                Verde &lt; {Math.round(data.sla.target_wait_seconds / 60)} min · Amarelo até{" "}
                {Math.round(data.sla.warning_wait_seconds / 60)} min · Vermelho acima
              </p>
              <ul className="mt-4 space-y-3 text-sm">
                <li className="flex items-center justify-between border-l-4 border-emerald-600 pl-3">
                  <span>Normal</span>
                  <strong>{data.sla.green}</strong>
                </li>
                <li className="flex items-center justify-between border-l-4 border-amber-500 pl-3">
                  <span>Atenção</span>
                  <strong>{data.sla.yellow}</strong>
                </li>
                <li className="flex items-center justify-between border-l-4 border-red-600 pl-3">
                  <span>Crítico</span>
                  <strong>{data.sla.red}</strong>
                </li>
              </ul>
              <div className="mt-6">
                <h3 className="text-sm font-medium">Por tipo</h3>
                <ul className="mt-2 space-y-1 text-sm text-ink/70">
                  {Object.entries(data.by_type).length === 0 && <li>Sem emissões no dia.</li>}
                  {Object.entries(data.by_type).map(([k, v]) => (
                    <li key={k} className="flex justify-between">
                      <span>{k}</span>
                      <span>{v}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          </div>

          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Fila atual (aguardando)</h2>
            {data.current_waiting.length === 0 ? (
              <p className="mt-3 text-sm text-ink/60">Nenhuma senha aguardando agora.</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-brand-100 bg-brand-50">
                    <tr>
                      <th className="px-3 py-2 font-medium">Senha</th>
                      <th className="px-3 py-2 font-medium">Tipo</th>
                      <th className="px-3 py-2 font-medium">Status</th>
                      <th className="px-3 py-2 font-medium">Espera</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.current_waiting.map((t) => (
                      <tr key={t.id} className="border-b border-brand-50">
                        <td className="px-3 py-2 font-semibold">{t.number}</td>
                        <td className="px-3 py-2">{t.type}</td>
                        <td className="px-3 py-2">{t.status}</td>
                        <td className="px-3 py-2">{fmtSec(t.wait_seconds)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
