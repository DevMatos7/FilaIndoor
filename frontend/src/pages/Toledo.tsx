import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Status = {
  toledo_enabled: boolean;
  configured_mode: string;
  effective_mode: string;
  adapter_implemented: boolean;
  discovery_only: boolean;
  toledo_mock?: boolean;
  message: string;
  toledo?: { confirmed?: { player_push?: boolean; history?: boolean }; configured?: boolean };
};

type Completeness = {
  percent: number;
  completed: number;
  total: number;
  fields: Record<string, boolean>;
};

type Discovery = {
  environment_name: string;
  mgv_version: string | null;
  mit_version: string | null;
  mit_cloud: boolean | null;
  mit_cloud_url: string | null;
  license_notes: string | null;
  stores_notes: string | null;
  players_notes: string | null;
  api_enabled: boolean | null;
  api_base_url: string | null;
  auth_type: string | null;
  integration_key_configured: boolean;
  network_notes: string | null;
  docs_compared: boolean;
  notes: string | null;
  mode_intent: string;
  completeness?: Completeness;
};

const empty: Discovery = {
  environment_name: "default",
  mgv_version: "",
  mit_version: "",
  mit_cloud: null,
  mit_cloud_url: "",
  license_notes: "",
  stores_notes: "",
  players_notes: "",
  api_enabled: null,
  api_base_url: "",
  auth_type: "",
  integration_key_configured: false,
  network_notes: "",
  docs_compared: false,
  notes: "",
  mode_intent: "NATIVE",
};

export default function Toledo() {
  const [status, setStatus] = useState<Status | null>(null);
  const [form, setForm] = useState<Discovery>(empty);
  const [completeness, setCompleteness] = useState<Completeness | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [st, disc] = await Promise.all([
        api.get<Status>("/toledo/status"),
        api.get<Discovery & { completeness: Completeness }>("/toledo/discovery"),
      ]);
      setStatus(st.data);
      const { completeness: c, ...rest } = disc.data;
      setForm({
        ...empty,
        ...rest,
        mgv_version: rest.mgv_version || "",
        mit_version: rest.mit_version || "",
        mit_cloud_url: rest.mit_cloud_url || "",
        license_notes: rest.license_notes || "",
        stores_notes: rest.stores_notes || "",
        players_notes: rest.players_notes || "",
        api_base_url: rest.api_base_url || "",
        auth_type: rest.auth_type || "",
        network_notes: rest.network_notes || "",
        notes: rest.notes || "",
      });
      setCompleteness(c);
    } catch {
      setError("Falha ao carregar discovery Toledo.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function setField<K extends keyof Discovery>(key: K, value: Discovery[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function testPush() {
    setMessage(null);
    setError(null);
    try {
      const { data } = await api.post<{ ok: boolean; skipped: boolean; detail?: string }>("/toledo/adapter/test-push", {
        ticket_number: "A999",
        counter: "1",
        department: "Açougue",
      });
      setMessage(
        data.skipped
          ? `Push ignorado (sem capacidade confirmada): ${data.detail || ""}`
          : data.ok
            ? `Push OK: ${data.detail || ""}`
            : `Push falhou (fila nativa intacta): ${data.detail || ""}`,
      );
    } catch {
      setError("Falha ao testar push.");
    }
  }

  async function syncHistory() {
    setMessage(null);
    setError(null);
    try {
      const { data } = await api.post<{ ok: boolean; count: number; detail?: string }>("/toledo/adapter/sync-history");
      setMessage(data.ok ? `Histórico: ${data.count} item(ns)` : `Sync histórico falhou: ${data.detail || ""}`);
    } catch {
      setError("Falha ao sincronizar histórico.");
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const payload = {
        ...form,
        mgv_version: form.mgv_version || null,
        mit_version: form.mit_version || null,
        mit_cloud_url: form.mit_cloud_url || null,
        license_notes: form.license_notes || null,
        stores_notes: form.stores_notes || null,
        players_notes: form.players_notes || null,
        api_base_url: form.api_base_url || null,
        auth_type: form.auth_type || null,
        network_notes: form.network_notes || null,
        notes: form.notes || null,
      };
      const { data } = await api.put<Discovery & { completeness: Completeness }>("/toledo/discovery", payload);
      setCompleteness(data.completeness);
      setMessage("Discovery salvo. Nenhum endpoint Toledo foi chamado.");
    } catch {
      setError("Não foi possível salvar o checklist.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">Toledo — Discovery</h1>
        <p className="mt-1 text-ink/70">Inventário do ambiente. Sem adapter operacional neste sprint.</p>
      </div>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}
      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      {status && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Flag</p>
            <p className="mt-1 font-display text-2xl font-semibold">{status.toledo_enabled ? "ON" : "OFF"}</p>
            <p className="text-sm text-ink/60">{status.message}</p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Modo efetivo</p>
            <p className="mt-1 font-display text-2xl font-semibold">{status.effective_mode}</p>
            <p className="text-sm text-ink/60">
              configurado: {status.configured_mode}
              {status.adapter_implemented ? " · adapter S14" : ""}
              {status.toledo_mock ? " · mock" : ""}
            </p>
          </div>
          <div className="border border-brand-100 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-wide text-ink/50">Checklist</p>
            <p className="mt-1 font-display text-2xl font-semibold">{completeness?.percent ?? 0}%</p>
            <p className="text-sm text-ink/60">
              {completeness?.completed}/{completeness?.total} campos essenciais
            </p>
          </div>
        </div>
      )}

      <section className="border border-brand-100 bg-white/80 p-4">
        <h2 className="font-display text-xl font-semibold">Adapter (Sprint 14)</h2>
        <p className="mt-1 text-sm text-ink/60">
          Fila nativa é a fonte da verdade. Push/histórico Toledo só rodam se confirmados — falha não bloqueia a botoeira.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <button
            type="button"
            className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900"
            onClick={() => void testPush()}
          >
            Testar player push
          </button>
          <button
            type="button"
            className="border border-brand-700 px-4 py-2 text-sm font-semibold text-brand-700"
            onClick={() => void syncHistory()}
          >
            Sync histórico
          </button>
        </div>
      </section>

      <form className="space-y-4 border border-brand-100 bg-white/80 p-4" onSubmit={(e) => void onSave(e)}>
        <h2 className="font-display text-xl font-semibold">Checklist de inventário</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">MGV version</span>
            <input className="w-full border border-brand-100 px-3 py-2" value={form.mgv_version || ""} onChange={(e) => setField("mgv_version", e.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">MIT version</span>
            <input className="w-full border border-brand-100 px-3 py-2" value={form.mit_version || ""} onChange={(e) => setField("mit_version", e.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">MIT Cloud</span>
            <select
              className="w-full border border-brand-100 px-3 py-2"
              value={form.mit_cloud === null ? "" : form.mit_cloud ? "1" : "0"}
              onChange={(e) => setField("mit_cloud", e.target.value === "" ? null : e.target.value === "1")}
            >
              <option value="">pendente</option>
              <option value="1">sim</option>
              <option value="0">não</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">MIT Cloud URL</span>
            <input className="w-full border border-brand-100 px-3 py-2" value={form.mit_cloud_url || ""} onChange={(e) => setField("mit_cloud_url", e.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">API habilitada</span>
            <select
              className="w-full border border-brand-100 px-3 py-2"
              value={form.api_enabled === null ? "" : form.api_enabled ? "1" : "0"}
              onChange={(e) => setField("api_enabled", e.target.value === "" ? null : e.target.value === "1")}
            >
              <option value="">pendente</option>
              <option value="1">sim</option>
              <option value="0">não</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">API base URL</span>
            <input className="w-full border border-brand-100 px-3 py-2" value={form.api_base_url || ""} onChange={(e) => setField("api_base_url", e.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">Auth (JWT / chave)</span>
            <input className="w-full border border-brand-100 px-3 py-2" value={form.auth_type || ""} onChange={(e) => setField("auth_type", e.target.value)} />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">Modo pretendido (S14)</span>
            <select className="w-full border border-brand-100 px-3 py-2" value={form.mode_intent} onChange={(e) => setField("mode_intent", e.target.value)}>
              <option value="NATIVE">NATIVE</option>
              <option value="TOLEDO_DISPLAY">TOLEDO_DISPLAY</option>
              <option value="TOLEDO_SYNC">TOLEDO_SYNC</option>
              <option value="TOLEDO_FULL">TOLEDO_FULL</option>
            </select>
          </label>
        </div>
        <label className="block text-sm">
          <span className="mb-1 block text-ink/70">Players</span>
          <textarea className="w-full border border-brand-100 px-3 py-2" rows={2} value={form.players_notes || ""} onChange={(e) => setField("players_notes", e.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-ink/70">Licença / lojas / rede</span>
          <textarea
            className="w-full border border-brand-100 px-3 py-2"
            rows={3}
            value={[form.license_notes, form.stores_notes, form.network_notes].filter(Boolean).join("\n") || form.notes || ""}
            onChange={(e) => {
              setField("notes", e.target.value);
              setField("license_notes", e.target.value);
            }}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.integration_key_configured} onChange={(e) => setField("integration_key_configured", e.target.checked)} />
          Chave de integração configurada no ambiente (não colar o secret aqui)
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.docs_compared} onChange={(e) => setField("docs_compared", e.target.checked)} />
          Documentação oficial comparada com este inventário
        </label>
        <button type="submit" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900">
          Salvar discovery
        </button>
        <p className="text-xs text-ink/50">
          Detalhes: <code>docs/integrations/toledo-discovery.md</code>
        </p>
      </form>
    </div>
  );
}
