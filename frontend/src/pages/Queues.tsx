import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { QueueSummary } from "../services/api";

export default function Queues() {
  const [queues, setQueues] = useState<QueueSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await api.get<QueueSummary[]>("/queues");
        if (alive) setQueues(data);
      } catch {
        if (alive) setError("Erro ao listar filas.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold text-brand-900">Filas</h1>
      <p className="mt-1 text-ink/70">Configuração e acompanhamento do core de atendimento.</p>

      {loading && <p className="mt-8 text-sm">Carregando…</p>}
      {error && (
        <p className="mt-8 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
      )}
      {!loading && !error && queues.length === 0 && (
        <p className="mt-8 text-sm text-ink/70">Nenhuma fila encontrada.</p>
      )}

      {!loading && queues.length > 0 && (
        <div className="mt-6 overflow-x-auto border border-brand-100 bg-white/80">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-brand-100 bg-brand-50 text-ink/80">
              <tr>
                <th className="px-4 py-3 font-medium">Nome</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Estratégia</th>
                <th className="px-4 py-3 font-medium">Ação</th>
              </tr>
            </thead>
            <tbody>
              {queues.map((q) => (
                <tr key={q.id} className="border-b border-brand-50">
                  <td className="px-4 py-3 font-medium">{q.name}</td>
                  <td className="px-4 py-3">{q.status}</td>
                  <td className="px-4 py-3">{q.priority_strategy}</td>
                  <td className="px-4 py-3">
                    <Link className="text-brand-700 underline-offset-2 hover:underline" to={`/queues/${q.id}`}>
                      Abrir
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
