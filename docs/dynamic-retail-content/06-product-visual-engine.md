# Module 4 — Product Visual Engine

**Status:** READY FOR HOMOLOGATION  
**Commit alvo:** `feat(dynamic-retail): product visual engine`  
**Base:** `6491eb4` (Module 3) · templates/enums já previstos no Module 2

## Objetivo

Conteúdo comercial visual com produtos reais:

| Tipo | Renderer | MVP |
|------|----------|-----|
| `PRODUCT_GRID` | `ProductGridRenderer` | 2×2 · 3×2 · 4×2 |
| `PRODUCT_HERO` | `ProductHeroRenderer` | 1 produto/página |
| `PROMOTION_BOARD` | `PromotionBoardRenderer` | grade promo + DE/POR |

Associação de imagem:

```
RetailProduct → ProductMediaLink → MediaAsset
```

Sem fluxo paralelo: Retail Data → DynamicContent → Playlist → Programming → Layout → Player → Override.

## Princípio — imagem não é preço

Nunca embutir binário em `RetailPrice`, `RetailPromotion` ou `DynamicRenderSnapshot`.  
Snapshot só carrega `{ asset_id, url }` públicos da Media Library.

## ProductMedia

Tabela `product_media_links` (migration `20261106_0018`):

| Campo | Notas |
|-------|--------|
| purpose | PRIMARY (MVP) · SECONDARY · BACKGROUND |
| source | **MANUAL** obrigatório neste módulo · CISS/SUPPLIER reservados |
| store_id | NULL = global · valor = loja |
| is_primary | um PRIMARY efetivo por escopo (produto+store+purpose) |

### Precedência de imagem

1. store-specific PRIMARY  
2. global PRIMARY  
3. fallback sem imagem (layout adapta; sem ícone quebrado)

### Isolamento

- MediaAsset é store-scoped no domínio atual → attach exige `store_id` da mesma loja.  
- Asset de outra loja → 403/422.  
- Delete de MediaAsset com vínculo ativo → **409**.  
- Delete do vínculo **não** apaga o arquivo.

## Media Library reuse

Fluxo admin: Produto → Associar imagem → `MediaPicker` (filtro IMAGE travado) → `MediaAsset`.  
Sem uploader paralelo · sem WEB/VIDEO como PRIMARY · sem cópia física por produto.

## CISS Image Source Audit

| Item | Evidência |
|------|-----------|
| Tabela | `DBA.PRODUTO_GRADE_IMAGENS` (~3 344 rows no contrato M1) |
| Campos | `PATHIMAGEM`, `PATHTHUMBNAIL`, `FLAGIMAGEMPADRAO`, `NOMEIMAGEM` |
| Exemplos (sanitizados) | paths Windows/UNC típicos de ERP local (`\\SERVER\…` / `D:\CISS\…`) — **não** servidos ao browser |
| Acesso backend | **não** comprovado neste ambiente (DB2 read-only de metadados; filesystem UNC/local não montado no container API) |
| Tipo/permissão | não validável sem mount |

**CISS IMAGE SOURCE: `NOT_USABLE`**

Decisão: Module 4 **não** importa automaticamente. Associação **manual** via Media Library. Import CISS fica PDR/MCP até path acessível + tipo suportado + segurança aceitável. Nunca enviar UNC/C:\ ao player.

## Templates system

| Slug | Tipo |
|------|------|
| `product_grid_2x2` / `_3x2` / `_4x2` | PRODUCT_GRID |
| `product_hero_clean` / `product_hero_promo` | PRODUCT_HERO |
| `promotion_board_2x2` / `_3x2` | PROMOTION_BOARD |

Aparência via `template.config` (columns, rows, image_fit=contain, badges). Sem CSS arbitrário · sem logo base64.

## Resolvers / preços

Todos os tipos usam `DynamicProductResolver` + `PriceDisplayResolver`.  
Renderers **não** reimplementam validade de promo, DE/POR, quantity tiers ou unit price.

## Snapshot & hash

- Mesmo `DynamicRenderSnapshot`.  
- Item inclui `image: { asset_id, url } \| null`.  
- `content_hash` inclui `image_asset_id`.  
- `data_version` considera `max(ProductMediaLink.updated_at)` → mudança de PRIMARY invalida cache lógico; ETag do player segue fluxo M3.

Player: **um** payload por conteúdo dinâmico (proibido N requests `/retail-products` na TV). Imagens HTTP à parte.

## Player / Override

`DynamicContentRenderer` switch compartilhado (Admin Preview = Studio = TV).  
`PlaybackClock` pausa sob QUEUE_CALL e retoma mesma página/tempo — sem mudança arquitetural.

## Fallbacks

- Sem imagem → brand background + nome + preço.  
- URL quebrada → `onError` → mesmo fallback (sem ícone nativo).  
- Zero produtos / zero promoções → status `ATENÇÃO`, snapshot não publishable, player skip.  
- Tipo desconhecido → skip + log (nunca tela preta).

## UI Admin (`/retail-content`)

Abas: Visão geral · Produtos · Tabelas · **Vitrines** · Sincronização CISS.  
Produtos: coluna/filtro COM IMAGEM / SEM IMAGEM · Product Drawer com preview + MediaPicker.  
Playlist Studio `DynamicPicker`: Tabela · Grade · Destaque · Painel.

## Segurança de imagem comercial

Imagens de SKU devem representar o produto real.  
**Não** usar geração de IA para simular embalagem/SKU.

## Fora de escopo (STOP)

stock filtering · WebSocket invalidation · Proof of Play · Retail Media · campaign advertiser · AI image/selection · Device Commands · Template Builder livre · Module 5.

## Travas preservadas

- `STOCK FILTER: DISABLED BY DESIGN`  
- `PROMOTION ENGINE: PASS` · `REAL ACTIVE PROMOTION: PENDING`  
- `MULTI-TIER ENGINE: PASS` · `REAL MULTI-TIER: PENDING`

## Screenshots

`docs/dynamic-retail-content/screenshots/module-4/`
