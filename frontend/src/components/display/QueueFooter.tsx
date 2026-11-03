import type { DisplayTicket } from "./types";

type Props = {
  department: string;
  current: DisplayTicket | null;
  lastCalled: DisplayTicket[];
};

export function QueueFooter({ department, current, lastCalled }: Props) {
  const previous = lastCalled
    .filter((t) => t.id !== current?.id)
    .slice(0, 3)
    .map((t) => t.number);

  return (
    <footer className="display-footer relative z-10 flex shrink-0 items-center border-t border-white/10 bg-[#071a12]">
      <div className="display-safe flex w-full items-center justify-between gap-[3vw] py-[2.2vh]">
        <div className="min-w-0 flex-1">
          <p className="truncate text-[clamp(0.85rem,1.4vw,1.35rem)] font-semibold uppercase tracking-[0.18em] text-brand-200">
            {department}
          </p>
          <p className="mt-1 text-[clamp(0.8rem,1.1vw,1.1rem)] text-white/55">
            {current?.number ? "Senha em atendimento" : "Aguardando próxima chamada"}
          </p>
          {previous.length > 0 && (
            <p className="mt-2 truncate text-[clamp(0.75rem,1vw,1rem)] text-white/40">
              Última chamada {previous[0]}
              {previous.length > 1 ? ` · ${previous.slice(1).join(" · ")}` : ""}
            </p>
          )}
        </div>

        {current?.number && (
          <div className="shrink-0 text-right">
            <p className="font-sans text-[clamp(3rem,7.5vw,6.5rem)] font-bold leading-none tracking-tight tabular-nums text-white">
              {current.number}
            </p>
          </div>
        )}
      </div>
    </footer>
  );
}
