# Dynamic Retail Content — Progresso

| Módulo | Status |
|--------|--------|
| 1 Retail Data Foundation | `FINAL HOMOLOGATION: PASS` |
| 1R Real CISS Reconciliation | `PASS` |
| 1R.1 Store timezone | `PASS` (`America/Cuiaba`) |
| 2 Price Table Engine | `TECHNICAL HOMOLOGATION: PASS` · visual fechado no M3 |
| 3 Dynamic Playlist & Player | `READY FOR HOMOLOGATION` |
| 4 Product Visual Engine | `NOT STARTED` |
| 5 Automation & Resilience | `NOT STARTED` |
| 6 Visual QA / Pilot Gate | `NOT STARTED` |

## Travas preservadas

- `hide_if_unavailable` / `available_only` = **DISABLED BY DESIGN**
- `PROMOTION ENGINE: PASS` · `REAL ACTIVE PROMOTION: PENDING`
- `MULTI-TIER ENGINE: PASS` · `REAL MULTI-TIER: PENDING`

## Module 3 notas

- Renderer único: `PriceTableRenderer` (admin = TV)
- SKU não vira descrição comercial na TV
- Player não usa preview draft — só snapshot persistido/current
- Screenshots: `docs/dynamic-retail-content/screenshots/module-3/`
