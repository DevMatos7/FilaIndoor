# Dynamic Retail Content — Progresso

| Módulo | Status |
|--------|--------|
| 1 Retail Data Foundation | `FINAL HOMOLOGATION: PASS` |
| 1R Real CISS Reconciliation | `PASS` |
| 1R.1 Store timezone | `PASS` (`America/Cuiaba`) |
| 2 Price Table Engine | `HOMOLOGATED` · visual PASS |
| 3 Dynamic Playlist & Player | `HOMOLOGATED` |
| 4 Product Visual Engine | `HOMOLOGATED` |
| 5 Automation & Resilience | `READY FOR HOMOLOGATION` |
| 6 Visual QA / Pilot Gate | `NOT STARTED` |

## Travas preservadas

- `hide_if_unavailable` / `available_only` = **DISABLED BY DESIGN**
- **STOCK COMMERCIAL SOURCE: NOT CONFIRMED**
- `PROMOTION ENGINE: PASS` · `REAL ACTIVE PROMOTION: PENDING`
- `MULTI-TIER ENGINE: PASS` · `REAL MULTI-TIER: PENDING`
- `CISS IMAGE SOURCE: NOT_USABLE` (associação manual via Media Library)
- **PRODUCTION MOCK GUARD: PASS** (`APP_ENV=production` + `RETAIL_PROVIDER=mock` → fail-fast)

## Module 5 notas

- APScheduler store-scoped + Postgres advisory lock
- Impact resolver + WS `dynamic_content.invalidated` (store-scoped)
- `valid_until` com boundaries de promoção (end inclusive) + freshness soft cap
- Player: prefetch + safe page boundary; STALE → skip urgente
- Docs: `07-automation-resilience.md`
- Screenshots: `docs/dynamic-retail-content/screenshots/module-5/`
