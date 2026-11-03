import { FormEvent, useCallback, useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { Alert, Button, Card, CardContent, Input, PageHeader } from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import api from "../services/api";

type MediaItem = {
  id: string;
  store_id: string;
  name: string;
  media_type: string;
  mime_type: string | null;
  public_url: string;
  size_bytes: number | null;
  duration_seconds: number | null;
  notes: string | null;
  created_at: string | null;
};

function fmtBytes(n: number | null) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Media() {
  const { selectedStoreId, selectedStore } = useStoreContext();
  const storeId = selectedStoreId || "";
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState("10");
  const [webUrl, setWebUrl] = useState("");
  const [preview, setPreview] = useState<MediaItem | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!storeId) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<MediaItem[]>("/media", {
        params: { store_id: storeId },
      });
      setItems(data);
    } catch {
      setError("Falha ao listar mídias.");
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !file || !name.trim()) {
      setError("Selecione a loja na barra superior e informe nome e arquivo.");
      return;
    }
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const form = new FormData();
      form.append("store_id", storeId);
      form.append("name", name.trim());
      form.append("file", file);
      if (duration) form.append("duration_seconds", duration);
      await api.post("/media", form, { headers: { "Content-Type": "multipart/form-data" } });
      setMessage(`Mídia “${name}” enviada.`);
      setName("");
      setFile(null);
      await load();
    } catch {
      setError("Upload rejeitado (tipo/tamanho/nome duplicado).");
    } finally {
      setBusy(false);
    }
  }

  async function onWeb(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !name.trim() || !webUrl.trim()) {
      setError("Selecione a loja na barra superior e informe nome e URL.");
      return;
    }
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await api.post("/media/web", {
        store_id: storeId,
        name: name.trim(),
        url: webUrl.trim(),
        duration_seconds: Number(duration) || 15,
      });
      setMessage(`WEB “${name}” cadastrado.`);
      setName("");
      setWebUrl("");
      await load();
    } catch {
      setError("Não foi possível cadastrar URL WEB.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    try {
      await api.delete(`/media/${id}`);
      setMessage("Mídia removida.");
      if (preview?.id === id) setPreview(null);
      await load();
    } catch {
      setError("Falha ao remover.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Conteúdos"
        description="Upload, preview e metadados (IMAGE / VIDEO / WEB)."
        actions={
          selectedStore ? (
            <div className="flex items-center gap-2 text-sm text-ink/70">
              <Building2 className="h-4 w-4 text-brand-600" aria-hidden />
              <span>{selectedStore.name}</span>
            </div>
          ) : undefined
        }
      />

      {error && <Alert variant="danger">{error}</Alert>}
      {message && <Alert variant="success">{message}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardContent className="space-y-3 p-4">
            <h2 className="font-sans text-section-title text-brand-900">Upload de arquivo</h2>
            <form onSubmit={onUpload} className="space-y-3">
              <Input label="Nome" value={name} onChange={(e) => setName(e.target.value)} />
              <label className="block text-sm font-medium text-ink">
                Arquivo (jpg/png/webp/gif/svg/mp4/webm)
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml,video/mp4,video/webm"
                  className="mt-1 block w-full text-sm"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </label>
              <Input
                label="Duração na TV (s)"
                type="number"
                min={3}
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
              />
              <Button type="submit" disabled={busy || !storeId} loading={busy}>
                Enviar
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 p-4">
            <h2 className="font-sans text-section-title text-brand-900">Mídia WEB</h2>
            <form onSubmit={onWeb} className="space-y-3">
              <Input label="Nome" value={name} onChange={(e) => setName(e.target.value)} />
              <Input
                label="URL https"
                value={webUrl}
                onChange={(e) => setWebUrl(e.target.value)}
                placeholder="https://…"
              />
              <Button type="submit" variant="secondary" disabled={busy || !storeId} loading={busy}>
                Cadastrar URL
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardContent className="p-4">
            <h2 className="font-sans text-section-title text-brand-900">Biblioteca</h2>
            {loading && <p className="mt-3 text-sm text-ink/60">Carregando…</p>}
            {!loading && items.length === 0 && (
              <p className="mt-3 text-sm text-ink/60">Nenhuma mídia nesta loja.</p>
            )}
            <ul className="mt-3 divide-y divide-brand-50">
              {items.map((m) => (
                <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                  <button type="button" className="text-left hover:underline" onClick={() => setPreview(m)}>
                    <span className="font-semibold">{m.name}</span>
                    <span className="ml-2 text-ink/60">
                      {m.media_type} · {fmtBytes(m.size_bytes)} · {m.duration_seconds ?? "—"}s
                    </span>
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-semantic-danger"
                    disabled={busy}
                    onClick={() => void remove(m.id)}
                  >
                    Remover
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <h2 className="font-sans text-section-title text-brand-900">Preview</h2>
            {!preview ? (
              <p className="mt-3 text-sm text-ink/60">Selecione uma mídia.</p>
            ) : (
              <div className="mt-3 space-y-3">
                <p className="text-sm text-ink/70">
                  {preview.name} · {preview.mime_type}
                </p>
                {preview.media_type === "IMAGE" && (
                  <img
                    src={preview.public_url}
                    alt={preview.name}
                    className="max-h-80 w-full object-contain bg-ink/5"
                  />
                )}
                {preview.media_type === "VIDEO" && (
                  <video src={preview.public_url} controls className="max-h-80 w-full bg-black" />
                )}
                {preview.media_type === "WEB" && (
                  <a
                    href={preview.public_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-700 underline"
                  >
                    {preview.public_url}
                  </a>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
