import { isPriorityType } from "./types";
import { DISPLAY_LAYER_Z, type ScreenOverride } from "./overrideTypes";

type Props = {
  override: ScreenOverride;
};

/** Visual reuse of UX-6A QueueCallOverlay — now driven by ScreenOverride. */
export function QueueCallOverride({ override }: Props) {
  const p = override.payload || {};
  const number = String(p.ticket_number || "");
  const department = String(p.department_name || "Atendimento");
  const ticketType = p.ticket_type as string | undefined;
  const instruction = String(p.instruction || "Dirija-se ao balcão");
  const priority = isPriorityType(ticketType);

  return (
    <div
      className="absolute inset-0 flex items-center justify-center bg-brand-900/95 motion-safe:animate-[displayFade_280ms_ease-out] motion-reduce:animate-none"
      style={{ zIndex: DISPLAY_LAYER_Z.override }}
      role="status"
      aria-live="polite"
    >
      <div className="display-safe max-w-[90%] text-center">
        <p className="text-[clamp(1.25rem,2.5vw,2.5rem)] font-semibold uppercase tracking-[0.22em] text-brand-100">
          {department}
        </p>
        <p className="mt-[3vh] font-sans text-[clamp(5rem,18vw,14rem)] font-bold leading-none tracking-tight tabular-nums text-white">
          {number}
        </p>
        {priority && (
          <p className="mt-6 text-[clamp(1rem,1.8vw,1.75rem)] font-semibold text-brand-100">
            Atendimento prioritário
          </p>
        )}
        <p className="mt-[4vh] text-[clamp(1.25rem,2.4vw,2.75rem)] font-medium text-white/90">
          {instruction}
        </p>
      </div>
    </div>
  );
}
