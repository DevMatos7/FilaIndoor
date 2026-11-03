import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import api from "../services/api";
import { OperatorShell } from "../components/operator/OperatorShell";
import { OperatorHeader } from "../components/operator/OperatorHeader";
import { OperatorLogin } from "../components/operator/OperatorLogin";
import { TerminalSelector } from "../components/operator/TerminalSelector";
import { CurrentTicket } from "../components/operator/CurrentTicket";
import { PrimaryAction } from "../components/operator/PrimaryAction";
import { SecondaryActions } from "../components/operator/SecondaryActions";
import { QueueSummary } from "../components/operator/QueueSummary";
import { OperatorFeedback } from "../components/operator/OperatorFeedback";
import {
  ActionKind,
  OperatorPanel,
  TERMINAL_STORAGE_KEY,
  Terminal,
  terminalLabel,
} from "../components/operator/types";

/**
 * Operator 2.0 — botoeira digital.
 * Contratos preservados:
 * NEXT  POST /queues/:id/next { terminal_id, auto_complete_current: true, auto_start: true }
 * RECALL / NO_SHOW / COMPLETE  POST /tickets/:id/{recall|no-show|complete}
 *
 * Nota: auto_complete_current já era contrato do frontend anterior (não inventado nesta sprint).
 */
export default function Operator() {
  const { queueId } = useParams();
  const [params, setParams] = useSearchParams();
  const terminalFromUrl = params.get("terminal") || "";

  const [tokenReady, setTokenReady] = useState(!!localStorage.getItem("token"));
  const [loginError, setLoginError] = useState<string | null>(null);
  const [pickingTerminal, setPickingTerminal] = useState(false);

  const [terminals, setTerminals] = useState<Terminal[]>([]);
  const [deptName, setDeptName] = useState<string>("");
  const [panel, setPanel] = useState<OperatorPanel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connectionWarn, setConnectionWarn] = useState(false);
  const [feedback, setFeedback] = useState<{ message: string; variant: "success" | "info" } | null>(
    null,
  );
  const [busyAction, setBusyAction] = useState<ActionKind>(null);
  const [tick, setTick] = useState(0);

  const busyRef = useRef(false);
  const feedbackTimer = useRef<number | null>(null);
  const panelRef = useRef<OperatorPanel | null>(null);

  const terminalId =
    terminalFromUrl ||
    (typeof window !== "undefined" ? localStorage.getItem(TERMINAL_STORAGE_KEY) || "" : "");

  const selectedTerminal = useMemo(
    () => terminals.find((t) => t.id === terminalId) || null,
    [terminals, terminalId],
  );

  useEffect(() => {
    panelRef.current = panel;
  }, [panel]);

  const flash = useCallback((message: string, variant: "success" | "info" = "success") => {
    if (feedbackTimer.current) window.clearTimeout(feedbackTimer.current);
    setFeedback({ message, variant });
    feedbackTimer.current = window.setTimeout(() => setFeedback(null), 2200);
  }, []);

  async function login(email: string, password: string) {
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
      // Terminal: reutiliza localStorage se ainda válido (reduz etapas no uso recorrente).
    } catch {
      setLoginError("Não foi possível entrar. Verifique usuário e senha.");
    }
  }

  function logout() {
    localStorage.removeItem("token");
    setTokenReady(false);
    setPanel(null);
    setError(null);
    setPickingTerminal(false);
  }

  function selectTerminal(id: string) {
    localStorage.setItem(TERMINAL_STORAGE_KEY, id);
    setParams({ terminal: id });
    setPickingTerminal(false);
  }

  function switchTerminal() {
    setPickingTerminal(true);
  }

  const loadPanel = useCallback(async () => {
    if (!queueId || !terminalId || !tokenReady || pickingTerminal) return;
    try {
      const { data } = await api.get<OperatorPanel>(`/queues/${queueId}/operator-panel`, {
        params: { terminal_id: terminalId },
      });
      setPanel(data);
      setError(null);
      setConnectionWarn(false);
      setTick(0);
    } catch {
      if (panelRef.current) {
        setConnectionWarn(true);
      } else {
        setError("Não foi possível carregar o atendimento.");
      }
    }
  }, [queueId, terminalId, tokenReady, pickingTerminal]);

  useEffect(() => {
    if (!tokenReady || !queueId) return;
    let alive = true;
    (async () => {
      try {
        const q = await api.get<{
          department_id: string;
          name: string;
          department_display_name?: string | null;
        }>(`/queues/${queueId}`);
        if (!alive) return;
        setDeptName(q.data.department_display_name || q.data.name);
        const { data } = await api.get<Terminal[]>("/terminals", {
          params: { department_id: q.data.department_id },
        });
        if (!alive) return;
        setTerminals(data);

        const stored = localStorage.getItem(TERMINAL_STORAGE_KEY) || "";
        const urlTerm = params.get("terminal") || "";
        const candidate = urlTerm || stored;
        const valid = data.some((t) => t.id === candidate);

        if (data.length === 1) {
          localStorage.setItem(TERMINAL_STORAGE_KEY, data[0].id);
          setParams({ terminal: data[0].id });
          setPickingTerminal(false);
          return;
        }
        if (valid) {
          if (urlTerm !== candidate) setParams({ terminal: candidate });
          setPickingTerminal(false);
          return;
        }
        setPickingTerminal(true);
      } catch {
        if (alive) setError("Não foi possível carregar os balcões.");
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokenReady, queueId]);

  useEffect(() => {
    if (terminalId) localStorage.setItem(TERMINAL_STORAGE_KEY, terminalId);
  }, [terminalId]);

  useEffect(() => {
    if (!terminalId || pickingTerminal) return;
    void loadPanel();
    const id = window.setInterval(() => void loadPanel(), 4000);
    return () => window.clearInterval(id);
  }, [loadPanel, terminalId, pickingTerminal]);

  useEffect(() => {
    if (!panel?.serving) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, [panel?.serving?.id]);

  useEffect(() => {
    return () => {
      if (feedbackTimer.current) window.clearTimeout(feedbackTimer.current);
    };
  }, []);

  const elapsed = useMemo(() => {
    if (panel?.elapsed_seconds == null) return null;
    return (panel.elapsed_seconds || 0) + tick;
  }, [panel, tick]);

  async function run(kind: ActionKind, action: () => Promise<void>, successMessage: string) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusyAction(kind);
    setError(null);
    try {
      await action();
      await loadPanel();
      flash(successMessage);
    } catch {
      setError("Não foi possível executar a ação. Tente novamente.");
    } finally {
      busyRef.current = false;
      setBusyAction(null);
    }
  }

  if (!tokenReady) {
    return <OperatorLogin onSubmit={login} error={loginError} />;
  }

  if (pickingTerminal || !terminalId || !selectedTerminal) {
    return (
      <TerminalSelector
        terminals={terminals}
        departmentName={deptName || panel?.name}
        onSelect={selectTerminal}
        onLogout={logout}
      />
    );
  }

  const serving = panel?.serving ?? null;
  const queueStatus = panel?.status || "OPEN";
  const closed = queueStatus === "CLOSED";
  const paused = queueStatus === "PAUSED";
  const waiting = panel?.waiting_count ?? 0;
  const priority = panel?.priority_waiting ?? 0;
  const emptyQueue = waiting === 0;
  const nextDisabled = closed || paused || emptyQueue || !!busyAction;

  const derivedState: "PRONTO" | "ATENDENDO" | "ENCERRADO" | "PAUSADO" = closed
    ? "ENCERRADO"
    : paused
      ? "PAUSADO"
      : serving
        ? "ATENDENDO"
        : "PRONTO";

  const department = deptName || panel?.name || "Atendimento";

  return (
    <OperatorShell>
      <OperatorHeader
        department={department}
        terminalName={selectedTerminal ? terminalLabel(selectedTerminal) : null}
        derivedState={derivedState}
        onSwitchTerminal={switchTerminal}
        onLogout={logout}
      />

      <main className="safe-op-x mx-auto flex w-full max-w-xl flex-1 flex-col gap-4 px-4 py-4 sm:py-5">
        {connectionWarn && (
          <OperatorFeedback message="Conexão instável — exibindo último estado." variant="warning" />
        )}
        {error && <OperatorFeedback message={error} variant="danger" />}
        {feedback && <OperatorFeedback message={feedback.message} variant={feedback.variant} />}

        {closed && (
          <OperatorFeedback
            message="Atendimento encerrado. Ações de chamada indisponíveis."
            variant="warning"
          />
        )}
        {paused && !closed && (
          <OperatorFeedback
            message="Fila pausada. Aguarde liberação operacional."
            variant="warning"
          />
        )}

        <CurrentTicket serving={serving} elapsed={elapsed} />

        {!closed && !paused && (
          <>
            <PrimaryAction
              disabled={nextDisabled}
              busy={busyAction === "next"}
              onClick={() =>
                void run(
                  "next",
                  async () => {
                    await api.post(
                      `/queues/${queueId}/next`,
                      {
                        terminal_id: terminalId,
                        auto_complete_current: true,
                        auto_start: true,
                      },
                      { headers: { "Idempotency-Key": crypto.randomUUID() } },
                    );
                  },
                  "Senha chamada",
                )
              }
            />

            <SecondaryActions
              hasTicket={!!serving}
              busy={!!busyAction}
              activeAction={
                busyAction === "recall" || busyAction === "no_show" || busyAction === "complete"
                  ? busyAction
                  : null
              }
              onRecall={() =>
                void run(
                  "recall",
                  async () => {
                    if (!serving) return;
                    await api.post(`/tickets/${serving.id}/recall`, { terminal_id: terminalId });
                  },
                  `Senha ${serving?.number || ""} rechamada`.trim(),
                )
              }
              onNoShow={() =>
                void run(
                  "no_show",
                  async () => {
                    if (!serving) return;
                    await api.post(`/tickets/${serving.id}/no-show`, { terminal_id: terminalId });
                  },
                  "Ausência registrada",
                )
              }
              onComplete={() =>
                void run(
                  "complete",
                  async () => {
                    if (!serving) return;
                    await api.post(`/tickets/${serving.id}/complete`, { terminal_id: terminalId });
                  },
                  "Atendimento finalizado",
                )
              }
            />
          </>
        )}
      </main>

      <QueueSummary waiting={waiting} priority={priority} empty={emptyQueue && !closed} />
    </OperatorShell>
  );
}
