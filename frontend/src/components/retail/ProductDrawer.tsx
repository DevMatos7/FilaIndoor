import { useEffect, useState } from "react";
import { Alert, Button, Drawer } from "../../design-system";
import { MediaPicker } from "../media/MediaPicker";
import type { MediaItem } from "../../pages/Media";
import api from "../../services/api";
import { formatBrl } from "../../utils/formatPrice";

type Props = {
  open: boolean;
  storeId: string;
  productId: string | null;
  onClose: () => void;
  onChanged: () => void;
};

type Detail = {
  id: string;
  description: string;
  commercial_description?: string | null;
  source_product_id?: string;
  unit?: string | null;
  primary_image?: { asset_id: string; url: string } | null;
  has_image?: boolean;
  image_status?: string;
  prices?: { price_kind: string; amount: number; min_qty?: number | null }[];
  promotion?: { promo_amount: number } | null;
  media?: {
    id: string;
    is_primary: boolean;
    purpose: string;
    asset?: { public_url?: string; name?: string } | null;
  }[];
};

export function ProductDrawer({ open, storeId, productId, onClose, onChanged }: Props) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!open || !storeId || !productId) return;
    setError(null);
    try {
      const { data } = await api.get<Detail>(`/retail-products/${productId}`, {
        params: { store_id: storeId },
      });
      setDetail(data);
    } catch {
      setError("Não foi possível carregar o produto.");
    }
  }

  useEffect(() => {
    void load();
  }, [open, storeId, productId]);

  async function onPick(assets: MediaItem[]) {
    if (!productId || !assets[0]) return;
    setBusy(true);
    try {
      await api.post(`/retail-products/${productId}/media`, {
        media_asset_id: assets[0].id,
        store_id: storeId,
        purpose: "PRIMARY",
        is_primary: true,
      });
      setPickerOpen(false);
      await load();
      onChanged();
    } catch {
      setError("Falha ao associar imagem (somente IMAGE da mesma loja).");
    } finally {
      setBusy(false);
    }
  }

  async function removeLink(linkId: string) {
    if (!productId) return;
    setBusy(true);
    try {
      await api.delete(`/retail-products/${productId}/media/${linkId}`, {
        params: { store_id: storeId },
      });
      await load();
      onChanged();
    } catch {
      setError("Falha ao remover vínculo.");
    } finally {
      setBusy(false);
    }
  }

  const regular = detail?.prices?.find((p) => p.price_kind === "REGULAR");

  return (
    <>
      <Drawer open={open} onClose={onClose} title="Produto">
        {error && <Alert variant="danger">{error}</Alert>}
        {!detail ? (
          <p className="text-sm text-ink/60">Carregando…</p>
        ) : (
          <div className="space-y-4">
            <div>
              <h3 className="font-display text-xl text-brand-900">
                {detail.commercial_description || detail.description}
              </h3>
              <p className="mt-1 text-sm text-ink/60">
                SKU {detail.source_product_id} · {detail.unit || "—"} ·{" "}
                {detail.image_status || (detail.has_image ? "COM IMAGEM" : "SEM IMAGEM")}
              </p>
              <p className="mt-2 text-lg tabular-nums font-semibold">
                {formatBrl(regular?.amount ?? detail.promotion?.promo_amount)}
              </p>
            </div>

            <div className="overflow-hidden rounded-ds border border-brand-100 bg-brand-50">
              {detail.primary_image?.url ? (
                <img
                  src={detail.primary_image.url}
                  alt=""
                  className="mx-auto max-h-56 object-contain p-4"
                />
              ) : (
                <div className="flex h-40 items-center justify-center text-sm text-ink/45">
                  Sem imagem — fallback visual na TV
                </div>
              )}
            </div>

            <Button type="button" onClick={() => setPickerOpen(true)} disabled={busy}>
              Associar imagem
            </Button>

            {(detail.media || []).length > 0 && (
              <ul className="space-y-2">
                {detail.media!.map((m) => (
                  <li
                    key={m.id}
                    className="flex items-center justify-between gap-2 rounded-ds border border-brand-100 px-3 py-2 text-sm"
                  >
                    <span>
                      {m.purpose}
                      {m.is_primary ? " · PRINCIPAL" : ""} · {m.asset?.name || m.id}
                    </span>
                    <Button size="sm" variant="ghost" onClick={() => void removeLink(m.id)} disabled={busy}>
                      Remover
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Drawer>
      <MediaPicker
        open={pickerOpen}
        onClose={() => !busy && setPickerOpen(false)}
        storeId={storeId}
        busy={busy}
        onConfirm={onPick}
        defaultFilter="IMAGE"
        lockFilter
        singleSelect
      />
    </>
  );
}
