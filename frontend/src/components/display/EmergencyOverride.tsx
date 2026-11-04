import { DISPLAY_LAYER_Z, type ScreenOverride } from "./overrideTypes";

type Props = { override: ScreenOverride };

/** High contrast, no flashing/strobes. */
export function EmergencyOverride({ override }: Props) {
  const p = override.payload || {};
  const title = String(p.title || "Aviso importante");
  const message = String(p.message || "");
  const instruction = p.instruction ? String(p.instruction) : null;

  return (
    <div
      className="absolute inset-0 flex items-center justify-center bg-[#1a0505] motion-safe:animate-[displayFade_320ms_ease-out] motion-reduce:animate-none"
      style={{ zIndex: DISPLAY_LAYER_Z.override }}
      role="alert"
      aria-live="assertive"
    >
      <div className="display-safe max-w-[88%] text-center">
        <p className="text-[clamp(1.1rem,2.2vw,2rem)] font-bold uppercase tracking-[0.28em] text-[#ffb4b4]">
          Aviso importante
        </p>
        <p className="mt-[3vh] font-sans text-[clamp(2.2rem,6vw,5.5rem)] font-bold leading-tight text-white">
          {title}
        </p>
        {message && (
          <p className="mt-[3vh] text-[clamp(1.35rem,2.8vw,3rem)] font-medium leading-snug text-white/95">
            {message}
          </p>
        )}
        {instruction && (
          <p className="mt-[4vh] text-[clamp(1.1rem,2vw,2.2rem)] font-semibold text-[#ffd0d0]">
            {instruction}
          </p>
        )}
      </div>
    </div>
  );
}
