import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Store = { id: string; name: string; external_code?: string | null };
type ProviderInfo = {
  provider: string;
  read_only: boolean;
  writes_forbidden: boolean;
  configured?: boolean;
  price_sync_minutes: number;
  stock_sync_minutes: number;
};
type Snapshot = {
  id: string;
  regular_price: number | null;
  promo_price: number | null;
  stock_qty: number | null;
  product: { external_product_id: string; sku: string | null; description: string; unit: string | null };
};
type SyncRun = {
  id: string;
  status: string;
  products_upserted: number;
  snapshots_upserted: number;
  started_at: string | null;
  error_message: string | null;
};
type OfferRender = {
  id: string;
  name: string;
  product_external_id: string;
  renderable: boolean;
  reason?: string | null;
  alert?: string;
  offer?: { title: string; lines: string[]; stock_qty?: number | null } | null;
};

export default function Integrations() {
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("");
  const [provider, setProvider] = useState<ProviderInfo | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [runs, setRuns] = useState<SyncRun[]>([]);
  const [offers, setOffers] = useState<OfferRender[]>([]);
  const [sku, setSku] = useState("SKU-PICANHA");
  const [offerName, setOfferName] = useState("Template Oferta Açougue");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!storeId) return;
    setLoading(true);
    setError(null);
    try {
      const [p, sn, r, active] = await Promise.all([
        api.get<ProviderInfo>("/integrations/provider"),
        api.get<Snapshot[]>("/integrations/snapshots", { params: { store_id: storeId } }),
        api.get<SyncRun[]>("/integrations/sync-runs", { params: { store_id: storeId, limit: 10 } }),
        api.get<OfferRender[]>("/integrations/offers/active", { params: { store_id: storeId } }),
      ]);
      setProvider(p.data);
      setSnapshots(sn.data);
      setRuns(r.data);
      setOffers(active.data);
    } catch {
      setError("Falha ao carregar integrações.");
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Store[]>("/stores");
        setStores(data);
        const prefer = data.find((s) => s.name.includes("Campo Novo")) || data[0];
        setStoreId((prev) => prev || prefer?.id || "");
      } catch {
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runSync() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await api.post("/integrations", {
        store_id: storeId,
        provider: "mock",
        external_store_id: stores.find((s) => s.id === storeId)?.external_code || "CAMPO_NOVO",
      });
      const { data } = await api.post<SyncRun>("/integrations/sync", null, { params: { store_id: storeId } });
      setMessage(`Sync ${data.status}: ${data.products_upserted} produtos, ${data.snapshots_upserted} snapshots`);
      await load();
    } catch {
      setError("Falha no sync ERP (somente leitura).");
    } finally {
      setBusy(false);
    }
  }

  async function createOffer(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const { data } = await api.post("/integrations/offers", {
        store_id: storeId,
        name: offerName,
        product_external_id: sku,
        template_key: "oferta_acougue",
        only_in_stock: true,
      });
      const rendered = await api.get(`/integrations/offers/${data.id}/render`);
      setMessage(
        rendered.data.renderable
          ? `Oferta: ${(rendered.data.offer?.lines || []).join(" · ")}`
          : `Não renderizável: ${rendered.data.reason}${rendered.data.alert ? ` — ${rendered.data.alert}` : ""}`,
      );
      await load();
    } catch {
      setError("Falha ao criar template de oferta.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">Integrações CISS</h1>
        <p className="mt-1 text-ink/70">ERP somente leitura → snapshot local → campanhas dinâmicas.</p>
      </div>

      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-ink/70">Loja</span>
          <select className="border border-brand-100 bg-white px-3 py-2" value={storeId} onChange={(e) => setStoreId(e.target.value)}>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={busy || !storeId}
          className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900 disabled:opacity-50"
          onClick={() => void runSync()}
        >
          Sincronizar Mock ERP
        </button>
      </div>

      {provider && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Provider</p>
            <p className="mt-1 font-display text-2xl font-semibold">{provider.provider}</p>
            <p className="text-sm text-ink/60">{provider.writes_forbidden ? "read-only (sem escrita no CISS)" : "—"}</p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Preços</p>
            <p className="mt-1 font-display text-2xl font-semibold">cada {provider.price_sync_minutes} min</p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Estoque</p>
            <p className="mt-1 font-display text-2xl font-semibold">cada {provider.stock_sync_minutes} min</p>
          </div>
        </div>
      )}

      <section className="border border-brand-100 bg-white/80 p-4">
        <h2 className="font-display text-xl font-semibold">Nova campanha (template)</h2>
        <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={(e) => void createOffer(e)}>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">Nome</span>
            <input className="border border-brand-100 bg-white px-3 py-2" value={offerName} onChange={(e) => setOfferName(e.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">product_external_id</span>
            <input className="border border-brand-100 bg-white px-3 py-2 font-mono" value={sku} onChange={(e) => setSku(e.target.value)} />
          </label>
          <button type="submit" disabled={busy} className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            Criar e renderizar
          </button>
        </form>
        <p className="mt-2 text-xs text-ink/50">Render usa apenas snapshot local — nunca consulta CISS por frame.</p>
      </section>

      {loading ? (
        <p className="text-sm text-ink/60">Carregando…</p>
      ) : (
        <>
          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Snapshots da loja</h2>
            {snapshots.length === 0 ? (
              <p className="mt-3 text-sm text-ink/60">Nenhum snapshot. Rode o sync mock.</p>
            ) : (
              <ul className="mt-3 divide-y divide-brand-50 text-sm">
                {snapshots.map((s) => (
                  <li key={s.id} className="flex flex-wrap justify-between gap-2 py-2">
                    <div>
                      <p className="font-semibold">{s.product.description}</p>
                      <p className="text-ink/60">
                        {s.product.external_product_id} · SKU {s.product.sku || "—"} · estoque {s.stock_qty ?? "—"}
                      </p>
                    </div>
                    <p className="font-mono text-brand-700">
                      {s.promo_price != null ? (
                        <>
                          <span className="text-ink/40 line-through">R$ {s.regular_price?.toFixed(2)}</span> R$ {s.promo_price.toFixed(2)}
                        </>
                      ) : (
                        <>R$ {s.regular_price?.toFixed(2) ?? "—"}</>
                      )}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Ofertas ativas (render)</h2>
            {offers.length === 0 ? (
              <p className="mt-3 text-sm text-ink/60">Nenhuma oferta.</p>
            ) : (
              <ul className="mt-3 grid gap-3 sm:grid-cols-2">
                {offers.map((o) => (
                  <li key={o.id} className="border border-brand-50 bg-brand-50/40 p-4">
                    <p className="text-xs uppercase tracking-wide text-ink/50">{o.name}</p>
                    {o.renderable && o.offer ? (
                      <div className="mt-2 space-y-1 font-display text-xl font-semibold text-brand-900">
                        {o.offer.lines.map((line) => (
                          <p key={line}>{line}</p>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-2 text-sm text-amber-800">{o.alert || o.reason || "indisponível"}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Sync runs</h2>
            <ul className="mt-3 divide-y divide-brand-50 text-sm">
              {runs.map((r) => (
                <li key={r.id} className="flex justify-between gap-2 py-2">
                  <span>
                    {r.status} · {r.products_upserted}/{r.snapshots_upserted}
                    {r.error_message ? ` · ${r.error_message}` : ""}
                  </span>
                  <span className="text-ink/50">{r.started_at ? new Date(r.started_at).toLocaleString() : ""}</span>
                </li>
              ))}
              {runs.length === 0 && <li className="py-2 text-ink/60">Nenhuma execução ainda.</li>}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
