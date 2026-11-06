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
  ChevronDown,
  ChevronUp,
  Clock,
  GripVertical,
  Image as ImageIcon,
  ListVideo,
  MoreVertical,
  Pause,
  Pencil,
  Play,
  Plus,
  SkipBack,
  SkipForward,
  Table2,
  Trash2,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  EmptyState,
  IconButton,
  Input,
  Modal,
  PageHeader,
  Select,
  Skeleton,
} from "../design-system";
import { DynamicPicker } from "../components/media/DynamicPicker";
import { MediaPicker } from "../components/media/MediaPicker";
import { MediaThumb } from "../components/media/MediaThumb";
import { StudioPreview } from "../components/media/StudioPreview";
import type { PlaylistItem as PlayerSlide } from "../components/display/types";
import { useStoreContext } from "../context/StoreContext";
import { effectiveItemDuration, formatClockDuration } from "../lib/signageFormat";
import type { MediaItem } from "./Media";
import api from "../services/api";

type PlaylistItemRow = {
  id: string;
  item_type?: "MEDIA" | "DYNAMIC" | string;
  asset_id: string | null;
  dynamic_content_id?: string | null;
  position: number;
  duration_seconds: number;
  duration_source?: string | null;
  effective_duration_seconds?: number | null;
  asset: MediaItem | null;
  dynamic_content?: {
    id: string;
    name: string;
    content_type?: string;
    status?: string | null;
    page_count?: number | null;
    item_count?: number | null;
    total_duration_seconds?: number | null;
  } | null;
};

type Playlist = {
  id: string;
  store_id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  items: PlaylistItemRow[];
  item_count?: number;
  total_duration_seconds?: number;
  usage_count?: number;
  usage?: {
    channel_count: number;
    schedule_count: number;
    display_count: number;
    usage_count: number;
  };
};

type SaveState = "idle" | "saving" | "saved" | "error";

function toPlayerSlide(item: PlaylistItemRow): PlayerSlide | null {
  const itype = (item.item_type || "MEDIA").toUpperCase();
  if (itype === "DYNAMIC") {
    if (!item.dynamic_content && !item.dynamic_content_id) return null;
    return {
      id: item.dynamic_content?.id || item.dynamic_content_id || item.id,
      item_id: item.id,
      item_type: "DYNAMIC",
      name: item.dynamic_content?.name || "Tabela",
      type: "DYNAMIC",
      url: "",
      mime_type: null,
      duration_seconds: effectiveItemDuration(item),
      dynamic_content: {
        id: item.dynamic_content?.id || item.dynamic_content_id || "",
        content_type: item.dynamic_content?.content_type || "PRICE_TABLE",
        name: item.dynamic_content?.name,
      },
    };
  }
  if (!item.asset) return null;
  return {
    id: item.id,
    item_type: "MEDIA",
    name: item.asset.name,
    type: item.asset.media_type,
    url: item.asset.public_url,
    mime_type: item.asset.mime_type,
    duration_seconds: effectiveItemDuration(item),
  };
}

export default function Playlists() {
  const { selectedStoreId, selectedStore, loading: storeLoading } = useStoreContext();
  const storeId = selectedStoreId || "";
  const [searchParams, setSearchParams] = useSearchParams();

  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [deletePl, setDeletePl] = useState<Playlist | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [dynamicPickerOpen, setDynamicPickerOpen] = useState(false);
  const [addChooserOpen, setAddChooserOpen] = useState(false);
  const [pickerBusy, setPickerBusy] = useState(false);

  const [dragId, setDragId] = useState<string | null>(null);
  const [reorderBusy, setReorderBusy] = useState(false);
  const [menuItemId, setMenuItemId] = useState<string | null>(null);
  const [durationEditId, setDurationEditId] = useState<string | null>(null);

  const [previewIndex, setPreviewIndex] = useState(0);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const [aspect, setAspect] = useState<"16:9" | "9:16">("16:9");

  const abortRef = useRef<AbortController | null>(null);
  const storeRef = useRef(storeId);
  const snapshotRef = useRef<Playlist[]>([]);

  const selected = playlists.find((p) => p.id === selectedId) || null;

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    if (saveState !== "saved") return;
    const t = window.setTimeout(() => setSaveState("idle"), 1500);
    return () => window.clearTimeout(t);
  }, [saveState]);

  const applyPlaylist = useCallback((data: Playlist) => {
    setPlaylists((prev) => {
      const exists = prev.some((p) => p.id === data.id);
      if (!exists) return [...prev, data];
      return prev.map((p) => (p.id === data.id ? data : p));
    });
  }, []);

  const load = useCallback(
    async (reason: "store" | "refresh" = "refresh") => {
      const sid = storeRef.current;
      if (!sid) {
        setPlaylists([]);
        setSelectedId(null);
        setLoading(false);
        return;
      }
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      if (reason === "store") {
        setPlaylists([]);
        setSelectedId(null);
        setError(null);
        setLoading(true);
        setPreviewPlaying(false);
      } else if (!snapshotRef.current.length) {
        setLoading(true);
      }
      try {
        const { data } = await api.get<Playlist[]>("/playlists", {
          params: { store_id: sid },
          signal: ac.signal,
        });
        if (storeRef.current !== sid) return;
        setPlaylists(data);
        snapshotRef.current = data;
        setError(null);
        const fromUrl = searchParams.get("playlist");
        setSelectedId((prev) => {
          if (fromUrl && data.some((p) => p.id === fromUrl)) return fromUrl;
          if (prev && data.some((p) => p.id === prev)) return prev;
          return data[0]?.id || null;
        });
      } catch (err: unknown) {
        const code = (err as { code?: string })?.code;
        if (code === "ERR_CANCELED") return;
        if (storeRef.current !== sid) return;
        setError("Não foi possível carregar as playlists.");
      } finally {
        if (storeRef.current === sid) setLoading(false);
      }
    },
    [searchParams],
  );

  useEffect(() => {
    storeRef.current = storeId;
    if (!storeId || storeLoading) {
      setPlaylists([]);
      setSelectedId(null);
      setLoading(!!storeLoading);
      return;
    }
    void load("store");
    return () => abortRef.current?.abort();
  }, [storeId, storeLoading, load]);

  useEffect(() => {
    if (!selectedId) return;
    const next = new URLSearchParams(searchParams);
    if (next.get("playlist") === selectedId) return;
    next.set("playlist", selectedId);
    setSearchParams(next, { replace: true });
  }, [selectedId, searchParams, setSearchParams]);

  useEffect(() => {
    setPreviewIndex(0);
    setPreviewPlaying(false);
    setMenuItemId(null);
    setDurationEditId(null);
  }, [selectedId]);

  // Preview auto-advance when playing
  useEffect(() => {
    if (!previewPlaying || !selected || selected.items.length === 0) return;
    const item = selected.items[previewIndex % selected.items.length];
    const ms = effectiveItemDuration(item) * 1000;
    const id = window.setTimeout(() => {
      setPreviewIndex((i) => (i + 1) % selected.items.length);
    }, ms);
    return () => window.clearTimeout(id);
  }, [previewPlaying, selected, previewIndex]);

  const totalDuration = useMemo(() => {
    if (!selected) return 0;
    if (typeof selected.total_duration_seconds === "number") return selected.total_duration_seconds;
    return selected.items.reduce((acc, i) => acc + effectiveItemDuration(i), 0);
  }, [selected]);

  async function withSave<T>(fn: () => Promise<T>): Promise<T | null> {
    setSaveState("saving");
    try {
      const result = await fn();
      setSaveState("saved");
      return result;
    } catch {
      setSaveState("error");
      return null;
    }
  }

  async function createPlaylist(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !createName.trim()) return;
    const data = await withSave(() =>
      api
        .post<Playlist>("/playlists", {
          store_id: storeId,
          name: createName.trim(),
          is_default: playlists.length === 0,
        })
        .then((r) => r.data),
    );
    if (!data) {
      setError("Não foi possível criar a playlist.");
      return;
    }
    setCreateOpen(false);
    setCreateName("");
    setToast("Playlist criada");
    setPlaylists((prev) => [...prev, data]);
    setSelectedId(data.id);
  }

  async function renamePlaylist(e: FormEvent) {
    e.preventDefault();
    if (!selected || !renameValue.trim()) return;
    const data = await withSave(() =>
      api
        .patch<Playlist>(`/playlists/${selected.id}`, {
          store_id: storeId,
          name: renameValue.trim(),
        })
        .then((r) => r.data),
    );
    if (!data) {
      setError("Não foi possível renomear.");
      return;
    }
    applyPlaylist(data);
    setRenameOpen(false);
    setToast("Nome atualizado");
  }

  async function confirmDeletePlaylist() {
    if (!deletePl) return;
    if ((deletePl.usage_count || 0) > 0) {
      setDeletePl(null);
      return;
    }
    setSaveState("saving");
    try {
      await api.delete(`/playlists/${deletePl.id}`, { params: { store_id: storeId } });
      setPlaylists((prev) => prev.filter((p) => p.id !== deletePl.id));
      if (selectedId === deletePl.id) setSelectedId(null);
      setDeletePl(null);
      setToast("Playlist excluída");
      setSaveState("saved");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Não foi possível excluir a playlist.";
      setToast(String(detail));
      setDeletePl(null);
      setSaveState("error");
    }
  }

  async function onPickerConfirm(assets: MediaItem[]) {
    if (!selectedId || assets.length === 0) return;
    setPickerBusy(true);
    const data = await withSave(() =>
      api
        .post<Playlist>(`/playlists/${selectedId}/items/bulk`, {
          asset_ids: assets.map((a) => a.id),
          store_id: storeId,
        })
        .then((r) => r.data),
    );
    setPickerBusy(false);
    if (!data) {
      setError("Não foi possível adicionar os conteúdos.");
      return;
    }
    applyPlaylist(data);
    setPickerOpen(false);
    setToast(
      assets.length > 1
        ? `${assets.length} conteúdos adicionados`
        : "Conteúdo adicionado",
    );
  }

  async function onDynamicConfirm(ids: string[]) {
    if (!selectedId || ids.length === 0) return;
    setPickerBusy(true);
    const data = await withSave(() =>
      api
        .post<Playlist>(`/playlists/${selectedId}/items/bulk`, {
          items: ids.map((id) => ({
            item_type: "DYNAMIC",
            dynamic_content_id: id,
          })),
          store_id: storeId,
        })
        .then((r) => r.data),
    );
    setPickerBusy(false);
    if (!data) {
      setError("Não foi possível adicionar a tabela dinâmica.");
      return;
    }
    applyPlaylist(data);
    setDynamicPickerOpen(false);
    setToast(ids.length > 1 ? `${ids.length} tabelas adicionadas` : "Tabela adicionada");
  }

  async function removeItem(itemId: string) {
    if (!selectedId) return;
    const prev = selected;
    setPlaylists((p) =>
      p.map((pl) =>
        pl.id === selectedId
          ? { ...pl, items: pl.items.filter((i) => i.id !== itemId) }
          : pl,
      ),
    );
    const data = await withSave(() =>
      api
        .delete<Playlist>(`/playlists/${selectedId}/items/${itemId}`, {
          params: { store_id: storeId },
        })
        .then((r) => r.data),
    );
    if (!data) {
      if (prev) applyPlaylist(prev);
      setError("Falha ao remover da playlist.");
      return;
    }
    applyPlaylist(data);
  }

  async function setDuration(itemId: string, seconds: number) {
    if (!selectedId) return;
    const prev = selected;
    const safe = Math.max(1, seconds);
    setPlaylists((p) =>
      p.map((pl) =>
        pl.id !== selectedId
          ? pl
          : {
              ...pl,
              items: pl.items.map((i) =>
                i.id === itemId ? { ...i, duration_seconds: safe } : i,
              ),
            },
      ),
    );
    const data = await withSave(() =>
      api
        .patch<Playlist>(`/playlists/${selectedId}/items/${itemId}`, {
          duration_seconds: safe,
          store_id: storeId,
        })
        .then((r) => r.data),
    );
    if (!data) {
      if (prev) applyPlaylist(prev);
      setError("Falha ao atualizar duração.");
      return;
    }
    applyPlaylist(data);
  }

  async function persistReorder(nextIds: string[], rollback: PlaylistItemRow[]) {
    if (!selected || reorderBusy) return;
    setReorderBusy(true);
    const optimistic = nextIds
      .map((id) => rollback.find((i) => i.id === id)!)
      .filter(Boolean)
      .map((item, idx) => ({ ...item, position: idx }));
    setPlaylists((prev) =>
      prev.map((p) => (p.id === selected.id ? { ...p, items: optimistic } : p)),
    );
    try {
      const { data } = await api.patch<Playlist>(`/playlists/${selected.id}/items/reorder`, {
        item_ids: nextIds,
        store_id: storeId,
      });
      applyPlaylist(data);
      setSaveState("saved");
    } catch {
      setPlaylists((prev) =>
        prev.map((p) => (p.id === selected.id ? { ...p, items: rollback } : p)),
      );
      setError("Falha ao reordenar. Ordem restaurada.");
      setSaveState("error");
    } finally {
      setReorderBusy(false);
    }
  }

  async function onDrop(targetId: string) {
    if (!selected || !dragId || dragId === targetId || reorderBusy) {
      setDragId(null);
      return;
    }
    const ids = selected.items.map((i) => i.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(targetId);
    setDragId(null);
    if (from < 0 || to < 0) return;
    const next = [...ids];
    next.splice(from, 1);
    next.splice(to, 0, dragId);
    await persistReorder(next, selected.items);
  }

  async function moveItem(itemId: string, dir: -1 | 1) {
    if (!selected || reorderBusy) return;
    const ids = selected.items.map((i) => i.id);
    const from = ids.indexOf(itemId);
    const to = from + dir;
    if (from < 0 || to < 0 || to >= ids.length) return;
    const next = [...ids];
    next.splice(from, 1);
    next.splice(to, 0, itemId);
    setMenuItemId(null);
    await persistReorder(next, selected.items);
  }

  const previewItem = selected?.items.length
    ? selected.items[previewIndex % selected.items.length]
    : null;
  const previewSlide = previewItem ? toPlayerSlide(previewItem) : null;

  const saveLabel =
    saveState === "saving"
      ? "Salvando..."
      : saveState === "saved"
        ? "Salvo"
        : saveState === "error"
          ? "Erro ao salvar"
          : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Playlists"
        description="Organize a sequência de conteúdos exibidos nas telas da loja."
        actions={
          <Button type="button" disabled={!storeId} onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden />
            Nova playlist
          </Button>
        }
      />

      {!storeId && !storeLoading && (
        <Alert variant="warning">Selecione uma loja na barra superior.</Alert>
      )}
      {toast && <Alert variant="success">{toast}</Alert>}
      {error && (
        <div className="space-y-2">
          <Alert variant="danger">{error}</Alert>
          <Button type="button" size="sm" variant="secondary" onClick={() => void load("refresh")}>
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

      {!loading && storeId && playlists.length === 0 && (
        <EmptyState
          icon={<ListVideo className="h-8 w-8" aria-hidden />}
          title="Nenhuma playlist criada"
          description="Crie uma playlist para organizar a sequência de conteúdos das telas."
          action={
            <Button type="button" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden />
              Criar playlist
            </Button>
          }
        />
      )}

      {!loading && playlists.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)]">
          {/* Playlist list */}
          <aside className="rounded-ds border border-brand-100 bg-surface p-3">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-brand-900">Minhas playlists</h2>
              {selectedStore && (
                <span className="text-xs text-ink/45">{playlists.length}</span>
              )}
            </div>
            {/* Mobile select */}
            <div className="mb-3 lg:hidden">
              <Select
                aria-label="Playlist"
                value={selectedId || ""}
                onChange={(e) => setSelectedId(e.target.value || null)}
              >
                {playlists.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <ul className="hidden max-h-[70vh] space-y-1 overflow-y-auto lg:block" role="listbox">
              {playlists.map((p) => {
                const dur =
                  typeof p.total_duration_seconds === "number"
                    ? p.total_duration_seconds
                    : p.items?.reduce((a, i) => a + effectiveItemDuration(i), 0) || 0;
                const count = p.item_count ?? p.items?.length ?? 0;
                const active = selectedId === p.id;
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={active}
                      onClick={() => setSelectedId(p.id)}
                      className={`w-full rounded-ds px-3 py-2.5 text-left transition ${
                        active
                          ? "bg-brand-50 ring-1 ring-brand-200"
                          : "hover:bg-brand-50/70"
                      }`}
                    >
                      <span className="block font-semibold text-brand-900">{p.name}</span>
                      <span className="mt-0.5 block text-xs text-ink/55">
                        {count} conteúdo{count === 1 ? "" : "s"} · {formatClockDuration(dur)}
                        {p.is_default ? " · padrão" : ""}
                        {(p.usage_count || 0) > 0 ? ` · em uso` : ""}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </aside>

          {/* Studio */}
          <section className="min-w-0 rounded-ds border border-brand-100 bg-surface p-4 sm:p-5">
            {!selected ? (
              <p className="text-sm text-ink/60">Selecione uma playlist.</p>
            ) : (
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-sans text-xl font-semibold text-brand-900">
                      {selected.name}
                    </h2>
                    <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink/65">
                      <span>
                        {selected.items.length} conteúdo
                        {selected.items.length === 1 ? "" : "s"}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" aria-hidden />
                        Duração total {formatClockDuration(totalDuration)}
                      </span>
                      {(selected.usage_count || 0) > 0 && (
                        <Badge tone="warning">
                          Em uso
                          {selected.usage
                            ? ` · ${selected.usage.channel_count + selected.usage.schedule_count + selected.usage.display_count}`
                            : ""}
                        </Badge>
                      )}
                      {saveLabel && (
                        <span
                          className={`text-xs ${
                            saveState === "error" ? "text-semantic-danger" : "text-ink/50"
                          }`}
                        >
                          {saveLabel}
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setRenameValue(selected.name);
                        setRenameOpen(true);
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" aria-hidden />
                      Renomear
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-semantic-danger"
                      onClick={() => setDeletePl(selected)}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      Excluir
                    </Button>
                    <Button type="button" size="sm" onClick={() => setAddChooserOpen(true)}>
                      <Plus className="h-3.5 w-3.5" aria-hidden />
                      Adicionar conteúdo
                    </Button>
                  </div>
                </div>

                {/* Preview + timeline */}
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-brand-900">Preview</h3>
                      <Select
                        aria-label="Proporção do preview"
                        value={aspect}
                        onChange={(e) => setAspect(e.target.value as "16:9" | "9:16")}
                        className="w-28"
                      >
                        <option value="16:9">16:9</option>
                        <option value="9:16">9:16</option>
                      </Select>
                    </div>
                    <div
                      className={`relative mx-auto w-full overflow-hidden rounded-ds bg-brand-950 ${
                        aspect === "16:9" ? "aspect-video max-w-xl" : "aspect-[9/16] max-w-[220px]"
                      }`}
                    >
                      <StudioPreview item={previewSlide} playing={previewPlaying} storeId={storeId} />
                    </div>
                    <div className="flex flex-wrap items-center justify-center gap-2">
                      <IconButton
                        label="Anterior"
                        icon={<SkipBack className="h-4 w-4" />}
                        disabled={!selected.items.length}
                        onClick={() => {
                          setPreviewIndex(
                            (i) =>
                              (i - 1 + selected.items.length) % selected.items.length,
                          );
                          setPreviewPlaying(false);
                        }}
                      />
                      <Button
                        type="button"
                        size="sm"
                        disabled={!selected.items.length}
                        onClick={() => setPreviewPlaying((p) => !p)}
                      >
                        {previewPlaying ? (
                          <>
                            <Pause className="h-4 w-4" aria-hidden /> Pausar
                          </>
                        ) : (
                          <>
                            <Play className="h-4 w-4" aria-hidden /> Play
                          </>
                        )}
                      </Button>
                      <IconButton
                        label="Próximo"
                        icon={<SkipForward className="h-4 w-4" />}
                        disabled={!selected.items.length}
                        onClick={() => {
                          setPreviewIndex((i) => (i + 1) % selected.items.length);
                          setPreviewPlaying(false);
                        }}
                      />
                    </div>
                    {previewItem && (
                      <p className="text-center text-xs text-ink/55">
                        {String(previewIndex + 1).padStart(2, "0")} ·{" "}
                        {(previewItem.item_type || "MEDIA").toUpperCase() === "DYNAMIC"
                          ? previewItem.dynamic_content?.name || "PRICE TABLE"
                          : previewItem.asset?.name || "Conteúdo"}{" "}
                        · {formatClockDuration(effectiveItemDuration(previewItem))}
                        {(previewItem.item_type || "").toUpperCase() === "DYNAMIC" &&
                        (previewItem.duration_source || "SOURCE").toUpperCase() === "SOURCE"
                          ? " automático"
                          : ""}
                      </p>
                    )}
                  </div>

                  <div className="min-w-0 space-y-3">
                    <h3 className="text-sm font-semibold text-brand-900">Sequência</h3>
                    {selected.items.length === 0 ? (
                      <EmptyState
                        title="Esta playlist ainda não possui conteúdos"
                        description="Adicione mídias ou tabelas dinâmicas CISS para montar a sequência."
                        action={
                          <Button type="button" onClick={() => setAddChooserOpen(true)}>
                            <Plus className="h-4 w-4" aria-hidden />
                            Adicionar conteúdo
                          </Button>
                        }
                      />
                    ) : (
                      <ul className="space-y-2">
                        {selected.items.map((item, idx) => {
                          const active = idx === previewIndex % selected.items.length;
                          const dur = effectiveItemDuration(item);
                          const isDynamic = (item.item_type || "MEDIA").toUpperCase() === "DYNAMIC";
                          const label = isDynamic
                            ? item.dynamic_content?.name || "PRICE TABLE"
                            : item.asset?.name || "Conteúdo";
                          const typeLabel = isDynamic
                            ? "PRICE TABLE"
                            : item.asset?.media_type || "MEDIA";
                          const autoDur =
                            isDynamic && (item.duration_source || "SOURCE").toUpperCase() === "SOURCE";
                          return (
                            <li
                              key={item.id}
                              draggable={!reorderBusy}
                              onDragStart={() => setDragId(item.id)}
                              onDragOver={(e) => e.preventDefault()}
                              onDrop={() => void onDrop(item.id)}
                              className={`flex items-center gap-2 rounded-ds border px-2 py-2 transition sm:gap-3 sm:px-3 ${
                                active
                                  ? "border-brand-500 bg-brand-50"
                                  : "border-brand-100 bg-surface-muted/40"
                              } ${dragId === item.id ? "opacity-50" : ""}`}
                            >
                              <button
                                type="button"
                                className="hidden cursor-grab touch-none text-ink/35 sm:block"
                                aria-label={`Reordenar ${label}`}
                                onClick={(e) => e.preventDefault()}
                              >
                                <GripVertical className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                className="flex min-w-0 flex-1 items-center gap-3 text-left"
                                onClick={() => {
                                  setPreviewIndex(idx);
                                  setPreviewPlaying(false);
                                }}
                              >
                                <span className="w-6 shrink-0 text-xs font-semibold tabular-nums text-ink/50">
                                  {active ? "▶" : String(idx + 1).padStart(2, "0")}
                                </span>
                                <div className="flex h-12 w-20 shrink-0 items-center justify-center overflow-hidden rounded-ds border border-brand-100 bg-brand-50">
                                  {isDynamic ? (
                                    <Table2 className="h-6 w-6 text-brand-700" aria-hidden />
                                  ) : (
                                    <MediaThumb
                                      mediaType={item.asset?.media_type || "IMAGE"}
                                      url={item.asset?.public_url}
                                      name={item.asset?.name}
                                    />
                                  )}
                                </div>
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-semibold text-brand-900">
                                    {label}
                                  </p>
                                  <p className="text-xs text-ink/55">
                                    {isDynamic ? (
                                      <>
                                        <Table2 className="mr-1 inline h-3 w-3 align-text-bottom" aria-hidden />
                                        {typeLabel}
                                        {item.dynamic_content?.page_count
                                          ? ` · ${item.dynamic_content.page_count} páginas`
                                          : ""}
                                        {" · "}
                                        {formatClockDuration(dur)}
                                        {autoDur ? " automático" : ""}
                                      </>
                                    ) : (
                                      <>
                                        {typeLabel} · {formatClockDuration(dur)}
                                      </>
                                    )}
                                  </p>
                                </div>
                              </button>

                              <div className="relative flex shrink-0 items-center gap-1">
                                {autoDur ? (
                                  <span
                                    className="rounded-ds px-2 py-1 text-xs font-medium text-ink/55"
                                    title="Duração automática do conteúdo"
                                  >
                                    {formatClockDuration(dur)}
                                  </span>
                                ) : durationEditId === item.id ? (
                                  <Input
                                    aria-label="Duração em segundos"
                                    type="number"
                                    min={1}
                                    className="w-20"
                                    defaultValue={dur}
                                    autoFocus
                                    onBlur={(e) => {
                                      const v = Number(e.target.value) || 1;
                                      setDurationEditId(null);
                                      if (v !== dur) void setDuration(item.id, v);
                                    }}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter") {
                                        (e.target as HTMLInputElement).blur();
                                      }
                                    }}
                                  />
                                ) : (
                                  <button
                                    type="button"
                                    className="rounded-ds px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50"
                                    onClick={() => setDurationEditId(item.id)}
                                  >
                                    {formatClockDuration(dur)}
                                  </button>
                                )}
                                <IconButton
                                  label={`Ações de ${label}`}
                                  icon={<MoreVertical className="h-4 w-4" />}
                                  onClick={() =>
                                    setMenuItemId((id) => (id === item.id ? null : item.id))
                                  }
                                />
                                {menuItemId === item.id && (
                                  <div
                                    role="menu"
                                    className="absolute right-0 top-9 z-20 w-48 rounded-ds border border-brand-100 bg-surface py-1 shadow-ds-md"
                                  >
                                    <button
                                      type="button"
                                      role="menuitem"
                                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-brand-50"
                                      disabled={idx === 0 || reorderBusy}
                                      onClick={() => void moveItem(item.id, -1)}
                                    >
                                      <ChevronUp className="h-3.5 w-3.5" aria-hidden />
                                      Mover para cima
                                    </button>
                                    <button
                                      type="button"
                                      role="menuitem"
                                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-brand-50"
                                      disabled={idx === selected.items.length - 1 || reorderBusy}
                                      onClick={() => void moveItem(item.id, 1)}
                                    >
                                      <ChevronDown className="h-3.5 w-3.5" aria-hidden />
                                      Mover para baixo
                                    </button>
                                    {!autoDur && (
                                      <button
                                        type="button"
                                        role="menuitem"
                                        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-brand-50"
                                        onClick={() => {
                                          setMenuItemId(null);
                                          setDurationEditId(item.id);
                                        }}
                                      >
                                        <Clock className="h-3.5 w-3.5" aria-hidden />
                                        Editar duração
                                      </button>
                                    )}
                                    <button
                                      type="button"
                                      role="menuitem"
                                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-semantic-danger hover:bg-semantic-danger-bg"
                                      onClick={() => {
                                        setMenuItemId(null);
                                        void removeItem(item.id);
                                      }}
                                    >
                                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                                      Remover da playlist
                                    </button>
                                  </div>
                                )}
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Nova playlist"
        footer={
          <>
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="pl-create-form">
              Criar
            </Button>
          </>
        }
      >
        <form id="pl-create-form" className="space-y-3" onSubmit={(e) => void createPlaylist(e)}>
          <Input
            label="Nome"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            required
            autoFocus
            placeholder="Ex.: Churrasco fim de semana"
          />
        </form>
      </Modal>

      <Modal
        open={renameOpen}
        onClose={() => setRenameOpen(false)}
        title="Renomear playlist"
        footer={
          <>
            <Button type="button" variant="ghost" onClick={() => setRenameOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="pl-rename-form">
              Salvar
            </Button>
          </>
        }
      >
        <form id="pl-rename-form" onSubmit={(e) => void renamePlaylist(e)}>
          <Input
            label="Nome"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            required
            autoFocus
          />
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deletePl}
        onClose={() => setDeletePl(null)}
        onConfirm={() => void confirmDeletePlaylist()}
        title={
          deletePl && (deletePl.usage_count || 0) > 0
            ? "Não é possível excluir"
            : "Excluir playlist?"
        }
        description={
          deletePl && (deletePl.usage_count || 0) > 0 ? (
            <p>
              Esta playlist está em uso
              {deletePl.usage
                ? ` (${[
                    deletePl.usage.channel_count && `${deletePl.usage.channel_count} canal(is)`,
                    deletePl.usage.schedule_count &&
                      `${deletePl.usage.schedule_count} programação(ões)`,
                    deletePl.usage.display_count && `${deletePl.usage.display_count} display(s)`,
                  ]
                    .filter(Boolean)
                    .join(", ")})`
                : ""}
              . Remova a associação antes de excluir.
            </p>
          ) : (
            <p>A sequência deixará de estar disponível. Conteúdos da biblioteca não serão excluídos.</p>
          )
        }
        confirmLabel={
          deletePl && (deletePl.usage_count || 0) > 0 ? "Entendi" : "Excluir"
        }
        danger={!(deletePl && (deletePl.usage_count || 0) > 0)}
      />

      <Modal
        open={addChooserOpen}
        onClose={() => setAddChooserOpen(false)}
        title="Adicionar conteúdo"
        footer={
          <Button type="button" variant="ghost" onClick={() => setAddChooserOpen(false)}>
            Fechar
          </Button>
        }
      >
        <p className="mb-3 text-sm text-ink/65">Escolha mídia da biblioteca ou tabela dinâmica CISS.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            className="flex flex-col items-start gap-2 rounded-ds border border-brand-100 p-4 text-left hover:bg-brand-50"
            onClick={() => {
              setAddChooserOpen(false);
              setPickerOpen(true);
            }}
          >
            <ImageIcon className="h-6 w-6 text-brand-700" aria-hidden />
            <span className="font-semibold text-brand-900">Mídia</span>
            <span className="text-xs text-ink/55">Imagem, vídeo ou Web</span>
          </button>
          <button
            type="button"
            className="flex flex-col items-start gap-2 rounded-ds border border-brand-100 p-4 text-left hover:bg-brand-50"
            onClick={() => {
              setAddChooserOpen(false);
              setDynamicPickerOpen(true);
            }}
          >
            <Table2 className="h-6 w-6 text-brand-700" aria-hidden />
            <span className="font-semibold text-brand-900">Dinâmico</span>
            <span className="text-xs text-ink/55">Tabela de preços CISS</span>
          </button>
        </div>
      </Modal>

      <MediaPicker
        open={pickerOpen}
        onClose={() => !pickerBusy && setPickerOpen(false)}
        storeId={storeId}
        busy={pickerBusy}
        onConfirm={onPickerConfirm}
      />

      <DynamicPicker
        open={dynamicPickerOpen}
        onClose={() => !pickerBusy && setDynamicPickerOpen(false)}
        storeId={storeId}
        busy={pickerBusy}
        onConfirm={onDynamicConfirm}
      />
    </div>
  );
}
