# Module 5R — CISS Offer & Product Image Source Hardening

**Base:** `75940de` (Module 5)  
**Auditoria:** `docs/dynamic-retail-content/reconciliation/module-5r-ciss-offers-images.json`  
**Read-only DB2:** SUPEREAL / schema DBA

## Decisões finais

| Gate | Resultado |
|------|-----------|
| CISS IMAGE PATH SOURCE | **NOT_USABLE** (`PRODUTO_GRADE_IMAGENS.PATHIMAGEM` UNC) |
| CISS IMAGE BLOB SOURCE | **USABLE** (`PRODUTO_ESPECIFICACAO_TECNICA.FOTOPRINCIPAL` BLOB JPEG) |
| OBSESPECIFIC FOR DISPLAY | **PARTIAL** (27/40 BETTER, mas mistura rótulo nutricional/CNPJ) → **NOT_ADOPTED** como precedência default |
| PROMOCAO_GESTAO | **CONFIRMED** |
| CISS OFFER SOURCE | **CONFIRMED** (+ `PROMOCAO_GESTAO_EMPRESA` por `IDEMPRESA`) |
| PRICE CHAIN | **CONFIRMED** (`PRODUTO_CADEIA_PRECO`) |
| REAL ACTIVE PROMOTION | **PASS** (campanhas vigentes encontradas; sync → `RetailOfferCampaign`) |

## FOTOPRINCIPAL

- Tipo: **BLOB** (1 048 576)
- Também existem: `FOTOESPECIFIC`, `FOTOVISAO1`, `FOTOVISAO2` (fora do MVP)
- Cobertura: 47 920 não-nulos · **9 902** com length ≠ 4912 · **4 591** SKUs ativos com imagem não-placeholder
- Magic: JPEG (`ffd8ff…`) em todas as amostras úteis; dimensões decodificadas (ex. 200×200)
- pyodbc: tipo ODBC **-98** não materializa BLOB direto → import via `HEX(SUBSTR)` em chunks

### Regra 4912

- 38 018 registros com `LENGTH=4912`
- Mesmo header JPEG + **mesmo SHA256** em amostras distintas  
  `0c2cba5fa5aa8a4552672c5aee88bd011e706ebd671596e7e5d268988923ce5e`
- Classificação: **PLACEHOLDER** (não importar)

## Import de imagem

```
CISS FOTOPRINCIPAL
  → hash / skip placeholder
  → MediaAsset (storage local)
  → ProductMediaLink source=CISS
  → invalidation IMAGE_CHANGED (Module 5)
```

Precedência de exibição:

1. MANUAL store  
2. CISS store  
3. MANUAL global  
4. CISS global  

Import automático **não** sobrescreve PRIMARY MANUAL.

## OBSESPECIFIC

- Tipo: CLOB  
- Amostra 40: BETTER 27 · EQUAL 13 · WORSE 0  
- Conteúdo inconsistente (nome comercial vs texto nutricional/CNPJ)  
- **NOT_ADOPTED** como `commercial_description` default neste módulo  
- Débito: seletor de qualidade + promoção parcial futura

## PROMOCAO_GESTAO / PRODUTO

| Campo | Semântica |
|-------|-----------|
| `IDPROMOCAO` | PK campanha |
| `DESCRPROMOCAO` | Nome |
| `DTINIPROMOCAO` / `DTFIMPROMOCAO` | Janela (timezone da Store) |
| `FLAGINATIVO` | T=inativo |
| `PROMOCAO_GESTAO_EMPRESA` | Escopo por `IDEMPRESA` |
| `VALPRECO` | Preço oferta bruto |
| `FLAGPRECOMANDATORIO=T` | `effective = VALPRECO × VALGRAMAENTRADA` |
| caso contrário | `effective = VALPRECO` |

`OfferPriceResolver` centraliza a fórmula (Decimal).

Domínio separado (não substitui `RetailPromotion` de política):

- `RetailOfferCampaign`
- `RetailOfferItem`

Promotion Board pode usar `rule.config.selection_source = CISS_OFFER` + `offer_campaign_id`.

## PRODUTO_CADEIA_PRECO

- **Não** é SKU: chave canônica permanece `IDPRODUTO:IDSUBPRODUTO`
- Modelos: `RetailPriceChain` + `RetailProductPriceChain`
- Semântica observada: agrupamento comercial / etiqueta de gôndola (variantes sob mesma cadeia)

## Sync / scheduler

Novas entidades (APScheduler Module 5):

| Entity | Default interval |
|--------|------------------|
| OFFER | `RETAIL_SYNC_OFFER_SECONDS` (120) |
| PRODUCT_IMAGE | `RETAIL_SYNC_PRODUCT_IMAGE_SECONDS` (900) |
| PRICE_CHAIN | `RETAIL_SYNC_PRICE_CHAIN_SECONDS` (900) |

Production mock guard permanece.

## Segurança

- CISS read-only  
- Sem BLOB no snapshot/WebSocket  
- Sem DSN/senha/SQL em APIs
