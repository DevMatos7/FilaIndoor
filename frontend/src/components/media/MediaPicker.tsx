import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import {
  Alert,
  Button,
  Drawer,
  EmptyState,
  Input,
  MediaCard,
  MediaCardSkeleton,
  Select,
} from "../../design-system";
import api from "../../services/api";
import type { MediaItem } from "../../pages/Media";

type FilterType = "ALL" | "IMAGE" | "VIDEO" | "WEB";

export type MediaPickerProps = {
  open: boolean;
  onClose: () => void;
  storeId: string;
  onConfirm: (assets: MediaItem[]) => void | Promise<void>;
  busy?: boolean;
  /** Initial / locked media type filter (e.g. IMAGE for product packshots). */
  defaultFilter?: FilterType;
  lockFilter?: boolean;
  /** When true, selecting a new asset replaces previous selection. */
  singleSelect?: boolean;
};

/**
 * Media Library picker for Playlist Studio / Product Media.
 * Multi-select: order = order of selection (unless singleSelect).
 */
export function MediaPicker({
  open,
  onClose,
  storeId,
  onConfirm,
  busy,
  defaultFilter = "ALL",
  lockFilter = false,
  singleSelect = false,
}: MediaPickerProps) {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterType>(defaultFilter);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  useEffect(() => {
    if (!open || !storeId) return;
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    setSelectedIds([]);
    setQuery("");
    setFilter(defaultFilter);
    void (async () => {
      try {
        const { data } = await api.get<MediaItem[]>("/media", {
          params: { store_id: storeId },
          signal: ac.signal,
        });
        setItems(data);
      } catch (err: unknown) {
        const code = (err as { code?: string })?.code;
        if (code === "ERR_CANCELED") return;
        setError("Não foi possível carregar a biblioteca.");
      } finally {
        setLoading(false);
      }
    })();
    return () => ac.abort();
  }, [open, storeId, defaultFilter]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((m) => {
      if (filter !== "ALL" && m.media_type !== filter) return false;
      if (!q) return true;
      return (
        m.name.toLowerCase().includes(q) ||
        (m.original_filename || "").toLowerCase().includes(q) ||
        (m.public_url || "").toLowerCase().includes(q)
      );
    });
  }, [items, query, filter]);

  function toggle(id: string) {
    setSelectedIds((prev) => {
      if (singleSelect) return prev.includes(id) ? [] : [id];
      return prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
    });
  }

  async function confirm() {
    const byId = new Map(items.map((i) => [i.id, i]));
    const ordered = selectedIds.map((id) => byId.get(id)).filter(Boolean) as MediaItem[];
    await onConfirm(ordered);
  }

  return (
    <Drawer
      open={open}
      onClose={() => !busy && onClose()}
      title="Adicionar conteúdo"
      className="max-w-3xl"
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-ink/60">
            {selectedIds.length === 0
              ? "Selecione um ou mais conteúdos"
              : `${selectedIds.length} selecionado${selectedIds.length === 1 ? "" : "s"}`}
          </p>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={busy || selectedIds.length === 0}
              loading={busy}
              onClick={() => void confirm()}
            >
              {singleSelect
                ? "Associar imagem"
                : selectedIds.length > 1
                  ? `Adicionar ${selectedIds.length} conteúdos`
                  : "Adicionar conteúdo"}
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="flex-1">
            <Input
              aria-label="Buscar na biblioteca"
              placeholder="Buscar conteúdos..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              leading={<Search className="h-4 w-4" aria-hidden />}
            />
          </div>
          <Select
            aria-label="Filtrar tipo"
            value={filter}
            onChange={(e) => setFilter(e.target.value as FilterType)}
            className="sm:w-40"
            disabled={lockFilter}
          >
            <option value="ALL">Todos</option>
            <option value="IMAGE">Imagens</option>
            <option value="VIDEO">Vídeos</option>
            <option value="WEB">Web</option>
          </Select>
        </div>

        {error && <Alert variant="danger">{error}</Alert>}

        {loading && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <MediaCardSkeleton key={i} />
            ))}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <EmptyState
            title={items.length === 0 ? "Biblioteca vazia" : "Nenhum conteúdo encontrado"}
            description={
              items.length === 0
                ? "Adicione conteúdos em Conteúdos antes de montar a playlist."
                : "Tente alterar a busca ou o filtro."
            }
          />
        )}

        {!loading && filtered.length > 0 && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3" role="listbox" aria-multiselectable>
            {filtered.map((item) => {
              const sel = selectedIds.includes(item.id);
              return (
                <MediaCard
                  key={item.id}
                  name={item.name}
                  mediaType={item.media_type}
                  previewUrl={item.public_url}
                  durationSeconds={item.duration_seconds}
                  width={item.width}
                  height={item.height}
                  selected={sel}
                  onOpen={() => toggle(item.id)}
                />
              );
            })}
          </div>
        )}
      </div>
    </Drawer>
  );
}
