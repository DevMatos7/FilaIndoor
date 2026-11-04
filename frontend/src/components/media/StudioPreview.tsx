import { useEffect, useRef } from "react";
import type { PlaylistItem } from "../display/types";
import { hostOf } from "../../lib/signageFormat";

type Props = {
  item: PlaylistItem | null;
  playing: boolean;
};

/** Admin preview — reuses MediaPlayer semantics without WS/heartbeat; muted; no surprise audio. */
export function StudioPreview({ item, playing }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    if (playing) {
      void v.play().catch(() => undefined);
    } else {
      v.pause();
    }
  }, [playing, item?.id]);

  if (!item) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-sm text-white/60">
        Sem conteúdos para pré-visualizar
      </div>
    );
  }

  if (item.type === "IMAGE") {
    return (
      <img
        key={item.id}
        src={item.url}
        alt=""
        className="absolute inset-0 h-full w-full object-contain"
      />
    );
  }

  if (item.type === "VIDEO") {
    return (
      <video
        key={item.id}
        ref={videoRef}
        src={item.url}
        className="absolute inset-0 h-full w-full object-contain"
        muted
        playsInline
        preload="metadata"
        loop={false}
      />
    );
  }

  if (item.type === "WEB") {
    return (
      <div className="absolute inset-0 flex flex-col bg-white">
        {playing ? (
          <iframe
            title={item.name}
            src={item.url}
            className="h-full w-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-sm text-ink/70">
            <p className="font-semibold text-brand-900">{item.name}</p>
            <p className="break-all text-xs">{hostOf(item.url)}</p>
            <p className="text-xs text-ink/45">Pressione Play para carregar a página</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full items-center justify-center text-sm text-white/60">
      Tipo não suportado
    </div>
  );
}
