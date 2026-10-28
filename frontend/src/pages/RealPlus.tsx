import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";

type Preview = {
  name: string;
  department_name?: string;
  waiting_count: number;
  estimated_wait_minutes: number;
  status: string;
};

type Tracking = {
  tracking_token: string;
  presence_status: string;
  ticket: {
    number: string;
    status: string;
    people_ahead: number;
    estimated_wait_minutes: number;
  };
  queue: { name: string | null; department_name: string | null };
  notifications: Array<{ id: string; title: string; body: string; channel: string; created_at: string }>;
  actions: { can_check_in: boolean; can_subscribe_push: boolean };
};

export default function RealPlus() {
  const { queueId } = useParams();
  const [params, setParams] = useSearchParams();
  const tokenFromUrl = params.get("t") || "";
  const [preview, setPreview] = useState<Preview | null>(null);
  const [track, setTrack] = useState<Tracking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadPreview = useCallback(async () => {
    if (!queueId) return;
    try {
      const { data } = await axios.get<Preview>(`${apiBase}/real-plus/queues/${queueId}/preview`);
      setPreview(data);
      setError(null);
    } catch {
      setError("REAL+ indisponível para esta fila.");
    }
  }, [queueId]);

  const loadTrack = useCallback(async (token: string) => {
    if (!token) return;
    try {
      const { data } = await axios.get<Tracking>(`${apiBase}/real-plus/track/${token}`);
      setTrack(data);
      setError(null);
    } catch {
      setError("Não foi possível carregar o acompanhamento.");
    }
  }, []);

  useEffect(() => {
    void loadPreview();
  }, [loadPreview]);

  useEffect(() => {
    if (tokenFromUrl) void loadTrack(tokenFromUrl);
  }, [tokenFromUrl, loadTrack]);

  useEffect(() => {
    if (!tokenFromUrl) return;
    const id = window.setInterval(() => void loadTrack(tokenFromUrl), 8000);
    return () => window.clearInterval(id);
  }, [tokenFromUrl, loadTrack]);

  async function issue(type: "NORMAL" | "PRIORITY") {
    if (!queueId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { data } = await axios.post<Tracking>(
        `${apiBase}/real-plus/queues/${queueId}/tickets`,
        { type, notify_when_ahead: 2 },
        { headers: { "Idempotency-Key": crypto.randomUUID() } },
      );
      setTrack(data);
      setParams({ t: data.tracking_token });
    } catch {
      setError("Falha ao retirar senha remota.");
    } finally {
      setBusy(false);
    }
  }

  async function checkIn() {
    if (!track || busy) return;
    setBusy(true);
    try {
      const { data } = await axios.post<Tracking>(`${apiBase}/real-plus/track/${track.tracking_token}/check-in`);
      setTrack(data);
    } catch {
      setError("Check-in não disponível no momento.");
    } finally {
      setBusy(false);
    }
  }

  async function subscribe() {
    if (!track || busy) return;
    setBusy(true);
    try {
      await axios.post(`${apiBase}/real-plus/track/${track.tracking_token}/subscribe`, {
        endpoint: "stub://browser",
      });
      await loadTrack(track.tracking_token);
    } catch {
      setError("Não foi possível ativar avisos.");
    } finally {
      setBusy(false);
    }
  }

  const dept = preview?.department_name || track?.queue.department_name || "Açougue";

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-brand-900 via-brand-700 to-ink text-white">
      <header className="px-6 py-6 text-center">
        <p className="font-display text-3xl font-semibold tracking-tight">REAL+</p>
        <p className="mt-1 text-lg uppercase tracking-[0.2em] text-brand-100">{dept}</p>
        <p className="mt-2 text-sm text-white/60">Fila virtual — acompanhe no celular</p>
      </header>

      <main className="mx-auto w-full max-w-lg flex-1 px-4 pb-10">
        {error && <p className="mb-4 border border-amber-200/40 bg-black/30 px-3 py-2 text-sm text-amber-100">{error}</p>}

        {!track && preview && (
          <section className="rounded-2xl bg-white/10 p-6 backdrop-blur">
            <p className="text-sm uppercase tracking-wide text-brand-100">Agora na loja</p>
            <p className="mt-2 font-display text-4xl font-semibold">{preview.waiting_count} pessoas aguardando</p>
            <p className="mt-2 text-lg text-white/80">
              aprox. {preview.estimated_wait_minutes > 0 ? `${preview.estimated_wait_minutes} min` : "sem espera"}
            </p>
            <div className="mt-8 grid gap-3">
              <button
                type="button"
                disabled={busy || preview.status !== "OPEN"}
                onClick={() => void issue("NORMAL")}
                className="min-h-[64px] rounded-xl bg-white text-lg font-semibold text-brand-900 disabled:opacity-50"
              >
                Retirar senha
              </button>
              <button
                type="button"
                disabled={busy || preview.status !== "OPEN"}
                onClick={() => void issue("PRIORITY")}
                className="min-h-[56px] rounded-xl border border-white/40 text-base font-semibold text-white disabled:opacity-50"
              >
                Senha prioritária
              </button>
            </div>
          </section>
        )}

        {track && (
          <section className="space-y-4">
            <div className="rounded-2xl bg-white/10 p-6 text-center backdrop-blur">
              <p className="text-sm uppercase tracking-wide text-brand-100">Sua senha</p>
              <p className="mt-2 font-display text-6xl font-bold tracking-tight">{track.ticket.number}</p>
              <p className="mt-3 text-white/80">
                {track.ticket.people_ahead} na frente · ~{track.ticket.estimated_wait_minutes} min
              </p>
              <p className="mt-2 text-xs uppercase tracking-wide text-brand-100">{track.presence_status.replace(/_/g, " ")}</p>
            </div>

            <div className="grid gap-3">
              {track.actions.can_check_in && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void checkIn()}
                  className="min-h-[56px] rounded-xl bg-white font-semibold text-brand-900 disabled:opacity-50"
                >
                  Cheguei na loja (check-in)
                </button>
              )}
              {track.actions.can_subscribe_push && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void subscribe()}
                  className="min-h-[48px] rounded-xl border border-white/40 font-semibold text-white disabled:opacity-50"
                >
                  Ativar avisos (push stub)
                </button>
              )}
            </div>

            <div className="rounded-2xl bg-black/20 p-4">
              <p className="text-sm font-semibold text-brand-100">Notificações</p>
              <ul className="mt-2 space-y-2 text-sm text-white/80">
                {track.notifications.map((n) => (
                  <li key={n.id}>
                    <span className="font-medium text-white">{n.title}</span> — {n.body}
                  </li>
                ))}
                {track.notifications.length === 0 && <li>Nenhum aviso ainda.</li>}
              </ul>
            </div>

            <button
              type="button"
              className="text-sm text-brand-100 underline-offset-2 hover:underline"
              onClick={() => {
                setTrack(null);
                setParams({});
                void loadPreview();
              }}
            >
              Nova senha
            </button>
          </section>
        )}

        <p className="mt-8 text-center text-xs text-white/40">
          <Link to="/" className="underline-offset-2 hover:underline">
            Admin
          </Link>
        </p>
      </main>
    </div>
  );
}
