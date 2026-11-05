import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CalendarRange,
  Clock,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  Drawer,
  EmptyState,
  Input,
  Modal,
  PageHeader,
  PriorityBadge,
  priorityLabel,
  Select,
  Skeleton,
  Tabs,
} from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import { formatClockDuration } from "../lib/signageFormat";
import api from "../services/api";

type PlaylistOption = {
  id: string;
  name: string;
  item_count?: number;
  total_duration_seconds?: number;
};

type LayoutTemplate = {
  id: string;
  name: string;
  slug: string;
  is_system?: boolean;
  zones?: Array<{ type: string; x: number; y: number; width: number; height: number }>;
};

type Schedule = {
  id: string;
  name: string;
  playlist_id: string;
  playlist_name?: string | null;
  playlist_summary?: PlaylistOption | null;
  start_date: string | null;
  end_date: string | null;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  priority: string;
  priority_label?: string;
  active: boolean;
  overnight?: boolean;
  conflict_kind?: string | null;
  conflict_label?: string | null;
  is_current?: boolean;
};

type Channel = {
  id: string;
  store_id: string;
  name: string;
  layout: string;
  layout_template_id: string | null;
  default_playlist_id: string | null;
  schedule_count?: number;
  schedules: Schedule[];
  groups: Array<{ id: string; name: string }>;
  layout_summary?: {
    name?: string;
    slug?: string;
    layout_template_id?: string | null;
    zones?: LayoutTemplate["zones"];
  };
  default_playlist?: PlaylistOption | null;
  usage_count?: number;
  usage?: { display_count: number; group_count: number };
};

type Overview = {
  channel: Channel;
  at: string;
  current: {
    source?: string;
    schedule?: Schedule | null;
    playlist?: PlaylistOption | null;
    playlist_id?: string | null;
    conflicts?: Array<{ message: string; kind?: string }>;
  };
  next: {
    at: string;
    schedule?: Schedule;
    playlist?: PlaylistOption | null;
  } | null;
  schedules: Schedule[];
  conflicts: Array<{
    kind: string;
    message: string;
    schedule_ids: string[];
    names: string[];
  }>;
};

const DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const DAY_FULL = [
  "Segunda-feira",
  "Terça-feira",
  "Quarta-feira",
  "Quinta-feira",
  "Sexta-feira",
  "Sábado",
  "Domingo",
];

function minutesOf(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + (m || 0);
}

function describeSchedule(s: Schedule) {
  const days = s.days_of_week.map((d) => DAY_FULL[d] || DAY_LABELS[d]).join(", ");
  return `${s.name}. ${days}. ${s.start_time} às ${s.end_time}. ${priorityLabel(s.priority)}. Playlist ${s.playlist_name || s.playlist_summary?.name || ""}.`;
}

function LayoutMini({ zones }: { zones?: LayoutTemplate["zones"] }) {
  if (!zones?.length) {
    return (
      <div className="h-16 w-24 rounded-ds border border-brand-100 bg-brand-50 text-[10px] text-ink/45 flex items-center justify-center">
        Layout
      </div>
    );
  }
  return (
    <div className="relative h-16 w-24 overflow-hidden rounded-ds border border-brand-200 bg-brand-950/90">
      {zones.map((z, i) => (
        <div
          key={i}
          className={`absolute border border-white/20 text-[8px] font-semibold uppercase tracking-wide text-white/80 ${
            z.type === "QUEUE" ? "bg-brand-600/80" : "bg-brand-400/50"
          }`}
          style={{
            left: `${z.x}%`,
            top: `${z.y}%`,
            width: `${z.width}%`,
            height: `${z.height}%`,
          }}
        >
          <span className="absolute left-0.5 top-0.5">{z.type === "QUEUE" ? "Senha" : "Mídia"}</span>
        </div>
      ))}
    </div>
  );
}

type SchedForm = {
  name: string;
  playlist_id: string;
  start_time: string;
  end_time: string;
  days: number[];
  priority: string;
  start_date: string;
  end_date: string;
};

const emptyForm = (playlistId = ""): SchedForm => ({
  name: "",
  playlist_id: playlistId,
  start_time: "08:00",
  end_time: "21:00",
  days: [0, 1, 2, 3, 4, 5, 6],
  priority: "NORMAL",
  start_date: "",
  end_date: "",
});

export default function Channels() {
  const { selectedStoreId, loading: storeLoading } = useStoreContext();
  const storeId = selectedStoreId || "";
  const [searchParams, setSearchParams] = useSearchParams();

  const [channels, setChannels] = useState<Channel[]>([]);
  const [playlists, setPlaylists] = useState<PlaylistOption[]>([]);
  const [templates, setTemplates] = useState<LayoutTemplate[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [view, setView] = useState<"today" | "week">("today");
  const [mobileDay, setMobileDay] = useState(() => (new Date().getDay() + 6) % 7);

  const [createChannelOpen, setCreateChannelOpen] = useState(false);
  const [channelName, setChannelName] = useState("");
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [deleteChannel, setDeleteChannel] = useState<Channel | null>(null);
  const [deleteSchedule, setDeleteSchedule] = useState<Schedule | null>(null);

  const [schedOpen, setSchedOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);
  const [form, setForm] = useState<SchedForm>(emptyForm());
  const [formError, setFormError] = useState<string | null>(null);
  const [formWarnings, setFormWarnings] = useState<string[]>([]);

  const [configOpen, setConfigOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const overviewAbort = useRef<AbortController | null>(null);
  const storeRef = useRef(storeId);

  // JS getDay: 0=Sun … convert to ISO weekday used by backend (0=Mon)
  const todayIso = (new Date().getDay() + 6) % 7;

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    if (saveState !== "saved") return;
    const t = window.setTimeout(() => setSaveState("idle"), 1600);
    return () => window.clearTimeout(t);
  }, [saveState]);

  const loadChannels = useCallback(async (reason: "store" | "refresh" = "refresh") => {
    const sid = storeRef.current;
    if (!sid) {
      setChannels([]);
      setSelectedId(null);
      setOverview(null);
      setLoading(false);
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    if (reason === "store") {
      setChannels([]);
      setSelectedId(null);
      setOverview(null);
      setError(null);
      setLoading(true);
    }
    try {
      const [ch, pl, tpl] = await Promise.all([
        api.get<Channel[]>("/channels", { params: { store_id: sid }, signal: ac.signal }),
        api.get<PlaylistOption[]>("/playlists", { params: { store_id: sid }, signal: ac.signal }),
        api.get<LayoutTemplate[]>("/layout-templates", { params: { store_id: sid }, signal: ac.signal }),
      ]);
      if (storeRef.current !== sid) return;
      setChannels(ch.data);
      setPlaylists(pl.data);
      setTemplates(tpl.data);
      const fromUrl = searchParams.get("channel");
      setSelectedId((prev) => {
        if (fromUrl && ch.data.some((c) => c.id === fromUrl)) return fromUrl;
        if (prev && ch.data.some((c) => c.id === prev)) return prev;
        return ch.data[0]?.id || null;
      });
      setError(null);
    } catch (err: unknown) {
      if ((err as { code?: string })?.code === "ERR_CANCELED") return;
      if (storeRef.current !== sid) return;
      setError("Não foi possível carregar a programação.");
    } finally {
      if (storeRef.current === sid) setLoading(false);
    }
  }, [searchParams]);

  const loadOverview = useCallback(async (channelId: string) => {
    overviewAbort.current?.abort();
    const ac = new AbortController();
    overviewAbort.current = ac;
    setOverviewLoading(true);
    try {
      const { data } = await api.get<Overview>(`/channels/${channelId}/programming-overview`, {
        params: { store_id: storeRef.current },
        signal: ac.signal,
      });
      setOverview(data);
    } catch (err: unknown) {
      if ((err as { code?: string })?.code === "ERR_CANCELED") return;
      setOverview(null);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => {
    storeRef.current = storeId;
    if (!storeId || storeLoading) {
      setChannels([]);
      setSelectedId(null);
      setOverview(null);
      setLoading(!!storeLoading);
      return;
    }
    void loadChannels("store");
    return () => abortRef.current?.abort();
  }, [storeId, storeLoading, loadChannels]);

  useEffect(() => {
    if (!selectedId) {
      setOverview(null);
      return;
    }
    const next = new URLSearchParams(searchParams);
    if (next.get("channel") !== selectedId) {
      next.set("channel", selectedId);
      setSearchParams(next, { replace: true });
    }
    void loadOverview(selectedId);
    const id = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      void loadOverview(selectedId);
    }, 45000);
    return () => {
      window.clearInterval(id);
      overviewAbort.current?.abort();
    };
  }, [selectedId, loadOverview, searchParams, setSearchParams]);

  const selected = channels.find((c) => c.id === selectedId) || overview?.channel || null;
  const schedules = overview?.schedules || selected?.schedules || [];

  const todaySchedules = useMemo(() => {
    return schedules
      .filter((s) => s.days_of_week.includes(todayIso))
      .slice()
      .sort((a, b) => minutesOf(a.start_time) - minutesOf(b.start_time));
  }, [schedules, todayIso]);

  const weekByDay = useMemo(() => {
    return DAY_LABELS.map((_, day) =>
      schedules
        .filter((s) => s.days_of_week.includes(day))
        .slice()
        .sort((a, b) => minutesOf(a.start_time) - minutesOf(b.start_time)),
    );
  }, [schedules]);

  function openNewSchedule() {
    setEditingSchedule(null);
    setForm(emptyForm(playlists[0]?.id || selected?.default_playlist_id || ""));
    setFormError(null);
    setFormWarnings([]);
    setSchedOpen(true);
  }

  function openEditSchedule(s: Schedule) {
    setEditingSchedule(s);
    setForm({
      name: s.name,
      playlist_id: s.playlist_id,
      start_time: s.start_time,
      end_time: s.end_time,
      days: [...s.days_of_week],
      priority: s.priority,
      start_date: s.start_date || "",
      end_date: s.end_date || "",
    });
    setFormError(null);
    setFormWarnings([]);
    setSchedOpen(true);
  }

  function computeLocalWarnings(f: SchedForm): string[] {
    const warnings: string[] = [];
    if (!selectedId) return warnings;
    const draftDays = new Set(f.days);
    for (const s of schedules) {
      if (editingSchedule && s.id === editingSchedule.id) continue;
      const shared = s.days_of_week.some((d) => draftDays.has(d));
      if (!shared) continue;
      const a0 = minutesOf(f.start_time);
      const a1 = minutesOf(f.end_time);
      const b0 = minutesOf(s.start_time);
      const b1 = minutesOf(s.end_time);
      const overnightA = a0 > a1;
      const overnightB = b0 > b1;
      // simple same-day overlap check (backend overnight ok; warn if times intersect)
      let overlap = false;
      if (!overnightA && !overnightB) overlap = a0 <= b1 && b0 <= a1;
      else overlap = true; // conservative for overnight
      if (!overlap) continue;
      if (s.priority === f.priority) {
        warnings.push(`Sobreposição ambígua com “${s.name}” (${priorityLabel(s.priority)}).`);
      } else {
        warnings.push(`Sobreposição com “${s.name}” — prioridade define a exibição.`);
      }
    }
    return warnings;
  }

  useEffect(() => {
    if (!schedOpen) return;
    setFormWarnings(computeLocalWarnings(form));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, schedOpen, schedules, editingSchedule]);

  async function submitSchedule(e: FormEvent) {
    e.preventDefault();
    if (!selectedId) return;
    if (!form.name.trim()) {
      setFormError("Informe um nome para a programação.");
      return;
    }
    if (!form.playlist_id) {
      setFormError("Selecione uma playlist.");
      return;
    }
    if (form.days.length === 0) {
      setFormError("Selecione ao menos um dia.");
      return;
    }
    setSaveState("saving");
    setFormError(null);
    const payload = {
      channel_id: selectedId,
      playlist_id: form.playlist_id,
      name: form.name.trim(),
      start_time: form.start_time,
      end_time: form.end_time,
      days_of_week: form.days,
      priority: form.priority,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
    };
    try {
      if (editingSchedule) {
        await api.patch(`/schedules/${editingSchedule.id}`, payload);
      } else {
        await api.post("/schedules", payload);
      }
      setSchedOpen(false);
      setToast("Programação salva");
      setSaveState("saved");
      await loadChannels("refresh");
      if (selectedId) await loadOverview(selectedId);
    } catch {
      setFormError("Não foi possível salvar a programação.");
      setSaveState("error");
    }
  }

  async function createChannel(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !channelName.trim()) return;
    setSaveState("saving");
    try {
      const { data } = await api.post<Channel>("/channels", {
        store_id: storeId,
        name: channelName.trim(),
        default_playlist_id: playlists[0]?.id || null,
      });
      setCreateChannelOpen(false);
      setChannelName("");
      setToast("Canal criado");
      setSaveState("saved");
      await loadChannels("refresh");
      setSelectedId(data.id);
    } catch {
      setError("Não foi possível criar o canal.");
      setSaveState("error");
    }
  }

  async function renameChannel(e: FormEvent) {
    e.preventDefault();
    if (!selected || !renameValue.trim()) return;
    setSaveState("saving");
    try {
      await api.patch(`/channels/${selected.id}`, {
        store_id: storeId,
        name: renameValue.trim(),
      });
      setRenameOpen(false);
      setToast("Nome atualizado");
      setSaveState("saved");
      await loadChannels("refresh");
    } catch {
      setError("Não foi possível renomear.");
      setSaveState("error");
    }
  }

  async function saveChannelConfig(e: FormEvent) {
    e.preventDefault();
    if (!selected) return;
    const fd = new FormData(e.target as HTMLFormElement);
    setSaveState("saving");
    try {
      await api.patch(`/channels/${selected.id}`, {
        store_id: storeId,
        default_playlist_id: (fd.get("default_playlist_id") as string) || null,
        layout_template_id: (fd.get("layout_template_id") as string) || null,
      });
      setConfigOpen(false);
      setToast("Canal atualizado");
      setSaveState("saved");
      await loadChannels("refresh");
      if (selected.id) await loadOverview(selected.id);
    } catch {
      setError("Não foi possível salvar a configuração do canal.");
      setSaveState("error");
    }
  }

  async function confirmDeleteChannel() {
    if (!deleteChannel) return;
    if ((deleteChannel.usage_count || 0) > 0) {
      setDeleteChannel(null);
      return;
    }
    setSaveState("saving");
    try {
      await api.delete(`/channels/${deleteChannel.id}`, { params: { store_id: storeId } });
      setDeleteChannel(null);
      setToast("Canal excluído");
      setSaveState("saved");
      await loadChannels("refresh");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Não foi possível excluir o canal.";
      setToast(String(detail));
      setDeleteChannel(null);
      setSaveState("error");
    }
  }

  async function confirmDeleteSchedule() {
    if (!deleteSchedule) return;
    setSaveState("saving");
    try {
      await api.delete(`/schedules/${deleteSchedule.id}`);
      setDeleteSchedule(null);
      setToast("Programação removida");
      setSaveState("saved");
      await loadChannels("refresh");
      if (selectedId) await loadOverview(selectedId);
    } catch {
      setError("Falha ao remover programação.");
      setSaveState("error");
    }
  }

  function ScheduleCard({ s }: { s: Schedule }) {
    return (
      <article
        className={`rounded-ds border px-3 py-3 ${
          s.is_current
            ? "border-brand-500 bg-brand-50"
            : s.conflict_kind === "AMBIGUOUS"
              ? "border-semantic-warning-border bg-semantic-warning-bg/40"
              : "border-brand-100 bg-surface"
        }`}
        aria-label={describeSchedule(s)}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold text-brand-900">{s.name}</h4>
              {s.is_current && <Badge tone="success">Em exibição agora</Badge>}
              <PriorityBadge priority={s.priority} />
            </div>
            <p className="mt-1 text-sm text-ink/70">
              {s.playlist_name || s.playlist_summary?.name || "Playlist"} · {s.start_time} – {s.end_time}
              {s.overnight ? " (atravessa meia-noite)" : ""}
            </p>
            <p className="mt-0.5 text-xs text-ink/55">
              {s.days_of_week.map((d) => DAY_LABELS[d]).join(" · ")}
              {s.start_date || s.end_date
                ? ` · Vigência ${s.start_date || "…"} → ${s.end_date || "sem data final"}`
                : ""}
            </p>
            {s.conflict_label && (
              <p className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-semantic-warning">
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                {s.conflict_label}
              </p>
            )}
          </div>
          <div className="flex gap-1">
            <Button type="button" size="sm" variant="ghost" onClick={() => openEditSchedule(s)}>
              <Pencil className="h-3.5 w-3.5" aria-hidden />
              Editar
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="text-semantic-danger"
              onClick={() => setDeleteSchedule(s)}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
              Excluir
            </Button>
          </div>
        </div>
      </article>
    );
  }

  const current = overview?.current;
  const next = overview?.next;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Programação"
        description="Defina quando cada playlist será exibida nas telas da loja."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" disabled={!storeId} onClick={() => setCreateChannelOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden />
              Novo canal
            </Button>
            <Button type="button" disabled={!selectedId} onClick={openNewSchedule}>
              <Plus className="h-4 w-4" aria-hidden />
              Nova programação
            </Button>
          </div>
        }
      />

      {!storeId && !storeLoading && (
        <Alert variant="warning">Selecione uma loja na barra superior.</Alert>
      )}
      {toast && <Alert variant="success">{toast}</Alert>}
      {error && (
        <div className="space-y-2">
          <Alert variant="danger">{error}</Alert>
          <Button type="button" size="sm" variant="secondary" onClick={() => void loadChannels("refresh")}>
            Tentar novamente
          </Button>
        </div>
      )}

      {loading && (
        <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
          <Skeleton.Card />
          <Skeleton.Card />
        </div>
      )}

      {!loading && storeId && channels.length === 0 && (
        <EmptyState
          icon={<CalendarRange className="h-8 w-8" aria-hidden />}
          title="Nenhum canal configurado"
          description="Crie um canal para organizar a programação de conteúdos da loja."
          action={
            <Button type="button" onClick={() => setCreateChannelOpen(true)}>
              Criar canal
            </Button>
          }
        />
      )}

      {!loading && channels.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
          <aside className="rounded-ds border border-brand-100 bg-surface p-3">
            <h2 className="mb-2 text-sm font-semibold text-brand-900">Canais</h2>
            <div className="mb-3 lg:hidden">
              <Select
                aria-label="Canal"
                value={selectedId || ""}
                onChange={(e) => setSelectedId(e.target.value || null)}
              >
                {channels.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </div>
            <ul className="hidden space-y-1 lg:block" role="listbox">
              {channels.map((c) => {
                const active = c.id === selectedId;
                return (
                  <li key={c.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={active}
                      className={`w-full rounded-ds px-3 py-2.5 text-left ${
                        active ? "bg-brand-50 ring-1 ring-brand-200" : "hover:bg-brand-50/70"
                      }`}
                      onClick={() => setSelectedId(c.id)}
                    >
                      <span className="block font-semibold text-brand-900">{c.name}</span>
                      <span className="mt-0.5 block text-xs text-ink/55">
                        {c.schedule_count ?? c.schedules?.length ?? 0} programação(ões)
                        {c.layout_summary?.name ? ` · ${c.layout_summary.name}` : ""}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </aside>

          <section className="min-w-0 space-y-4 rounded-ds border border-brand-100 bg-surface p-4 sm:p-5">
            {!selected ? (
              <p className="text-sm text-ink/60">Selecione um canal.</p>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-sans text-xl font-semibold text-brand-900">{selected.name}</h2>
                    <p className="mt-1 text-sm text-ink/60">
                      Conteúdo padrão:{" "}
                      <strong>{selected.default_playlist?.name || "Não definido"}</strong>
                      {selected.default_playlist?.total_duration_seconds != null &&
                        ` · ${formatClockDuration(selected.default_playlist.total_duration_seconds)}`}
                      {" · "}
                      Layout: <strong>{selected.layout_summary?.name || selected.layout}</strong>
                      {saveState === "saving" && " · Salvando..."}
                      {saveState === "saved" && " · Salvo"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setRenameValue(selected.name);
                        setRenameOpen(true);
                      }}
                    >
                      Renomear
                    </Button>
                    <Button type="button" size="sm" variant="secondary" onClick={() => setConfigOpen(true)}>
                      Configuração
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="text-semantic-danger"
                      onClick={() => setDeleteChannel(selected)}
                    >
                      Excluir canal
                    </Button>
                  </div>
                </div>

                {/* Agora / Próximo */}
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-ds border border-brand-100 bg-brand-50/50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">Agora</p>
                    {overviewLoading && !current ? (
                      <Skeleton.Line className="mt-2" />
                    ) : current?.schedule ? (
                      <>
                        <p className="mt-1 font-sans text-lg font-semibold text-brand-900">
                          {current.schedule.name}
                        </p>
                        <p className="text-sm text-ink/70">
                          {current.playlist?.name || current.schedule.playlist_name} ·{" "}
                          {current.schedule.start_time} – {current.schedule.end_time}
                        </p>
                        <div className="mt-2">
                          <PriorityBadge priority={current.schedule.priority} />
                        </div>
                      </>
                    ) : (
                      <>
                        <p className="mt-1 font-sans text-lg font-semibold text-brand-900">
                          {current?.playlist?.name || "Conteúdo padrão"}
                        </p>
                        <p className="text-sm text-ink/70">
                          {current?.source === "channel_default"
                            ? "Nenhuma programação específica ativa"
                            : "Nenhum conteúdo resolvido"}
                        </p>
                      </>
                    )}
                  </div>
                  <div className="rounded-ds border border-brand-100 bg-surface p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-ink/55">Próximo</p>
                    {next?.schedule ? (
                      <>
                        <p className="mt-1 font-sans text-lg font-semibold text-brand-900">
                          {next.schedule.name}
                        </p>
                        <p className="inline-flex items-center gap-1 text-sm text-ink/70">
                          <Clock className="h-3.5 w-3.5" aria-hidden />
                          {next.schedule.start_time}
                          {next.playlist?.name ? ` · ${next.playlist.name}` : ""}
                        </p>
                      </>
                    ) : (
                      <p className="mt-1 text-sm text-ink/55">Nenhuma programação futura nos próximos dias.</p>
                    )}
                  </div>
                </div>

                <Tabs
                  items={[
                    { id: "today", label: "Hoje" },
                    { id: "week", label: "Semana" },
                  ]}
                  value={view}
                  onChange={(id) => setView(id as "today" | "week")}
                />

                {view === "today" && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-brand-900">
                      {DAY_FULL[todayIso]}
                    </h3>
                    {todaySchedules.length === 0 ? (
                      <EmptyState
                        title="Nenhuma programação para hoje"
                        description={
                          selected.default_playlist_id
                            ? "O conteúdo padrão do canal continuará sendo exibido."
                            : "Defina um conteúdo padrão ou crie uma programação."
                        }
                        action={
                          <Button type="button" onClick={openNewSchedule}>
                            Criar programação
                          </Button>
                        }
                      />
                    ) : (
                      <ol className="relative space-y-3 border-l-2 border-brand-100 pl-4">
                        {todaySchedules.map((s) => {
                          const startM = minutesOf(s.start_time);
                          const endM = minutesOf(s.end_time);
                          const span = Math.max(30, (endM >= startM ? endM - startM : 24 * 60 - startM + endM) / 4);
                          return (
                            <li key={s.id} className="relative">
                              <span className="absolute -left-[1.35rem] top-3 h-2.5 w-2.5 rounded-full bg-brand-600" />
                              <p className="mb-1 text-xs font-semibold tabular-nums text-ink/50">
                                {s.start_time}
                              </p>
                              <div style={{ minHeight: `${Math.min(120, span)}px` }}>
                                <ScheduleCard s={s} />
                              </div>
                            </li>
                          );
                        })}
                      </ol>
                    )}
                  </div>
                )}

                {view === "week" && (
                  <div className="space-y-4">
                    {/* Mobile: day picker */}
                    <div className="lg:hidden">
                      <Select
                        aria-label="Dia da semana"
                        value={String(mobileDay)}
                        onChange={(e) => setMobileDay(Number(e.target.value))}
                      >
                        {DAY_FULL.map((label, iso) => (
                          <option key={label} value={iso}>
                            {label}
                          </option>
                        ))}
                      </Select>
                      <div className="mt-3 space-y-2">
                        {(weekByDay[mobileDay] || []).map((s) => (
                          <ScheduleCard key={s.id} s={s} />
                        ))}
                        {(weekByDay[mobileDay] || []).length === 0 && (
                          <p className="text-sm text-ink/55">Sem programação neste dia.</p>
                        )}
                      </div>
                    </div>
                    <div className="hidden gap-3 lg:grid lg:grid-cols-7">
                      {DAY_LABELS.map((label, day) => (
                        <div key={label} className="min-w-0">
                          <p
                            className={`mb-2 text-center text-xs font-semibold uppercase tracking-wide ${
                              day === todayIso ? "text-brand-700" : "text-ink/50"
                            }`}
                          >
                            {label}
                          </p>
                          <div className="space-y-2">
                            {weekByDay[day].map((s) => (
                              <button
                                key={s.id}
                                type="button"
                                className={`w-full rounded-ds border px-2 py-2 text-left text-xs ${
                                  s.is_current
                                    ? "border-brand-500 bg-brand-50"
                                    : s.conflict_kind === "AMBIGUOUS"
                                      ? "border-semantic-warning-border bg-semantic-warning-bg/30"
                                      : "border-brand-100"
                                }`}
                                onClick={() => openEditSchedule(s)}
                                aria-label={describeSchedule(s)}
                              >
                                <p className="font-semibold text-brand-900 line-clamp-2">{s.name}</p>
                                <p className="mt-0.5 text-ink/55">
                                  {s.start_time}–{s.end_time}
                                </p>
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}

      {/* Create channel */}
      <Modal
        open={createChannelOpen}
        onClose={() => setCreateChannelOpen(false)}
        title="Novo canal"
        footer={
          <>
            <Button type="button" variant="ghost" onClick={() => setCreateChannelOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="ch-create">
              Criar
            </Button>
          </>
        }
      >
        <form id="ch-create" onSubmit={(e) => void createChannel(e)}>
          <Input
            label="Nome"
            value={channelName}
            onChange={(e) => setChannelName(e.target.value)}
            required
            placeholder="Ex.: Canal Açougue"
            autoFocus
          />
        </form>
      </Modal>

      <Modal
        open={renameOpen}
        onClose={() => setRenameOpen(false)}
        title="Renomear canal"
        footer={
          <>
            <Button type="button" variant="ghost" onClick={() => setRenameOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="ch-rename">
              Salvar
            </Button>
          </>
        }
      >
        <form id="ch-rename" onSubmit={(e) => void renameChannel(e)}>
          <Input label="Nome" value={renameValue} onChange={(e) => setRenameValue(e.target.value)} required />
        </form>
      </Modal>

      {/* Channel config */}
      <Drawer
        open={configOpen && !!selected}
        onClose={() => setConfigOpen(false)}
        title="Configuração do canal"
        className="max-w-lg"
        footer={
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setConfigOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="ch-config">
              Salvar
            </Button>
          </div>
        }
      >
        {selected && (
          <form id="ch-config" className="space-y-4" onSubmit={(e) => void saveChannelConfig(e)}>
            <div>
              <p className="mb-1 text-sm font-medium text-ink">Conteúdo padrão</p>
              <p className="mb-2 text-xs text-ink/55">
                Exibido quando nenhuma programação específica está ativa.
              </p>
              <Select
                name="default_playlist_id"
                aria-label="Conteúdo padrão"
                defaultValue={selected.default_playlist_id || ""}
              >
                <option value="">Nenhum</option>
                {playlists.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.item_count != null ? ` · ${p.item_count} conteúdos` : ""}
                    {p.total_duration_seconds != null
                      ? ` · ${formatClockDuration(p.total_duration_seconds)}`
                      : ""}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <p className="mb-1 text-sm font-medium text-ink">Layout</p>
              <Select
                name="layout_template_id"
                aria-label="Layout"
                defaultValue={selected.layout_template_id || selected.layout_summary?.layout_template_id || ""}
              >
                <option value="">Automático (legado: {selected.layout})</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </Select>
              <div className="mt-3">
                <LayoutMini zones={selected.layout_summary?.zones} />
              </div>
            </div>
          </form>
        )}
      </Drawer>

      {/* Schedule drawer */}
      <Drawer
        open={schedOpen}
        onClose={() => setSchedOpen(false)}
        title={editingSchedule ? "Editar programação" : "Nova programação"}
        className="max-w-lg"
        footer={
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setSchedOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="sched-form">
              Salvar
            </Button>
          </div>
        }
      >
        <form id="sched-form" className="space-y-4" onSubmit={(e) => void submitSchedule(e)}>
          <Input
            label="Nome"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
            placeholder="Ex.: Churrasco"
          />
          <Select
            label="Playlist"
            value={form.playlist_id}
            onChange={(e) => setForm((f) => ({ ...f, playlist_id: e.target.value }))}
            required
          >
            <option value="" disabled>
              Selecione…
            </option>
            {playlists.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.item_count != null ? ` · ${p.item_count} conteúdos` : ""}
                {p.total_duration_seconds != null
                  ? ` · ${formatClockDuration(p.total_duration_seconds)}`
                  : ""}
              </option>
            ))}
          </Select>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">Dias da semana</legend>
            <div className="mb-2 flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setForm((f) => ({ ...f, days: [0, 1, 2, 3, 4, 5, 6] }))}
              >
                Todos os dias
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setForm((f) => ({ ...f, days: [0, 1, 2, 3, 4] }))}
              >
                Segunda a sexta
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setForm((f) => ({ ...f, days: [5, 6] }))}
              >
                Fim de semana
              </Button>
            </div>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Dias">
              {DAY_LABELS.map((label, idx) => {
                const on = form.days.includes(idx);
                return (
                  <button
                    key={label}
                    type="button"
                    aria-pressed={on}
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        days: on ? f.days.filter((d) => d !== idx) : [...f.days, idx].sort(),
                      }))
                    }
                    className={`rounded-ds px-2.5 py-1.5 text-xs font-semibold ${
                      on ? "bg-brand-700 text-white" : "border border-brand-100 text-ink/70"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Início"
              type="time"
              value={form.start_time}
              onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))}
              required
            />
            <Input
              label="Fim"
              type="time"
              value={form.end_time}
              onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))}
              required
              hint={
                minutesOf(form.start_time) > minutesOf(form.end_time)
                  ? "Atravessa meia-noite (suportado)"
                  : undefined
              }
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Vigência — início"
              type="date"
              value={form.start_date}
              onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
              hint="Opcional"
            />
            <Input
              label="Vigência — fim"
              type="date"
              value={form.end_date}
              onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
              hint="Deixe vazio = sem data final"
            />
          </div>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">Prioridade</legend>
            <div className="space-y-2">
              {(
                [
                  {
                    id: "NORMAL",
                    title: "Programação normal",
                    help: "Segue a programação comum.",
                  },
                  {
                    id: "HIGH",
                    title: "Prioritária",
                    help: "Assume quando houver disputa com uma programação normal.",
                  },
                  {
                    id: "EMERGENCY",
                    title: "Emergencial",
                    help: "Maior prioridade dentro da agenda (conteúdo base — não é Screen Override).",
                  },
                ] as const
              ).map((opt) => (
                <label
                  key={opt.id}
                  className={`flex cursor-pointer gap-3 rounded-ds border px-3 py-2 ${
                    form.priority === opt.id ? "border-brand-600 bg-brand-50" : "border-brand-100"
                  }`}
                >
                  <input
                    type="radio"
                    name="priority"
                    className="mt-1"
                    checked={form.priority === opt.id}
                    onChange={() => setForm((f) => ({ ...f, priority: opt.id }))}
                  />
                  <span>
                    <span className="block text-sm font-semibold text-brand-900">{opt.title}</span>
                    <span className="block text-xs text-ink/60">{opt.help}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="rounded-ds border border-brand-100 bg-surface-muted/50 px-3 py-2 text-sm">
            <p className="font-semibold text-brand-900">Resumo</p>
            <p className="mt-1 text-ink/70">
              {form.name || "Sem nome"} · {form.start_time}–{form.end_time} ·{" "}
              {form.days.map((d) => DAY_LABELS[d]).join(" ")} · {priorityLabel(form.priority)}
            </p>
          </div>

          {formWarnings.map((w) => (
            <Alert key={w} variant="warning">
              {w}
            </Alert>
          ))}
          {formError && <Alert variant="danger">{formError}</Alert>}
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteChannel}
        onClose={() => setDeleteChannel(null)}
        onConfirm={() => void confirmDeleteChannel()}
        title={
          deleteChannel && (deleteChannel.usage_count || 0) > 0
            ? "Não é possível excluir"
            : "Excluir canal?"
        }
        description={
          deleteChannel && (deleteChannel.usage_count || 0) > 0 ? (
            <p>
              Este canal está em uso
              {deleteChannel.usage
                ? ` (${[
                    deleteChannel.usage.display_count &&
                      `${deleteChannel.usage.display_count} display(s)`,
                    deleteChannel.usage.group_count &&
                      `${deleteChannel.usage.group_count} grupo(s)`,
                  ]
                    .filter(Boolean)
                    .join(", ")})`
                : ""}
              . Remova as associações antes de excluir.
            </p>
          ) : (
            <p>As programações deste canal deixarão de estar ativas. Playlists não serão excluídas.</p>
          )
        }
        confirmLabel={
          deleteChannel && (deleteChannel.usage_count || 0) > 0 ? "Entendi" : "Excluir"
        }
        danger={!(deleteChannel && (deleteChannel.usage_count || 0) > 0)}
      />

      <ConfirmDialog
        open={!!deleteSchedule}
        onClose={() => setDeleteSchedule(null)}
        onConfirm={() => void confirmDeleteSchedule()}
        title="Remover esta programação?"
        description={
          <p>
            A playlist deixará de ser exibida nos horários definidos por esta programação. A playlist
            permanece na biblioteca.
          </p>
        }
        confirmLabel="Remover"
        danger
      />
    </div>
  );
}
