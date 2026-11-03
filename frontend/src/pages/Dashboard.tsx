import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ListOrdered } from "lucide-react";
import {
  Alert,
  Card,
  CardContent,
  EmptyState,
  MetricCard,
  PageHeader,
  QueueStatus,
  SkeletonMetric,
} from "../design-system";
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
      <PageHeader
        title="Início"
        description="Visão rápida do dia e das filas ativas."
        actions={
          <Link
            to="/analytics"
            className="text-sm font-medium text-brand-700 underline-offset-2 hover:underline"
          >
            Ver analytics completo →
          </Link>
        }
      />

      {loading && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonMetric key={i} />
          ))}
        </div>
      )}

      {error && <Alert variant="danger">{error}</Alert>}

      {!loading && k && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          <MetricCard label="Atendimentos hoje" value={String(k.completed)} />
          <MetricCard label="Aguardando" value={String(k.waiting)} />
          <MetricCard label="Tempo médio espera" value={fmtSec(k.wait.avg_seconds)} />
          <MetricCard label="Tempo médio atendimento" value={fmtSec(k.service.avg_seconds)} />
          <MetricCard label="Maior espera" value={fmtSec(k.wait.max_seconds)} />
          <MetricCard label="Ausências" value={String(k.no_show)} />
        </div>
      )}

      {!loading && !error && queues.length === 0 && (
        <EmptyState
          icon={<ListOrdered className="h-8 w-8" aria-hidden />}
          title="Nenhuma fila cadastrada"
          description="Cadastre uma fila de atendimento para começar a acompanhar a operação da loja."
        />
      )}

      {queues.length > 0 && (
        <div>
          <h2 className="font-sans text-section-title text-brand-900">Filas</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {queues.map((q) => (
              <Link key={q.id} to={`/queues/${q.id}`} className="block">
                <Card interactive className="h-full">
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-sans text-lg font-semibold text-brand-900">{q.name}</h3>
                      <QueueStatus status={q.status} />
                    </div>
                    <p className="mt-2 text-sm text-ink/70">Estratégia: {q.priority_strategy}</p>
                    <p className="mt-1 text-sm text-ink/70">
                      Prefixos {q.normal_prefix} / {q.priority_prefix}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
