import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw } from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  DeviceStatus,
  EmptyState,
  Input,
  MetricCard,
  PageHeader,
  Select,
  Skeleton,
  Tabs,
} from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import {
  AnalyticsOverview,
  Delta,
  PeriodPreset,
  fetchAnalyticsOverview,
  formatDeltaPct,
  formatPct,
  formatSeconds,
  resolvePeriod,
} from "../services/analyticsService";

type TabId = "overview" | "service" | "queues" | "ops" | "devices";

function Trend({ delta, invertGood = false }: { delta: Delta | null | undefined; invertGood?: boolean }) {
  const label = formatDeltaPct(delta, invertGood);
  if (!label || !delta) return null;
  const bad = invertGood ? (delta.pct ?? 0) > 0 : (delta.pct ?? 0) < 0;
  const good = invertGood ? (delta.pct ?? 0) < 0 : (delta.pct ?? 0) > 0;
  const cls = good ? "text-semantic-success" : bad ? "text-semantic-danger" : "text-ink/50";
  return <span className={`text-xs tabular-nums ${cls}`}>vs ant. {label}</span>;
}

function ChartCard({
  title,
  description,
  loading,
  empty,
  children,
  summary,
}: {
  title: string;
  description?: string;
  loading?: boolean;
  empty?: boolean;
  children: React.ReactNode;
  summary: string;
}) {
  return (
    <section
      className="rounded-ds border border-brand-100 bg-white p-4 shadow-ds-sm"
      aria-label={title}
    >
      <h3 className="font-sans text-sm font-semibold text-brand-900">{title}</h3>
      {description && <p className="mt-0.5 text-xs text-ink/55">{description}</p>}
      <p className="sr-only">{summary}</p>
      <div className="mt-3 h-56 w-full">
        {loading ? (
          <Skeleton.Card className="h-full" />
        ) : empty ? (
          <p className="flex h-full items-center justify-center text-sm text-ink/50">Sem dados no período.</p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

export default function Analytics() {
  const { selectedStoreId: storeId } = useStoreContext();
  const [searchParams, setSearchParams] = useSearchParams();

  const urlFrom = searchParams.get("from");
  const urlTo = searchParams.get("to");
  const urlQueue = searchParams.get("queue") || "";
  const urlType = searchParams.get("type") || "";
  const urlPreset = (searchParams.get("preset") as PeriodPreset) || "today";

  const [preset, setPreset] = useState<PeriodPreset>(
    urlFrom && urlTo && !searchParams.get("preset") ? "custom" : urlPreset,
  );
  const [customFrom, setCustomFrom] = useState(urlFrom || "");
  const [customTo, setCustomTo] = useState(urlTo || "");
  const [queueId, setQueueId] = useState(urlQueue);
  const [ticketType, setTicketType] = useState(urlType);
  const [tab, setTab] = useState<TabId>("overview");

  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [devicesError, setDevicesError] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const hasDataRef = useRef(false);

  const period = useMemo(
    () => resolvePeriod(preset, customFrom, customTo),
    [preset, customFrom, customTo],
  );

  const syncUrl = useCallback(
    (next: { from: string; to: string; queue?: string; type?: string; preset: PeriodPreset }) => {
      setSearchParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          p.set("from", next.from);
          p.set("to", next.to);
          p.set("preset", next.preset);
          if (next.queue) p.set("queue", next.queue);
          else p.delete("queue");
          if (next.type) p.set("type", next.type);
          else p.delete("type");
          return p;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const load = useCallback(
    async (opts?: { soft?: boolean }) => {
      if (!storeId) {
        setData(null);
        setLoading(false);
        return;
      }
      if (period.to < period.from) {
        setError("Período inválido: data final anterior à inicial.");
        return;
      }
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      if (!opts?.soft) setLoading(true);
      setError(null);
      try {
        const overview = await fetchAnalyticsOverview(
          {
            store_id: storeId,
            from: period.from,
            to: period.to,
            queue_id: queueId || undefined,
            ticket_type: ticketType || undefined,
          },
          ac.signal,
        );
        if (ac.signal.aborted) return;
        setData(overview);
        hasDataRef.current = true;
        setStale(false);
        setDevicesError(Boolean(overview.devices_current?.error) || overview.devices_current?.available === false);
        syncUrl({
          from: period.from,
          to: period.to,
          queue: queueId,
          type: ticketType,
          preset,
        });
      } catch (err: unknown) {
        if ((err as { code?: string })?.code === "ERR_CANCELED") return;
        if (opts?.soft && hasDataRef.current) setStale(true);
        else {
          setError("Não foi possível carregar os indicadores.");
          setData(null);
          hasDataRef.current = false;
        }
      } finally {
        if (!ac.signal.aborted) setLoading(false);
      }
    },
    [storeId, period, queueId, ticketType, preset, syncUrl],
  );

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  useEffect(() => {
    if (preset !== "today") return;
    const id = window.setInterval(() => {
      if (document.hidden) return;
      void load({ soft: true });
    }, 60000);
    return () => window.clearInterval(id);
  }, [preset, load]);

  const m = data?.metrics;
  const queues: Array<{ id: string; name: string }> =
    data?.available_queues ||
    data?.queues?.map((q) => ({ id: q.queue_id, name: q.name })) ||
    [];

  const volumeSummary = useMemo(() => {
    if (!data?.series.volume.length) return "Sem volume.";
    const issued = data.series.volume.reduce((a, b) => a + b.issued, 0);
    const completed = data.series.volume.reduce((a, b) => a + b.completed, 0);
    return `No período: ${issued} emitidas e ${completed} concluídas.`;
  }, [data]);

  const waitSummary = useMemo(() => {
    if (!m) return "";
    return `Espera média ${formatSeconds(m.wait.avg_seconds)}, P90 ${formatSeconds(m.wait.p90_seconds)}, com ${m.wait.sample_count} amostras.`;
  }, [m]);

  const sortedQueues = useMemo(() => {
    return [...(data?.queues || [])];
  }, [data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Acompanhe demanda, espera, atendimento e nível de serviço da operação."
        actions={
          <Button type="button" variant="ghost" onClick={() => void load()} aria-label="Atualizar analytics">
            <RefreshCw className="h-4 w-4" aria-hidden />
            Atualizar
          </Button>
        }
      />

      <div className="flex flex-col gap-3 rounded-ds border border-brand-100 bg-white p-3 shadow-ds-sm lg:flex-row lg:flex-wrap lg:items-end">
        <div className="flex flex-wrap gap-1" role="group" aria-label="Período">
          {(
            [
              ["today", "Hoje"],
              ["yesterday", "Ontem"],
              ["7d", "7 dias"],
              ["30d", "30 dias"],
              ["custom", "Personalizado"],
            ] as const
          ).map(([id, label]) => (
            <Button
              key={id}
              type="button"
              size="sm"
              variant={preset === id ? "primary" : "ghost"}
              aria-pressed={preset === id}
              onClick={() => {
                setPreset(id);
                if (id !== "custom") {
                  const p = resolvePeriod(id);
                  setCustomFrom(p.from);
                  setCustomTo(p.to);
                }
              }}
            >
              {label}
            </Button>
          ))}
        </div>
        {preset === "custom" && (
          <div className="flex flex-wrap gap-2">
            <Input
              type="date"
              label="De"
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
            />
            <Input
              type="date"
              label="Até"
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
            />
          </div>
        )}
        <Select
          label="Fila"
          value={queueId}
          onChange={(e) => setQueueId(e.target.value)}
          className="lg:w-48"
        >
          <option value="">Todas as filas</option>
          {queues.map((q) => (
            <option key={q.id} value={q.id}>
              {q.name}
            </option>
          ))}
        </Select>
        <Select
          label="Tipo"
          value={ticketType}
          onChange={(e) => setTicketType(e.target.value)}
          className="lg:w-40"
        >
          <option value="">Todos</option>
          <option value="NORMAL">Normal</option>
          <option value="PRIORITY">Prioritário</option>
          <option value="PRIORITY_PLUS">Prioritário+</option>
        </Select>
      </div>

      {stale && <Alert variant="warning">Dados desatualizados — a última atualização falhou.</Alert>}
      {error && (
        <div className="space-y-2">
          <Alert variant="danger">{error}</Alert>
          <Button type="button" size="sm" variant="ghost" onClick={() => void load()}>
            Tentar novamente
          </Button>
        </div>
      )}

      {loading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton.Metric key={i} />
          ))}
        </div>
      )}

      {!loading && data?.empty && (
        <EmptyState
          title="Nenhum atendimento encontrado neste período."
          description="Ajuste o intervalo ou a fila para explorar outros dados."
        />
      )}

      {!loading && data && !data.empty && m && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <MetricCard
              label="Senhas emitidas"
              value={<span className="tabular-nums">{m.issued}</span>}
              trend={<Trend delta={data.comparison.issued} />}
            />
            <MetricCard
              label="Atendimentos concluídos"
              value={<span className="tabular-nums">{m.completed}</span>}
              trend={<Trend delta={data.comparison.completed} />}
            />
            <MetricCard
              label="Espera média"
              value={<span className="tabular-nums">{formatSeconds(m.wait.avg_seconds)}</span>}
              hint={m.wait.sample_count ? `${m.wait.sample_count} amostras` : "sem amostras"}
              trend={<Trend delta={data.comparison.wait_avg} invertGood />}
            />
            <MetricCard
              label="P90 de espera"
              value={<span className="tabular-nums">{formatSeconds(m.wait.p90_seconds)}</span>}
              trend={<Trend delta={data.comparison.wait_p90} invertGood />}
              status={m.wait.p90_seconds != null && m.wait.p90_seconds >= 900 ? "danger" : m.wait.p90_seconds != null && m.wait.p90_seconds >= 600 ? "warning" : "default"}
            />
            <MetricCard
              label="Tempo médio de atendimento"
              value={<span className="tabular-nums">{formatSeconds(m.service.avg_seconds)}</span>}
              hint={
                m.service.sample_count
                  ? `${m.service.sample_count} com timestamps`
                  : "sem dados suficientes"
              }
            />
            <MetricCard
              label="Ausências (no-show)"
              value={<span className="tabular-nums">{m.no_show}</span>}
              trend={<Trend delta={data.comparison.no_show} invertGood />}
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Dentro do SLA"
              value={
                <span className="tabular-nums">
                  {formatPct(m.sla.within_target_rate)}
                </span>
              }
              hint={
                m.sla.evaluable
                  ? `${m.sla.within_target} de ${m.sla.evaluable} avaliáveis · meta ${Math.round(m.sla.target_wait_seconds / 60)} min`
                  : "nenhum ticket avaliável"
              }
              status={
                m.sla.within_target_rate == null
                  ? "default"
                  : m.sla.within_target_rate >= 0.9
                    ? "success"
                    : m.sla.within_target_rate >= 0.75
                      ? "warning"
                      : "danger"
              }
            />
            <MetricCard
              label="Throughput"
              value={<span className="tabular-nums">{m.throughput_per_hour}</span>}
              hint="concluídos / hora no período"
            />
            <MetricCard
              label="Taxa de conclusão"
              value={<span className="tabular-nums">{formatPct(m.completion_rate)}</span>}
              hint="concluídas ÷ emitidas (cohorts distintos)"
            />
            <MetricCard
              label="Canceladas"
              value={<span className="tabular-nums">{m.cancelled}</span>}
              hint="não entram em no-show"
            />
          </div>

          <Tabs
            items={[
              { id: "overview", label: "Overview" },
              { id: "service", label: "Atendimento" },
              { id: "queues", label: "Filas" },
              { id: "ops", label: "Balcões" },
              { id: "devices", label: "Saúde operacional" },
            ]}
            value={tab}
            onChange={(id) => setTab(id as TabId)}
          />

          {(tab === "overview" || tab === "service") && (
            <div className="grid gap-4 xl:grid-cols-2">
              <ChartCard
                title="Volume de atendimentos"
                description={data.series.granularity === "hour" ? "Por hora" : "Por dia"}
                loading={false}
                empty={!data.series.volume.some((p) => p.issued || p.completed)}
                summary={volumeSummary}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.series.volume} accessibilityLayer>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8eef5" />
                    <XAxis
                      dataKey="bucket"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(v: string) =>
                        data.series.granularity === "hour" ? v.slice(11, 16) : v.slice(5)
                      }
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="issued" name="Emitidas" fill="#1d4f91" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="completed" name="Concluídas" fill="#5b8def" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard
                title="Espera média e P90"
                description="Calculados sobre observações individuais do bucket"
                empty={!data.series.wait.some((p) => p.sample_count)}
                summary={waitSummary}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.series.wait} accessibilityLayer>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8eef5" />
                    <XAxis
                      dataKey="bucket"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(v: string) =>
                        data.series.granularity === "hour" ? v.slice(11, 16) : v.slice(5)
                      }
                    />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatSeconds(Number(v))} />
                    <Tooltip formatter={(v: number) => formatSeconds(v)} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="avg_seconds"
                      name="Espera média"
                      stroke="#1d4f91"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="p90_seconds"
                      name="P90"
                      stroke="#c45c26"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard
                title="Demanda por horário"
                description="Emissões agregadas por hora do dia (todo o período)"
                empty={!data.demand_hourly.some((h) => h.issued)}
                summary={`Pico às ${
                  [...data.demand_hourly].sort((a, b) => b.issued - a.issued)[0]?.hour ?? "—"
                }h.`}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.demand_hourly} accessibilityLayer>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8eef5" />
                    <XAxis dataKey="hour" tick={{ fontSize: 10 }} tickFormatter={(h) => `${h}h`} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="issued" name="Emitidas" fill="#1d4f91" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard
                title="SLA de espera"
                description={m.sla.definition}
                empty={m.sla.evaluable === 0}
                summary={`Dentro ${m.sla.green}, atenção ${m.sla.yellow}, crítico ${m.sla.red}, não avaliáveis ${m.sla.unknown}.`}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: "Dentro", value: m.sla.green, color: "#1f7a4d" },
                      { name: "Atenção", value: m.sla.yellow, color: "#b7791f" },
                      { name: "Crítico", value: m.sla.red, color: "#b42318" },
                      { name: "N/A", value: m.sla.unknown, color: "#94a3b8" },
                    ]}
                    accessibilityLayer
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8eef5" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" name="Tickets">
                      {[
                        { name: "Dentro", value: m.sla.green, color: "#1f7a4d" },
                        { name: "Atenção", value: m.sla.yellow, color: "#b7791f" },
                        { name: "Crítico", value: m.sla.red, color: "#b42318" },
                        { name: "N/A", value: m.sla.unknown, color: "#94a3b8" },
                      ].map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <ul className="mt-2 flex flex-wrap gap-2 text-xs">
                  <li><Badge tone="success">Dentro {m.sla.green}</Badge></li>
                  <li><Badge tone="warning">Atenção {m.sla.yellow}</Badge></li>
                  <li><Badge tone="danger">Crítico {m.sla.red}</Badge></li>
                  <li><Badge tone="neutral">N/A {m.sla.unknown}</Badge></li>
                </ul>
              </ChartCard>
            </div>
          )}

          {(tab === "overview" || tab === "queues") && (
            <section className="space-y-3" aria-labelledby="queue-cmp">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h2 id="queue-cmp" className="font-sans text-base font-semibold text-brand-900">
                    Desempenho por fila
                  </h2>
                  <p className="text-xs text-ink/55">
                    Ordenado por pior SLA, depois maior P90. P90 do total não é média dos P90.
                  </p>
                </div>
              </div>

              {/* Desktop table */}
              <div className="hidden overflow-x-auto rounded-ds border border-brand-100 md:block">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-brand-50 text-xs uppercase tracking-wide text-ink/55">
                    <tr>
                      <th scope="col" className="px-3 py-2">Fila</th>
                      <th scope="col" className="px-3 py-2">Emitidas</th>
                      <th scope="col" className="px-3 py-2">Concluídas</th>
                      <th scope="col" className="px-3 py-2">Espera méd.</th>
                      <th scope="col" className="px-3 py-2">P90</th>
                      <th scope="col" className="px-3 py-2">SLA</th>
                      <th scope="col" className="px-3 py-2">No-show</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedQueues.map((q) => (
                      <tr key={q.queue_id} className="border-t border-brand-50">
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            className="font-medium text-brand-800 hover:underline"
                            onClick={() => setQueueId(q.queue_id)}
                          >
                            {q.name}
                          </button>
                        </td>
                        <td className="px-3 py-2 tabular-nums">{q.issued}</td>
                        <td className="px-3 py-2 tabular-nums">{q.completed}</td>
                        <td className="px-3 py-2 tabular-nums">{formatSeconds(q.wait_avg_seconds)}</td>
                        <td className="px-3 py-2 tabular-nums">{formatSeconds(q.wait_p90_seconds)}</td>
                        <td className="px-3 py-2 tabular-nums">{formatPct(q.sla_within_rate)}</td>
                        <td className="px-3 py-2 tabular-nums">{q.no_show}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <ul className="space-y-2 md:hidden">
                {sortedQueues.map((q) => (
                  <li key={q.queue_id} className="rounded-ds border border-brand-100 bg-white p-3">
                    <button
                      type="button"
                      className="font-semibold text-brand-900"
                      onClick={() => setQueueId(q.queue_id)}
                    >
                      {q.name}
                    </button>
                    <dl className="mt-2 grid grid-cols-2 gap-1 text-xs text-ink/70">
                      <div>Emitidas <span className="tabular-nums font-medium text-ink">{q.issued}</span></div>
                      <div>Concl. <span className="tabular-nums font-medium text-ink">{q.completed}</span></div>
                      <div>Espera <span className="tabular-nums font-medium text-ink">{formatSeconds(q.wait_avg_seconds)}</span></div>
                      <div>P90 <span className="tabular-nums font-medium text-ink">{formatSeconds(q.wait_p90_seconds)}</span></div>
                      <div>SLA <span className="tabular-nums font-medium text-ink">{formatPct(q.sla_within_rate)}</span></div>
                      <div>No-show <span className="tabular-nums font-medium text-ink">{q.no_show}</span></div>
                    </dl>
                  </li>
                ))}
              </ul>

              {Object.keys(data.by_type || {}).length > 0 && (
                <div className="rounded-ds border border-brand-100 bg-white p-4">
                  <h3 className="text-sm font-semibold text-brand-900">Mix por tipo</h3>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {Object.entries(data.by_type).map(([k, v]) => (
                      <li key={k}>
                        <Badge tone="neutral">
                          {k === "NORMAL" ? "Normal" : k === "PRIORITY" ? "Prioritário" : k}:{" "}
                          <span className="tabular-nums">{v}</span>
                        </Badge>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}

          {tab === "ops" && (
            <section className="space-y-4">
              {data.terminals.available ? (
                <div className="rounded-ds border border-brand-100 bg-white p-4">
                  <h2 className="text-sm font-semibold text-brand-900">Desempenho por balcão</h2>
                  <p className="text-xs text-ink/55">{data.terminals.note}</p>
                  <ul className="mt-3 divide-y divide-brand-50">
                    {data.terminals.items.map((t) => (
                      <li key={t.terminal_id} className="flex justify-between gap-2 py-2 text-sm">
                        <span className="font-medium">{t.terminal_id}</span>
                        <span className="tabular-nums text-ink/70">
                          {t.completed} concl. · atendimento méd. {formatSeconds(t.service_avg_seconds)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <EmptyState
                  title="Sem dados de balcão neste período"
                  description={data.terminals.reason || "terminal_id histórico indisponível."}
                />
              )}
              {data.operators.available ? (
                <div className="rounded-ds border border-brand-100 bg-white p-4">
                  <h2 className="text-sm font-semibold text-brand-900">Atendimentos por operador</h2>
                  <p className="text-xs text-ink/55">{data.operators.note}</p>
                  <ul className="mt-3 divide-y divide-brand-50">
                    {data.operators.items.map((o) => (
                      <li key={o.operator_id} className="flex justify-between gap-2 py-2 text-sm">
                        <span className="font-mono text-xs">{o.operator_id}</span>
                        <span className="tabular-nums">{o.completed}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <Alert variant="info">
                  {data.operators.reason || "Produtividade por operador indisponível — sem operator_id histórico."}
                </Alert>
              )}
            </section>
          )}

          {tab === "devices" && (
            <section className="space-y-3">
              <div>
                <h2 className="font-sans text-base font-semibold text-brand-900">
                  {data.devices_current.label || "Situação atual da frota"}
                </h2>
                <p className="text-xs text-ink/55">
                  {data.devices_current.note ||
                    "Snapshot agora — o filtro de período não transforma isto em uptime histórico."}
                </p>
              </div>
              {devicesError || data.devices_current.error ? (
                <Alert variant="warning">
                  Não foi possível carregar o snapshot de dispositivos. Os indicadores de filas permanecem disponíveis.
                </Alert>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <MetricCard label="Online" value={data.devices_current.online ?? 0} status="success" />
                  <MetricCard label="Com atenção" value={data.devices_current.degraded ?? 0} status="warning" />
                  <MetricCard label="Offline" value={data.devices_current.offline ?? 0} status="danger" />
                  <MetricCard label="Desabilitados" value={data.devices_current.disabled ?? 0} />
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <DeviceStatus status="ONLINE" />
                <DeviceStatus status="DEGRADED" />
                <DeviceStatus status="OFFLINE" />
                <DeviceStatus status="DISABLED" />
              </div>
              <Alert variant="info">
                Sem Proof of Play: não há impressões/exibições de mídia. Conteúdo programado ≠ conteúdo confirmado na TV.
              </Alert>
            </section>
          )}

          <p className="text-xs text-ink/45">
            {data.period.timezone_note} · Comparação: {data.comparison.note}
          </p>
        </>
      )}
    </div>
  );
}
