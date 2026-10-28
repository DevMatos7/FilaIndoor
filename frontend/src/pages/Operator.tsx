import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import api, { Ticket } from "../services/api";

type Terminal = { id: string; name: string; code: string; department_id: string };

type Panel = {
  name: string;
  department_name?: string;
  waiting_count: number;
  priority_waiting: number;
  serving: Ticket | null;
  elapsed_seconds: number | null;
  terminal_id?: string | null;
};

function formatElapsed(total: number | null | undefined) {
  const s = Math.max(0, total || 0);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export default function Operator() {
  const { queueId } = useParams();
  const [params, setParams] = useSearchParams();
  const terminalId = params.get("terminal") || localStorage.getItem("operator_terminal") || "";

  const [tokenReady, setTokenReady] = useState(!!localStorage.getItem("token"));
  const [email, setEmail] = useState("operator@real.local");
  const [password, setPassword] = useState("operator123");
  const [loginError, setLoginError] = useState<string | null>(null);

  const [terminals, setTerminals] = useState<Terminal[]>([]);
  const [panel, setPanel] = useState<Panel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const busyRef = useRef(false);

  const elapsed = useMemo(() => {
    if (!panel?.elapsed_seconds && panel?.elapsed_seconds !== 0) return null;
    return (panel.elapsed_seconds || 0) + tick;
  }, [panel, tick]);

  async function login(e: FormEvent) {
    e.preventDefault();
    setLoginError(null);
    try {
      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);
      const { data } = await api.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      localStorage.setItem("token", data.access_token);
      setTokenReady(true);
    } catch {
      setLoginError("Falha no login do operador.");
    }
  }

  const loadPanel = useCallback(async () => {
    if (!queueId || !terminalId || !tokenReady) return;
    try {
      const { data } = await api.get<Panel>(`/queues/${queueId}/operator-panel`, {
        params: { terminal_id: terminalId },
      });
      setPanel(data);
      setError(null);
      setTick(0);
    } catch {
      setError("Não foi possível atualizar o painel.");
    }
  }, [queueId, terminalId, tokenReady]);

  useEffect(() => {
    if (!tokenReady || !queueId) return;
    (async () => {
      try {
        const q = await api.get<{ department_id: string }>(`/queues/${queueId}`);
        const { data } = await api.get<Terminal[]>("/terminals", {
          params: { department_id: q.data.department_id },
        });
        setTerminals(data);
        if (!terminalId && data[0]) {
          localStorage.setItem("operator_terminal", data[0].id);
          setParams({ terminal: data[0].id });
        }
      } catch {
        setError("Falha ao carregar terminais.");
      }
    })();
  }, [tokenReady, queueId, terminalId, setParams]);

  useEffect(() => {
    if (terminalId) localStorage.setItem("operator_terminal", terminalId);
  }, [terminalId]);

  useEffect(() => {
    void loadPanel();
    const id = window.setInterval(() => void loadPanel(), 4000);
    return () => window.clearInterval(id);
  }, [loadPanel]);

  useEffect(() => {
    if (!panel?.serving) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, [panel?.serving?.id]);

  async function run(action: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      await action();
      await loadPanel();
    } catch {
      setError("Operação não concluída. Tente novamente.");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function selectTerminal(id: string) {
    localStorage.setItem("operator_terminal", id);
    setParams({ terminal: id });
  }

  if (!tokenReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-brand-900 px-4 text-white">
        <form onSubmit={login} className="w-full max-w-md border border-white/20 bg-white/10 p-8 backdrop-blur">
          <h1 className="font-display text-3xl font-semibold">Botoeira</h1>
          <p className="mt-1 text-sm text-brand-100">Identificação do operador</p>
          <label className="mt-6 block text-sm">
            E-mail
            <input
              className="mt-1 w-full border border-white/20 bg-brand-900/40 px-3 py-2 text-white outline-none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </label>
          <label className="mt-4 block text-sm">
            Senha
            <input
              className="mt-1 w-full border border-white/20 bg-brand-900/40 px-3 py-2 text-white outline-none"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />
          </label>
          {loginError && <p className="mt-4 text-sm text-amber-200">{loginError}</p>}
          <button type="submit" className="mt-6 w-full bg-white py-3 font-semibold text-brand-900">
            Entrar
          </button>
        </form>
      </div>
    );
  }

  const serving = panel?.serving;

  return (
    <div className="flex min-h-screen flex-col bg-ink text-white">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div>
          <p className="font-display text-2xl font-semibold">{panel?.name || "Açougue"}</p>
          <p className="text-sm text-white/70">Terminal operacional</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="border border-white/20 bg-transparent px-3 py-2 text-sm"
            value={terminalId}
            onChange={(e) => selectTerminal(e.target.value)}
          >
            <option value="">Selecione o balcão</option>
            {terminals.map((t) => (
              <option key={t.id} value={t.id} className="text-ink">
                {t.code} — {t.name}
              </option>
            ))}
          </select>
          <Link to="/" className="text-sm text-white/70 underline-offset-2 hover:underline">
            Admin
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-5 px-4 py-6">
        {error && (
          <p className="border border-red-400/40 bg-red-500/20 px-4 py-3 text-sm" role="alert">
            {error}
          </p>
        )}

        <section className="rounded-2xl bg-white px-6 py-10 text-center text-ink">
          <p className="text-sm uppercase tracking-[0.2em] text-brand-700">Atendendo</p>
          <p className="mt-3 font-display text-7xl font-bold tracking-tight">{serving?.number || "—"}</p>
          <p className="mt-4 font-display text-4xl tabular-nums text-brand-700">{formatElapsed(elapsed)}</p>
          {serving && (
            <p className="mt-2 text-sm text-ink/60">
              {serving.type === "PRIORITY" || serving.type === "PRIORITY_PLUS" ? "Prioritária" : "Normal"} ·{" "}
              {serving.status}
            </p>
          )}
        </section>

        <button
          type="button"
          disabled={busy || !terminalId}
          onClick={() =>
            void run(async () => {
              await api.post(
                `/queues/${queueId}/next`,
                { terminal_id: terminalId, auto_complete_current: true, auto_start: true },
                { headers: { "Idempotency-Key": crypto.randomUUID() } },
              );
            })
          }
          className="min-h-[110px] rounded-2xl bg-brand-500 text-2xl font-bold tracking-wide disabled:opacity-50"
        >
          PRÓXIMA SENHA
        </button>

        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            disabled={busy || !serving || !terminalId}
            onClick={() =>
              void run(async () => {
                if (!serving) return;
                await api.post(`/tickets/${serving.id}/recall`, {
                  terminal_id: terminalId,
                });
              })
            }
            className="min-h-[80px] rounded-2xl border-2 border-white/30 text-xl font-semibold disabled:opacity-40"
          >
            RECHAMAR
          </button>
          <button
            type="button"
            disabled={busy || !serving || !terminalId}
            onClick={() =>
              void run(async () => {
                if (!serving) return;
                await api.post(`/tickets/${serving.id}/no-show`, {
                  terminal_id: terminalId,
                });
              })
            }
            className="min-h-[80px] rounded-2xl border-2 border-amber-300/70 text-xl font-semibold text-amber-200 disabled:opacity-40"
          >
            AUSENTE
          </button>
        </div>

        <button
          type="button"
          disabled={busy || !serving || !terminalId}
          onClick={() =>
            void run(async () => {
              if (!serving) return;
              await api.post(`/tickets/${serving.id}/complete`, {
                terminal_id: terminalId,
              });
            })
          }
          className="min-h-[72px] rounded-2xl bg-white/10 text-lg font-semibold disabled:opacity-40"
        >
          FINALIZAR ATENDIMENTO
        </button>
      </main>

      <footer className="border-t border-white/10 px-5 py-4 text-center text-white/80">
        <p className="text-lg">
          Fila · <strong>{panel?.waiting_count ?? "—"}</strong> aguardando ·{" "}
          <strong>{panel?.priority_waiting ?? "—"}</strong> prioritárias
        </p>
      </footer>
    </div>
  );
}
