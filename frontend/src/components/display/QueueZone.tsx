import type { DisplayTicket } from "./types";

type Props = {
  department: string;
  current: DisplayTicket | null;
  lastCalled: DisplayTicket[];
  config?: Record<string, unknown>;
};

/**
 * QUEUE zone variants: footer | sidebar | fullscreen
 * Reuses UX-6A hierarchy without being a separate page.
 */
export function QueueZone({ department, current, lastCalled, config }: Props) {
  const variant = String(config?.variant || "footer");
  const showLast = config?.show_last_called !== false;
  const showLabel = config?.show_label !== false;
  const previous = lastCalled
    .filter((t) => t.id !== current?.id)
    .slice(0, 3)
    .map((t) => t.number);

  if (variant === "fullscreen") {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center bg-[#071a12] px-[4%] text-center">
        <p className="text-[clamp(1.1rem,2.2vw,2.2rem)] font-semibold uppercase tracking-[0.2em] text-brand-200">
          {department}
        </p>
        {current?.number ? (
          <p className="mt-[4vh] font-sans text-[clamp(4.5rem,16vw,12rem)] font-bold leading-none tabular-nums">
            {current.number}
          </p>
        ) : (
          <p className="mt-[4vh] text-[clamp(1.25rem,2.5vw,2.5rem)] text-white/55">
            Aguardando próxima chamada
          </p>
        )}
        {showLast && previous[0] && (
          <p className="mt-8 text-[clamp(0.9rem,1.4vw,1.35rem)] text-white/40">
            Última chamada {previous[0]}
          </p>
        )}
      </div>
    );
  }

  if (variant === "sidebar") {
    return (
      <div className="flex h-full w-full flex-col justify-center bg-[#071a12] px-[8%] py-[6%]">
        <p className="text-[clamp(0.75rem,1.1vw,1.15rem)] font-semibold uppercase tracking-[0.16em] text-brand-200">
          {department}
        </p>
        {showLabel && (
          <p className="mt-2 text-[clamp(0.7rem,0.95vw,1rem)] text-white/50">
            {current?.number ? "Senha em atendimento" : "Aguardando próxima chamada"}
          </p>
        )}
        {current?.number ? (
          <p className="mt-4 font-sans text-[clamp(2.5rem,5.5vw,5rem)] font-bold leading-none tabular-nums">
            {current.number}
          </p>
        ) : null}
        {showLast && previous[0] && (
          <p className="mt-6 text-[clamp(0.7rem,0.9vw,0.95rem)] text-white/40">
            Última {previous[0]}
          </p>
        )}
      </div>
    );
  }

  // footer (default) — UX-6A visual language
  return (
    <div className="flex h-full w-full items-center bg-[#071a12]">
      <div className="display-safe flex w-full items-center justify-between gap-[3vw]">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[clamp(0.85rem,1.4vw,1.35rem)] font-semibold uppercase tracking-[0.18em] text-brand-200">
            {department}
          </p>
          {showLabel && (
            <p className="mt-1 text-[clamp(0.8rem,1.1vw,1.1rem)] text-white/55">
              {current?.number ? "Senha em atendimento" : "Aguardando próxima chamada"}
            </p>
          )}
          {showLast && previous.length > 0 && (
            <p className="mt-2 truncate text-[clamp(0.75rem,1vw,1rem)] text-white/40">
              Última chamada {previous[0]}
              {previous.length > 1 ? ` · ${previous.slice(1).join(" · ")}` : ""}
            </p>
          )}
        </div>
        {current?.number && (
          <p className="shrink-0 font-sans text-[clamp(3rem,7.5vw,6.5rem)] font-bold leading-none tabular-nums">
            {current.number}
          </p>
        )}
      </div>
    </div>
  );
}
