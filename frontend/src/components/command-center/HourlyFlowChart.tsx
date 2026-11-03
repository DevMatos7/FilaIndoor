import { useMemo } from "react";

type HourPoint = { hour: number; issued: number; completed: number };

export default function HourlyFlowChart({ hourly }: { hourly: HourPoint[] }) {
  const points = useMemo(() => {
    const active = hourly.filter((h) => h.issued > 0 || h.completed > 0);
    return active.length > 0 ? active : hourly.slice(8, 21);
  }, [hourly]);

  const max = Math.max(1, ...points.map((h) => Math.max(h.issued, h.completed)));
  const totalIssued = points.reduce((a, h) => a + h.issued, 0);
  const totalCompleted = points.reduce((a, h) => a + h.completed, 0);
  const summary = `Fluxo do dia: ${totalIssued} senhas emitidas e ${totalCompleted} atendimentos concluídos nas horas exibidas.`;

  return (
    <div>
      <p className="sr-only">{summary}</p>
      <div className="flex h-44 items-end gap-1" role="img" aria-label={summary}>
        {points.map((h) => (
          <div key={h.hour} className="flex flex-1 flex-col items-center justify-end gap-1">
            <div className="flex h-36 w-full items-end justify-center gap-0.5">
              <div
                className="w-1/2 rounded-t-sm bg-brand-300"
                style={{ height: `${(h.issued / max) * 100}%`, minHeight: h.issued ? 3 : 0 }}
                title={`${String(h.hour).padStart(2, "0")}h · Emitidas ${h.issued}`}
              />
              <div
                className="w-1/2 rounded-t-sm bg-brand-700"
                style={{
                  height: `${(h.completed / max) * 100}%`,
                  minHeight: h.completed ? 3 : 0,
                }}
                title={`${String(h.hour).padStart(2, "0")}h · Atendidas ${h.completed}`}
              />
            </div>
            <span className="text-[10px] tabular-nums text-ink/50">
              {String(h.hour).padStart(2, "0")}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink/60">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2 w-3 rounded-sm bg-brand-300" aria-hidden />
          Emitidas
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2 w-3 rounded-sm bg-brand-700" aria-hidden />
          Atendidas
        </span>
        <span className="text-ink/45">
          Total {totalIssued} emitidas · {totalCompleted} atendidas
        </span>
      </div>
    </div>
  );
}
