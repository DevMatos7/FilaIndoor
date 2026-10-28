import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";

type Settings = {
  id: string;
  name: string;
  status: string;
  priority_strategy: string;
  normal_prefix: string;
  priority_prefix: string;
  digits: number;
  reset_policy: string;
  kiosk_enabled: boolean;
  kiosk_token: string | null;
  department_display_name: string | null;
  priority_rule: {
    normal_weight: number;
    priority_weight: number;
    priority_max_wait_seconds: number;
    normal_max_wait_seconds: number | null;
  };
};

export default function QueueSettings() {
  const { queueId } = useParams();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!queueId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Settings>(`/queues/${queueId}/settings`);
      setSettings(data);
    } catch {
      setError("Falha ao carregar configuração.");
    } finally {
      setLoading(false);
    }
  }, [queueId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!settings || !queueId) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const { data } = await api.patch<Settings>(`/queues/${queueId}`, {
        name: settings.name,
        status: settings.status,
        priority_strategy: settings.priority_strategy,
        normal_prefix: settings.normal_prefix,
        priority_prefix: settings.priority_prefix,
        digits: settings.digits,
        reset_policy: settings.reset_policy,
        kiosk_enabled: settings.kiosk_enabled,
        department_display_name: settings.department_display_name,
        normal_weight: settings.priority_rule.normal_weight,
        priority_weight: settings.priority_rule.priority_weight,
        priority_max_wait_seconds: settings.priority_rule.priority_max_wait_seconds,
        normal_max_wait_seconds: settings.priority_rule.normal_max_wait_seconds,
      });
      setSettings(data);
      setMessage("Configuração salva.");
    } catch {
      setError("Não foi possível salvar.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-sm text-ink/60">Carregando…</p>;
  if (error && !settings) return <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>;
  if (!settings) return <p>Fila não encontrada.</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <Link to={`/queues/${queueId}`} className="text-sm text-brand-700 hover:underline">← Voltar à fila</Link>
        <h1 className="mt-2 font-display text-3xl font-semibold text-brand-900">Configuração da fila</h1>
        <p className="mt-1 text-ink/70">Prioridade, numeração e totem.</p>
      </div>

      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}
      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}

      <form onSubmit={onSubmit} className="space-y-4 border border-brand-100 bg-white/80 p-5">
        <label className="block text-sm">
          Nome
          <input className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={settings.name} onChange={(e) => setSettings({ ...settings, name: e.target.value })} />
        </label>
        <label className="block text-sm">
          Nome exibido (departamento)
          <input
            className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2"
            value={settings.department_display_name || ""}
            onChange={(e) => setSettings({ ...settings, department_display_name: e.target.value })}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            Status
            <select className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={settings.status} onChange={(e) => setSettings({ ...settings, status: e.target.value })}>
              <option value="OPEN">OPEN</option>
              <option value="PAUSED">PAUSED</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </label>
          <label className="text-sm">
            Estratégia
            <select
              className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2"
              value={settings.priority_strategy}
              onChange={(e) => setSettings({ ...settings, priority_strategy: e.target.value })}
            >
              <option value="WEIGHTED">WEIGHTED</option>
              <option value="FIFO">FIFO</option>
              <option value="MAX_WAIT">MAX_WAIT</option>
            </select>
          </label>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            Peso normal
            <input
              type="number"
              min={1}
              className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2"
              value={settings.priority_rule.normal_weight}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  priority_rule: { ...settings.priority_rule, normal_weight: Number(e.target.value) },
                })
              }
            />
          </label>
          <label className="text-sm">
            Peso prioritária
            <input
              type="number"
              min={1}
              className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2"
              value={settings.priority_rule.priority_weight}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  priority_rule: { ...settings.priority_rule, priority_weight: Number(e.target.value) },
                })
              }
            />
          </label>
          <label className="text-sm">
            Max espera prioridade (s)
            <input
              type="number"
              min={0}
              className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2"
              value={settings.priority_rule.priority_max_wait_seconds}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  priority_rule: { ...settings.priority_rule, priority_max_wait_seconds: Number(e.target.value) },
                })
              }
            />
          </label>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            Prefixo normal
            <input className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={settings.normal_prefix} onChange={(e) => setSettings({ ...settings, normal_prefix: e.target.value })} />
          </label>
          <label className="text-sm">
            Prefixo prioridade
            <input className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={settings.priority_prefix} onChange={(e) => setSettings({ ...settings, priority_prefix: e.target.value })} />
          </label>
          <label className="text-sm">
            Dígitos
            <input type="number" min={1} max={6} className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2" value={settings.digits} onChange={(e) => setSettings({ ...settings, digits: Number(e.target.value) })} />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings.kiosk_enabled}
            onChange={(e) => setSettings({ ...settings, kiosk_enabled: e.target.checked })}
          />
          Totem habilitado
        </label>
        {settings.kiosk_token && (
          <p className="text-xs text-ink/60">Token totem: <code>{settings.kiosk_token}</code></p>
        )}

        <button type="submit" disabled={saving} className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </form>
    </div>
  );
}
