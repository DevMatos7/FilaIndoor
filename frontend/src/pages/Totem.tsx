import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { enqueueLocal, flushLocalOutbox, loadCache, saveCache } from "../services/edgeOffline";
import { TotemBoot } from "../components/totem/TotemBoot";
import { TotemHeader } from "../components/totem/TotemHeader";
import { TotemShell } from "../components/totem/TotemShell";
import { TotemStatusInfo } from "../components/totem/TotemStatusInfo";
import { ServiceChoice } from "../components/totem/ServiceChoice";
import { TicketSuccess } from "../components/totem/TicketSuccess";
import { TotemError } from "../components/totem/TotemError";
import { TotemProcessing } from "../components/totem/TotemProcessing";
import { TotemUnavailable } from "../components/totem/TotemUnavailable";
import type { IssueResponse, QueueStatus, TotemUiState } from "../components/totem/types";

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";
const STATUS_POLL_MS = 30_000;

/**
 * State machine (preservada + closed/unavailable derivados):
 * boot → idle → processing → success → idle
 *                 ↘ printer_error → idle
 *                 ↘ server_error → idle/retry
 * offline / closed / unavailable → sem emissão
 */
export default function Totem() {
  const { queueId } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || localStorage.getItem("kiosk_token") || "";
  const [state, setState] = useState<TotemUiState>("boot");
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [issued, setIssued] = useState<IssueResponse | null>(null);
  const [booted, setBooted] = useState(false);
  const busyRef = useRef(false);
  const resetTimer = useRef<number | null>(null);

  useEffect(() => {
    if (token) localStorage.setItem("kiosk_token", token);
  }, [token]);

  const clearReset = () => {
    if (resetTimer.current) {
      window.clearTimeout(resetTimer.current);
      resetTimer.current = null;
    }
  };

  const scheduleIdle = useCallback(
    (ms = 4500) => {
      clearReset();
      resetTimer.current = window.setTimeout(() => {
        setIssued(null);
        busyRef.current = false;
        setState((s) => {
          if (s === "closed" || s === "unavailable") return s;
          return "idle";
        });
        void loadStatusRef.current();
      }, ms);
    },
    [],
  );

  const loadStatusRef = useRef<() => Promise<void>>(async () => undefined);

  const loadStatus = useCallback(async () => {
    if (!queueId) return;
    if (!token) {
      setBooted(true);
      setState((s) =>
        s === "processing" || s === "success" || s === "printer_error" ? s : "unavailable",
      );
      return;
    }

    if (!navigator.onLine) {
      const cached = loadCache<QueueStatus>("kiosk_status", queueId, 30 * 60 * 1000);
      if (cached) setStatus(cached);
      setBooted(true);
      setState((s) =>
        s === "processing" || s === "success" || s === "printer_error" ? s : "offline",
      );
      return;
    }

    try {
      const { data } = await axios.get<QueueStatus>(`${apiBase}/kiosk/${queueId}/status`, {
        headers: { "X-Kiosk-Token": token },
        timeout: 8000,
      });
      setStatus(data);
      saveCache("kiosk_status", queueId, data);
      setBooted(true);
      setState((s) => {
        if (s === "processing" || s === "success" || s === "printer_error") return s;
        if (data.status === "CLOSED") return "closed";
        if (data.status !== "OPEN") return "closed"; // PAUSED etc. — backend só emite OPEN
        if (s === "offline" || s === "server_error" || s === "unavailable" || s === "boot" || s === "closed") {
          return "idle";
        }
        return s === "idle" ? "idle" : s;
      });
      void flushLocalOutbox().catch(() => undefined);
    } catch {
      const cached = loadCache<QueueStatus>("kiosk_status", queueId, 30 * 60 * 1000);
      setBooted(true);
      if (cached) {
        setStatus(cached);
        if (!navigator.onLine) {
          setState((s) =>
            s === "processing" || s === "success" || s === "printer_error" ? s : "offline",
          );
        } else {
          // Mantém idle se possível — não bloqueia emissão por falha de refresh
          setState((s) => {
            if (s === "processing" || s === "success" || s === "printer_error") return s;
            if (s === "boot" || s === "offline" || s === "server_error" || s === "unavailable") {
              return cached.status === "OPEN" ? "idle" : "closed";
            }
            return s;
          });
        }
      } else {
        setState((s) =>
          s === "processing" || s === "success" || s === "printer_error" ? s : "server_error",
        );
      }
    }
  }, [queueId, token]);

  loadStatusRef.current = loadStatus;

  useEffect(() => {
    void loadStatus();
    const id = window.setInterval(() => void loadStatus(), STATUS_POLL_MS);
    const onOnline = () => void loadStatus();
    const onOffline = () =>
      setState((s) =>
        s === "processing" || s === "success" || s === "printer_error" ? s : "offline",
      );
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      clearReset();
    };
  }, [loadStatus]);

  async function issue(type: "NORMAL" | "PRIORITY") {
    if (!queueId || !token || busyRef.current) return;
    if (status && status.status !== "OPEN") {
      setState("closed");
      return;
    }
    if (!navigator.onLine) {
      // Sem backend nem emissão local com número — indisponível comercial
      setState("offline");
      return;
    }

    busyRef.current = true;
    setState("processing");
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
      } else {
        setState("printer_error");
      }
      scheduleIdle(data.print?.ok ? 4000 : 7000);
      void loadStatus();
    } catch {
      // Outbox preservado — cliente não vê termos Edge/API
      if (status?.store_id) {
        enqueueLocal({
          store_id: status.store_id,
          event_type: "TICKET_ISSUE",
          origin_device: "kiosk",
          event_id: idempotencyKey,
          payload: { queue_id: queueId, type, source: "KIOSK", deferred: true },
        });
      }
      setState("server_error");
      busyRef.current = false;
      scheduleIdle(8000);
    }
  }

  function handleRetry() {
    if (busyRef.current) return;
    clearReset();
    setIssued(null);
    setState("idle");
    void loadStatus();
  }

  const dept = status?.department_name || issued?.department_name || status?.name || "Atendimento";
  const blocked =
    state === "processing" || state === "success" || state === "printer_error" || busyRef.current;
  const showBoot = !booted && state === "boot";

  return (
    <TotemShell>
      {showBoot ? (
        <TotemBoot />
      ) : (
        <>
          <TotemHeader
            department={dept}
            prompt={state === "idle" ? "Como deseja ser atendido?" : undefined}
          />

          <main className="safe-totem-x mx-auto flex w-full max-w-xl flex-1 flex-col justify-center gap-5 px-5 pb-4">
            {state === "idle" && (
              <ServiceChoice
                disabled={blocked}
                waitingCount={status?.waiting_count}
                estimatedWaitSeconds={status?.estimated_wait_seconds}
                onNormal={() => void issue("NORMAL")}
                onPriority={() => void issue("PRIORITY")}
              />
            )}

            {state === "processing" && <TotemProcessing />}

            {state === "success" && issued && (
              <TicketSuccess
                number={issued.ticket.number}
                priority={issued.ticket.type === "PRIORITY" || issued.ticket.type === "PRIORITY_PLUS"}
                printed
              />
            )}

            {state === "printer_error" && issued && (
              <TotemError variant="printer" ticketNumber={issued.ticket.number} />
            )}

            {state === "server_error" && (
              <TotemError variant="server" onRetry={handleRetry} />
            )}

            {state === "offline" && (
              <TotemUnavailable
                title="Atendimento temporariamente indisponível"
                description="Procure um colaborador."
              />
            )}

            {state === "closed" && (
              <TotemUnavailable
                title={
                  status?.status === "PAUSED"
                    ? "Atendimento pausado neste momento"
                    : "Atendimento encerrado neste momento"
                }
                description="Procure um colaborador se precisar de ajuda."
              />
            )}

            {state === "unavailable" && (
              <TotemUnavailable
                title="Atendimento temporariamente indisponível"
                description="Procure um colaborador."
              />
            )}
          </main>

          {(state === "idle" || state === "processing") && (
            <TotemStatusInfo
              hint={
                state === "processing"
                  ? "Estamos preparando sua senha."
                  : "Retire sua senha e continue suas compras normalmente."
              }
            />
          )}
        </>
      )}
    </TotemShell>
  );
}
