# Module 6 — Final QA Matrix

**Store:** Loja Campo Novo · IDEMPRESA `1` · `America/Cuiaba`  
**Provider (host gate):** `ciss_db2`  
**Evidence root:** `docs/dynamic-retail-content/screenshots/module-6/`  
**Reconciliation:** `reconciliation/module-6-pilot-gate.json`

| ID | Area | Scenario | Data source | Viewport | Evidence | Result | Defect |
|----|------|----------|-------------|----------|----------|--------|--------|
| DRC6-G01 | Env | Production mock guard | fixture Settings | — | gate JSON | PASS | — |
| DRC6-G02 | Store | Campo Novo / IDEMPRESA 1 / TZ | CISS+DB | — | gate JSON | PASS | — |
| DRC6-G03 | Health | Commercial entities sync | CISS | — | A07 | PASS | Docker UI still labels Fonte:MOCK (API container) |
| DRC6-G04 | Price | ≥30 SKU CISS=DB | REAL CISS | — | gate sample | PASS | mismatches=0 |
| DRC6-G05 | Offer | Active PROMOCAO_GESTAO → RetailOffer | REAL CISS | — | seed + D04 | PASS | Emp1 uses PRICED_ITEMS scope fallback |
| DRC6-G06 | Offer price | DIRECT + WEIGHT formula | CISS+fixture | — | gate + unit | PASS | Real WEIGHT_CONVERTED if present |
| DRC6-G07 | Image | FOTOPRINCIPAL import + identity | REAL CISS | — | gate + D02 | PASS | — |
| DRC6-G08 | Image | Placeholder 4912 skipped | REAL CISS | — | gate | PASS | — |
| DRC6-G09 | Image | Incremental 2nd sync blob_reads | REAL CISS | — | gate metrics | PASS | fingerprint meta-only |
| DRC6-G10 | Desc | No source_product_id on TV | REAL | 1920 | D01–D04 | PASS | P0 fixed (repair 4777) |
| DRC6-V01 | Admin | Overview | mixed | 1366 | A01 | PASS | — |
| DRC6-V02 | Admin | Products / CISS source | mixed | 1366 | A02–A03 | PASS WITH DEBT | coverage still growing |
| DRC6-V03 | Admin | Tables / Vitrines / Offer | mixed | 1366 | A04–A06 | PASS | — |
| DRC6-V04 | Admin | Sync healthy | mixed | 1366 | A07–A08 | PASS WITH DEBT | Fonte:MOCK in docker |
| DRC6-D01 | Display | PRICE_TABLE real | REAL | 1920 | D01 | PASS | — |
| DRC6-D02 | Display | PRODUCT_GRID + CISS image | REAL | 1920 | D02 | PASS | ~200×200 CISS JPEG adequada |
| DRC6-D03 | Display | PRODUCT_HERO | REAL | 1920 | D03 | PASS WITH DEBT | capture sometimes lands on grid if playlist race |
| DRC6-D04 | Display | PROMOTION_BOARD CISS_OFFER | REAL | 1920 | D04 | PASS | DE/POR + OFERTA |
| DRC6-D05 | Display | QUEUE_CALL over dynamic | REAL | 1920 | D05 | PASS WITH DEBT | footer always shows senha; full overlay timing soft |
| DRC6-D06 | Display | Timer resume | REAL | 1920 | D06 | PASS WITH DEBT | engine homologated M3/M5 |
| DRC6-D07 | Display | Mixed playlist | REAL | 1920 | D07 | PASS | — |
| DRC6-D08 | Display | Stale fallback | fixture+engine | 1920 | D08 | PASS | M5 evidence reused/soft |
| DRC6-D09 | Display | Recovery | REAL | 1920 | D09 | PASS | — |
| DRC6-D10 | Display | 4K | REAL | 3840 | D10 | PASS | CISS images low-res upscaled = aceitável |
| DRC6-D11 | Display | Portrait | REAL | 1080×1920 | D11 | PASS | — |
| DRC6-S01 | Security | No BLOB/HEX/secrets in health | — | — | gate | PASS | — |
| DRC6-S02 | Stock | available_only impossible | — | — | health | PASS | DISABLED BY DESIGN |
| DRC6-R01 | Release | origin/main updated | git | — | status | FAIL | local ahead 7; no auto-push |

## Visual review notes

| Shot | Verdict | Comment |
|------|---------|---------|
| D01 | PASS | Tabela real, nomes comerciais, UN/KG, rodapé fila |
| D02 | PASS | Imagens CISS reais (Sonho de Valsa / Presunto) |
| D03 | PASS WITH DEBT | Conteúdo dinâmico ok; hero vs grid race em captura |
| D04 | PASS | Board CISS_OFFER com DE/POR |
| D05–D06 | PASS WITH DEBT | Integração fila presente; override timing soft |
| A07 | PASS WITH DEBT | Health FRESH; label MOCK no container |
