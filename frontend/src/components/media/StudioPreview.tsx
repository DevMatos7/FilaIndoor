import { useEffect, useRef, useState } from "react";
import type { PlaylistItem } from "../display/types";
import { hostOf } from "../../lib/signageFormat";
import { DynamicContentRenderer } from "../dynamic-content/DynamicContentRenderer";
import type { PriceTableSnapshot } from "../dynamic-content/dynamicContentTypes";
import api from "../../services/api";

type Props = {
  item: PlaylistItem | null;
  playing: boolean;
  storeId?: string;
};

/** Admin preview — shared renderers; muted; no surprise audio. */
export function StudioPreview({ item, playing, storeId }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [dynSnap, setDynSnap] = useState<PriceTableSnapshot | null>(null);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    if (playing) {
      void v.play().catch(() => undefined);
    } else {
      v.pause();
    }
  }, [playing, item?.id]);

  useEffect(() => {
    if (!item || (item.item_type !== "DYNAMIC" && item.type !== "DYNAMIC" && item.type !== "PRICE_TABLE")) {
      setDynSnap(null);
      return;
    }
    const contentId = item.dynamic_content?.id || item.id;
    if (!storeId || !contentId) return;
    let alive = true;
    api
      .post(`/dynamic-content/${contentId}/preview`, null, { params: { store_id: storeId } })
      .then((res) => {
        if (alive) setDynSnap(res.data as PriceTableSnapshot);
      })
      .catch(() => {
        if (alive) setDynSnap(null);
      });
    return () => {
      alive = false;
    };
  }, [item?.id, item?.item_type, item?.type, item?.dynamic_content?.id, storeId]);

  if (!item) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-sm text-white/60">
        Sem conteúdos para pré-visualizar
      </div>
    );
  }

  if (item.item_type === "DYNAMIC" || item.type === "DYNAMIC" || item.type === "PRICE_TABLE") {
    return (
      <div className="absolute inset-0">
        <DynamicContentRenderer mode="preview" snapshot={dynSnap} pageIndex={0} />
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
