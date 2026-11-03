# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `HOMOLOGATED` | `03-design-system.md` |
| UX-2 App Shell + IA | `HOMOLOGATED` | `02-information-architecture.md` · `04-admin-shell.md` |
| UX-3 Command Center | `HOMOLOGATED` | `05-command-center.md` |
| UX-4 Totem 2.0 | `READY FOR HOMOLOGATION` | `06-totem.md` |
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

## Decisões UX-4

- `/totem/:queueId` preservada; experiência kiosk customer-facing (marca REAL).
- DM Sans para ações/senha; sem info técnica no modo público.
- Prioridade: ícone + texto + descrição (não só cor).
- Diagnostics em `/totem/:queueId/diagnostics` (sessão admin).
- Edge/outbox/idempotência preservados; copy comercial em falhas.
- Poll status 30s; ETA só com waiting > 0 e dado real.

## Critérios UX-4

```text
Totem modernizado ✓
marca REAL ✓
sem info técnica no público ✓
normal / prioritário claros ✓
processing / success / printer / server ✓
Edge transparente + offline comercial ✓
double-tap não duplica ✓
diagnostics separado ✓
768×1024 / 800×1280 ✓
a11y + reduced motion ✓
APIs / rota preservadas ✓
build PASS (ver relatório) ✓
docs ✓
```
