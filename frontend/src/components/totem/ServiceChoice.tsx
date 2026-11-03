import { Accessibility, Ticket } from "lucide-react";
import { formatWaitMinutes } from "./types";

type Props = {
  disabled?: boolean;
  waitingCount?: number | null;
  estimatedWaitSeconds?: number | null;
  onNormal: () => void;
  onPriority: () => void;
};

export function ServiceChoice({
  disabled,
  waitingCount,
  estimatedWaitSeconds,
  onNormal,
  onPriority,
}: Props) {
  const showWaiting = typeof waitingCount === "number";
  const eta =
    showWaiting && waitingCount! > 0 ? formatWaitMinutes(estimatedWaitSeconds) : null;

  return (
    <div className="flex w-full flex-col gap-4">
      <button
        type="button"
        disabled={disabled}
        onClick={onNormal}
        className="totem-btn group flex min-h-[112px] flex-col items-center justify-center gap-2 rounded-2xl bg-white px-5 py-8 text-center text-brand-900 shadow-lg transition duration-150 enabled:active:scale-[0.98] enabled:active:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-55 motion-reduce:transition-none motion-reduce:active:scale-100 sm:min-h-[128px]"
        aria-label="Atendimento normal"
      >
        <Ticket className="h-9 w-9 text-brand-700" aria-hidden strokeWidth={2.25} />
        <span className="text-2xl font-bold tracking-wide sm:text-3xl">ATENDIMENTO NORMAL</span>
        {eta && (
          <span className="text-base text-ink/65">
            aproximadamente <strong className="text-brand-800">{eta}</strong>
          </span>
        )}
      </button>

      <button
        type="button"
        disabled={disabled}
        onClick={onPriority}
        className="totem-btn group flex min-h-[112px] flex-col items-center justify-center gap-2 rounded-2xl border-[3px] border-brand-900 bg-[#f5c518] px-5 py-8 text-center text-brand-950 shadow-lg transition duration-150 enabled:active:scale-[0.98] enabled:active:brightness-95 disabled:cursor-not-allowed disabled:opacity-55 motion-reduce:transition-none motion-reduce:active:scale-100 sm:min-h-[128px]"
        aria-label="Atendimento prioritário — para pessoas com direito ao atendimento prioritário"
      >
        <Accessibility className="h-9 w-9 text-brand-950" aria-hidden strokeWidth={2.25} />
        <span className="text-2xl font-bold tracking-wide sm:text-3xl">ATENDIMENTO PRIORITÁRIO</span>
        <span className="max-w-sm text-base font-medium leading-snug text-brand-950/85">
          Para pessoas com direito ao atendimento prioritário
        </span>
      </button>

      {showWaiting && (
        <p className="pt-1 text-center text-lg font-medium text-white/90" aria-live="polite">
          {waitingCount === 0
            ? "Ninguém aguardando no momento"
            : waitingCount === 1
              ? "1 pessoa aguardando"
              : `${waitingCount} pessoas aguardando`}
        </p>
      )}
    </div>
  );
}
