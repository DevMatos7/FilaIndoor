# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `HOMOLOGATED` | `03-design-system.md` |
| UX-2 App Shell + IA | `HOMOLOGATED` | `02-information-architecture.md` · `04-admin-shell.md` |
| UX-3 Command Center | `READY FOR HOMOLOGATION` | `05-command-center.md` |
| UX-4 Totem 2.0 | `PLANNED` | — |
| UX-5 Operator 2.0 | `PLANNED` | — |
| UX-6A Display Public Mode | `PLANNED` | — |
| UX-6B Layout Engine | `PLANNED` | — |
| UX-6C Screen Override | `PLANNED` | — |
| UX-7 Media Library | `PLANNED` | — |
| UX-8 Playlist Studio | `PLANNED` | — |
| UX-9 Programming Studio | `PLANNED` | — |
| UX-10 Screen & Device Fleet | `PLANNED` | — |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## Decisões UX-3

- `/` = Command Center; nav **Início** aponta para ele (sem “Central da operação”).
- StoreContext obrigatório; agregador `GET /operations/overview?store_id=`.
- Alertas = derived view (sem engine/tabela).
- Polling 30s + AbortController; stale snapshot preservado.
- Conteúdo = canal/playlist/agenda reais (sem “campanha” inventada).
- Sem Recharts / Vitest / RTL / Playwright / migration / customer-facing.

## Critérios UX-3

```text
/ = Command Center ✓
StoreContext ✓
KPIs operacionais ✓
filas ao vivo ✓
device health ✓
alertas derivados ✓
fluxo horário ✓
conteúdo atual quando suportado ✓
auto + manual refresh ✓
loading skeleton ✓
empty / partial / stale ✓
responsividade + a11y ✓
sem dados fictícios ✓
sem migration ✓
build PASS (ver relatório) ✓
docs ✓
```
