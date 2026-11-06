# MODULE 3 — Dynamic Playlist & Player

## Status semântico

`PRICE_TABLE` **não é mídia estática**. É uma **view dinâmica** de dados CISS reconciliados, resolvida no backend e renderizada pelo mesmo `PriceTableRenderer` no admin e na TV.

## Arquitetura final

```text
Playlist
  ├── MEDIA
  └── DYNAMIC
↓
ContentSequence (playlist item timer)
↓
ContentRenderer
   ├── MediaPlayer
   └── DynamicContentRenderer
           ↓
      PriceTableRenderer
↓
OverrideResolver (cobre; base permanece montada)
```

## PlaylistItem

| Campo | MEDIA | DYNAMIC |
|-------|-------|---------|
| `item_type` | MEDIA | DYNAMIC |
| `asset_id` | NOT NULL | NULL |
| `dynamic_content_id` | NULL | NOT NULL |
| `duration_source` | SOURCE/OVERRIDE | SOURCE (MVP default) |

Constraint: exatamente um de `asset_id` / `dynamic_content_id`.

Backfill: itens existentes → `MEDIA`.

Downgrade: **bloqueado** se existirem itens DYNAMIC ativos.

## Duração

- **MEDIA**: `item.duration_seconds || asset.duration_seconds || 10` (inalterado).
- **DYNAMIC SOURCE**: `page_count × page_duration` (FULL_CYCLE) ou `total_duration_seconds` (FIXED) — calculado do snapshot/config atual, **não congelado** na playlist.
- **DYNAMIC OVERRIDE**: duração explícita do item (não liberado na UI MVP).

## Player

- Config preserva MEDIA; adiciona `item_type` + descriptor `dynamic_content`.
- `GET /api/v1/player/dynamic-content/{id}` com `X-Display-Token`.
- Same-store + active; STALE/FAILED → 403 (player faz skip).
- ETag / If-None-Match → 304.
- Cache local `dynamic_content:<id>` com `valid_until`; cache expirado **nunca** exibe preço.

## Timers / PlaybackClock

| Relógio | Comportamento |
|---------|---------------|
| Playlist item timer | `active_elapsed`; pausa sob override |
| Page timer (PRICE_TABLE) | `floor(active_elapsed / page_duration) % page_count` (FIXED) ou clamp (FULL_CYCLE) |
| Override | PAUSE → RESUME mesma página / tempo restante |
| VIDEO | elemento pausa/resume |
| IMAGE | só clock |
| WEB | clock pausa; iframe externo sem pause real (limitação documentada) |

## Descrição comercial (TV)

```text
display_description = commercial_description ?? description
```

Sem descrição válida → item inválido. **Nunca** `source_product_id` / SKU / GTIN como label na TV.

## Preview draft

`POST /dynamic-content/preview` (draft temporário) é **somente admin**. O player consome apenas conteúdo persistido + snapshot via `ensure_current_snapshot()`.

## Isolamento / delete

- Playlist store A + DynamicContent store B → rejeitado.
- `DELETE` com `usage_count > 0` → 409.
- `usage_count` / `usage` aditivos na API admin.

## Module 4 (visual)

`PRODUCT_GRID` / `PRODUCT_HERO` / `PROMOTION_BOARD` + `ProductMediaLink` → ver [06-product-visual-engine.md](./06-product-visual-engine.md).  
`DynamicContentRenderer` roteia os quatro tipos; PlaybackClock / ETag / stale / override inalterados.

## Module 5 (automação)

Invalidação WS `dynamic_content.invalidated`, cache por `valid_until`, prefetch no boundary de página e STALE skip urgente — ver [07-automation-resilience.md](./07-automation-resilience.md).

## Não implementado (Module 6+)

WebSocket invalidation / stock filter / Proof of Play / Retail Media / Automation.
