import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Clock,
  ListOrdered,
  Monitor,
  Network,
  Printer,
  RefreshCw,
  TabletSmartphone,
  Users,
  Wifi,
  WifiOff,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  MetricCard,
  PageHeader,
  QueueStatus,
  SkeletonCard,
  SkeletonMetric,
  SlaIndicator,
  StatusDot,
  cn,
} from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import HourlyFlowChart from "../components/command-center/HourlyFlowChart";
import {
  CommandCenterView,
  LIVE_TTL_MS,
  LiveState,
  REFRESH_MS,
  fetchCommandCenter,
  fmtSec,
  hasPartialFailure,
  relativeAge,
} from "../services/commandCenter";

const DEVICE_LABELS: Record<string, { label: string; icon: typeof Monitor }> = {
  DISPLAY: { label: "Telas", icon: Monitor },
  KIOSK: { label: "Totens", icon: TabletSmartphone },
  PRINTER: { label: "Impressoras", icon: Printer },
  BUTTON: { label: "Botoeiras", icon: Activity },
  EDGE: { label: "Edge devices", icon: Network },
};

type LoadReason = "initial" | "refresh" | "store";

export default function Dashboard() {
  const { selectedStoreId, selectedStore, loading: storeLoading } = useStoreContext();
  const [data, setData] = useState<CommandCenterView | null>(null);
  const [live, setLive] = useState<LiveState>("updating");
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  const storeRef = useRef(selectedStoreId);
  const dataRef = useRef<CommandCenterView | null>(null);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  const load = useCallback(async (reason: LoadReason = "refresh") => {
    const storeId = storeRef.current;
    if (!storeId) return;
    if (inFlight.current && reason === "refresh") return;

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    inFlight.current = true;

    if (reason === "store" || reason === "initial") {
      setData(null);
      setError(null);
      setLive("updating");
    } else if (dataRef.current) {
      setLive("updating");
    } else {
      setLive("updating");
    }

    try {
      const view = await fetchCommandCenter(storeId, ac.signal);
      if (storeRef.current !== storeId) return;
      setData(view);
      setError(null);
      setLive(hasPartialFailure(view) ? "partial" : "live");
    } catch (err: unknown) {
      const name = (err as { name?: string; code?: string })?.name;
      const code = (err as { code?: string })?.code;
      if (name === "CanceledError" || code === "ERR_CANCELED") return;
      if (storeRef.current !== storeId) return;
      if (dataRef.current) {
        setLive("stale");
        setError("Não foi possível atualizar. Exibindo último snapshot.");
      } else {
        setLive("error");
        setError("Não foi possível carregar a operação desta loja.");
      }
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    storeRef.current = selectedStoreId;
    if (!selectedStoreId || storeLoading) return;
    void load("store");
    return () => abortRef.current?.abort();
  }, [selectedStoreId, storeLoading, load]);

  useEffect(() => {
    if (!selectedStoreId) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      void load("refresh");
    }, REFRESH_MS);
    return () => window.clearInterval(id);
  }, [selectedStoreId, load]);

  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!data) return;
    if (live === "error" || live === "updating" || live === "partial") return;
    const age = Date.now() - data.fetchedAt;
    if (age > LIVE_TTL_MS && live === "live") setLive("stale");
  }, [tick, data, live]);

  const storeName = selectedStore?.name || data?.storeName || "Loja";
  const loading = storeLoading || (!!selectedStoreId && !data && !error);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operação da loja"
        description={
          <span>
            <span className="font-medium text-brand-800">{storeName}</span>
            {" · "}
            Visão operacional em tempo quase real
          </span>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <LiveBadge state={live} age={data ? relativeAge(data.fetchedAt) : undefined} />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void load("refresh")}
              disabled={!selectedStoreId}
              loading={live === "updating" && !!data}
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              Atualizar
            </Button>
          </div>
        }
      />

      {!selectedStoreId && !storeLoading && (
        <EmptyState
          title="Nenhuma loja selecionada"
          description="Escolha uma loja na barra superior para ver a operação."
        />
      )}

      {error && !data && <Alert variant="danger">{error}</Alert>}
      {error && data && (
        <Alert variant="warning" title="Dados desatualizados">
          {error}
        </Alert>
      )}

      {loading && (
        <div className="space-y-4" aria-busy="true" aria-label="Carregando operação">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonMetric key={i} />
            ))}
          </div>
          <div className="grid gap-4 lg:grid-cols-12">
            <SkeletonCard className="min-h-48 lg:col-span-7" />
            <SkeletonCard className="min-h-48 lg:col-span-5" />
          </div>
        </div>
      )}

      {data && (
        <>
          <section aria-labelledby="cc-kpis">
            <h2 id="cc-kpis" className="sr-only">
              Indicadores
            </h2>
            {data.sections.metrics === "error" && (
              <Alert variant="warning" className="mb-3">
                Não foi possível atualizar parte dos indicadores.
              </Alert>
            )}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
              <MetricCard
                label="Aguardando agora"
                value={String(data.metrics.waiting)}
                icon={<Users className="h-4 w-4" />}
                status={
                  data.metrics.waiting >= 15
                    ? "danger"
                    : data.metrics.waiting >= 8
                      ? "warning"
                      : "default"
                }
              />
              <MetricCard
                label="Em atendimento"
                value={String(data.metrics.serving)}
                icon={<Activity className="h-4 w-4" />}
              />
              <MetricCard
                label="Espera média"
                value={fmtSec(data.metrics.waitAvg)}
                hint="hoje"
                icon={<Clock className="h-4 w-4" />}
              />
              <MetricCard
                label="P90 de espera"
                value={fmtSec(data.metrics.waitP90)}
                hint="hoje"
                icon={<Clock className="h-4 w-4" />}
                status={
                  data.metrics.waitP90 != null && data.metrics.waitP90 >= 900
                    ? "danger"
                    : data.metrics.waitP90 != null && data.metrics.waitP90 >= 600
                      ? "warning"
                      : "default"
                }
              />
              <MetricCard
                label="Atendimentos hoje"
                value={String(data.metrics.completed)}
                hint={`${data.metrics.issued} emitidas`}
                icon={<ListOrdered className="h-4 w-4" />}
              />
              <MetricCard
                label="Ausências"
                value={String(data.metrics.no_show)}
                hint={
                  data.metrics.activeTerminals
                    ? `${data.metrics.activeTerminals} balcões ativos`
                    : undefined
                }
                icon={<AlertTriangle className="h-4 w-4" />}
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <SlaStrip sla={data.metrics.sla} />
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-12">
            <section className="space-y-3 lg:col-span-7" aria-labelledby="cc-queues">
              <div className="flex items-center justify-between gap-2">
                <h2 id="cc-queues" className="font-sans text-section-title text-brand-900">
                  Filas ao vivo
                </h2>
                <Link to="/queues" className="text-sm font-medium text-brand-700 hover:underline">
                  Ver filas
                </Link>
              </div>
              {data.sections.queues === "error" ? (
                <Alert variant="warning">Não foi possível atualizar as filas ao vivo.</Alert>
              ) : data.queues.length === 0 ? (
                <EmptyState
                  title="Nenhuma fila configurada nesta loja"
                  description="Cadastre filas de atendimento para monitorar a operação."
                />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {data.queues.map((q) => (
                    <Link
                      key={q.id}
                      to={`/queues/${q.id}`}
                      className="block rounded-ds focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
                    >
                      <Card interactive className="h-full">
                        <CardContent className="space-y-3 p-4">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-semibold text-brand-900">{q.name}</p>
                              {q.department_name && (
                                <p className="text-xs text-ink/55">{q.department_name}</p>
                              )}
                            </div>
                            <QueueStatus status={q.status} />
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <p className="text-xs text-ink/50">Aguardando</p>
                              <p className="font-semibold tabular-nums">{q.waiting_count}</p>
                            </div>
                            <div>
                              <p className="text-xs text-ink/50">Prioritárias</p>
                              <p className="font-semibold tabular-nums">{q.priority_waiting}</p>
                            </div>
                            <div>
                              <p className="text-xs text-ink/50">Senha atual</p>
                              <p className="font-semibold tabular-nums">{q.current_number || "—"}</p>
                            </div>
                            <div>
                              <p className="text-xs text-ink/50">Espera est.</p>
                              <p className="font-semibold tabular-nums">
                                {fmtSec(q.estimated_wait_seconds)}
                              </p>
                            </div>
                          </div>
                          <SlaIndicator level={q.sla_level} />
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <div className="space-y-4 lg:col-span-5">
              <section aria-labelledby="cc-alerts">
                <h2 id="cc-alerts" className="mb-3 font-sans text-section-title text-brand-900">
                  Atenção necessária
                </h2>
                <Card>
                  <CardContent className="space-y-2 p-4">
                    {data.alerts.length === 0 ? (
                      <div className="py-4 text-center">
                        <p className="font-medium text-brand-800">Operação normal</p>
                        <p className="mt-1 text-sm text-ink/60">
                          Nenhum alerta operacional no momento.
                        </p>
                      </div>
                    ) : (
                      data.alerts.map((a) => (
                        <Alert
                          key={a.id}
                          variant={
                            a.severity === "CRITICAL"
                              ? "danger"
                              : a.severity === "WARNING"
                                ? "warning"
                                : "info"
                          }
                          title={a.title}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span>{a.description}</span>
                            {a.href && (
                              <Link
                                to={a.href}
                                className="font-medium underline-offset-2 hover:underline"
                              >
                                Abrir
                              </Link>
                            )}
                          </div>
                        </Alert>
                      ))
                    )}
                  </CardContent>
                </Card>
              </section>

              <section aria-labelledby="cc-devices">
                <div className="mb-3 flex items-center justify-between">
                  <h2 id="cc-devices" className="font-sans text-section-title text-brand-900">
                    Saúde dos dispositivos
                  </h2>
                  <Link to="/devices" className="text-sm font-medium text-brand-700 hover:underline">
                    Ver dispositivos
                  </Link>
                </div>
                <Card>
                  <CardContent className="space-y-3 p-4">
                    {data.sections.devices === "error" ? (
                      <Alert variant="warning">
                        Não foi possível atualizar a saúde dos dispositivos.
                      </Alert>
                    ) : (
                      <>
                        {Object.entries(DEVICE_LABELS).map(([key, meta]) => {
                          const cat = data.devices.categories[key];
                          if (!cat || cat.total === 0) return null;
                          const Icon = meta.icon;
                          const ops = cat.online + cat.degraded + cat.offline;
                          const tone =
                            cat.level === "CRITICAL"
                              ? "offline"
                              : cat.level === "WARNING"
                                ? "degraded"
                                : "online";
                          return (
                            <div
                              key={key}
                              className="flex items-center justify-between gap-3 text-sm"
                            >
                              <span className="inline-flex items-center gap-2 text-ink/80">
                                <Icon className="h-4 w-4 text-brand-600" aria-hidden />
                                {meta.label}
                              </span>
                              <StatusDot
                                tone={tone}
                                label={`${cat.online} / ${ops || cat.total} online`}
                              />
                            </div>
                          );
                        })}
                        <div className="flex items-center justify-between gap-3 border-t border-brand-50 pt-3 text-sm">
                          <span className="inline-flex items-center gap-2 text-ink/80">
                            {data.edge.status === "ONLINE" ? (
                              <Wifi className="h-4 w-4 text-status-online" aria-hidden />
                            ) : (
                              <WifiOff className="h-4 w-4 text-status-degraded" aria-hidden />
                            )}
                            Edge
                          </span>
                          <StatusDot
                            tone={data.edge.status === "ONLINE" ? "online" : "degraded"}
                            label={data.edge.status === "ONLINE" ? "Online" : "Atenção"}
                          />
                        </div>
                        {data.devices.terminals.total > 0 && (
                          <p className="text-xs text-ink/50">
                            Balcões: {data.devices.terminals.active} / {data.devices.terminals.total}{" "}
                            ativos
                          </p>
                        )}
                        {Object.values(data.devices.categories).every((c) => !c || c.total === 0) &&
                          data.devices.terminals.total === 0 && (
                            <EmptyState
                              title="Nenhum dispositivo vinculado a esta loja"
                              description="Vincule telas, totens ou impressoras para monitorar a saúde."
                            />
                          )}
                      </>
                    )}
                  </CardContent>
                </Card>
              </section>
            </div>
          </div>

          <section aria-labelledby="cc-flow">
            <Card>
              <CardHeader
                title="Fluxo de atendimentos"
                description="Emitidas vs atendidas por hora (hoje)"
              />
              <h2 id="cc-flow" className="sr-only">
                Fluxo de atendimentos
              </h2>
              <CardContent>
                <HourlyFlowChart hourly={data.hourly} />
              </CardContent>
            </Card>
          </section>

          <div className="grid gap-4 lg:grid-cols-12">
            <section className="lg:col-span-8" aria-labelledby="cc-content">
              <h2 id="cc-content" className="mb-3 font-sans text-section-title text-brand-900">
                Agora nas telas
              </h2>
              <Card>
                <CardContent className="space-y-3 p-4">
                  {data.sections.content === "error" ? (
                    <Alert variant="warning">Não foi possível determinar o conteúdo atual.</Alert>
                  ) : !data.content.available || data.content.items.length === 0 ? (
                    <p className="text-sm text-ink/60">
                      {data.content.message || "Nenhum conteúdo ativo identificado."}
                    </p>
                  ) : (
                    data.content.items.map((item, idx) => (
                      <div
                        key={item.channel_id || `c-${idx}`}
                        className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-50 py-2 last:border-0"
                      >
                        <div>
                          <p className="font-medium text-brand-900">
                            {item.channel_name || "Canal / telas"}
                          </p>
                          <p className="text-sm text-ink/65">
                            Playlist: {item.playlist_name || item.schedule_name || "—"}
                            {item.schedule_name && item.playlist_name
                              ? ` · Agenda ${item.schedule_name}`
                              : ""}
                          </p>
                        </div>
                        <Badge tone="brand">{item.screen_count} telas</Badge>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </section>

            <section className="lg:col-span-4" aria-labelledby="cc-actions">
              <h2 id="cc-actions" className="mb-3 font-sans text-section-title text-brand-900">
                Ações rápidas
              </h2>
              <Card>
                <CardContent className="flex flex-col gap-2 p-4">
                  <Link
                    to="/queues"
                    className={cn(
                      "inline-flex items-center justify-start gap-2 rounded-ds border border-brand-700",
                      "px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50",
                      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
                    )}
                  >
                    <ListOrdered className="h-4 w-4" aria-hidden /> Ver filas
                  </Link>
                  <Link
                    to="/media"
                    className={cn(
                      "inline-flex items-center justify-start gap-2 rounded-ds border border-brand-700",
                      "px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50",
                      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
                    )}
                  >
                    <Monitor className="h-4 w-4" aria-hidden /> Gerenciar conteúdo
                  </Link>
                  <Link
                    to="/devices"
                    className={cn(
                      "inline-flex items-center justify-start gap-2 rounded-ds border border-brand-100",
                      "px-4 py-2.5 text-sm font-semibold text-brand-800 hover:bg-brand-50",
                      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
                    )}
                  >
                    <TabletSmartphone className="h-4 w-4" aria-hidden /> Ver dispositivos
                  </Link>
                </CardContent>
              </Card>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

function LiveBadge({ state, age }: { state: LiveState; age?: string }) {
  if (state === "live") {
    return (
      <Badge
        tone="success"
        icon={<span className="h-1.5 w-1.5 rounded-full bg-semantic-success" aria-hidden />}
      >
        Ao vivo{age ? ` · ${age}` : ""}
      </Badge>
    );
  }
  if (state === "updating") {
    return <Badge tone="info">Atualizando…</Badge>;
  }
  if (state === "stale") {
    return <Badge tone="warning">Dados desatualizados{age ? ` · ${age}` : ""}</Badge>;
  }
  if (state === "partial") {
    return <Badge tone="warning">Erro parcial</Badge>;
  }
  return <Badge tone="danger">Erro</Badge>;
}

function SlaStrip({ sla }: { sla: CommandCenterView["metrics"]["sla"] }) {
  const total = sla.green + sla.yellow + sla.red;
  const pct = total > 0 ? Math.round((sla.green / total) * 100) : null;
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <SlaIndicator level={sla.red > 0 ? "CRITICAL" : sla.yellow > 0 ? "WARNING" : "OK"} />
      {pct != null ? (
        <span className="text-ink/70">
          <strong className="text-brand-900">{pct}%</strong> dentro da meta (&lt;{" "}
          {Math.round(sla.target_wait_seconds / 60)} min)
        </span>
      ) : (
        <span className="text-ink/55">Sem amostras de SLA hoje</span>
      )}
      <span className="text-xs text-ink/45">
        Normal {sla.green} · Atenção {sla.yellow} · Crítico {sla.red}
      </span>
    </div>
  );
}
