# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `HOMOLOGATED` | `03-design-system.md` |
| UX-2 App Shell + IA | `HOMOLOGATED` | `02-information-architecture.md` · `04-admin-shell.md` |
| UX-3 Command Center | `HOMOLOGATED` | `05-command-center.md` |
| UX-4 Totem 2.0 | `HOMOLOGATED` | `06-totem.md` |
| UX-5 Operator 2.0 | `HOMOLOGATED` | `07-operator.md` |
| UX-6A Display Public Mode | `CODE HOMOLOGATED` | `08-display-public-mode.md` · VISUAL PENDING |
| UX-6B Layout Engine | `CODE HOMOLOGATED` | `08b-layout-engine.md` · VISUAL PENDING |
| UX-6C Screen Override | `READY FOR HOMOLOGATION` | `08c-screen-override.md` · VISUAL PENDING |
| UX-7 Media Library | `PLANNED` | **não iniciar sem gate Display 2.0** |
| UX-8 Playlist Studio | `PLANNED` | — |
| UX-9 Programming Studio | `PLANNED` | — |
| UX-10 Screen & Device Fleet | `PLANNED` | — |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## DISPLAY 2.0 Gate

Capacidade = UX-6A + UX-6B + UX-6C.

| Dimensão | Status |
|----------|--------|
| CODE | PASS (após testes UX-6C) |
| VISUAL | **PENDING** — exige capturas reais (footer/sidebar/queue_fullscreen + QUEUE_CALL + EMERGENCY @ 1920×1080) |

Não marcar Display 2.0 como HOMOLOGATED comercialmente sem validação visual.

## Decisões UX-6C

- `screen_overrides` + `ScreenOverrideService` (prioridade centralizada).
- QUEUE_CALL via call/recall best-effort; core queue independente.
- WS: `override` embutido em `ticket.*`; admin via `screen.override.*`.
- Player: `active_overrides` aditivo.
- Frontend: OverrideManager / Resolver / Renderer; layout permanece montado.
- Pre-flight UX-6B uniqueness: PASS (índice parcial global já existia).

## Débitos (roadmap)

- UX-4: Offline issue / Edge local ticketing.
- UX-5+: Operator Presence / Capacity; NEXT auto_complete legado.
- UX-6*: **VISUAL VALIDATION PENDING** (Display 2.0 gate).
- UX-6C: Queue Call Buffer/FIFO; editor visual overrides; screen group target; analytics; Retail Media campaign entity.
- Git: push sequencial quando auth disponível.

## Critérios UX-6C

```text
screen_overrides + migration ✓
priority centralizada ✓
target scopes + tenant validation ✓
queue/recall integration + core safety ✓
player active_overrides ✓
OverrideManager/Resolver/Renderer ✓
legacy adapter + rolling deploy ✓
build + testes ✓
VISUAL VALIDATION PENDING
```
