import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  MetricCard,
  PageHeader,
  StatusDot,
  Tabs,
} from "../design-system";
import type { StatusDotTone } from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import api from "../services/api";
import { formatBrl } from "../utils/formatPrice";
import { PriceTableBuilder } from "../components/retail/PriceTableBuilder";

type Health = {
  store_id: string;
  store_name: string;
  timezone: string;
  timezone_valid: boolean;
  source: string;
  status: string;
  mapping: { configured: boolean; company_code: string | null; location_code: string | null };
  entities: { entity: string; count: number; last_success_at: string | null; lag_seconds: number | null; status: string }[];
};

type Overview = {
  products: number;
  store_products: number;
  active_regular_prices: number;
  active_promotions: number;
  tables: number;
  ciss_status: string;
};

type TableRow = {
  id: string;
  name: string;
  selection_mode: string;
  template_name?: string;
  item_count?: number | null;
  page_count?: number | null;
  total_duration_seconds?: number | null;
  status?: string;
  updated_at?: string | null;
};

type ProductRow = {
  id: string;
  description: string;
  commercial_description?: string | null;
  source_product_id?: string;
  unit?: string | null;
  regular_price?: number | null;
  promotion_price?: number | null;
  quantity_tiers?: { min_qty: number; amount: number }[];
  synced_at?: string | null;
};

function statusTone(status: string): StatusDotTone {
  if (status === "FRESH" || status === "PRONTA") return "online";
  if (status === "DEGRADED" || status === "ATENÇÃO" || status === "UNKNOWN") return "degraded";
  if (status === "STALE" || status === "FAILED" || status === "DADOS DESATUALIZADOS") return "offline";
  return "neutral";
}

function formatLag(sec: number | null | undefined): string {
  if (sec == null) return "—";
  if (sec < 60) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.round(sec / 60)} min`;
  return `${(sec / 3600).toFixed(1)} h`;
}

export default function RetailContent() {
  const { selectedStoreId: storeId, loading: storesLoading } = useStoreContext();
  const [tab, setTab] = useState("overview");
  const [health, setHealth] = useState<Health | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [tables, setTables] = useState<TableRow[]>([]);
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [companyCode, setCompanyCode] = useState("1");
  const [msg, setMsg] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!storeId) return;
    setError(null);
    try {
      const [h, o, t, p] = await Promise.all([
        api.get<Health>("/retail-data/health", { params: { store_id: storeId } }),
        api.get<Overview>("/dynamic-content/overview", { params: { store_id: storeId } }),
        api.get<TableRow[]>("/dynamic-content", { params: { store_id: storeId } }),
        api.get<ProductRow[]>("/retail-products", { params: { store_id: storeId, limit: 50 } }),
      ]);
      setHealth(h.data);
      setOverview(o.data);
      setTables(t.data);
      setProducts(p.data);
      if (h.data.mapping.company_code) setCompanyCode(h.data.mapping.company_code);
    } catch {
      setError("Não foi possível carregar Produtos & preços.");
    }
  }, [storeId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function ensureMapping() {
    if (!storeId) return;
    try {
      await api.post("/retail-data/store-sources", {
        store_id: storeId,
        company_code: companyCode,
        source_system: "CISS",
      });
      setMsg("Mapeamento loja ↔ CISS salvo.");
      await load();
    } catch {
      setError("Falha ao salvar mapeamento.");
    }
  }

  async function syncNow() {
    if (!storeId) return;
    setSyncing(true);
    try {
      await api.post("/retail-data/sync", {
        store_id: storeId,
        entities: ["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"],
        full: true,
      });
      setMsg("Sincronização CISS solicitada.");
      await load();
    } catch {
      setError("Falha na sincronização (driver DB2 pode estar só no host).");
    } finally {
      setSyncing(false);
    }
  }

  async function removeTable(id: string) {
    if (!storeId) return;
    await api.delete(`/dynamic-content/${id}`, { params: { store_id: storeId } });
    await load();
  }

  if (!storesLoading && !storeId) {
    return (
      <div className="space-y-4">
        <PageHeader title="Produtos & preços" description="Selecione uma loja no seletor superior." />
        <Alert variant="warning">Nenhuma loja selecionada.</Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Produtos & preços"
        description="Tabelas dinâmicas alimentadas pelo CISS — sem preço digitável."
        actions={
          <Button
            onClick={() => {
              setEditId(null);
              setBuilderOpen(true);
            }}
          >
            + Nova tabela
          </Button>
        }
      />

      {error && (
        <Alert variant="danger" role="alert">
          {error}
        </Alert>
      )}
      {msg && <Alert variant="success">{msg}</Alert>}

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "overview", label: "Visão geral" },
          { id: "products", label: "Produtos" },
          { id: "tables", label: "Tabelas" },
          { id: "sync", label: "Sincronização CISS" },
        ]}
      />

      {tab === "overview" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <MetricCard label="Produtos (catálogo)" value={String(overview?.products ?? "—")} />
          <MetricCard label="Na loja" value={String(overview?.store_products ?? "—")} />
          <MetricCard label="Preços regulares" value={String(overview?.active_regular_prices ?? "—")} />
          <MetricCard label="Promoções" value={String(overview?.active_promotions ?? "—")} />
          <MetricCard label="Tabelas" value={String(overview?.tables ?? "—")} />
          <Card className="sm:col-span-2 lg:col-span-5">
            <CardContent className="flex flex-wrap items-center gap-3 py-4">
              <StatusDot
                tone={statusTone(health?.status || "")}
                label={`CISS: ${health?.status || overview?.ciss_status || "—"}`}
              />
              <span className="text-sm text-ink/60">
                Timezone {health?.timezone} {health && !health.timezone_valid ? "(inválido)" : ""}
              </span>
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "products" && (
        <div className="overflow-x-auto rounded-ds border border-brand-100">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-brand-50 text-brand-900">
              <tr>
                <th className="px-3 py-2">Produto</th>
                <th className="px-3 py-2">SKU</th>
                <th className="px-3 py-2">Un.</th>
                <th className="px-3 py-2">Regular</th>
                <th className="px-3 py-2">Promo</th>
                <th className="px-3 py-2">Faixas</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className="border-t border-brand-50">
                  <td className="px-3 py-2">{p.commercial_description || p.description}</td>
                  <td className="px-3 py-2 font-mono text-xs">{p.source_product_id}</td>
                  <td className="px-3 py-2">{p.unit}</td>
                  <td className="px-3 py-2 tabular-nums">{formatBrl(p.regular_price)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatBrl(p.promotion_price)}</td>
                  <td className="px-3 py-2 text-xs text-ink/70">
                    {(p.quantity_tiers || [])
                      .map((t) => `${t.min_qty}+ ${formatBrl(t.amount)}`)
                      .join(" · ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {products.length === 0 && <EmptyState title="Sem produtos" description="Sincronize o CISS nesta loja." />}
        </div>
      )}

      {tab === "tables" && (
        <div className="grid gap-3 md:grid-cols-2">
          {tables.map((t) => (
            <Card key={t.id}>
              <CardContent className="space-y-2 py-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-display text-lg text-brand-900">{t.name}</h3>
                    <p className="text-sm text-ink/60">
                      {t.selection_mode} · {t.template_name}
                    </p>
                  </div>
                  <Badge tone={t.status === "PRONTA" ? "success" : "warning"}>{t.status || "—"}</Badge>
                </div>
                <p className="text-sm text-ink/70">
                  {t.item_count ?? "—"} produtos · {t.page_count ?? "—"} pág. · {t.total_duration_seconds ?? "—"}s
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setEditId(t.id);
                      setBuilderOpen(true);
                    }}
                  >
                    Editar
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => void removeTable(t.id)}>
                    Excluir
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {tables.length === 0 && (
            <EmptyState
              title="Nenhuma tabela"
              description="Crie a primeira tabela de preços com dados reais do CISS."
              action={
                <Button
                  onClick={() => {
                    setEditId(null);
                    setBuilderOpen(true);
                  }}
                >
                  + Nova tabela
                </Button>
              }
            />
          )}
        </div>
      )}

      {tab === "sync" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="space-y-3 py-4">
              <p className="text-sm">
                Mapeamento:{" "}
                {health?.mapping.configured
                  ? `IDEMPRESA ${health.mapping.company_code}`
                  : "não configurado"}
              </p>
              <div className="flex flex-wrap gap-2">
                <input
                  className="rounded-ds border border-brand-100 px-3 py-2 text-sm"
                  value={companyCode}
                  onChange={(e) => setCompanyCode(e.target.value)}
                  aria-label="IDEMPRESA"
                />
                <Button variant="secondary" onClick={() => void ensureMapping()}>
                  Salvar mapeamento
                </Button>
                <Button onClick={() => void syncNow()} disabled={syncing}>
                  {syncing ? "Sincronizando…" : "Sincronizar agora"}
                </Button>
              </div>
              <ul className="space-y-1 text-sm">
                {(health?.entities || []).map((e) => (
                  <li key={e.entity} className="flex items-center gap-2">
                    <StatusDot
                      tone={statusTone(e.status)}
                      label={`${e.entity}: ${e.count} · ${e.status} · lag ${formatLag(e.lag_seconds)}`}
                    />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}

      {storeId && (
        <PriceTableBuilder
          open={builderOpen}
          storeId={storeId}
          contentId={editId}
          onClose={() => setBuilderOpen(false)}
          onSaved={() => void load()}
        />
      )}
    </div>
  );
}
