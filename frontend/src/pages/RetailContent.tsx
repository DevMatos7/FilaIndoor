import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, PageHeader, StatusDot } from "../design-system";
import type { StatusDotTone } from "../design-system";
import { useStoreContext } from "../context/StoreContext";
import api from "../services/api";

type EntityHealth = {
  entity: string;
  count: number;
  last_success_at: string | null;
  lag_seconds: number | null;
  status: string;
};

type Health = {
  store_id: string;
  store_name: string;
  timezone: string;
  timezone_valid: boolean;
  source: string;
  status: string;
  mapping: { configured: boolean; company_code: string | null; location_code: string | null };
  entities: EntityHealth[];
};

function statusTone(status: string): StatusDotTone {
  if (status === "FRESH") return "online";
  if (status === "DEGRADED" || status === "UNKNOWN") return "degraded";
  if (status === "STALE" || status === "FAILED") return "offline";
  return "neutral";
}

function formatLag(sec: number | null): string {
  if (sec == null) return "—";
  if (sec < 60) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.round(sec / 60)} min`;
  return `${(sec / 3600).toFixed(1)} h`;
}

export default function RetailContent() {
  const { selectedStoreId: storeId, stores, loading: storesLoading } = useStoreContext();
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [companyCode, setCompanyCode] = useState("1");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!storeId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Health>("/retail-data/health", { params: { store_id: storeId } });
      setHealth(data);
      if (data.mapping.company_code) setCompanyCode(data.mapping.company_code);
    } catch {
      setError("Não foi possível carregar a saúde dos dados de produto e preço.");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function ensureMapping() {
    if (!storeId) return;
    setMsg(null);
    try {
      await api.post("/retail-data/store-sources", {
        store_id: storeId,
        company_code: companyCode,
        source_system: "CISS",
      });
      setMsg("Mapeamento loja ↔ CISS salvo.");
      await load();
    } catch {
      setError("Falha ao salvar mapeamento. Verifique permissões e company_code.");
    }
  }

  async function runSync() {
    if (!storeId) return;
    setSyncing(true);
    setMsg(null);
    setError(null);
    try {
      if (!health?.mapping.configured) {
        await api.post("/retail-data/store-sources", {
          store_id: storeId,
          company_code: companyCode,
          source_system: "CISS",
        });
      }
      await api.post("/retail-data/sync", {
        store_id: storeId,
        entities: ["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"],
        full: false,
      });
      setMsg("Sincronização concluída.");
      await load();
    } catch {
      setError("Sincronização falhou. Os dados anteriores foram preservados.");
    } finally {
      setSyncing(false);
    }
  }

  const storeName = stores.find((s) => s.id === storeId)?.name || health?.store_name || "Loja";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Produtos & preços"
        description="Fundação de dados CISS — sincronização e saúde (sem tabela visual ainda)."
      />

      {storesLoading && <p className="text-sm text-ink/60">Carregando lojas…</p>}
      {!storeId && !storesLoading && (
        <Alert variant="warning">Selecione uma loja no topo para ver a sincronização.</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}
      {msg && <Alert variant="success">{msg}</Alert>}

      {storeId && (
        <>
          <Card>
            <CardContent className="space-y-4 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-ink/50">Loja</p>
                  <p className="font-display text-xl text-brand-900">{storeName}</p>
                  <p className="text-sm text-ink/60">
                    Timezone: {health?.timezone || "—"}{" "}
                    {health && !health.timezone_valid ? "(inválido)" : ""}
                  </p>
                </div>
                <StatusDot
                  tone={statusTone(health?.status || "UNKNOWN")}
                  label={health?.status || (loading ? "…" : "—")}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {(health?.entities || []).map((e) => (
                  <div key={e.entity} className="rounded-ds border border-brand-100/80 bg-surface-muted/40 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink/55">{e.entity}</p>
                      <StatusDot tone={statusTone(e.status)} label={e.status} showLabel={false} />
                    </div>
                    <p className="mt-2 font-display text-2xl text-brand-900">{e.count}</p>
                    <p className="text-xs text-ink/55">
                      Lag {formatLag(e.lag_seconds)} · {e.status}
                    </p>
                  </div>
                ))}
                {!loading && (!health?.entities || health.entities.length === 0) && (
                  <p className="text-sm text-ink/60 sm:col-span-2">Sem dados sincronizados ainda.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-4 p-5">
              <h2 className="font-display text-lg text-brand-900">Mapeamento CISS</h2>
              <p className="text-sm text-ink/65">
                Associe a loja ao código de empresa do ERP (IDEMPRESA). A TV nunca consulta o banco
                diretamente.
              </p>
              <div className="flex flex-wrap items-end gap-3">
                <label className="block text-sm">
                  <span className="text-ink/60">Company code (IDEMPRESA)</span>
                  <input
                    className="mt-1 block w-40 rounded-ds border border-brand-200 px-3 py-2"
                    value={companyCode}
                    onChange={(ev) => setCompanyCode(ev.target.value)}
                  />
                </label>
                <Button type="button" variant="secondary" onClick={() => void ensureMapping()}>
                  Salvar mapeamento
                </Button>
                <Button type="button" onClick={() => void runSync()} disabled={syncing}>
                  {syncing ? "Sincronizando…" : "Sincronizar agora"}
                </Button>
                <Button type="button" variant="ghost" onClick={() => void load()}>
                  Atualizar
                </Button>
              </div>
              {health?.mapping.configured && (
                <p className="text-xs text-ink/55">
                  Mapeamento ativo · company_code={health.mapping.company_code}
                  {health.mapping.location_code ? ` · local=${health.mapping.location_code}` : ""}
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
