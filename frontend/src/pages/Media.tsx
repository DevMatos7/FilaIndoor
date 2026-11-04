import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ExternalLink,
  Globe,
  Image as ImageIcon,
  MoreVertical,
  Pencil,
  Plus,
  Search,
  Trash2,
  Upload,
  Video,
} from "lucide-react";
import {
  Alert,
  Badge,
  Button,
  ConfirmDialog,
  Drawer,
  EmptyState,
  IconButton,
  Input,
  MediaCard,
  MediaCardSkeleton,
  PageHeader,
  Select,
} from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import api from "../services/api";

export type MediaItem = {
  id: string;
  store_id: string;
  name: string;
  media_type: string;
  mime_type: string | null;
  original_filename?: string | null;
  public_url: string;
  size_bytes: number | null;
  duration_seconds: number | null;
  width?: number | null;
  height?: number | null;
  checksum?: string | null;
  notes: string | null;
  usage_count?: number;
  created_at: string | null;
  updated_at?: string | null;
};

type ContentKind = "IMAGE" | "VIDEO" | "WEB";
type FilterType = "ALL" | ContentKind;
type SortKey = "newest" | "oldest" | "name";

type Limits = {
  image_max_mb: number;
  video_max_mb: number;
};

function fmtBytes(n: number | null | undefined) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtDate(iso: string | null | undefined) {
  if (!iso) return null;
  try {
    return new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").toLocaleDateString(
      "pt-BR",
    );
  } catch {
    return null;
  }
}

function fmtDuration(sec?: number | null) {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function hostOf(url: string) {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export default function Media() {
  const { selectedStoreId, selectedStore, loading: storeLoading } = useStoreContext();
  const storeId = selectedStoreId || "";

  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [staleWarning, setStaleWarning] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterType>("ALL");
  const [sort, setSort] = useState<SortKey>("newest");

  const [createOpen, setCreateOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selected, setSelected] = useState<MediaItem | null>(null);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDuration, setEditDuration] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [techOpen, setTechOpen] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<MediaItem | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [menuId, setMenuId] = useState<string | null>(null);

  const [kind, setKind] = useState<ContentKind>("IMAGE");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [webUrl, setWebUrl] = useState("");
  const [duration, setDuration] = useState("10");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [limits, setLimits] = useState<Limits>({ image_max_mb: 10, video_max_mb: 100 });
  const [dragOver, setDragOver] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const storeRef = useRef(storeId);
  const itemsRef = useRef(items);
  const createTriggerRef = useRef<HTMLButtonElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    void api
      .get<Limits>("/media/limits")
      .then((r) => setLimits(r.data))
      .catch(() => undefined);
  }, []);

  const load = useCallback(async (reason: "store" | "refresh" = "refresh") => {
    const sid = storeRef.current;
    if (!sid) {
      setItems([]);
      setLoading(false);
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    if (reason === "store") {
      setItems([]);
      setSelected(null);
      setDetailsOpen(false);
      setMenuId(null);
      setError(null);
      setStaleWarning(null);
      setLoading(true);
    } else if (!itemsRef.current.length) {
      setLoading(true);
    }

    try {
      const { data } = await api.get<MediaItem[]>("/media", {
        params: { store_id: sid },
        signal: ac.signal,
      });
      if (storeRef.current !== sid) return;
      setItems(data);
      setError(null);
      setStaleWarning(null);
    } catch (err: unknown) {
      const name = (err as { name?: string; code?: string })?.name;
      const code = (err as { code?: string })?.code;
      if (name === "CanceledError" || code === "ERR_CANCELED") return;
      if (storeRef.current !== sid) return;
      if (itemsRef.current.length) {
        setStaleWarning("Não foi possível atualizar. Exibindo última lista.");
      } else {
        setError("Não foi possível carregar os conteúdos.");
      }
    } finally {
      if (storeRef.current === sid) setLoading(false);
    }
  }, []);

  useEffect(() => {
    storeRef.current = storeId;
    if (!storeId || storeLoading) {
      setItems([]);
      setLoading(!!storeLoading);
      return;
    }
    void load("store");
    return () => abortRef.current?.abort();
  }, [storeId, storeLoading, load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = items.filter((m) => {
      if (filter !== "ALL" && m.media_type !== filter) return false;
      if (!q) return true;
      return (
        m.name.toLowerCase().includes(q) ||
        (m.original_filename || "").toLowerCase().includes(q) ||
        (m.public_url || "").toLowerCase().includes(q)
      );
    });
    list = [...list].sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name, "pt-BR");
      const da = a.created_at ? Date.parse(a.created_at) : 0;
      const db = b.created_at ? Date.parse(b.created_at) : 0;
      return sort === "oldest" ? da - db : db - da;
    });
    return list;
  }, [items, query, filter, sort]);

  function openCreate() {
    setKind("IMAGE");
    setName("");
    setFile(null);
    setWebUrl("");
    setDuration("10");
    setFormError(null);
    setUploadProgress(null);
    setCreateOpen(true);
  }

  function openDetails(item: MediaItem) {
    setSelected(item);
    setEditing(false);
    setEditName(item.name);
    setEditDuration(String(item.duration_seconds ?? ""));
    setEditNotes(item.notes || "");
    setTechOpen(false);
    setMenuId(null);
    setDetailsOpen(true);
  }

  function acceptFile(f: File | null) {
    if (!f) return;
    setFile(f);
    if (!name.trim()) {
      const base = f.name.replace(/\.[^.]+$/, "");
      setName(base);
    }
    if (f.type.startsWith("video/")) setKind("VIDEO");
    else if (f.type.startsWith("image/")) setKind("IMAGE");
  }

  async function submitCreate(e: FormEvent) {
    e.preventDefault();
    if (!storeId || uploadBusy) return;
    setFormError(null);

    if (!name.trim()) {
      setFormError("Informe um nome para o conteúdo.");
      return;
    }

    if (kind === "WEB") {
      const url = webUrl.trim();
      if (!url.startsWith("http://") && !url.startsWith("https://")) {
        setFormError("Informe uma URL válida (http:// ou https://).");
        return;
      }
      setUploadBusy(true);
      try {
        const { data } = await api.post<MediaItem>("/media/web", {
          store_id: storeId,
          name: name.trim(),
          url,
          duration_seconds: Number(duration) || 15,
        });
        setCreateOpen(false);
        setToast("Conteúdo adicionado");
        setHighlightId(data.id);
        window.setTimeout(() => setHighlightId(null), 4000);
        await load("refresh");
      } catch {
        setFormError("Não foi possível adicionar o conteúdo. Tente novamente.");
      } finally {
        setUploadBusy(false);
      }
      return;
    }

    if (!file) {
      setFormError("Selecione um arquivo.");
      return;
    }
    const maxMb = kind === "IMAGE" ? limits.image_max_mb : limits.video_max_mb;
    if (file.size > maxMb * 1024 * 1024) {
      setFormError(`Arquivo excede o limite de ${maxMb} MB.`);
      return;
    }
    if (kind === "IMAGE" && !file.type.startsWith("image/")) {
      setFormError("Tipo incompatível. Selecione uma imagem.");
      return;
    }
    if (kind === "VIDEO" && !file.type.startsWith("video/")) {
      setFormError("Tipo incompatível. Selecione um vídeo.");
      return;
    }

    setUploadBusy(true);
    setUploadProgress(0);
    try {
      const form = new FormData();
      form.append("store_id", storeId);
      form.append("name", name.trim());
      form.append("file", file);
      if (duration) form.append("duration_seconds", duration);
      const { data } = await api.post<MediaItem>("/media", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (ev) => {
          if (ev.total) setUploadProgress(Math.round((ev.loaded / ev.total) * 100));
        },
      });
      setCreateOpen(false);
      setToast("Conteúdo adicionado");
      setHighlightId(data.id);
      window.setTimeout(() => setHighlightId(null), 4000);
      await load("refresh");
    } catch {
      setFormError("Não foi possível adicionar o conteúdo. Tente novamente.");
    } finally {
      setUploadBusy(false);
      setUploadProgress(null);
    }
  }

  async function saveEdit() {
    if (!selected || !storeId) return;
    setUploadBusy(true);
    setFormError(null);
    try {
      const { data } = await api.patch<MediaItem>(`/media/${selected.id}`, {
        store_id: storeId,
        name: editName.trim(),
        notes: editNotes,
        duration_seconds: editDuration ? Number(editDuration) : undefined,
      });
      setSelected(data);
      setEditing(false);
      setToast("Informações atualizadas");
      await load("refresh");
    } catch {
      setFormError("Não foi possível salvar as alterações.");
    } finally {
      setUploadBusy(false);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget || !storeId) return;
    setDeleteBusy(true);
    try {
      await api.delete(`/media/${deleteTarget.id}`, { params: { store_id: storeId } });
      setToast("Conteúdo excluído");
      if (selected?.id === deleteTarget.id) {
        setDetailsOpen(false);
        setSelected(null);
      }
      setDeleteTarget(null);
      await load("refresh");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Não foi possível excluir o conteúdo.";
      setToast(String(detail));
      setDeleteTarget(null);
    } finally {
      setDeleteBusy(false);
    }
  }

  const showEmptyLibrary = !loading && !error && items.length === 0;
  const showEmptyFilter =
    !loading && !error && items.length > 0 && filtered.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Conteúdos"
        description="Gerencie imagens, vídeos e conteúdos exibidos nas telas da loja."
        actions={
          <Button
            ref={createTriggerRef}
            type="button"
            onClick={openCreate}
            disabled={!storeId}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Novo conteúdo
          </Button>
        }
      />

      {!storeId && !storeLoading && (
        <Alert variant="warning">Selecione uma loja na barra superior para ver os conteúdos.</Alert>
      )}
      {toast && <Alert variant="success">{toast}</Alert>}
      {staleWarning && <Alert variant="warning">{staleWarning}</Alert>}
      {error && (
        <div className="space-y-2">
          <Alert variant="danger">{error}</Alert>
          <Button type="button" size="sm" variant="secondary" onClick={() => void load("refresh")}>
            Tentar novamente
          </Button>
        </div>
      )}

      {storeId && (
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="min-w-[200px] flex-1">
            <Input
              aria-label="Buscar conteúdos"
              placeholder="Buscar conteúdos..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              leading={<Search className="h-4 w-4" aria-hidden />}
            />
          </div>
          <Select
            aria-label="Filtrar por tipo"
            value={filter}
            onChange={(e) => setFilter(e.target.value as FilterType)}
            className="sm:w-40"
          >
            <option value="ALL">Todos</option>
            <option value="IMAGE">Imagens</option>
            <option value="VIDEO">Vídeos</option>
            <option value="WEB">Web</option>
          </Select>
          <Select
            aria-label="Ordenar"
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="sm:w-44"
          >
            <option value="newest">Mais recentes</option>
            <option value="oldest">Mais antigos</option>
            <option value="name">Nome A–Z</option>
          </Select>
          <p className="text-sm text-ink/55 sm:ml-auto">
            {query || filter !== "ALL"
              ? `${filtered.length} de ${items.length}`
              : `${items.length} conteúdo${items.length === 1 ? "" : "s"}`}
            {selectedStore ? ` · ${selectedStore.name}` : ""}
          </p>
        </div>
      )}

      {loading && (
        <div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
          aria-busy
          aria-label="Carregando conteúdos"
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <MediaCardSkeleton key={i} />
          ))}
        </div>
      )}

      {showEmptyLibrary && (
        <EmptyState
          icon={<Upload className="h-8 w-8" aria-hidden />}
          title="Sua biblioteca ainda está vazia"
          description="Adicione imagens, vídeos ou páginas Web para começar a programar suas telas."
          action={
            <Button type="button" onClick={openCreate}>
              <Plus className="h-4 w-4" aria-hidden />
              Adicionar conteúdo
            </Button>
          }
        />
      )}

      {showEmptyFilter && (
        <EmptyState
          title="Nenhum conteúdo encontrado"
          description="Tente alterar a busca ou os filtros."
        />
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {filtered.map((item) => (
            <div key={item.id} className="relative">
              <MediaCard
                name={item.name}
                mediaType={item.media_type}
                previewUrl={item.public_url}
                durationSeconds={item.duration_seconds}
                width={item.width}
                height={item.height}
                createdAtLabel={fmtDate(item.created_at)}
                highlighted={highlightId === item.id}
                onOpen={() => openDetails(item)}
                menu={
                  <div className="relative">
                    <IconButton
                      label={`Ações de ${item.name}`}
                      icon={<MoreVertical className="h-4 w-4" />}
                      variant="secondary"
                      className="bg-surface/95 shadow-ds"
                      onClick={() => setMenuId((id) => (id === item.id ? null : item.id))}
                    />
                    {menuId === item.id && (
                      <div
                        role="menu"
                        className="absolute right-0 z-20 mt-1 w-44 rounded-ds border border-brand-100 bg-surface py-1 shadow-ds-md"
                      >
                        <button
                          type="button"
                          role="menuitem"
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-brand-50"
                          onClick={() => openDetails(item)}
                        >
                          Visualizar
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-brand-50"
                          onClick={() => {
                            openDetails(item);
                            setEditing(true);
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5" aria-hidden />
                          Editar informações
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-semantic-danger hover:bg-semantic-danger-bg"
                          onClick={() => {
                            setMenuId(null);
                            setDeleteTarget(item);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" aria-hidden />
                          Excluir
                        </button>
                      </div>
                    )}
                  </div>
                }
              />
            </div>
          ))}
        </div>
      )}

      {/* Create drawer */}
      <Drawer
        open={createOpen}
        onClose={() => !uploadBusy && setCreateOpen(false)}
        title="Novo conteúdo"
        className="max-w-lg"
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              type="button"
              disabled={uploadBusy}
              onClick={() => setCreateOpen(false)}
            >
              Cancelar
            </Button>
            <Button type="submit" form="media-create-form" loading={uploadBusy} disabled={uploadBusy}>
              Salvar
            </Button>
          </div>
        }
      >
        <form id="media-create-form" className="space-y-4" onSubmit={(e) => void submitCreate(e)}>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">O que deseja adicionar?</legend>
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  { id: "IMAGE", label: "Imagem", icon: ImageIcon },
                  { id: "VIDEO", label: "Vídeo", icon: Video },
                  { id: "WEB", label: "Página Web", icon: Globe },
                ] as const
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  disabled={uploadBusy}
                  onClick={() => {
                    setKind(opt.id);
                    setFile(null);
                    setFormError(null);
                  }}
                  className={`flex flex-col items-center gap-1 rounded-ds border px-2 py-3 text-xs font-semibold transition ${
                    kind === opt.id
                      ? "border-brand-600 bg-brand-50 text-brand-800"
                      : "border-brand-100 text-ink/70 hover:bg-brand-50"
                  }`}
                >
                  <opt.icon className="h-5 w-5" aria-hidden />
                  {opt.label}
                </button>
              ))}
            </div>
          </fieldset>

          {(kind === "IMAGE" || kind === "VIDEO") && (
            <div
              className={`rounded-ds border border-dashed px-4 py-8 text-center transition ${
                dragOver ? "border-brand-600 bg-brand-50" : "border-brand-200 bg-surface-muted"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                acceptFile(e.dataTransfer.files?.[0] || null);
              }}
            >
              <Upload className="mx-auto h-8 w-8 text-brand-500" aria-hidden />
              <p className="mt-2 text-sm font-medium text-brand-900">Arraste um arquivo aqui</p>
              <p className="mt-1 text-xs text-ink/55">
                ou{" "}
                <button
                  type="button"
                  className="font-semibold text-brand-700 underline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  selecionar arquivo
                </button>
              </p>
              <p className="mt-2 text-xs text-ink/45">
                {kind === "IMAGE"
                  ? `Imagens até ${limits.image_max_mb} MB`
                  : `Vídeos até ${limits.video_max_mb} MB`}
              </p>
              <input
                ref={fileInputRef}
                type="file"
                className="sr-only"
                accept={kind === "IMAGE" ? "image/*" : "video/*"}
                onChange={(e) => acceptFile(e.target.files?.[0] || null)}
              />
              {file && (
                <p className="mt-3 text-sm text-ink">
                  <Badge tone="brand">{file.name}</Badge> · {fmtBytes(file.size)}
                </p>
              )}
            </div>
          )}

          {kind === "WEB" && (
            <Input
              label="URL"
              value={webUrl}
              onChange={(e) => setWebUrl(e.target.value)}
              placeholder="https://…"
              required
              disabled={uploadBusy}
            />
          )}

          <Input
            label="Nome"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            disabled={uploadBusy}
          />
          <Input
            label="Duração na TV (s)"
            type="number"
            min={1}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            disabled={uploadBusy}
          />

          {uploadProgress != null && (
            <p className="text-sm text-ink/70" aria-live="polite">
              Enviando {uploadProgress}%
            </p>
          )}
          {uploadBusy && uploadProgress == null && kind === "WEB" && (
            <p className="text-sm text-ink/70">Enviando conteúdo...</p>
          )}
          {formError && <Alert variant="danger">{formError}</Alert>}
        </form>
      </Drawer>

      {/* Details drawer */}
      <Drawer
        open={detailsOpen && !!selected}
        onClose={() => setDetailsOpen(false)}
        title={selected?.name || "Conteúdo"}
        className="max-w-lg"
        footer={
          selected ? (
            <div className="flex flex-wrap justify-between gap-2">
              <Button
                type="button"
                variant="ghost"
                className="text-semantic-danger"
                onClick={() => setDeleteTarget(selected)}
              >
                <Trash2 className="h-4 w-4" aria-hidden />
                Excluir
              </Button>
              <div className="flex gap-2">
                {!editing ? (
                  <Button type="button" variant="secondary" onClick={() => setEditing(true)}>
                    <Pencil className="h-4 w-4" aria-hidden />
                    Editar
                  </Button>
                ) : (
                  <>
                    <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
                      Cancelar
                    </Button>
                    <Button type="button" loading={uploadBusy} onClick={() => void saveEdit()}>
                      Salvar
                    </Button>
                  </>
                )}
              </div>
            </div>
          ) : undefined
        }
      >
        {selected && (
          <div className="space-y-4">
            <div className="overflow-hidden rounded-ds bg-ink/5">
              {selected.media_type === "IMAGE" && (
                <img
                  src={selected.public_url}
                  alt={selected.name}
                  className="max-h-[40vh] w-full object-contain"
                />
              )}
              {selected.media_type === "VIDEO" && (
                <video
                  src={selected.public_url}
                  controls
                  className="max-h-[40vh] w-full bg-black"
                />
              )}
              {selected.media_type === "WEB" && (
                <div className="space-y-2 p-2">
                  <iframe
                    title={selected.name}
                    src={selected.public_url}
                    sandbox="allow-scripts allow-same-origin allow-forms"
                    className="h-48 w-full rounded-ds border border-brand-100 bg-white"
                    referrerPolicy="no-referrer"
                  />
                  <a
                    href={selected.public_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 underline"
                  >
                    Abrir em nova aba
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                  </a>
                </div>
              )}
            </div>

            {!editing ? (
              <div className="space-y-2">
                <p className="font-sans text-lg font-semibold text-brand-900">{selected.name}</p>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="brand">{selected.media_type}</Badge>
                  {typeof selected.usage_count === "number" && selected.usage_count > 0 && (
                    <Badge tone="warning">Em {selected.usage_count} playlist(s)</Badge>
                  )}
                </div>
                <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                  <dt className="text-ink/55">Duração</dt>
                  <dd>{fmtDuration(selected.duration_seconds)}</dd>
                  {selected.width && selected.height && (
                    <>
                      <dt className="text-ink/55">Dimensões</dt>
                      <dd>
                        {selected.width} × {selected.height}
                      </dd>
                    </>
                  )}
                  <dt className="text-ink/55">Criado</dt>
                  <dd>{fmtDate(selected.created_at) || "—"}</dd>
                  {selected.media_type === "WEB" && (
                    <>
                      <dt className="text-ink/55">Domínio</dt>
                      <dd className="break-all">{hostOf(selected.public_url)}</dd>
                    </>
                  )}
                  {selected.notes && (
                    <>
                      <dt className="text-ink/55">Notas</dt>
                      <dd>{selected.notes}</dd>
                    </>
                  )}
                </dl>
              </div>
            ) : (
              <div className="space-y-3">
                <Input label="Nome" value={editName} onChange={(e) => setEditName(e.target.value)} />
                <Input
                  label="Duração (s)"
                  type="number"
                  min={1}
                  value={editDuration}
                  onChange={(e) => setEditDuration(e.target.value)}
                />
                <Input
                  label="Notas"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                />
                {formError && <Alert variant="danger">{formError}</Alert>}
              </div>
            )}

            <details
              open={techOpen}
              onToggle={(e) => setTechOpen((e.target as HTMLDetailsElement).open)}
              className="rounded-ds border border-brand-100"
            >
              <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-brand-800">
                Detalhes técnicos
              </summary>
              <dl className="space-y-1 border-t border-brand-50 px-3 py-2 text-xs text-ink/70">
                <div className="flex justify-between gap-2">
                  <dt>ID</dt>
                  <dd className="break-all font-mono">{selected.id}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>MIME</dt>
                  <dd>{selected.mime_type || "—"}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Arquivo</dt>
                  <dd className="break-all">{selected.original_filename || "—"}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Tamanho</dt>
                  <dd>{fmtBytes(selected.size_bytes)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Checksum</dt>
                  <dd className="break-all font-mono">{selected.checksum || "—"}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>URL</dt>
                  <dd className="break-all">{selected.public_url}</dd>
                </div>
              </dl>
            </details>
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => !deleteBusy && setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget && (deleteTarget.usage_count || 0) > 0) {
            setDeleteTarget(null);
            return;
          }
          void confirmDelete();
        }}
        title={
          deleteTarget && (deleteTarget.usage_count || 0) > 0
            ? "Não é possível excluir"
            : "Excluir conteúdo?"
        }
        description={
          deleteTarget && (deleteTarget.usage_count || 0) > 0 ? (
            <p>
              Este conteúdo está sendo utilizado em uma ou mais playlists. Remova-o das playlists
              antes de excluir.
            </p>
          ) : (
            <p>Este conteúdo deixará de ficar disponível para uso.</p>
          )
        }
        confirmLabel={
          deleteTarget && (deleteTarget.usage_count || 0) > 0 ? "Entendi" : "Excluir"
        }
        danger={!(deleteTarget && (deleteTarget.usage_count || 0) > 0)}
        loading={deleteBusy}
      />
    </div>
  );
}
