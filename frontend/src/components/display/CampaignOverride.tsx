import { MediaPlayer } from "./MediaPlayer";
import type { PlaylistItem } from "./types";
import { DISPLAY_LAYER_Z, type ScreenOverride } from "./overrideTypes";

type Props = { override: ScreenOverride };

/** Temporary content takeover — media if available, else branded text. */
export function CampaignOverride({ override }: Props) {
  const p = override.payload || {};
  const mediaUrl = p.media_url ? String(p.media_url) : null;
  const mediaType = String(p.media_type || "IMAGE").toUpperCase();
  const title = String(p.title || "Campanha");
  const message = String(p.message || "");

  if (mediaUrl) {
    const item: PlaylistItem = {
      id: String(p.media_asset_id || override.id),
      name: title,
      type: mediaType,
      url: mediaUrl,
      mime_type: (p.mime_type as string) || null,
      duration_seconds: 30,
    };
    return (
      <div
        className="absolute inset-0 bg-black motion-safe:animate-[displayFade_280ms_ease-out] motion-reduce:animate-none"
        style={{ zIndex: DISPLAY_LAYER_Z.override }}
        role="status"
      >
        <MediaPlayer item={item} />
      </div>
    );
  }

  return (
    <div
      className="absolute inset-0 flex items-center justify-center bg-brand-800 motion-safe:animate-[displayFade_280ms_ease-out] motion-reduce:animate-none"
      style={{ zIndex: DISPLAY_LAYER_Z.override }}
      role="status"
      aria-live="polite"
    >
      <div className="display-safe max-w-[88%] text-center">
        <p className="text-[clamp(1rem,1.8vw,1.6rem)] font-semibold uppercase tracking-[0.28em] text-brand-100">
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
