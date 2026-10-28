import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Store = { id: string; name: string };
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
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("");
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
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<MediaItem[]>("/media", {
        params: { store_id: storeId || undefined },
      });
      setItems(data);
    } catch {
      setError("Falha ao listar mídias.");
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Store[]>("/stores");
        setStores(data);
        setStoreId((prev) => prev || data[0]?.id || "");
      } catch {
        /* seed cria loja; se falhar, upload exige store_id manual */
      }
    })();
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !file || !name.trim()) {
      setError("Informe loja, nome e arquivo.");
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
      setError("Informe loja, nome e URL.");
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
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">Mídias</h1>
        <p className="mt-1 text-ink/70">Upload, preview e metadados (IMAGE / VIDEO / WEB).</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          Loja
          <select className="mt-1 block min-w-[14rem] border border-brand-100 bg-sand px-2 py-2" value={storeId} onChange={(e) => setStoreId(e.target.value)}>
            <option value="">Todas (lista)</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={onUpload} className="space-y-3 border border-brand-100 bg-white/80 p-4">
          <h2 className="font-display text-xl font-semibold">Upload de arquivo</h2>
          <label className="block text-sm">
            Nome
            <input className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="block text-sm">
            Arquivo (jpg/png/webp/gif/svg/mp4/webm)
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml,video/mp4,video/webm"
              className="mt-1 block w-full text-sm"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
          <label className="block text-sm">
            Duração na TV (s)
            <input type="number" min={3} className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={duration} onChange={(e) => setDuration(e.target.value)} />
          </label>
          <button type="submit" disabled={busy || !storeId} className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            Enviar
          </button>
        </form>

        <form onSubmit={onWeb} className="space-y-3 border border-brand-100 bg-white/80 p-4">
          <h2 className="font-display text-xl font-semibold">Mídia WEB</h2>
          <label className="block text-sm">
            Nome
            <input className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="block text-sm">
            URL https
            <input className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={webUrl} onChange={(e) => setWebUrl(e.target.value)} placeholder="https://…" />
          </label>
          <button type="submit" disabled={busy || !storeId} className="border border-brand-700 px-4 py-2 text-sm font-semibold text-brand-700 disabled:opacity-50">
            Cadastrar URL
          </button>
        </form>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section className="border border-brand-100 bg-white/80 p-4">
          <h2 className="font-display text-xl font-semibold">Biblioteca</h2>
          {loading && <p className="mt-3 text-sm text-ink/60">Carregando…</p>}
          {!loading && items.length === 0 && (
            <p className="mt-3 text-sm text-ink/60">Nenhuma mídia. Faça upload para a loja.</p>
          )}
          <ul className="mt-3 divide-y divide-brand-50">
            {items.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <button type="button" className="text-left hover:underline" onClick={() => setPreview(m)}>
                  <span className="font-semibold">{m.name}</span>
                  <span className="ml-2 text-ink/60">{m.media_type} · {fmtBytes(m.size_bytes)} · {m.duration_seconds ?? "—"}s</span>
                </button>
                <button type="button" className="text-red-700 underline-offset-2 hover:underline" disabled={busy} onClick={() => void remove(m.id)}>
                  Remover
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="border border-brand-100 bg-white/80 p-4">
          <h2 className="font-display text-xl font-semibold">Preview</h2>
          {!preview ? (
            <p className="mt-3 text-sm text-ink/60">Selecione uma mídia.</p>
          ) : (
            <div className="mt-3 space-y-3">
              <p className="text-sm text-ink/70">{preview.name} · {preview.mime_type}</p>
              {preview.media_type === "IMAGE" && (
                <img src={preview.public_url} alt={preview.name} className="max-h-80 w-full object-contain bg-ink/5" />
              )}
              {preview.media_type === "VIDEO" && (
                <video src={preview.public_url} controls className="max-h-80 w-full bg-black" />
              )}
              {preview.media_type === "WEB" && (
                <a href={preview.public_url} target="_blank" rel="noreferrer" className="text-brand-700 underline">
                  {preview.public_url}
                </a>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
