# Module 6 — Pilot Defect Register

## P0

*Nenhum aberto após correções do gate.*

| ID | Título | Status | Correção |
|----|--------|--------|----------|
| DRC6-P0-01 | Descrição TV = `source_product_id` (4777 SKUs via `_ensure_minimal_product`) | **FIXED** | Placeholder sem ID; `price_resolver` bloqueia ID/GTIN; repair CISS em 4777 SKUs |

## P1

*Nenhum aberto.*

## P2

| ID | Título | Status | Nota |
|----|--------|--------|------|
| DRC6-P2-01 | API Docker `RETAIL_PROVIDER=mock` enquanto host gate usa `ciss_db2` | OPEN | Admin mostra Fonte:MOCK; piloto deve rodar API com `ciss_db2` |
| DRC6-P2-02 | Media import host ≠ volume Docker | OPEN | Requer `docker cp`/volume compartilhado após import CISS no host |
| DRC6-P2-03 | Cobertura imagem CISS inicial baixa (~0,07% no gate; cresce por ciclo) | OPEN | Incremental OK; import completo leva vários ciclos de 200 SKUs |
| DRC6-P2-04 | Captura Hero vs Grid race na playlist da TV | OPEN | Payload hero OK; timing de captura às vezes pega item seguinte |
| DRC6-P2-05 | Imagens CISS ~200×200 em Hero/4K | OPEN | Aceitável; não alta resolução |

## P3

| ID | Título | Status |
|----|--------|--------|
| DRC6-P3-01 | Copy admin / polish baseline | OPEN |
| DRC6-P3-02 | Scripts `_m6_debug_*` de diagnóstico | OPEN | Não fazem parte do runtime |

## Aceites explícitos para CONDITIONAL GO

- STOCK FILTER DISABLED BY DESIGN
- PHYSICAL HARDWARE VALIDATION: PENDING
- RELEASE DELIVERY: local `main` ahead of `origin/main` (sem push automático)
- Cobertura de imagem CISS parcial com fallback visual
