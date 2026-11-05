import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link } from "react-router-dom";
import {
  MoreVertical,
  RefreshCw,
  Search,
  Unplug,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  DeviceStatus,
  Drawer,
  EmptyState,
  Input,
  MetricCard,
  Modal,
  PageHeader,
  Select,
  Skeleton,
} from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import api from "../services/api";

type ChannelOption = {
  id: string;
  name: string;
  layout_summary?: { name?: string; slug?: string } | null;
};

type FleetItem = {
  id: string;
  fleet_kind: string;
  device_id: string | null;
  display_id: string | null;
  terminal_id?: string;
  name: string;
  device_type: string;
  type_label: string;
  status: string;
  status_label: string;
  active: boolean;
  device_enabled?: boolean | null;
  last_seen_at: string | null;
  last_seen_relative: string | null;
  department?: { id: string; name: string } | null;
  queue?: { id: string; name: string } | null;
  commercial_code?: string | null;
  channel?: { id: string; name: string } | null;
  layout?: { name?: string; slug?: string; zones?: unknown[] } | null;
  programmed?: {
    source?: string;
    playlist_name?: string | null;
    schedule_name?: string | null;
    label?: string;
    confirmed?: boolean;
    note?: string;
  } | null;
  overrides?: Array<{ id: string; override_type: string; label: string }>;
  audio_enabled?: boolean;
  token_configured?: boolean;
  app_version?: string | null;
  config_version?: number | null;
  ip_address?: string | null;
  edge?: {
    status: string;
    pending: number;
    failed: number;
    last_synced_at?: string | null;
    details_path?: string;
  };
  diagnostics?: Record<string, unknown>;
  search_text?: string;
  note?: string;
};

type FleetResponse = {
  store_id: string;
  at: string;
  heartbeat: { online_seconds: number; degraded_seconds: number; note: string };
  summary: {
    total: number;
    online: number;
    degraded: number;
    offline: number;
    disabled: number;
    attention: number;
    displays: number;
    kiosks: number;
    by_type: Record<string, number>;
  };
  items: FleetItem[];
  edge: {
    status: string;
    pending: number;
    failed: number;
    synced: number;
    last_synced_at: string | null;
    details_path: string;
  };
  groups: Array<{ id: string; name: string; channel_id: string; channel_name?: string }>;
  channels: ChannelOption[];
  device_types_present: string[];
};

type TypeFilter = "ALL" | "DISPLAY" | "KIOSK" | "PRINTER" | "BUTTON" | "EDGE" | "TERMINAL";
type StatusFilter = "ALL" | "ONLINE" | "DEGRADED" | "OFFLINE" | "DISABLED";

const TYPE_FILTERS: Array<{ id: TypeFilter; label: string; types: string[] }> = [
  { id: "ALL", label: "Todos", types: [] },
  { id: "DISPLAY", label: "Telas", types: ["DISPLAY"] },
  { id: "KIOSK", label: "Totens", types: ["KIOSK"] },
  { id: "PRINTER", label: "Impressoras", types: ["PRINTER"] },
  { id: "BUTTON", label: "Botoeiras", types: ["BUTTON"] },
  { id: "EDGE", label: "Edge", types: ["EDGE"] },
  { id: "TERMINAL", label: "Terminais", types: ["TERMINAL"] },
];

const STATUS_FILTERS: Array<{ id: StatusFilter; label: string }> = [
  { id: "ALL", label: "Todos" },
  { id: "ONLINE", label: "Online" },
  { id: "DEGRADED", label: "Com atenção" },
  { id: "OFFLINE", label: "Offline" },
  { id: "DISABLED", label: "Desabilitados" },
];

function absoluteTime(iso: string | null | undefined) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR");
  } catch {
    return iso;
  }
}

export default function Devices() {
  const { selectedStoreId: storeId } = useStoreContext();
  const [fleet, setFleet] = useState<FleetResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);

  const [typeFilter, setTypeFilter] = useState<TypeFilter>("ALL");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [query, setQuery] = useState("");

  const [selected, setSelected] = useState<FleetItem | null>(null);
  const [techOpen, setTechOpen] = useState(false);

  const [pairOpen, setPairOpen] = useState(false);
  const [pairingCode, setPairingCode] = useState("");
  const [pairName, setPairName] = useState("");
  const [pairBusy, setPairBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const [channelTarget, setChannelTarget] = useState<FleetItem | null>(null);
  const [channelId, setChannelId] = useState("");
  const [channelBusy, setChannelBusy] = useState(false);

  const [disableTarget, setDisableTarget] = useState<FleetItem | null>(null);
  const [enableTarget, setEnableTarget] = useState<FleetItem | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const selectedIdRef = useRef<string | null>(null);
  const hasFleetRef = useRef(false);
  selectedIdRef.current = selected?.id ?? null;

  const load = useCallback(async (opts?: { soft?: boolean }) => {
    if (!storeId) {
      setFleet(null);
      hasFleetRef.current = false;
      setLoading(false);
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    if (!opts?.soft) {
      setLoading(true);
      setSelected(null);
    }
    setError(null);
    try {
      const { data } = await api.get<FleetResponse>("/devices/fleet", {
        params: { store_id: storeId },
        signal: ac.signal,
      });
      if (ac.signal.aborted) return;
      setFleet(data);
      hasFleetRef.current = true;
      setStale(false);
      setUpdatedAt(new Date());
      const keep = selectedIdRef.current;
      if (keep) {
        const next = data.items.find((i) => i.id === keep) || null;
        setSelected(next);
      }
    } catch (err: unknown) {
      if ((err as { code?: string; name?: string })?.code === "ERR_CANCELED") return;
      if (opts?.soft && hasFleetRef.current) {
        setStale(true);
      } else {
        setError("Não foi possível carregar os dispositivos.");
        setFleet(null);
        hasFleetRef.current = false;
      }
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only on store change
  }, [storeId]);

  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.hidden) return;
      void load({ soft: true });
    }, 30000);
    return () => window.clearInterval(id);
  }, [load]);

  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 10000);
    return () => window.clearInterval(id);
  }, []);

  const updatedLabel = useMemo(() => {
    void tick;
    if (!updatedAt) return null;
    const sec = Math.max(0, Math.round((Date.now() - updatedAt.getTime()) / 1000));
    if (sec < 15) return "Atualizado agora";
    if (sec < 60) return `Atualizado há ${sec}s`;
    return `Atualizado há ${Math.floor(sec / 60)} min`;
  }, [updatedAt, tick]);

  const typeOptions = useMemo(() => {
    const present = new Set(fleet?.device_types_present || []);
    return TYPE_FILTERS.filter((f) => f.id === "ALL" || f.types.some((t) => present.has(t)));
  }, [fleet]);

  const filtered = useMemo(() => {
    let rows = fleet?.items || [];
    if (typeFilter !== "ALL") {
      const types = TYPE_FILTERS.find((f) => f.id === typeFilter)?.types || [];
      rows = rows.filter((i) => types.includes(i.device_type));
    }
    if (statusFilter !== "ALL") {
      rows = rows.filter((i) => i.status === statusFilter);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      rows = rows.filter(
        (i) =>
          (i.search_text || "").includes(q) ||
          i.name.toLowerCase().includes(q) ||
          (i.commercial_code || "").toLowerCase().includes(q) ||
          (i.department?.name || "").toLowerCase().includes(q) ||
          (i.channel?.name || "").toLowerCase().includes(q),
      );
    }
    return rows;
  }, [fleet, typeFilter, statusFilter, query]);

  async function enroll(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !pairingCode.trim()) return;
    setPairBusy(true);
    setToast(null);
    try {
      await api.post("/devices/enroll", {
        pairing_code: pairingCode.trim(),
        store_id: storeId,
        name: pairName.trim() || undefined,
      });
      setPairOpen(false);
      setPairingCode("");
      setPairName("");
      setToast("Dispositivo pareado");
      await load({ soft: true });
    } catch {
      setError("Falha ao parear dispositivo. Verifique o código.");
    } finally {
      setPairBusy(false);
    }
  }

  async function confirmChannel() {
    if (!channelTarget?.display_id || !storeId) return;
    setChannelBusy(true);
    try {
      await api.post(`/displays/${channelTarget.display_id}/channel`, {
        channel_id: channelId || null,
        store_id: storeId,
      });
      setChannelTarget(null);
      setToast("Canal atualizado");
      await load({ soft: true });
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setError(
        status === 422
          ? "Canal inválido ou pertence a outra loja."
          : "Não foi possível alterar o canal.",
      );
    } finally {
      setChannelBusy(false);
    }
  }

  async function confirmDisable() {
    if (!disableTarget?.device_id) return;
    try {
      await api.post(`/devices/${disableTarget.device_id}/disable`);
      setDisableTarget(null);
      setToast("Dispositivo desabilitado");
      await load({ soft: true });
    } catch {
      setError("Não foi possível desabilitar.");
    }
  }

  async function confirmEnable() {
    if (!enableTarget?.device_id) return;
    try {
      await api.post(`/devices/${enableTarget.device_id}/enable`);
      setEnableTarget(null);
      setToast("Dispositivo reabilitado");
      await load({ soft: true });
    } catch {
      setError("Não foi possível reabilitar.");
    }
  }

  const summary = fleet?.summary;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Telas & dispositivos"
        description="Acompanhe a saúde e a configuração dos dispositivos da loja."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {updatedLabel && (
              <span className="text-xs text-ink/50" aria-live="polite">
                {updatedLabel}
              </span>
            )}
            <Button
              type="button"
              variant="ghost"
              onClick={() => void load()}
              aria-label="Atualizar frota"
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              Atualizar
            </Button>
            <Button type="button" onClick={() => setPairOpen(true)} disabled={!storeId}>
              Parear dispositivo
            </Button>
          </div>
        }
      />

      {toast && <Alert variant="success">{toast}</Alert>}
      {stale && (
        <Alert variant="warning">Dados desatualizados — a última atualização falhou.</Alert>
      )}
      {error && (
        <div className="space-y-2">
          <Alert variant="danger">{error}</Alert>
          <Button type="button" variant="ghost" size="sm" onClick={() => void load()}>
            Tentar novamente
          </Button>
        </div>
      )}

      {loading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton.Card key={i} className="h-24 rounded-ds" />
          ))}
        </div>
      )}

      {!loading && summary && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Total" value={summary.total} hint={`${summary.displays} telas`} />
          <MetricCard label="Online" value={summary.online} status="success" />
          <MetricCard
            label="Com atenção"
            value={summary.attention}
            status={summary.attention ? "warning" : "default"}
          />
          <MetricCard
            label="Offline"
            value={summary.offline}
            status={summary.offline ? "danger" : "default"}
          />
        </div>
      )}

      {!loading && fleet && (
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div
            className="flex flex-wrap gap-1"
            role="group"
            aria-label="Filtrar por tipo"
          >
            {typeOptions.map((f) => (
              <Button
                key={f.id}
                type="button"
                size="sm"
                variant={typeFilter === f.id ? "primary" : "ghost"}
                aria-pressed={typeFilter === f.id}
                onClick={() => setTypeFilter(f.id)}
              >
                {f.label}
              </Button>
            ))}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Select
              aria-label="Filtrar por status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="sm:w-44"
            >
              {STATUS_FILTERS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </Select>
            <div className="relative sm:w-64">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/40"
                aria-hidden
              />
              <Input
                aria-label="Buscar dispositivos"
                placeholder="Nome, código, canal…"
                className="pl-9"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {!loading && storeId && fleet && fleet.items.length === 0 && (
        <EmptyState
          title="Nenhum dispositivo cadastrado nesta loja."
          description="Pareie um dispositivo para começar a acompanhar a operação."
          action={
            <Button type="button" onClick={() => setPairOpen(true)}>
              Parear dispositivo
            </Button>
          }
        />
      )}

      {!loading && fleet && fleet.items.length > 0 && filtered.length === 0 && (
        <EmptyState title="Nenhum dispositivo corresponde aos filtros selecionados." />
      )}

      {!loading && filtered.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((item) => (
            <li key={item.id}>
              <article
                className="flex h-full flex-col rounded-ds border border-brand-100 bg-white p-4 shadow-ds-sm"
                aria-label={`${item.name}. ${item.type_label}. ${item.status_label}.`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate font-sans text-base font-semibold text-brand-900">
                      {item.name}
                    </h3>
                    <p className="text-xs text-ink/55">{item.type_label}</p>
                  </div>
                  <DeviceStatus status={item.status} />
                </div>

                <dl className="mt-3 space-y-1 text-sm text-ink/75">
                  {item.channel && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Canal</dt>
                      <dd className="truncate font-medium text-brand-900">{item.channel.name}</dd>
                    </div>
                  )}
                  {item.device_type === "DISPLAY" && !item.channel && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Canal</dt>
                      <dd className="text-ink/55">Sem canal atribuído</dd>
                    </div>
                  )}
                  {item.layout?.name && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Layout</dt>
                      <dd className="truncate">{item.layout.name}</dd>
                    </div>
                  )}
                  {item.programmed?.playlist_name && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Programado agora</dt>
                      <dd className="truncate">{item.programmed.playlist_name}</dd>
                    </div>
                  )}
                  {item.department && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Contexto</dt>
                      <dd className="truncate">{item.department.name}</dd>
                    </div>
                  )}
                  {item.edge && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Pendências</dt>
                      <dd>
                        {item.edge.pending} · falhas {item.edge.failed}
                      </dd>
                    </div>
                  )}
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Último contato</dt>
                    <dd>{item.last_seen_relative || "sem contato"}</dd>
                  </div>
                </dl>

                {(item.overrides?.length || 0) > 0 && (
                  <p className="mt-2 text-xs font-medium text-semantic-warning">
                    Interrupção ativa: {item.overrides![0].label}
                  </p>
                )}

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button type="button" size="sm" onClick={() => { setSelected(item); setTechOpen(false); }}>
                    Abrir
                  </Button>
                  {item.device_type === "DISPLAY" && item.display_id && (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setChannelTarget(item);
                        setChannelId(item.channel?.id || "");
                      }}
                    >
                      {item.channel ? "Alterar canal" : "Atribuir canal"}
                    </Button>
                  )}
                  {item.fleet_kind === "EDGE_SYNC" && (
                    <Link
                      to="/edge"
                      className="inline-flex items-center justify-center rounded-ds px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-50"
                    >
                      Ver detalhes do Edge
                    </Link>
                  )}
                  <details className="relative ml-auto">
                    <summary
                      className="flex h-8 w-8 cursor-pointer list-none items-center justify-center rounded-ds text-ink/60 hover:bg-brand-50"
                      aria-label={`Mais ações para ${item.name}`}
                    >
                      <MoreVertical className="h-4 w-4" aria-hidden />
                    </summary>
                    <div className="absolute right-0 z-10 mt-1 min-w-[10rem] rounded-ds border border-brand-100 bg-white p-1 shadow-ds-md">
                      {item.device_id && item.status !== "DISABLED" && (
                        <button
                          type="button"
                          className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-brand-50"
                          onClick={() => setDisableTarget(item)}
                        >
                          Desabilitar
                        </button>
                      )}
                      {item.device_id && item.status === "DISABLED" && (
                        <button
                          type="button"
                          className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-brand-50"
                          onClick={() => setEnableTarget(item)}
                        >
                          Reabilitar
                        </button>
                      )}
                      <button
                        type="button"
                        className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-brand-50"
                        onClick={() => { setSelected(item); setTechOpen(true); }}
                      >
                        Diagnóstico
                      </button>
                    </div>
                  </details>
                </div>
              </article>
            </li>
          ))}
        </ul>
      )}

      {fleet?.groups && fleet.groups.length > 0 && (
        <section aria-labelledby="groups-heading" className="rounded-ds border border-brand-100 bg-white p-4">
          <h2 id="groups-heading" className="text-sm font-semibold text-brand-900">
            Grupos de telas
          </h2>
          <p className="mt-1 text-xs text-ink/55">
            Organização secundária (ScreenGroup). Override por grupo não está disponível nesta sprint.
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {fleet.groups.map((g) => (
              <li key={g.id}>
                <Badge tone="neutral">
                  {g.name}
                  {g.channel_name ? ` · ${g.channel_name}` : ""}
                </Badge>
              </li>
            ))}
          </ul>
        </section>
      )}

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.name || "Dispositivo"}
      >
        {selected && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <DeviceStatus status={selected.status} />
              <Badge tone="neutral">{selected.type_label}</Badge>
              {selected.department && <Badge tone="neutral">{selected.department.name}</Badge>}
            </div>

            <section aria-labelledby="health-h">
              <h3 id="health-h" className="text-sm font-semibold text-brand-900">
                Saúde
              </h3>
              <dl className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-ink/50">Último contato</dt>
                  <dd>
                    {selected.last_seen_relative || "sem contato"}
                    {selected.last_seen_at && (
                      <span className="block text-xs text-ink/45">
                        {absoluteTime(selected.last_seen_at)}
                      </span>
                    )}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ink/50">Habilitado</dt>
                  <dd>{selected.active ? "Sim" : "Não"}</dd>
                </div>
                {selected.app_version && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Versão do app</dt>
                    <dd>{selected.app_version}</dd>
                  </div>
                )}
              </dl>
              {selected.status === "OFFLINE" && (
                <p className="mt-2 flex items-start gap-2 text-xs text-ink/60">
                  <Unplug className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                  Offline indica ausência de contato recente — não significa necessariamente defeito.
                </p>
              )}
              {selected.status === "DEGRADED" && (
                <p className="mt-2 text-xs text-semantic-warning">
                  Com atenção — heartbeat atrasado (entre{" "}
                  {fleet?.heartbeat.online_seconds}s e {fleet?.heartbeat.degraded_seconds}s).
                </p>
              )}
            </section>

            {selected.device_type === "DISPLAY" && (
              <section aria-labelledby="display-h">
                <h3 id="display-h" className="text-sm font-semibold text-brand-900">
                  Tela / player
                </h3>
                <dl className="mt-2 space-y-1 text-sm">
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Canal</dt>
                    <dd>{selected.channel?.name || "Sem canal atribuído"}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Layout esperado</dt>
                    <dd>{selected.layout?.name || "—"}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Programado agora</dt>
                    <dd>
                      {selected.programmed?.playlist_name ||
                        selected.programmed?.schedule_name ||
                        "—"}
                      <span className="block text-xs text-ink/45">
                        Conteúdo esperado — não é Proof of Play
                      </span>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Token do player</dt>
                    <dd>{selected.token_configured ? "CONFIGURADO" : "AUSENTE"}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink/50">Áudio</dt>
                    <dd>{selected.audio_enabled ? "Ativado" : "Desativado"}</dd>
                  </div>
                  {selected.queue && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink/50">Fila</dt>
                      <dd>{selected.queue.name}</dd>
                    </div>
                  )}
                </dl>
                {(selected.overrides?.length || 0) > 0 && (
                  <div className="mt-3 rounded-ds border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
                    <p className="font-medium text-amber-950">Interrupção ativa</p>
                    <ul className="mt-1 list-disc pl-4 text-amber-900">
                      {selected.overrides!.map((o) => (
                        <li key={o.id}>{o.label}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setChannelTarget(selected);
                      setChannelId(selected.channel?.id || "");
                    }}
                  >
                    {selected.channel ? "Alterar canal" : "Atribuir canal"}
                  </Button>
                </div>
              </section>
            )}

            {selected.edge && (
              <section>
                <h3 className="text-sm font-semibold text-brand-900">Edge</h3>
                <p className="mt-1 text-sm text-ink/70">
                  Status {selected.edge.status} · pendências {selected.edge.pending} · falhas{" "}
                  {selected.edge.failed}
                </p>
                <Link
                  to="/edge"
                  className="mt-2 inline-flex text-sm font-semibold text-brand-700 hover:underline"
                >
                  Abrir página Edge
                </Link>
              </section>
            )}

            <section aria-labelledby="diag-h">
              <h3 id="diag-h" className="text-sm font-semibold text-brand-900">
                Diagnóstico
              </h3>
              <ul className="mt-2 space-y-1 text-sm text-ink/75">
                <li>
                  Player:{" "}
                  {selected.token_configured
                    ? selected.status === "ONLINE"
                      ? "online (heartbeat recente)"
                      : "token configurado"
                    : selected.device_type === "DISPLAY"
                      ? "token ausente"
                      : "n/a"}
                </li>
                <li>
                  Heartbeat: {selected.last_seen_relative || "sem registro"}
                </li>
                <li>
                  Canal: {selected.channel?.name || "não configurado"}
                </li>
                <li>
                  Conteúdo esperado:{" "}
                  {selected.programmed?.playlist_name || "—"}
                </li>
              </ul>
            </section>

            <details open={techOpen} onToggle={(e) => setTechOpen((e.target as HTMLDetailsElement).open)}>
              <summary className="cursor-pointer text-sm font-semibold text-brand-900">
                Detalhes técnicos
              </summary>
              <dl className="mt-2 space-y-1 text-xs text-ink/60">
                {selected.device_id && (
                  <div className="flex justify-between gap-2">
                    <dt>device_id</dt>
                    <dd className="font-mono">{selected.device_id}</dd>
                  </div>
                )}
                {selected.display_id && (
                  <div className="flex justify-between gap-2">
                    <dt>display_id</dt>
                    <dd className="font-mono">{selected.display_id}</dd>
                  </div>
                )}
                {selected.config_version != null && (
                  <div className="flex justify-between gap-2">
                    <dt>config_version</dt>
                    <dd>{selected.config_version}</dd>
                  </div>
                )}
                {selected.ip_address && (
                  <div className="flex justify-between gap-2">
                    <dt>Último IP</dt>
                    <dd>{selected.ip_address}</dd>
                  </div>
                )}
                {selected.commercial_code && (
                  <div className="flex justify-between gap-2">
                    <dt>Código</dt>
                    <dd>{selected.commercial_code}</dd>
                  </div>
                )}
              </dl>
            </details>

            {selected.device_id && (
              <div className="flex flex-wrap gap-2 border-t border-brand-100 pt-4">
                {selected.status !== "DISABLED" ? (
                  <Button type="button" variant="danger" onClick={() => setDisableTarget(selected)}>
                    Desabilitar
                  </Button>
                ) : (
                  <Button type="button" onClick={() => setEnableTarget(selected)}>
                    Reabilitar
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </Drawer>

      <Modal
        open={pairOpen}
        onClose={() => setPairOpen(false)}
        title="Parear dispositivo"
      >
        <form className="space-y-3" onSubmit={enroll}>
          <p className="text-sm text-ink/65">
            Digite o código exibido em /pair no dispositivo.
          </p>
          <Input
            label="Código de pareamento"
            value={pairingCode}
            onChange={(e) => setPairingCode(e.target.value)}
            maxLength={6}
            required
            inputMode="numeric"
          />
          <Input
            label="Nome (opcional)"
            value={pairName}
            onChange={(e) => setPairName(e.target.value)}
          />
          <p className="text-xs text-ink/55">
            O dispositivo deve estar na tela de pareamento. Loja atual do StoreContext será usada.
          </p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setPairOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" loading={pairBusy}>
              Confirmar pareamento
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!channelTarget}
        onClose={() => setChannelTarget(null)}
        onConfirm={() => void confirmChannel()}
        title="Alterar canal desta tela?"
        description={
          <div className="space-y-3">
            <p>A programação exibida poderá mudar imediatamente.</p>
            <Select
              label="Canal"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
            >
              <option value="">Sem canal</option>
              {(fleet?.channels || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {c.layout_summary?.name ? ` · ${c.layout_summary.name}` : ""}
                </option>
              ))}
            </Select>
          </div>
        }
        confirmLabel={channelBusy ? "Salvando…" : "Alterar canal"}
        loading={channelBusy}
      />

      <ConfirmDialog
        open={!!disableTarget}
        onClose={() => setDisableTarget(null)}
        onConfirm={() => void confirmDisable()}
        title="Desabilitar dispositivo?"
        description="Ele deixará de participar da operação até ser reabilitado."
        confirmLabel="Desabilitar"
        danger
      />

      <ConfirmDialog
        open={!!enableTarget}
        onClose={() => setEnableTarget(null)}
        onConfirm={() => void confirmEnable()}
        title="Reabilitar dispositivo?"
        description="O dispositivo voltará a poder enviar heartbeat e participar da frota."
        confirmLabel="Reabilitar"
      />
    </div>
  );
}
