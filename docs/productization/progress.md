# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `HOMOLOGATED` | `03-design-system.md` |
| UX-2 App Shell + IA | `HOMOLOGATED` | `02-information-architecture.md` · `04-admin-shell.md` |
| UX-3 Command Center | `HOMOLOGATED` | `05-command-center.md` |
| UX-4 Totem 2.0 | `HOMOLOGATED` | `06-totem.md` |
| UX-5 Operator 2.0 | `READY FOR HOMOLOGATION` | `07-operator.md` |
| UX-6A Display Public Mode | `PLANNED` | — |
| UX-6B Layout Engine | `PLANNED` | — |
| UX-6C Screen Override | `PLANNED` | — |
| UX-7 Media Library | `PLANNED` | — |
| UX-8 Playlist Studio | `PLANNED` | — |
| UX-9 Programming Studio | `PLANNED` | — |
| UX-10 Screen & Device Fleet | `PLANNED` | — |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## Decisões UX-5

- Operator = botoeira digital (não admin); link Admin removido.
- NEXT/RECALL/NO_SHOW/COMPLETE preservados; `auto_complete_current`+`auto_start` mantidos (já existiam).
- Estados derivados PRONTO/ATENDENDO/ENCERRADO/PAUSADO — sem presence persistente.
- Terminal persistido em `localStorage.operator_terminal`; seleção por cards.
- NO_SHOW sem modal (proteção visual); documentado em `07-operator.md`.
- Diagnostics do totem endurecido: `/auth/me` + roles admin/manager.

## Débitos (roadmap)

- UX-4: **Offline issue real / Edge local ticketing** (outbox sem senha local).
- UX-5+: **Operator Presence / Capacity** (AVAILABLE/SERVING/PAUSED/OFFLINE).
- UX-3: N+1 `queue_status` no agregador em lojas grandes.
- Git: publicar commits UX-0→UX-5 individualmente quando auth estiver ok.

## Critérios UX-5

```text
Operator modernizado ✓
login + terminal selection ✓
senha dominante + timer ✓
NEXT / RECALL / NO_SHOW / COMPLETE ✓
fila resumida ✓
prioridade explícita ✓
feedback + anti double-tap ✓
sem info técnica / sem Admin ✓
mobile + tablet ✓
APIs preservadas / sem migration ✓
build PASS (ver relatório) ✓
docs ✓
```
