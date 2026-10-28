import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { QueueSummary } from "../services/api";

type Summary = {
  kpis: {
    issued: number;
    completed: number;
    waiting: number;
    no_show: number;
    wait: { avg_seconds: number | null; max_seconds: number | null };
    service: { avg_seconds: number | null };
  };
};

function fmtSec(v: number | null | undefined) {
  if (v == null) return "—";
  const m = Math.floor(v / 60);
  const s = Math.round(v % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function Dashboard() {
  const [queues, setQueues] = useState<QueueSummary[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [qs, an] = await Promise.all([
          api.get<QueueSummary[]>("/queues"),
          api.get<Summary>("/analytics/summary"),
        ]);
        if (alive) {
          setQueues(qs.data);
          setSummary(an.data);
        }
      } catch {
        if (alive) setError("Não foi possível carregar o dashboard.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const k = summary?.kpis;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-brand-900">Dashboard operacional</h1>
          <p className="mt-1 text-ink/70">Visão rápida do dia e das filas ativas.</p>
        </div>
        <Link to="/analytics" className="text-sm font-medium text-brand-700 underline-offset-2 hover:underline">
          Ver analytics completo →
        </Link>
      </div>

      {loading && <p className="text-sm text-ink/60">Carregando…</p>}
      {error && (
        <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      {!loading && k && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          {[
            { label: "Atendimentos hoje", value: String(k.completed) },
            { label: "Aguardando", value: String(k.waiting) },
            { label: "Tempo médio espera", value: fmtSec(k.wait.avg_seconds) },
            { label: "Tempo médio atendimento", value: fmtSec(k.service.avg_seconds) },
            { label: "Maior espera", value: fmtSec(k.wait.max_seconds) },
            { label: "Ausências", value: String(k.no_show) },
          ].map((card) => (
            <div key={card.label} className="border border-brand-100 bg-white/80 p-4">
              <p className="text-xs uppercase tracking-wide text-ink/55">{card.label}</p>
              <p className="mt-2 font-display text-3xl font-semibold text-brand-900">{card.value}</p>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && queues.length === 0 && (
        <div className="border border-dashed border-brand-500/40 bg-white/60 p-6">
          <p className="font-medium">Nenhuma fila cadastrada</p>
          <p className="mt-1 text-sm text-ink/70">Execute o seed do backend para criar a Fila Açougue.</p>
        </div>
      )}

      {queues.length > 0 && (
        <div>
          <h2 className="font-display text-xl font-semibold text-brand-900">Filas</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {queues.map((q) => (
              <Link
                key={q.id}
                to={`/queues/${q.id}`}
                className="border border-brand-100 bg-white/80 p-5 transition hover:border-brand-500"
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-display text-xl font-semibold">{q.name}</h3>
                  <span className="text-xs uppercase tracking-wide text-brand-700">{q.status}</span>
                </div>
                <p className="mt-2 text-sm text-ink/70">Estratégia: {q.priority_strategy}</p>
                <p className="mt-1 text-sm text-ink/70">
                  Prefixos {q.normal_prefix} / {q.priority_prefix}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
