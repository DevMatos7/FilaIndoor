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
  Select,
  StatusDot,
  Tabs,
} from "../design-system";
import type { StatusDotTone } from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import api from "../services/api";
import { formatBrl } from "../utils/formatPrice";
import { PriceTableBuilder } from "../components/retail/PriceTableBuilder";
import { ProductDrawer } from "../components/retail/ProductDrawer";

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
  content_type?: string;
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
  has_image?: boolean;
  image_status?: string;
  primary_image?: { url?: string } | null;
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

function typeLabel(t?: string) {
  switch ((t || "").toUpperCase()) {
    case "PRODUCT_GRID":
      return "Grade de produtos";
    case "PRODUCT_HERO":
      return "Produto em destaque";
    case "PROMOTION_BOARD":
      return "Painel promocional";
    default:
      return "Tabela de preços";
  }
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
  const [builderType, setBuilderType] = useState("PRICE_TABLE");
  const [imageFilter, setImageFilter] = useState<"all" | "with" | "without">("all");
  const [productId, setProductId] = useState<string | null>(null);
  const [vitrineChooser, setVitrineChooser] = useState(false);

  const load = useCallback(async () => {
    if (!storeId) return;
    setError(null);
    try {
      const [h, o, t, p] = await Promise.all([
        api.get<Health>("/retail-data/health", { params: { store_id: storeId } }),
        api.get<Overview>("/dynamic-content/overview", { params: { store_id: storeId } }),
        api.get<TableRow[]>("/dynamic-content", { params: { store_id: storeId } }),
        api.get<ProductRow[]>("/retail-products", {
          params: { store_id: storeId, limit: 50, has_image: imageFilter },
        }),
      ]);
      setHealth(h.data);
      setOverview(o.data);
      setTables(t.data);
      setProducts(p.data);
      if (h.data.mapping.company_code) setCompanyCode(h.data.mapping.company_code);
    } catch {
      setError("Não foi possível carregar Produtos & preços.");
    }
  }, [storeId, imageFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  // Store change: clear drafts/selections
  useEffect(() => {
    setBuilderOpen(false);
    setEditId(null);
    setProductId(null);
    setVitrineChooser(false);
    setMsg(null);
  }, [storeId]);

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

  const priceTables = tables.filter((t) => !t.content_type || t.content_type === "PRICE_TABLE");
  const vitrines = tables.filter((t) =>
    ["PRODUCT_GRID", "PRODUCT_HERO", "PROMOTION_BOARD"].includes((t.content_type || "").toUpperCase()),
  );

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
        description="Conteúdo dinâmico CISS — tabela, grade, destaque e painel promocional."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setBuilderType("PRICE_TABLE");
                setEditId(null);
                setBuilderOpen(true);
              }}
            >
              + Nova tabela
            </Button>
            <Button
              onClick={() => {
                setVitrineChooser(true);
              }}
            >
              + Nova vitrine
            </Button>
          </div>
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
          { id: "vitrines", label: "Vitrines" },
          { id: "sync", label: "Sincronização CISS" },
        ]}
      />

      {tab === "overview" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <MetricCard label="Produtos (catálogo)" value={String(overview?.products ?? "—")} />
          <MetricCard label="Na loja" value={String(overview?.store_products ?? "—")} />
          <MetricCard label="Preços regulares" value={String(overview?.active_regular_prices ?? "—")} />
          <MetricCard label="Promoções" value={String(overview?.active_promotions ?? "—")} />
          <MetricCard label="Conteúdos dinâmicos" value={String(overview?.tables ?? "—")} />
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
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-sm text-ink/70" htmlFor="img-filter">
              Imagem
            </label>
            <Select
              id="img-filter"
              value={imageFilter}
              onChange={(e) => setImageFilter(e.target.value as "all" | "with" | "without")}
              className="w-44"
            >
              <option value="all">Todos</option>
              <option value="with">Com imagem</option>
              <option value="without">Sem imagem</option>
            </Select>
          </div>
          <div className="overflow-x-auto rounded-ds border border-brand-100">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-brand-50 text-brand-900">
                <tr>
                  <th className="px-3 py-2">Produto</th>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">Un.</th>
                  <th className="px-3 py-2">Regular</th>
                  <th className="px-3 py-2">Promo</th>
                  <th className="px-3 py-2">Imagem</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-t border-brand-50">
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        className="text-left font-medium text-brand-800 hover:underline"
                        onClick={() => setProductId(p.id)}
                      >
                        {p.commercial_description || p.description}
                      </button>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{p.source_product_id}</td>
                    <td className="px-3 py-2">{p.unit}</td>
                    <td className="px-3 py-2 tabular-nums">{formatBrl(p.regular_price)}</td>
                    <td className="px-3 py-2 tabular-nums">{formatBrl(p.promotion_price)}</td>
                    <td className="px-3 py-2">
                      <Badge tone={p.has_image ? "success" : "neutral"}>
                        {p.image_status || (p.has_image ? "COM IMAGEM" : "SEM IMAGEM")}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {products.length === 0 && (
              <EmptyState title="Sem produtos" description="Sincronize o CISS nesta loja." />
            )}
          </div>
        </div>
      )}

      {tab === "tables" && (
        <div className="grid gap-3 md:grid-cols-2">
          {priceTables.map((t) => (
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
                      setBuilderType("PRICE_TABLE");
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
          {priceTables.length === 0 && (
            <EmptyState title="Nenhuma tabela" description="Crie a primeira tabela de preços." />
          )}
        </div>
      )}

      {tab === "vitrines" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button type="button" onClick={() => setVitrineChooser(true)}>
              + Nova vitrine
            </Button>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {vitrines.map((t) => (
              <Card key={t.id}>
                <CardContent className="space-y-2 py-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-ink/50">{typeLabel(t.content_type)}</p>
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
                        setBuilderType(t.content_type || "PRODUCT_GRID");
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
            {vitrines.length === 0 && (
              <EmptyState title="Nenhuma vitrine" description="Crie grade, destaque ou painel promocional." />
            )}
          </div>
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

      {vitrineChooser && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-950/40 p-4">
          <div className="w-full max-w-lg rounded-ds bg-surface p-5 shadow-ds-md">
            <h3 className="font-display text-xl text-brand-900">Nova vitrine</h3>
            <p className="mt-1 text-sm text-ink/65">Escolha o tipo de conteúdo visual.</p>
            <div className="mt-4 grid gap-3">
              {(
                [
                  ["PRODUCT_GRID", "Grade de produtos", "Vários produtos em grade 2×2 / 3×2 / 4×2"],
                  ["PRODUCT_HERO", "Produto em destaque", "Um produto por página com foto e preço"],
                  ["PROMOTION_BOARD", "Painel promocional", "Campanha visual de ofertas"],
                ] as const
              ).map(([type, title, desc]) => (
                <button
                  key={type}
                  type="button"
                  className="rounded-ds border border-brand-100 p-4 text-left hover:bg-brand-50"
                  onClick={() => {
                    setVitrineChooser(false);
                    setBuilderType(type);
                    setEditId(null);
                    setBuilderOpen(true);
                  }}
                >
                  <span className="block font-semibold text-brand-900">{title}</span>
                  <span className="mt-1 block text-xs text-ink/55">{desc}</span>
                </button>
              ))}
            </div>
            <div className="mt-4 flex justify-end">
              <Button variant="ghost" onClick={() => setVitrineChooser(false)}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}

      {storeId && (
        <PriceTableBuilder
          open={builderOpen}
          storeId={storeId}
          contentId={editId}
          contentType={builderType}
          titleLabel={builderType === "PRICE_TABLE" ? "tabela" : "vitrine"}
          onClose={() => setBuilderOpen(false)}
          onSaved={() => void load()}
        />
      )}

      {storeId && (
        <ProductDrawer
          open={!!productId}
          storeId={storeId}
          productId={productId}
          onClose={() => setProductId(null)}
          onChanged={() => void load()}
        />
      )}
    </div>
  );
}
