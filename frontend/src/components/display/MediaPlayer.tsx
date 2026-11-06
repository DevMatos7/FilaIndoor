import { useEffect, useRef } from "react";
import type { PlaylistItem } from "./types";
import { DisplayFallback } from "./DisplayFallback";

type Props = {
  item: PlaylistItem | null;
  paused?: boolean;
  onMediaFailed?: (item: PlaylistItem) => void;
};

/**
 * Renders IMAGE | VIDEO | WEB for the media zone.
 * Failures advance via onMediaFailed — no technical errors on screen.
 * When paused (override covering): VIDEO pauses; IMAGE holds; WEB clock pauses in parent.
 */
export function MediaPlayer({ item, paused = false, onMediaFailed }: Props) {
  const failedRef = useRef<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    failedRef.current = null;
  }, [item?.id]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v || item?.type !== "VIDEO") return;
    if (paused) {
      v.pause();
    } else {
      void v.play().catch(() => undefined);
    }
  }, [paused, item?.id, item?.type]);

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
          ref={videoRef}
          src={item.url}
          className="absolute inset-0 h-full w-full object-cover"
          autoPlay={!paused}
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
