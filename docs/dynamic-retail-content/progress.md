# Dynamic Retail Content — Progresso

| Módulo | Status |
|--------|--------|
| 1 Retail Data Foundation | `FINAL HOMOLOGATED` |
| 1R Real CISS Reconciliation | `PASS` |
| 1R.1 Store timezone | `PASS` (`America/Cuiaba`) |
| 2 Price Table Engine | `FINAL HOMOLOGATED` |
| 3 Dynamic Playlist & Player | `FINAL HOMOLOGATED` |
| 4 Product Visual Engine | `FINAL HOMOLOGATED` |
| 5 Automation & Resilience | `FINAL HOMOLOGATED` |
| 5R CISS Offers & Product Images | `FINAL HOMOLOGATED` |
| 6 Visual QA / Pilot Gate | `CONDITIONAL GO` · `FINAL HOMOLOGATED` (com condições) |

## Travas preservadas

- `hide_if_unavailable` / `available_only` = **DISABLED BY DESIGN**
- **STOCK COMMERCIAL SOURCE: NOT CONFIRMED**
- `PROMOTION ENGINE: PASS` · `REAL ACTIVE PROMOTION: PASS`
- `MULTI-TIER ENGINE: PASS` · `REAL MULTI-TIER: PASS` (ex. “A PARTIR DE 50” em SKU real)
- `CISS IMAGE PATH SOURCE: NOT_USABLE`
- `CISS IMAGE BLOB SOURCE: USABLE` (FOTOPRINCIPAL; placeholder LENGTH=4912 excluído)
- `CISS OFFER SOURCE: CONFIRMED` · `PRICE CHAIN: CONFIRMED`
- **PRODUCTION MOCK GUARD: PASS**
- **PRODUCT_IMAGE incremental:** fingerprint meta-only no 2º sync (`blob_reads=0`)

## Module 6 artefatos

- Matrix: `09-final-qa-matrix.md`
- Defects: `10-pilot-defects.md`
- Readiness: `11-pilot-readiness-report.md`
- Gate JSON: `reconciliation/module-6-pilot-gate.json`
- Screenshots: `screenshots/module-6/{admin,display}/`
- Playwright: `frontend/e2e/specs/09-drc6-pilot-gate.spec.ts`

## STOP

Não iniciar Proof of Play / Retail Media / Device Commands / Stock Intelligence / AI.
