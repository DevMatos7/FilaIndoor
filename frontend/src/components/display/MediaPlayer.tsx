import { useEffect, useRef } from "react";
import type { PlaylistItem } from "./types";
import { DisplayFallback } from "./DisplayFallback";

type Props = {
  item: PlaylistItem | null;
  onMediaFailed?: (item: PlaylistItem) => void;
};

/**
 * Renders IMAGE | VIDEO | WEB for the media zone.
 * Failures advance via onMediaFailed — no technical errors on screen.
 */
export function MediaPlayer({ item, onMediaFailed }: Props) {
  const failedRef = useRef<string | null>(null);

  useEffect(() => {
    failedRef.current = null;
  }, [item?.id]);

  function fail(slide: PlaylistItem) {
    if (failedRef.current === slide.id) return;
    failedRef.current = slide.id;
    console.warn("[display] media failed", slide.id, slide.type);
    onMediaFailed?.(slide);
  }

  if (!item) {
    return <DisplayFallback />;
  }

  return (
    <div className="absolute inset-0 bg-brand-950">
      {item.type === "IMAGE" && (
        <img
          key={item.id}
          src={item.url}
          alt=""
          className="absolute inset-0 h-full w-full object-cover motion-safe:animate-[displayFade_400ms_ease-out] motion-reduce:animate-none"
          onError={() => fail(item)}
        />
      )}
      {item.type === "VIDEO" && (
        <video
          key={item.id}
          src={item.url}
          className="absolute inset-0 h-full w-full object-cover"
          autoPlay
          muted
          playsInline
          preload="auto"
          onError={() => fail(item)}
          onEnded={() => {
            /* duration timer in parent advances playlist; ended is extra safety */
          }}
        />
      )}
      {item.type === "WEB" && (
        <iframe
          key={item.id}
          title="conteúdo"
          src={item.url}
          className="absolute inset-0 h-full w-full border-0 bg-white"
          onError={() => fail(item)}
        />
      )}
      {item.type !== "IMAGE" && item.type !== "VIDEO" && item.type !== "WEB" && (
        <DisplayFallback />
      )}
    </div>
  );
}
