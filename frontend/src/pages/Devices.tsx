import { FormEvent, useCallback, useEffect, useState } from "react";
import api from "../services/api";

type Terminal = {
  id: string;
  name: string;
  code: string;
  active: boolean;
  department_id: string;
};

type ManagedDevice = {
  id: string;
  name: string;
  device_type: string;
  status: string;
  store_id: string | null;
  display_id?: string | null;
  last_seen_at: string | null;
  app_version: string | null;
  config_version: number;
  ip_address: string | null;
  enrolled: boolean;
  audio_enabled: boolean;
  metadata?: { free_storage_mb?: number; playlist_version?: number };
};

type Display = {
  id: string;
  name: string;
  code: string;
  token: string;
  audio_enabled: boolean;
  audio_template: string;
  active: boolean;
  queue_id: string | null;
  channel_id?: string | null;
  playlist_id?: string | null;
  device?: ManagedDevice | null;
};

type Store = { id: string; name: string };
type Overview = { terminals: Terminal[]; displays: Display[]; devices?: ManagedDevice[] };

const STATUS_STYLE: Record<string, string> = {
  ONLINE: "bg-emerald-100 text-emerald-900",
  DEGRADED: "bg-amber-100 text-amber-900",
  OFFLINE: "bg-slate-100 text-slate-700",
  DISABLED: "bg-red-100 text-red-800",
};

export default function Devices() {
  const [data, setData] = useState<Overview | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pairingCode, setPairingCode] = useState("");
  const [enrollStore, setEnrollStore] = useState("");
  const [enrollName, setEnrollName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: res } = await api.get<Overview>("/devices/overview");
      setData(res);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setError(
        status === 401
          ? "Sessão expirada — faça login novamente para ver lojas e dispositivos."
          : "Falha ao carregar dispositivos.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    (async () => {
      try {
        const { data: s } = await api.get<Store[]>("/stores");
        setStores(s);
        setEnrollStore((prev) => prev || s[0]?.id || "");
      } catch {
        /* ignore */
      }
    })();
  }, [load]);

  async function toggleAudio(d: Display) {
    setMessage(null);
    try {
      await api.patch(`/displays/${d.id}`, { audio_enabled: !d.audio_enabled });
      setMessage(`${d.name}: áudio ${!d.audio_enabled ? "ativado" : "desativado"}`);
      await load();
    } catch {
      setError("Não foi possível atualizar o display.");
    }
  }

  async function toggleTerminal(t: Terminal) {
    setMessage(null);
    try {
      await api.patch(`/terminals/${t.id}`, { active: !t.active });
      setMessage(`${t.code}: ${!t.active ? "ativado" : "desativado"}`);
      await load();
    } catch {
      setError("Não foi possível atualizar o terminal.");
    }
  }

  async function enroll(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const { data: res } = await api.post<ManagedDevice>("/devices/enroll", {
        pairing_code: pairingCode.trim(),
        store_id: enrollStore,
        name: enrollName.trim() || undefined,
      });
      setMessage(`Dispositivo enrolled: ${res.name} (${res.status})`);
      setPairingCode("");
      setEnrollName("");
      await load();
    } catch {
      setError("Falha no enroll — verifique o código e a loja.");
    }
  }

  async function setEnabled(device: ManagedDevice, enable: boolean) {
    setMessage(null);
    try {
      await api.post(`/devices/${device.id}/${enable ? "enable" : "disable"}`);
      setMessage(`${device.name}: ${enable ? "habilitado" : "desabilitado"}`);
      await load();
    } catch {
      setError("Não foi possível alterar o status do device.");
    }
  }

  const managed = data?.devices || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-brand-900">Dispositivos</h1>
        <p className="mt-1 text-ink/70">Enrollment, heartbeat, health e telemetria das TVs e terminais.</p>
      </div>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}
      {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {message && <p className="border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-900">{message}</p>}

      <section className="border border-brand-100 bg-white/80 p-4">
        <h2 className="font-display text-xl font-semibold">Adicionar (enroll)</h2>
        <p className="mt-1 text-sm text-ink/60">Informe o código de 6 dígitos gerado pelo player.</p>
        <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={(e) => void enroll(e)}>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">Código</span>
            <input
              className="border border-brand-100 bg-white px-3 py-2 font-mono tracking-widest"
              value={pairingCode}
              onChange={(e) => setPairingCode(e.target.value)}
              placeholder="829461"
              maxLength={6}
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">Loja</span>
            <select
              className="border border-brand-100 bg-white px-3 py-2"
              value={enrollStore}
              onChange={(e) => setEnrollStore(e.target.value)}
              required
            >
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-ink/70">Nome (opcional)</span>
            <input
              className="border border-brand-100 bg-white px-3 py-2"
              value={enrollName}
              onChange={(e) => setEnrollName(e.target.value)}
              placeholder="TV Açougue 3"
            />
          </label>
          <button type="submit" className="bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900">
            Vincular
          </button>
        </form>
      </section>

      {!loading && data && (
        <>
          <section className="border border-brand-100 bg-white/80 p-4">
            <h2 className="font-display text-xl font-semibold">Fleet / health</h2>
            {managed.length === 0 ? (
              <p className="mt-3 text-sm text-ink/60">Nenhum device gerenciado ainda.</p>
            ) : (
              <ul className="mt-3 divide-y divide-brand-50">
                {managed.map((d) => (
                  <li key={d.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
                    <div>
                      <p className="font-semibold">
                        {d.name}{" "}
                        <span className="font-normal text-ink/50">· {d.device_type}</span>
                      </p>
                      <p className="text-ink/60">
                        v{d.app_version || "—"} · cfg {d.config_version}
                        {d.ip_address ? ` · ${d.ip_address}` : ""}
                        {d.metadata?.free_storage_mb != null ? ` · ${d.metadata.free_storage_mb} MB livres` : ""}
                        {d.last_seen_at ? ` · visto ${new Date(d.last_seen_at).toLocaleString()}` : " · nunca visto"}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${STATUS_STYLE[d.status] || STATUS_STYLE.OFFLINE}`}>
                        {d.status}
                      </span>
                      {d.status === "DISABLED" ? (
                        <button type="button" className="text-brand-700 underline-offset-2 hover:underline" onClick={() => void setEnabled(d, true)}>
                          Habilitar
                        </button>
                      ) : (
                        <button type="button" className="text-brand-700 underline-offset-2 hover:underline" onClick={() => void setEnabled(d, false)}>
                          Desabilitar
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="border border-brand-100 bg-white/80 p-4">
              <h2 className="font-display text-xl font-semibold">Terminais</h2>
              {data.terminals.length === 0 ? (
                <p className="mt-3 text-sm text-ink/60">Nenhum terminal cadastrado.</p>
              ) : (
                <ul className="mt-3 divide-y divide-brand-50">
                  {data.terminals.map((t) => (
                    <li key={t.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                      <div>
                        <p className="font-semibold">
                          {t.code} — {t.name}
                        </p>
                        <p className="text-ink/60">{t.active ? "Ativo" : "Inativo"}</p>
                      </div>
                      <button type="button" className="text-brand-700 underline-offset-2 hover:underline" onClick={() => void toggleTerminal(t)}>
                        {t.active ? "Desativar" : "Ativar"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="border border-brand-100 bg-white/80 p-4">
              <h2 className="font-display text-xl font-semibold">Displays / TVs</h2>
              {data.displays.length === 0 ? (
                <p className="mt-3 text-sm text-ink/60">Nenhum display cadastrado.</p>
              ) : (
                <ul className="mt-3 divide-y divide-brand-50">
                  {data.displays.map((d) => (
                    <li key={d.id} className="space-y-2 py-3 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold">
                            {d.code} — {d.name}
                          </p>
                          <p className="text-ink/60">
                            {d.audio_enabled ? "Áudio master ligado" : "Sem áudio"} · {d.active ? "Ativo" : "Inativo"}
                            {d.channel_id ? " · canal vinculado" : ""}
                            {d.device ? ` · ${d.device.status}` : ""}
                          </p>
                        </div>
                        <button type="button" className="text-brand-700 underline-offset-2 hover:underline" onClick={() => void toggleAudio(d)}>
                          {d.audio_enabled ? "Desligar áudio" : "Ligar áudio"}
                        </button>
                      </div>
                      {d.queue_id && (
                        <a
                          className="inline-block text-brand-700 underline-offset-2 hover:underline"
                          href={`/display/${d.queue_id}?token=${d.token}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Abrir player
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
