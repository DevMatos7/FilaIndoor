# Dynamic Retail Content — Progresso

| Módulo | Status |
|--------|--------|
| 1 Retail Data Foundation | `FINAL HOMOLOGATION: PASS` |
| 1R Real CISS Reconciliation | `PASS` |
| 1R.1 Store timezone | `PASS` (`America/Cuiaba`) |
| 2 Price Table Engine | `HOMOLOGATED` · visual PASS |
| 3 Dynamic Playlist & Player | `HOMOLOGATED` |
| 4 Product Visual Engine | `READY FOR HOMOLOGATION` |
| 5 Automation & Resilience | `NOT STARTED` |
| 6 Visual QA / Pilot Gate | `NOT STARTED` |

## Travas preservadas

- `hide_if_unavailable` / `available_only` = **DISABLED BY DESIGN**
- `PROMOTION ENGINE: PASS` · `REAL ACTIVE PROMOTION: PENDING`
- `MULTI-TIER ENGINE: PASS` · `REAL MULTI-TIER: PENDING`
- `CISS IMAGE SOURCE: NOT_USABLE` (associação manual via Media Library)

## Module 4 notas

- `ProductMediaLink` → `MediaAsset` (MANUAL); sem import CISS filesystem
- Renderers: Grid / Hero / PromotionBoard + PriceTable (shared admin/TV)
- Screenshots: `docs/dynamic-retail-content/screenshots/module-4/`
