import { DISPLAY_LAYER_Z, type ScreenOverride } from "./overrideTypes";

type Props = { override: ScreenOverride };

/** Institutional / neutral REAL notice. */
export function ManualOverride({ override }: Props) {
  const p = override.payload || {};
  const title = String(p.title || "Aviso");
  const message = String(p.message || "");

  return (
    <div
      className="absolute inset-0 flex items-center justify-center bg-brand-900/92 motion-safe:animate-[displayFade_280ms_ease-out] motion-reduce:animate-none"
      style={{ zIndex: DISPLAY_LAYER_Z.override }}
      role="status"
      aria-live="polite"
    >
      <div className="display-safe max-w-[88%] text-center">
        <p className="text-[clamp(1rem,1.8vw,1.6rem)] font-semibold uppercase tracking-[0.3em] text-brand-100">
          Real
        </p>
        <p className="mt-[3vh] font-sans text-[clamp(2rem,5.5vw,4.5rem)] font-bold leading-tight text-white">
          {title}
        </p>
        {message && (
          <p className="mt-[3vh] text-[clamp(1.25rem,2.6vw,2.75rem)] font-medium leading-snug text-white/90">
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
