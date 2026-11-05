# FASE 2 — Progresso

| Gate | Nome | Status |
|------|------|--------|
| P0 | Release Candidate | `IN PROGRESS` — remoto + tag OK; falta SLA + inventário + aceite loja |
| P1 | Instalação loja piloto | `BLOCKED` (aguarda fechamento P0 humano) |
| P2 | Operação assistida | `PLANNED` |
| P3 | Observação 7 / 14 / 30 dias | `PLANNED` |
| P4 | Lições e defeitos reais | `PLANNED` |
| P5 | Go / No-Go rollout | `PLANNED` |
| P6 | Roadmap pós-piloto | `PLANNED` |

## Decisões travadas

- Resiliência Piloto 1: **ONLINE-DEPENDENT**
- Productization: **CONDITIONAL GO** / Display 2.0: **GO**
- Sem features novas durante P0–P3

## Release Delivery

| Item | Status |
|------|--------|
| Push `main` | **GO** (`95ae83a`) |
| Tag `rc-pilot-1` | **GO** |
| RELEASE DELIVERY | **GO** |

Ver `rc-notes.md`.

## Próximo passo

1. Confirmar SLA do piloto (600/900 ou outra política)  
2. Preencher `02-install-checklist.md` (loja, devices, contatos)  
3. Colher aceite ONLINE-DEPENDENT  
4. Fechar P0 → liberar **P1 Instalação**
