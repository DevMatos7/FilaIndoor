import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { loadCache, readOutbox } from "../services/edgeOffline";
import type { QueueStatus } from "../components/totem/types";

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";
const APP_VERSION = "0.1.0";

function maskToken(token: string): string {
  if (!token) return "AUSENTE";
  if (token.length <= 6) return "CONFIGURADO (••••)";
  return `CONFIGURADO (${token.slice(0, 2)}•••${token.slice(-2)})`;
}

/**
 * Diagnóstico TI — requer sessão admin (localStorage token).
 * Não exibe segredos completos.
 */
export default function TotemDiagnostics() {
  const { queueId } = useParams();
  const [params] = useSearchParams();
  const adminToken = localStorage.getItem("token");
  const kioskToken = params.get("token") || localStorage.getItem("kiosk_token") || "";

  const [online, setOnline] = useState(navigator.onLine);
  const [apiOk, setApiOk] = useState<"ok" | "fail" | "checking">("checking");
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const outbox = useMemo(() => readOutbox(), [online, apiOk]);
  const cached = queueId ? loadCache<QueueStatus>("kiosk_status", queueId, 30 * 60 * 1000) : null;

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const healthBase = apiBase.replace(/\/api\/v1\/?$/, "");
        const res = await fetch(`${healthBase}/health`, { cache: "no-store" });
        if (alive) setApiOk(res.ok ? "ok" : "fail");
      } catch {
        if (alive) setApiOk("fail");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!queueId || !kioskToken) return;
    let alive = true;
    (async () => {
      try {
        const { data } = await axios.get<QueueStatus>(`${apiBase}/kiosk/${queueId}/status`, {
          headers: { "X-Kiosk-Token": kioskToken },
          timeout: 8000,
        });
        if (alive) {
          setStatus(data);
          setStatusError(null);
        }
      } catch (err: unknown) {
        if (!alive) return;
        const msg =
          axios.isAxiosError(err) && err.response?.status === 403
            ? "Token kiosk inválido ou totem desabilitado"
            : "Falha ao consultar status da fila";
        setStatusError(msg);
      }
    })();
    return () => {
      alive = false;
    };
  }, [queueId, kioskToken]);

  if (!adminToken) {
    return <Navigate to="/login" replace />;
  }

  const rows: Array<{ label: string; value: string }> = [
    { label: "Totem", value: "FilaIndoor Kiosk 2.0" },
    { label: "Queue ID", value: queueId || "—" },
    { label: "Fila / departamento", value: status?.department_name || status?.name || cached?.department_name || cached?.name || "—" },
    { label: "Status da fila", value: status?.status || cached?.status || "—" },
    { label: "Aguardando", value: String(status?.waiting_count ?? cached?.waiting_count ?? "—") },
    { label: "API base", value: apiBase },
    { label: "API health", value: apiOk === "checking" ? "…" : apiOk === "ok" ? "OK" : "FALHA" },
    { label: "Navegador online", value: online ? "sim" : "não" },
    { label: "Edge outbox (local)", value: `${outbox.length} evento(s)` },
    { label: "Cache status", value: cached ? "presente" : "ausente" },
    { label: "Store ID (cache)", value: status?.store_id || cached?.store_id || "—" },
    { label: "Kiosk token", value: maskToken(kioskToken) },
    { label: "Impressora", value: "via API kiosk (provider no servidor)" },
    { label: "App version", value: APP_VERSION },
    { label: "Last sync", value: outbox[0]?.occurred_at || "— (outbox vazio ou já enviado)" },
  ];

  return (
    <div className="min-h-[100dvh] bg-surface-muted p-4 font-sans text-ink sm:p-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">Diagnóstico</p>
            <h1 className="text-2xl font-semibold text-brand-900">Totem</h1>
          </div>
          <Link
            to={`/totem/${queueId}${kioskToken ? `?token=${encodeURIComponent(kioskToken)}` : ""}`}
            className="rounded-ds border border-brand-200 bg-white px-3 py-2 text-sm font-semibold text-brand-800 hover:bg-brand-50"
          >
            Voltar ao totem
          </Link>
        </div>

        {statusError && (
          <p className="mb-3 rounded-ds border border-semantic-warning-border bg-semantic-warning-bg px-3 py-2 text-sm text-semantic-warning">
            {statusError}
          </p>
        )}

        <dl className="divide-y divide-brand-100 overflow-hidden rounded-ds border border-brand-100 bg-white shadow-ds">
          {rows.map((r) => (
            <div key={r.label} className="grid grid-cols-1 gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink/50">{r.label}</dt>
              <dd className="break-all font-mono text-sm text-brand-900 sm:col-span-2">{r.value}</dd>
            </div>
          ))}
        </dl>

        <p className="mt-4 text-xs text-ink/50">
          Rota protegida por sessão administrativa. Tokens e segredos nunca são exibidos por completo.
        </p>
      </div>
    </div>
  );
}
