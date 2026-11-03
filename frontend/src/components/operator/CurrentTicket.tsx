import { Accessibility, Clock } from "lucide-react";
import { formatElapsed, isPriority } from "./types";
import type { Ticket } from "../../services/api";

type Props = {
  serving: Ticket | null;
  elapsed: number | null;
};

export function CurrentTicket({ serving, elapsed }: Props) {
  if (!serving) {
    return (
      <section className="rounded-2xl border border-white/10 bg-white/5 px-5 py-10 text-center">
        <p className="text-2xl font-semibold text-white">Pronto para atender</p>
        <p className="mt-3 text-base text-white/65">Chame a próxima senha.</p>
      </section>
    );
  }

  const priority = isPriority(serving.type);

  return (
    <section
      className="rounded-2xl bg-white px-5 py-8 text-center text-brand-950 shadow-lg motion-safe:animate-[opTicket_220ms_ease-out] motion-reduce:animate-none"
      aria-live="polite"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">Atendendo</p>
      <p className="mt-2 font-sans text-[clamp(3.75rem,16vw,6.5rem)] font-bold leading-none tracking-tight tabular-nums">
        {serving.number}
      </p>
      {priority && (
        <p className="mt-4 inline-flex items-center gap-2 rounded-full bg-semantic-warning-bg px-3 py-1.5 text-sm font-semibold text-semantic-warning">
          <Accessibility className="h-4 w-4" aria-hidden />
          Prioritário
        </p>
      )}
      <p className="mt-5 inline-flex items-center justify-center gap-2 text-3xl font-semibold tabular-nums text-brand-700">
        <Clock className="h-6 w-6" aria-hidden />
        <span className="sr-only">Tempo de atendimento</span>
        {formatElapsed(elapsed)}
      </p>
    </section>
  );
}
