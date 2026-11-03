import { isPriorityType, type CallOverlay } from "./types";

type Props = {
  call: CallOverlay | null;
};

/**
 * Full-screen call takeover (~7s). Media remains mounted underneath (parent).
 * Not a Layout Engine zone — UX-6C may replace with screen_overrides.
 */
export function QueueCallOverlay({ call }: Props) {
  if (!call) return null;

  const priority = isPriorityType(call.ticketType);

  return (
    <div
      className="absolute inset-0 z-40 flex items-center justify-center bg-brand-900/95 motion-safe:animate-[displayFade_280ms_ease-out] motion-reduce:animate-none"
      role="status"
      aria-live="polite"
    >
      <div className="display-safe max-w-[90%] text-center">
        <p className="text-[clamp(1.25rem,2.5vw,2.5rem)] font-semibold uppercase tracking-[0.22em] text-brand-100">
          {call.department}
        </p>
        <p className="mt-[3vh] font-sans text-[clamp(5rem,18vw,14rem)] font-bold leading-none tracking-tight tabular-nums text-white">
          {call.number}
        </p>
        {priority && (
          <p className="mt-6 text-[clamp(1rem,1.8vw,1.75rem)] font-semibold text-brand-100">
            Atendimento prioritário
          </p>
        )}
        <p className="mt-[4vh] text-[clamp(1.25rem,2.4vw,2.75rem)] font-medium text-white/90">
          Dirija-se ao balcão
        </p>
      </div>
    </div>
  );
}
