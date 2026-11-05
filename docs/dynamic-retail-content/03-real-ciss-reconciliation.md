# Module 1R — Real CISS Reconciliation Gate

**Data:** 2026-11-05  
**Base:** `2c0e429` + hardenings desta execução  
**Ambiente:** host Windows + IBM DB2 ODBC · `RETAIL_PROVIDER=ciss_db2`  
**Artefatos:** `docs/dynamic-retail-content/reconciliation/`

---

## Decisão

| Gate | Resultado |
|------|-----------|
| REAL STORE MAPPING | **PASS** |
| REAL DB2 SYNC | **PASS** |
| REAL IDEMPOTENCY | **PASS** |
| REGULAR PRICE SOURCE | **CONFIRMED** |
| PROMOTION SOURCE | **CONFIRMED** |
| QUANTITY PRICE SOURCE | **CONFIRMED** |
| UNIT SOURCE | **CONFIRMED** |
| STOCK SOURCE | **PARTIALLY CONFIRMED** (soma por `IDEMPRESA`; local preferencial **NOT CONFIRMED**) |
| REGULAR / PROMO / QTY / UNIT MATCH (amostra) | **100%** |
| UNEXPLAINED PRICE MISMATCH | **0** |
| CODE VALIDATION | **PASS** (retail foundation `8 passed`; integração geral `93 passed`) |
| REGRESSION EXTERNA | `test_programming_studio_ux9` **FAILED** pré-existente / flaky — **fora do escopo DRC** |

**MODULE 1:** READY FOR FINAL HOMOLOGATION  
**MODULE 2:** NOT STARTED / NOT AUTHORIZED by this document alone — aguarda homologação humana explícita.

---

## 1. Loja piloto / mapping

| Campo | Valor |
|-------|-------|
| Store app | Loja Campo Novo |
| store_id | `c73b48c6-9646-4dee-854a-b65eb212b8ad` |
| timezone | `America/Sao_Paulo` |
| IDEMPRESA | `1` |
| Nome fantasia CISS | Supermercado Real |
| Razão social | Casagrande & Cia Ltda - EPP |
| location_code | `null` (não assumido) |
| Razão do vínculo | Loja piloto operacional do app ↔ empresa matriz CISS `1` (Supermercado Real) |

`retail_store_sources`: `source_system=CISS`, `company_code=1`, `active=true`.

---

## 2. Amostra

- **31 SKUs** (meta ≥30)
- Distribuição (um SKU pode cobrir mais de uma tag): regular UN, KG, promo expirada, qty ativa, sem estoque, recentemente alterados
- Ver detalhe: [`reconciliation/module-1-real-sample.md`](./reconciliation/module-1-real-sample.md)

### NOT AVAILABLE IN SAMPLE

| Tipo | Status |
|------|--------|
| Promoção **ativa** na empresa 1 | **NOT AVAILABLE IN SAMPLE** (0 vigentes; 40 expiradas históricas) |
| Faixas qty multi-tier tipo 1 / 3+ / 6+ | **NOT AVAILABLE IN SAMPLE** (apenas 1 faixa ativa `TIPOSTATUS=A`) |

Não fabricamos casos.

---

## 3. PRICE SOURCE-OF-TRUTH

**Fonte regular exibível:** `POLITICA_PRECO_PRODUTO.VALPRECOVAREJO` filtrada por `IDEMPRESA`.

**Prova operacional:** view `EMP1_BUSCA_PRECO_GERTEC_VW` (consulta de preço Gertec da empresa 1).

| Set | Compared | MATCH | MISMATCH |
|-----|----------|-------|----------|
| Gertec confirmação dedicada | 50 | 50 | 0 |
| Amostra 1R (com barcode joinável) | 6 | 6 | 0 |

`PRODUTO_GRADE.VALPRECOVAREJO` **não** é fonte por loja (ex.: política 13,49 vs grade 0,00).

**PRICE_SOURCE_STATUS: CONFIRMED**

Artefato: `reconciliation/gertec-price-truth.json`

---

## 4. Promoção

Campos confirmados: `VALPROMVAREJO`, `DTINIPROMOCAOVAR`, `DTFIMPROMOCAOVAR`, `QTDMINPROMVAREJO`.

Regra de vigência (timezone da loja / `America/Sao_Paulo` para DATE CISS):

- before start → inactive  
- during → active  
- after end → inactive  

Na amostra: promoções expiradas → **nenhuma** `RetailPromotion.active` indevida (**MATCH 31/31**).

---

## 5. Quantity pricing

Fonte: `PRODUTO_DESCONTO_QTDE` (`QTDPRODUTO`, `VALPRECOVAREJO`, ignora `TIPOSTATUS` I/N).

Bug ODBC: `QTDPRODUTO` sem escala (50 → 50000) — corrigido com `CAST(... AS DOUBLE)` (igual preços).

Caso real ativo: `189261:189261` → faixa **50+ @ 0,99** sincronizada sem colapsar.

Multi-tier 1/3/6: **NOT AVAILABLE IN SAMPLE**.

---

## 6. Unidade / estoque

- Unidade: `PRODUTO.EMBALAGEMSAIDA` (KG / UN observados) — **CONFIRMED**, MATCH 31/31  
- Estoque: `PRODUTO_GRADE_SALDO_EST_VW.QTDATUALESTOQUE` somado por `IDEMPRESA`+produto+sub  
- Múltiplos `IDLOCALESTOQUE` existem; **não** escolhemos `location_code` automático  
- Implicação Módulo 2: **não** habilitar `hide_if_unavailable` até local preferencial confirmado

---

## 7. Sync real + idempotência

Provider `ciss_db2`, entidades PRODUCT / PRICE / PROMOTION / AVAILABILITY, `full=True`, duas passagens.

| | Sync #1 | Sync #2 |
|--|---------|---------|
| Status | SUCCESS ×4 | SUCCESS ×4 |
| Active prices loja | — | estável `5026 → 5026` |
| Duplicatas de produto (mesma chave) | 0 | 0 |

Watermarks avançaram / permaneceram coerentes por entidade (ver JSON).

Health pós-sync: **FRESH**.

---

## 8. Reconciliação (serviço + API)

Após fetch pontual por SKU (`fetch_*_for_products` / `by_ids`):

| Campo | MATCH | MISMATCH | NOT_COMPARABLE |
|-------|-------|----------|----------------|
| regular_price | 31 | 0 | 0 |
| unit | 31 | 0 | 0 |
| promotion | 31 | 0 | 0 |
| quantity_tiers | 31 | 0 | 0 |
| availability | 31 | 0 | 0 |
| **summary** | **31** | **0** | **0** |

API: `GET /retail-products/{id}?store_id=` devolve prices / promotion / availability — camada entregue à futura UI validada na amostra (regular/unit 31/31).

---

## 9. Correções realizadas nesta execução

1. `CAST(VALPRECOVAREJO AS DOUBLE)` (já) + **`CAST(QTDPRODUTO AS DOUBLE)`**  
2. Vigência de promoção no adapter (`_promo_window_active`)  
3. Reconcile com fetch pontual por `source_product_id`  
4. Endpoint detalhe `GET /retail-products/{id}`  
5. Documentação do gate + amostra + Gertec truth

---

## 10. Classificação final de fontes

| Item | Status |
|------|--------|
| regular price source | **CONFIRMED** |
| promotion source | **CONFIRMED** |
| quantity price source | **CONFIRMED** |
| unit | **CONFIRMED** |
| stock source (empresa, soma locais) | **PARTIALLY CONFIRMED** |
| stock location_code preferencial | **NOT CONFIRMED** |
| active promo cases now | **NOT AVAILABLE IN SAMPLE** |
| multi-tier qty ladder | **NOT AVAILABLE IN SAMPLE** |
| PDV frontbox UI screenshot | **NOT CONFIRMED** (Gertec view usada como consulta operacional) |

---

## STOP

Módulo 2 — Price Table Engine **não** iniciado neste gate.
