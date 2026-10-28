import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Store = { id: string; name: string };
type MediaItem = { id: string; name: string; media_type: string; public_url: string; duration_seconds: number | null };
type PlaylistItem = {
  id: string;
  asset_id: string;
  position: number;
  duration_seconds: number;
  asset: MediaItem | null;
};
type Playlist = {
  id: string;
  store_id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  items: PlaylistItem[];
};

export default function Playlists() {
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("");
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [assets, setAssets] = useState<MediaItem[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [previewIndex, setPreviewIndex] = useState(0);

  const selected = playlists.find((p) => p.id === selectedId) || null;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pl, media] = await Promise.all([
        api.get<Playlist[]>("/playlists", { params: { store_id: storeId || undefined } }),
        api.get<MediaItem[]>("/media", { params: { store_id: storeId || undefined } }),
      ]);
      setPlaylists(pl.data);
      setAssets(media.data);
      setSelectedId((prev) => {
        if (prev && pl.data.some((p) => p.id === prev)) return prev;
        return pl.data[0]?.id || null;
      });
    } catch {
      setError("Falha ao carregar playlists.");
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
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    if (storeId) void load();
  }, [load, storeId]);

  useEffect(() => {
    setPreviewIndex(0);
  }, [selectedId]);

  useEffect(() => {
    if (!selected || selected.items.length === 0) return;
    const item = selected.items[previewIndex % selected.items.length];
    const ms = Math.max(3, item.duration_seconds || 10) * 1000;
    const id = window.setTimeout(() => {
      setPreviewIndex((i) => (i + 1) % selected.items.length);
    }, ms);
    return () => window.clearTimeout(id);
  }, [selected, previewIndex]);

  async function createPlaylist(e: FormEvent) {
    e.preventDefault();
    if (!storeId || !name.trim()) return;
    setMessage(null);
    try {
      const { data } = await api.post<Playlist>("/playlists", {
        store_id: storeId,
        name: name.trim(),
        is_default: playlists.length === 0,
      });
      setName("");
      setMessage(`Playlist “${data.name}” criada.`);
      await load();
      setSelectedId(data.id);
    } catch {
      setError("Não foi possível criar a playlist.");
    }
  }

  async function addAsset(assetId: string) {
    if (!selectedId) return;
    try {
      const { data } = await api.post<Playlist>(`/playlists/${selectedId}/items`, { asset_id: assetId });
      setPlaylists((prev) => prev.map((p) => (p.id === data.id ? data : p)));
      setMessage("Mídia adicionada.");
    } catch {
      setError("Falha ao adicionar item.");
    }
  }

  async function removeItem(itemId: string) {
    if (!selectedId) return;
    try {
      const { data } = await api.delete<Playlist>(`/playlists/${selectedId}/items/${itemId}`);
      setPlaylists((prev) => prev.map((p) => (p.id === data.id ? data : p)));
    } catch {
      setError("Falha ao remover item.");
    }
  }

  async function setDuration(itemId: string, duration_seconds: number) {
    if (!selectedId) return;
    try {
      const { data } = await api.patch<Playlist>(`/playlists/${selectedId}/items/${itemId}`, {
        duration_seconds,
      });
      setPlaylists((prev) => prev.map((p) => (p.id === data.id ? data : p)));
    } catch {
      setError("Falha ao atualizar duração.");
    }
  }

  async function setDefault() {
    if (!selectedId) return;
    try {
      const { data } = await api.patch<Playlist>(`/playlists/${selectedId}`, { is_default: true });
      setPlaylists((prev) =>
        prev.map((p) => ({
          ...p,
          is_default: p.id === data.id,
          ...(p.id === data.id ? data : {}),
        })),
      );
      setMessage("Playlist definida como padrão da loja.");
    } catch {
      setError("Falha ao definir padrão.");
    }
  }

  async function onDrop(targetId: string) {
    if (!selected || !dragId || dragId === targetId) {
      setDragId(null);
      return;
    }
    const ids = selected.items.map((i) => i.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(targetId);
    if (from < 0 || to < 0) {
      setDragId(null);
      return;
    }
    const next = [...ids];
    next.splice(from, 1);
    next.splice(to, 0, dragId);
    setDragId(null);
    // otimista
    const reordered = next
      .map((id) => selected.items.find((i) => i.id === id)!)
      .filter(Boolean)
      .map((item, idx) => ({ ...item, position: idx }));
    setPlaylists((prev) => prev.map((p) => (p.id === selected.id ? { ...p, items: reordered } : p)));
    try {
      const { data } = await api.patch<Playlist>(`/playlists/${selected.id}/items/reorder`, { item_ids: next });
      setPlaylists((prev) => prev.map((p) => (p.id === data.id ? data : p)));
    } catch {
      setError("Falha ao reordenar.");
      await load();
    }
  }

  const previewItem = selected && selected.items.length > 0 ? selected.items[previewIndex % selected.items.length] : null;
  const usedAssetIds = new Set(selected?.items.map((i) => i.asset_id) || []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-brand-900">Playlists</h1>
          <p className="mt-1 text-ink/70">Monte a ordem das mídias, ajuste duração e pré-visualize o ciclo.</p>
        </div>
        <label className="text-sm">
          Loja
          <select className="mt-1 block min-w-[14rem] border border-brand-100 bg-sand px-2 py-2" value={storeId} onChange={(e) => setStoreId(e.target.value)}>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      <form onSubmit={createPlaylist} className="flex flex-wrap items-end gap-3 border border-brand-100 bg-white/80 p-4">
        <label className="text-sm">
          Nova playlist
          <input className="mt-1 block min-w-[16rem] border border-brand-100 bg-sand px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex.: Final de semana" />
        </label>
        <button type="submit" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white">Criar</button>
      </form>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}

      {!loading && (
        <div className="grid gap-6 xl:grid-cols-[220px_1.2fr_1fr]">
          <section className="border border-brand-100 bg-white/80 p-3">
            <h2 className="font-display text-lg font-semibold">Listas</h2>
            <ul className="mt-3 space-y-1 text-sm">
              {playlists.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(p.id)}
                    className={`w-full px-2 py-2 text-left ${selectedId === p.id ? "bg-brand-50 font-semibold" : "hover:bg-brand-50/60"}`}
                  >
                    {p.name}
                    {p.is_default && <span className="ml-2 text-xs text-brand-700">padrão</span>}
                  </button>
                </li>
              ))}
              {playlists.length === 0 && <li className="text-ink/60">Nenhuma playlist.</li>}
            </ul>
          </section>

          <section className="border border-brand-100 bg-white/80 p-4">
            {!selected ? (
              <p className="text-sm text-ink/60">Selecione ou crie uma playlist.</p>
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-display text-xl font-semibold">{selected.name}</h2>
                  {!selected.is_default && (
                    <button type="button" className="text-sm text-brand-700 underline" onClick={() => void setDefault()}>
                      Definir como padrão
                    </button>
                  )}
                </div>
                <p className="mt-1 text-sm text-ink/60">Arraste para reordenar.</p>
                <ul className="mt-4 space-y-2">
                  {selected.items.map((item) => (
                    <li
                      key={item.id}
                      draggable
                      onDragStart={() => setDragId(item.id)}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={() => void onDrop(item.id)}
                      className={`flex flex-wrap items-center gap-3 border border-brand-100 bg-sand/60 px-3 py-2 text-sm ${dragId === item.id ? "opacity-50" : ""}`}
                    >
                      <span className="cursor-grab text-ink/40" title="Arrastar">⠿</span>
                      <span className="min-w-[8rem] font-semibold">{item.asset?.name || item.asset_id}</span>
                      <span className="text-ink/60">{item.asset?.media_type}</span>
                      <label className="ml-auto flex items-center gap-1 text-xs">
                        Duração (s)
                        <input
                          type="number"
                          min={1}
                          className="w-16 border border-brand-100 bg-white px-1 py-1"
                          value={item.duration_seconds}
                          onChange={(e) => void setDuration(item.id, Number(e.target.value) || 1)}
                        />
                      </label>
                      <button type="button" className="text-red-700 underline" onClick={() => void removeItem(item.id)}>
                        Remover
                      </button>
                    </li>
                  ))}
                  {selected.items.length === 0 && <li className="text-sm text-ink/60">Adicione mídias da biblioteca.</li>}
                </ul>

                <div className="mt-5">
                  <h3 className="text-sm font-medium">Biblioteca da loja</h3>
                  <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-sm">
                    {assets.map((a) => (
                      <li key={a.id} className="flex items-center justify-between gap-2 py-1">
                        <span>{a.name} · {a.media_type}</span>
                        <button
                          type="button"
                          disabled={usedAssetIds.has(a.id)}
                          className="text-brand-700 underline disabled:opacity-40"
                          onClick={() => void addAsset(a.id)}
                        >
                          {usedAssetIds.has(a.id) ? "Na lista" : "Adicionar"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </section>

          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Preview</h2>
            {!previewItem?.asset ? (
              <p className="mt-3 text-sm text-ink/60">Sem itens para pré-visualizar.</p>
            ) : (
              <div className="mt-3 space-y-2">
                <p className="text-sm text-ink/70">
                  {previewItem.asset.name} · {previewItem.duration_seconds}s
                </p>
                <div className="aspect-video overflow-hidden bg-ink/10">
                  {previewItem.asset.media_type === "IMAGE" && (
                    <img src={previewItem.asset.public_url} alt="" className="h-full w-full object-contain" />
                  )}
                  {previewItem.asset.media_type === "VIDEO" && (
                    <video key={previewItem.id} src={previewItem.asset.public_url} className="h-full w-full object-contain" autoPlay muted playsInline />
                  )}
                  {previewItem.asset.media_type === "WEB" && (
                    <iframe title={previewItem.asset.name} src={previewItem.asset.public_url} className="h-full w-full border-0" />
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
