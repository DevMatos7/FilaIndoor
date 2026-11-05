# Module 1R — Real sample

> Price source-of-truth (além desta amostra): `gertec-price-truth.json` — **50/50 MATCH** `EMP1_BUSCA_PRECO_GERTEC_VW` ↔ `POLITICA_PRECO_PRODUTO` → **CONFIRMED**.  
> Relatório: [`../03-real-ciss-reconciliation.md`](../03-real-ciss-reconciliation.md).

**Date (UTC):** 2026-11-05
**Store day:** 2026-11-05 (`America/Cuiaba`)
**Store app:** Loja Campo Novo (`c73b48c6-9646-4dee-854a-b65eb212b8ad`) timezone=`America/Cuiaba`
**IDEMPRESA:** 1 — Supermercado Real / Casagrande & Cia Ltda - EPP
**Mapping:** company_code=`1` location_code=`None` active=True
**Correspondência:** loja piloto app «Loja Campo Novo» ↔ CISS empresa 1 «Supermercado Real» (matriz Supermercado Real / Casagrande).
**SKUs na amostra:** 31

## Disponibilidade de buckets CISS

| Bucket | Candidates | Gate note |
|--------|------------|-----------|
| kg | 30 |  |
| no_stock | 20 |  |
| promo_expired | 20 |  |
| qty | 1 |  |
| recent | 20 |  |
| regular_un | 40 |  |

- promo_active: **NOT AVAILABLE IN SAMPLE**
- qty multi-tier (1/3/6): **NOT AVAILABLE IN SAMPLE**
- qty single active: **AVAILABLE**
- Gertec vs política (amostra): compared=6 MATCH=6 MISMATCH=0 missing_barcode=25

## SKUs

### 1. `100153:100153` — MEXIRICA MORGOTE KG

- tags: promo_expired
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **5.98** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 4.98 (2018-09-12 → 2018-09-19) min=0.0 status=**AFTER_END**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '2544a45b-c7c3-4bb2-83de-6023651abf28', 'description': 'MEXIRICA MORGOTE KG', 'unit': 'KG', 'regular': 5.98, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '2544a45b-c7c3-4bb2-83de-6023651abf28', 'source_product_id': '100153:100153', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 5.98}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 2. `167059:167059` — SUCO PO FRESH LARANJA 15G

- tags: promo_expired
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **0.78** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.59 (2017-08-31 → 2017-11-30) min=0.0 status=**AFTER_END**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': 'f7e0157a-99ba-4945-ad6f-9aa6ce60e1a3', 'description': 'SUCO PO FRESH LARANJA 15G', 'unit': 'UN', 'regular': 0.78, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'f7e0157a-99ba-4945-ad6f-9aa6ce60e1a3', 'source_product_id': '167059:167059', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 0.78}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 3. `159731:159731` — TEMP ADORALLE CARNE/LEG/ARROZ 50G

- tags: promo_expired
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **2.69** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 2.29 (2017-08-10 → 2017-09-19) min=0.0 status=**AFTER_END**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': '82d56716-03f3-41df-ba6a-f02eaca75702', 'description': 'TEMP ADORALLE CARNE/LEG/ARROZ 50G', 'unit': 'UN', 'regular': 2.69, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '82d56716-03f3-41df-ba6a-f02eaca75702', 'source_product_id': '159731:159731', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 2.69}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 4. `189261:189261` — BOMBOM LACTA SONHO VALSA 20G

- tags: qty
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **0.99** | Gertec: 0.99 (MATCH)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[{'min_qty': 50.0, 'amount': 0.99, 'status': 'A'}]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '979b128e-ed27-46d0-bebe-372f3f031f7e', 'description': 'BOMBOM LACTA SONHO VALSA 20G', 'unit': 'UN', 'regular': 0.99, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [{'min_qty': 50.0, 'amount': 0.99}], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '979b128e-ed27-46d0-bebe-372f3f031f7e', 'source_product_id': '189261:189261', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 0.99}, {'price_kind': 'QUANTITY', 'amount': 0.99, 'min_qty': 50.0}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'MATCH', 'store_company': 'MATCH'}`

### 5. `115235:115237` — CS PE  CASAGRANDE

- tags: kg
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **12.35** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': 'd58f681f-67ee-4c94-b551-c0b0f9788398', 'description': 'CS PE  CASAGRANDE', 'unit': 'KG', 'regular': 12.35, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'd58f681f-67ee-4c94-b551-c0b0f9788398', 'source_product_id': '115235:115237', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 12.35}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 6. `127:127` — CS LOMBO SADIA TEMP CONG KG

- tags: kg
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **20.79** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': 'af23f4f1-5054-44b5-9e7c-907e15c66a4b', 'description': 'CS LOMBO SADIA TEMP CONG KG', 'unit': 'KG', 'regular': 20.79, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'af23f4f1-5054-44b5-9e7c-907e15c66a4b', 'source_product_id': '127:127', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 20.79}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 7. `135:135` — PRES SADIA COZ S/CAPA GORDURA

- tags: kg
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **31.98** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}, {'local': 6, 'qty': 0.0}, {'local': 10, 'qty': 0.0}, {'local': 11, 'qty': 0.0}], 'total': 0.0, 'locals_count': 5}`
- canonical: `{'product_id': '59651858-dad3-4c17-9f9b-f47b4512af66', 'description': 'PRES SADIA COZ S/CAPA GORDURA', 'unit': 'KG', 'regular': 31.98, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '59651858-dad3-4c17-9f9b-f47b4512af66', 'source_product_id': '135:135', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 31.98}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 8. `167406:167406` — SALGADINHO FEST REAL KG

- tags: kg
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **26.99** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': 'd7fe44f4-b9b6-4d73-b1ad-25799cc1f8f9', 'description': 'SALGADINHO FEST REAL KG', 'unit': 'KG', 'regular': 26.99, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'd7fe44f4-b9b6-4d73-b1ad-25799cc1f8f9', 'source_product_id': '167406:167406', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 26.99}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 9. `5109:5109` — NEUTRALIZ ODORES BOM AR AERO CED/LAR 360ML

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **8.99** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 10, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': 'd2022b7d-b28b-4ffc-9586-ffc1c6275ed7', 'description': 'NEUTRALIZ ODORES BOM AR AERO CED/LAR 360ML', 'unit': 'UN', 'regular': 8.99, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'd2022b7d-b28b-4ffc-9586-ffc1c6275ed7', 'source_product_id': '5109:5109', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 8.99}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 10. `157042:157042` — VINHO ITA VALDORELLA CHIANTI TTO  750ML

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **56.88** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': 'de13d3d6-3ae1-48d3-bf8c-ad41ddf23fdc', 'description': 'VINHO ITA VALDORELLA CHIANTI TTO  750ML', 'unit': 'UN', 'regular': 56.88, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'de13d3d6-3ae1-48d3-bf8c-ad41ddf23fdc', 'source_product_id': '157042:157042', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 56.88}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 11. `157043:157043` — BALA TIC TAC MACA VERDE/MARACUJA 16G

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **1.49** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '86aede12-5731-4072-b225-d370f91b7dc7', 'description': 'BALA TIC TAC MACA VERDE/MARACUJA 16G', 'unit': 'UN', 'regular': 1.49, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '86aede12-5731-4072-b225-d370f91b7dc7', 'source_product_id': '157043:157043', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 1.49}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 12. `157046:157046` — ABS INT DAYS S/ABAS 40UN

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **10.49** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': 'aa958575-7e07-4567-8007-9bffcf80599b', 'description': 'ABS INT DAYS S/ABAS 40UN', 'unit': 'UN', 'regular': 10.49, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'aa958575-7e07-4567-8007-9bffcf80599b', 'source_product_id': '157046:157046', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 10.49}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 13. `1:1` — PRODUTO GERAL

- tags: no_stock
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **988.0** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 2, 'qty': 0.0}, {'local': 6, 'qty': 0.0}, {'local': 10, 'qty': 0.0}, {'local': 11, 'qty': 0.0}], 'total': 0.0, 'locals_count': 5}`
- canonical: `{'product_id': '6ac01ca5-60ce-4b8f-96df-24d8103fe21e', 'description': 'PRODUTO GERAL', 'unit': 'UN', 'regular': 988.0, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '6ac01ca5-60ce-4b8f-96df-24d8103fe21e', 'source_product_id': '1:1', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 988.0}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 14. `2:2` — PEIXE TAMBACU CASA PEIXE C/ESC KG

- tags: no_stock
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **13.49** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}, {'local': 6, 'qty': 0.0}], 'total': 0.0, 'locals_count': 3}`
- canonical: `{'product_id': '008ad562-6219-4394-96f3-494394cf419f', 'description': 'PEIXE TAMBACU CASA PEIXE C/ESC KG', 'unit': 'KG', 'regular': 13.49, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '008ad562-6219-4394-96f3-494394cf419f', 'source_product_id': '2:2', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 13.49}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 15. `9:9` — JILO

- tags: no_stock
- IDEMPRESA / unit: 1 / `KG`
- CISS regular: **4.98** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '8cb4e397-430d-447b-ab56-7e8fa936bcb8', 'description': 'JILO', 'unit': 'KG', 'regular': 4.98, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '8cb4e397-430d-447b-ab56-7e8fa936bcb8', 'source_product_id': '9:9', 'unit': 'KG', 'prices': [{'price_kind': 'REGULAR', 'amount': 4.98}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 16. `142883:245726` — CESTA NATAL PREMIUM ATACADO

- tags: recent
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **123.58** | Gertec: 123.58 (MATCH)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [], 'total': 0, 'locals_count': 0}`
- canonical: `{'product_id': 'd447cc05-d279-4110-9866-89ca40e918f7', 'description': 'CESTA NATAL PREMIUM ATACADO', 'unit': 'UN', 'regular': 123.58, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'd447cc05-d279-4110-9866-89ca40e918f7', 'source_product_id': '142883:245726', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 123.58}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'MATCH', 'store_company': 'MATCH'}`

### 17. `142883:245728` — CESTA NATAL PREMIUM ATACADO

- tags: recent
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **155.87** | Gertec: 155.87 (MATCH)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [], 'total': 0, 'locals_count': 0}`
- canonical: `{'product_id': '3177b366-862c-428d-8ffa-77336114d8db', 'description': 'CESTA NATAL PREMIUM ATACADO', 'unit': 'UN', 'regular': 155.87, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '3177b366-862c-428d-8ffa-77336114d8db', 'source_product_id': '142883:245728', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 155.87}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'MATCH', 'store_company': 'MATCH'}`

### 18. `142883:245724` — CESTA NATAL PREMIUM ATACADO

- tags: recent
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **128.98** | Gertec: 128.98 (MATCH)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [], 'total': 0, 'locals_count': 0}`
- canonical: `{'product_id': 'f62cbac1-5a61-4834-8863-b1ab91d7311a', 'description': 'CESTA NATAL PREMIUM ATACADO', 'unit': 'UN', 'regular': 128.98, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'f62cbac1-5a61-4834-8863-b1ab91d7311a', 'source_product_id': '142883:245724', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 128.98}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'MATCH', 'store_company': 'MATCH'}`

### 19. `157047:157047` — FAQUEIRO TRAMONTINA 42 PCS C/ESTOJO ACO INOX

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **551.89** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '29bfba14-a201-49e8-add0-2d668586fa24', 'description': 'FAQUEIRO TRAMONTINA 42 PCS C/ESTOJO ACO INOX', 'unit': 'UN', 'regular': 551.89, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '29bfba14-a201-49e8-add0-2d668586fa24', 'source_product_id': '157047:157047', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 551.89}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 20. `157048:157048` — SABON LIQ TRICOFACIL MOR 2LT

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **24.69** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': 'b672dea6-717a-49d2-b911-8bbc36ec6a66', 'description': 'SABON LIQ TRICOFACIL MOR 2LT', 'unit': 'UN', 'regular': 24.69, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'b672dea6-717a-49d2-b911-8bbc36ec6a66', 'source_product_id': '157048:157048', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 24.69}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 21. `157049:157049` — SABON LIQ TRICOFACIL NEUTRO 2LT

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **21.59** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': 'd1f23e0c-1b39-49d9-a49a-8377a6a8d6a6', 'description': 'SABON LIQ TRICOFACIL NEUTRO 2LT', 'unit': 'UN', 'regular': 21.59, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'd1f23e0c-1b39-49d9-a49a-8377a6a8d6a6', 'source_product_id': '157049:157049', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 21.59}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 22. `157050:157050` — ESPONJA LIMPPANO MULTIUSO 3UN

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **3.39** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [], 'total': 0, 'locals_count': 0}`
- canonical: `{'product_id': '88344932-e3be-44df-8008-eff7dd8108e1', 'description': 'ESPONJA LIMPPANO MULTIUSO 3UN', 'unit': 'UN', 'regular': 3.39, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '88344932-e3be-44df-8008-eff7dd8108e1', 'source_product_id': '157050:157050', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 3.39}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 23. `157051:157051` — PASSA FIO DENTAL D.CLEAN LV60PG50 UN

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **13.98** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': 'c26878fc-d3d8-4750-960e-0461c4589287', 'description': 'PASSA FIO DENTAL D.CLEAN LV60PG50 UN', 'unit': 'UN', 'regular': 13.98, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'c26878fc-d3d8-4750-960e-0461c4589287', 'source_product_id': '157051:157051', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 13.98}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 24. `157293:157293` — COLA CASCOLA EXTRA SEM TOLUOL 30GR

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **4.99** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': '4ef4576e-7133-4bb6-9a5d-4eb2ef4a8423', 'description': 'COLA CASCOLA EXTRA SEM TOLUOL 30GR', 'unit': 'UN', 'regular': 4.99, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '4ef4576e-7133-4bb6-9a5d-4eb2ef4a8423', 'source_product_id': '157293:157293', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 4.99}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 25. `157053:157053` — ESC DENTALCLEAN 5500 SENSITIVE ULT MAC UN

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **15.9** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '382ed5d9-8cbb-4d1b-872e-973430f8f8e1', 'description': 'ESC DENTALCLEAN 5500 SENSITIVE ULT MAC UN', 'unit': 'UN', 'regular': 15.9, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '382ed5d9-8cbb-4d1b-872e-973430f8f8e1', 'source_product_id': '157053:157053', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 15.9}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 26. `157054:157054` — RACAO P/CAES ADUL SOMAXX PCT 15KG

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **136.59** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': 'd35f8546-ecf7-40c1-b754-572376213f4c', 'description': 'RACAO P/CAES ADUL SOMAXX PCT 15KG', 'unit': 'UN', 'regular': 136.59, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'd35f8546-ecf7-40c1-b754-572376213f4c', 'source_product_id': '157054:157054', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 136.59}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 27. `157055:157055` — RACAO P/CAES RPM CANISTER EQUIL PCT 15KG

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **99.89** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '6b8cf3d4-0001-497b-9b42-154784e69729', 'description': 'RACAO P/CAES RPM CANISTER EQUIL PCT 15KG', 'unit': 'UN', 'regular': 99.89, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '6b8cf3d4-0001-497b-9b42-154784e69729', 'source_product_id': '157055:157055', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 99.89}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 28. `157294:157294` — COLA CASCOLA FLEXITE USO GERAL 50GR

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **3.49** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}, {'local': 3, 'qty': 0.0}], 'total': 0.0, 'locals_count': 2}`
- canonical: `{'product_id': '1959b26f-b126-4d26-b21f-cc3016a47e78', 'description': 'COLA CASCOLA FLEXITE USO GERAL 50GR', 'unit': 'UN', 'regular': 3.49, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '1959b26f-b126-4d26-b21f-cc3016a47e78', 'source_product_id': '157294:157294', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 3.49}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 29. `157056:157056` — RACAO P/CAES FILHOTE NUTRI CANISTER NAT PCT 15KG

- tags: regular_un
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **99.89** | Gertec: None (NOT_COMPARABLE)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [{'local': 1, 'qty': 0.0}], 'total': 0.0, 'locals_count': 1}`
- canonical: `{'product_id': '86581644-a1b8-453b-a1e6-6e59d4808410', 'description': 'RACAO P/CAES FILHOTE NUTRI CANISTER NAT PCT 15KG', 'unit': 'UN', 'regular': 99.89, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '86581644-a1b8-453b-a1e6-6e59d4808410', 'source_product_id': '157056:157056', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 99.89}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'NOT_COMPARABLE', 'store_company': 'MATCH'}`

### 30. `146018:146018` — CESTA BASICA ATACADO

- tags: recent
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **123.95** | Gertec: 123.95 (MATCH)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [], 'total': 0, 'locals_count': 0}`
- canonical: `{'product_id': '383bda1b-9ae4-4574-8cfa-579ebf09585d', 'description': 'CESTA BASICA ATACADO', 'unit': 'UN', 'regular': 123.95, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': '383bda1b-9ae4-4574-8cfa-579ebf09585d', 'source_product_id': '146018:146018', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 123.95}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'MATCH', 'store_company': 'MATCH'}`

### 31. `212427:245211` — CESTA DIA DAS CRIANCAS REAL

- tags: recent
- IDEMPRESA / unit: 1 / `UN`
- CISS regular: **83.9** | Gertec: 83.9 (MATCH)
- CISS promo: 0.0 (None → None) min=0.0 status=**NO_PROMO**
- quantity tiers: `[]`
- stock: `{'by_local': [], 'total': 0, 'locals_count': 0}`
- canonical: `{'product_id': 'f22f8d42-8cce-4692-95d4-f8665019ce63', 'description': 'CESTA DIA DAS CRIANCAS REAL', 'unit': 'UN', 'regular': 83.9, 'promo_active': None, 'promo_start': None, 'promo_end': None, 'qty_tiers': [], 'available': False, 'stock_qty': 0.0}`
- API: `{'id': 'f22f8d42-8cce-4692-95d4-f8665019ce63', 'source_product_id': '212427:245211', 'unit': 'UN', 'prices': [{'price_kind': 'REGULAR', 'amount': 83.9}], 'promotion': None, 'availability': {'available': False, 'current_stock_qty': 0.0}}`
- results: `{'regular': 'MATCH', 'unit': 'MATCH', 'promo': 'MATCH', 'qty_tiers': 'MATCH', 'api_regular': 'MATCH', 'api_unit': 'MATCH', 'stock': 'MATCH', 'gertec': 'MATCH', 'store_company': 'MATCH'}`
