# Module 2 — Price Table Engine

**Status:** implementação  
**Consome:** retail_* homologado (Module 1 / 1R / 1R.1)  
**Não inclui:** Playlist DYNAMIC · Player · Layout TV · QUEUE_CALL

## Fontes CISS (referência)

| Uso | Objeto CISS |
|-----|-------------|
| Preço por loja | `POLITICA_PRECO_PRODUTO` |
| Cadastro produtos (view) | `PRODUTOS_VIEW` (referência operacional; sync usa `PRODUTO`/`PRODUTO_GRADE` já homologados) |

## Domínio retail consumido

| Necessidade | Fonte canônica |
|-------------|----------------|
| produto / descrição | `RetailProduct.commercial_description ?? description` |
| unidade | `RetailProduct.unit` |
| preço regular | `RetailPrice` kind=`REGULAR` active |
| promoção vigente | `RetailPromotion` active **e** janela no `store.timezone` |
| quantity tiers | `RetailPrice` kind=`QUANTITY` active, ordenados por `min_qty` |
| freshness | `GET /retail-data/health` → PRICE entity / overall |

**Proibido:** SQL DB2 no Dynamic Content · preço digitável · fallback inventado.

## Selection modes

| Mode | Resolução |
|------|-----------|
| MANUAL | só `dynamic_content_products` (não excluded), ordem `position` |
| AUTOMATIC | só regras (`section/group/subgroup`, `promotion_only`, sort, limit) |
| HYBRID | 1) pinned 2) regra 3) −excluded 4) dedupe 5) limit |

`available_only`: campo existe; **UI força false**; se true → `ValidationError` (STOCK FILTER DISABLED BY DESIGN).

## PriceDisplayResolver

Usa `Decimal`. Timezone = `Store.timezone` apenas.

| Caso | Resultado |
|------|-----------|
| regular só | `display_price = regular`, `is_promotion=false` |
| promo vigente + promo < regular | `display_price=promo`, `show_from_to=true` (DE/POR) |
| promo vigente sem regular válido | `display_price=promo`, sem DE/POR |
| quantity tiers | lista `{min_qty, amount, condition_text}` — nunca amount isolado |
| amount ≤ 0 ou missing | **não exibível** |

Format: `pt-BR` / `R$ #.##` via formatador central.

## Missing price

| Mode | Comportamento |
|------|----------------|
| MANUAL / pin HYBRID | warning explícito; status ≠ PRONTA |
| AUTOMATIC | filtra; conta `ignored_missing_price` |

## Freshness ao gerar snapshot

| Status | Comportamento |
|--------|----------------|
| FRESH | gera normalmente |
| DEGRADED | gera + warning admin |
| STALE / FAILED | **bloqueia** snapshot publicável |

## Paginação / duração

- `items_per_page` (limites por template)  
- `page_duration_seconds` ∈ [3, 120]  
- `FULL_CYCLE`: `total = page_count × page_duration`  
- `FIXED`: `total_duration_seconds` fixo; páginas rotacionam dentro da janela (player no Módulo 3)

## Templates system

| slug | UI | items/page default |
|------|-----|--------------------|
| `price_table_clean` | Tabela limpa | 8 |
| `price_table_compact` | Tabela compacta | 16 |
| `price_table_two_columns` | Duas colunas | 12 |
| `price_table_promo` | Promocional | 6 |

`store_id NULL` + índice parcial unique(slug) WHERE store_id IS NULL.

## Validações

- VISUAL VALIDATION: fechada no **Module 3** via `PriceTableRenderer` compartilhado (admin = TV).
- REAL ACTIVE PROMOTION VALIDATION: PENDING REAL CASE  
- REAL MULTI-TIER VALIDATION: PENDING REAL CASE  
- STOCK FILTER: DISABLED BY DESIGN  

Ver também: [05-dynamic-playlist-player.md](./05-dynamic-playlist-player.md).

