import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { enqueueLocal, flushLocalOutbox, loadCache, saveCache } from "../services/edgeOffline";

type TotemState =
  | "idle"
  | "processing"
  | "success"
  | "printer_error"
  | "server_error"
  | "offline";

type QueueStatus = {
  name: string;
  department_name?: string;
  store_id?: string | null;
  waiting_count: number;
  estimated_wait_seconds: number;
  status: string;
};

type IssueResponse = {
  ticket: {
    id: string;
    number: string;
    type: string;
    people_ahead?: number;
    estimated_wait_seconds?: number;
  };
  print: {
    ok: boolean;
    message?: string;
    provider?: string;
  };
  department_name?: string;
};

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";

function waitLabel(seconds: number) {
  return `${Math.max(1, Math.round(seconds / 60))} min`;
}

export default function Totem() {
  const { queueId } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || localStorage.getItem("kiosk_token") || "";
  const [state, setState] = useState<TotemState>("idle");
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [issued, setIssued] = useState<IssueResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const busyRef = useRef(false);
  const resetTimer = useRef<number | null>(null);

  useEffect(() => {
    if (token) localStorage.setItem("kiosk_token", token);
  }, [token]);

  const loadStatus = useCallback(async () => {
    if (!queueId || !token) return;
    if (!navigator.onLine) {
      const cached = loadCache<QueueStatus>("kiosk_status", queueId, 30 * 60 * 1000);
      if (cached) setStatus(cached);
      setState((s) => (s === "processing" || s === "success" || s === "printer_error" ? s : "offline"));
      return;
    }
    try {
      const { data } = await axios.get<QueueStatus>(`${apiBase}/kiosk/${queueId}/status`, {
        headers: { "X-Kiosk-Token": token },
        timeout: 8000,
      });
      setStatus(data);
      saveCache("kiosk_status", queueId, data);
      setState((s) => (s === "offline" || s === "server_error" ? "idle" : s));
      void flushLocalOutbox().catch(() => undefined);
    } catch {
      const cached = loadCache<QueueStatus>("kiosk_status", queueId, 30 * 60 * 1000);
      if (cached) {
        setStatus(cached);
        setState((s) => (s === "processing" || s === "success" || s === "printer_error" ? s : "offline"));
      } else {
        setState((s) => (s === "processing" || s === "success" || s === "printer_error" ? s : "server_error"));
      }
    }
  }, [queueId, token]);

  useEffect(() => {
    void loadStatus();
    const id = window.setInterval(() => void loadStatus(), 8000);
    const onOnline = () => void loadStatus();
    const onOffline = () => setState("offline");
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      if (resetTimer.current) window.clearTimeout(resetTimer.current);
    };
  }, [loadStatus]);

  function scheduleIdle(ms = 4500) {
    if (resetTimer.current) window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => {
      setIssued(null);
      setMessage(null);
      busyRef.current = false;
      setState("idle");
      void loadStatus();
    }, ms);
  }

  async function issue(type: "NORMAL" | "PRIORITY") {
    if (!queueId || !token || busyRef.current) return;
    if (!navigator.onLine) {
      setState("offline");
      return;
    }

    busyRef.current = true;
    setState("processing");
    setMessage(null);
    setIssued(null);

    const idempotencyKey = crypto.randomUUID();

    try {
      const { data } = await axios.post<IssueResponse>(
        `${apiBase}/kiosk/${queueId}/tickets`,
        { type, source: "KIOSK" },
        {
          headers: {
            "X-Kiosk-Token": token,
            "Idempotency-Key": idempotencyKey,
          },
          timeout: 15000,
        },
      );
      setIssued(data);
      if (data.print?.ok) {
        setState("success");
        setMessage("Imprimindo...");
      } else {
        setState("printer_error");
        setMessage(data.print?.message || "Não foi possível imprimir.");
      }
      scheduleIdle(data.print?.ok ? 4000 : 7000);
      void loadStatus();
    } catch {
      if (status?.store_id) {
        enqueueLocal({
          store_id: status.store_id,
          event_type: "TICKET_ISSUE",
          origin_device: "kiosk",
          event_id: idempotencyKey,
          payload: { queue_id: queueId, type, source: "KIOSK", deferred: true },
        });
        setState("offline");
        setMessage("Sem conexão com o edge. Pedido guardado para sincronizar.");
      } else {
        setState("server_error");
        setMessage("Atendimento temporariamente indisponível. Procure um colaborador.");
      }
      busyRef.current = false;
      scheduleIdle(5000);
    }
  }

  const dept = status?.department_name || issued?.department_name || "Açougue";
  const blocked = state === "processing" || state === "success" || state === "printer_error";

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-brand-900 via-brand-700 to-brand-900 text-white">
      <header className="px-6 py-5 text-center">
        <p className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">REAL</p>
        <p className="mt-1 text-lg uppercase tracking-[0.2em] text-brand-100">{dept}</p>
        <p className="mt-2 text-sm text-brand-100/80">
          {status?.status === "OPEN" || !status ? "Operação aberta" : `Fila: ${status.status}`}
        </p>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-5 px-4 pb-8">
        {state === "idle" && (
          <>
            <button
              type="button"
              disabled={blocked}
              onClick={() => void issue("NORMAL")}
              className="min-h-[140px] rounded-2xl bg-white px-6 py-8 text-center text-brand-900 shadow-lg transition active:scale-[0.99] disabled:opacity-60"
            >
              <span className="block font-display text-3xl font-bold sm:text-4xl">SENHA NORMAL</span>
              <span className="mt-2 block text-base text-ink/70">Atendimento convencional</span>
            </button>
            <button
              type="button"
              disabled={blocked}
              onClick={() => void issue("PRIORITY")}
              className="min-h-[140px] rounded-2xl border-4 border-amber-300 bg-amber-400 px-6 py-8 text-center text-brand-900 shadow-lg transition active:scale-[0.99] disabled:opacity-60"
              aria-label="Senha prioritária — atendimento preferencial"
            >
              <span className="block font-display text-3xl font-bold sm:text-4xl">SENHA PRIORITÁRIA</span>
              <span className="mt-2 block text-base font-medium text-brand-900/80">
                Preferencial — claramente identificada
              </span>
            </button>
          </>
        )}

        {state === "processing" && (
          <div className="rounded-2xl bg-white/10 px-6 py-16 text-center backdrop-blur">
            <p className="font-display text-3xl font-semibold">Emitindo sua senha...</p>
            <p className="mt-3 text-brand-100">Aguarde, não toque novamente.</p>
          </div>
        )}

        {state === "success" && issued && (
          <div className="rounded-2xl bg-white px-6 py-12 text-center text-brand-900">
            <p className="text-lg uppercase tracking-wide text-brand-700">Sua senha é</p>
            <p className="mt-2 font-display text-7xl font-bold">{issued.ticket.number}</p>
            <p className="mt-4 text-xl">{message || "Imprimindo..."}</p>
          </div>
        )}

        {state === "printer_error" && issued && (
          <div className="rounded-2xl border-2 border-amber-300 bg-amber-50 px-6 py-10 text-center text-brand-900">
            <p className="text-lg">Sua senha <strong>{issued.ticket.number}</strong> foi registrada.</p>
            <p className="mt-4 text-xl font-semibold">Não foi possível imprimir.</p>
            <p className="mt-2 text-base text-ink/80">Solicite ajuda a um colaborador.</p>
            {message && <p className="mt-3 text-sm text-ink/60">{message}</p>}
          </div>
        )}

        {state === "offline" && (
          <div className="rounded-2xl bg-white/10 px-6 py-12 text-center">
            <p className="font-display text-2xl font-semibold">Sistema operando localmente</p>
            <p className="mt-3 text-brand-100">Sem conexão no momento. A operação será retomada automaticamente.</p>
          </div>
        )}

        {state === "server_error" && (
          <div className="rounded-2xl bg-red-50 px-6 py-12 text-center text-red-900">
            <p className="font-display text-2xl font-semibold">Atendimento temporariamente indisponível.</p>
            <p className="mt-3">{message || "Procure um colaborador."}</p>
          </div>
        )}
      </main>

      <footer className="px-6 pb-8 text-center text-brand-100">
        {status ? (
          <>
            <p className="text-lg font-medium">{status.waiting_count} pessoas aguardando</p>
            <p className="mt-1 text-base">Espera aproximada: {waitLabel(status.estimated_wait_seconds)}</p>
          </>
        ) : (
          <p className="text-sm opacity-80">Carregando informações da fila…</p>
        )}
        {!token && <p className="mt-3 text-sm text-amber-200">Token do totem ausente na URL (?token=…)</p>}
      </footer>
    </div>
  );
}
