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
| UX-6C Screen Override | `CODE HOMOLOGATED` | `08c-screen-override.md` · VISUAL PENDING |
| UX-7 Media Library 2.0 | `CODE HOMOLOGATED` | `09-media-library.md` · VISUAL PENDING |
| UX-8 Playlist Studio | `CODE HOMOLOGATED` | `10-playlist-studio.md` · VISUAL PENDING |
| UX-9 Programming Studio | `READY FOR HOMOLOGATION` | `11-programming-studio.md` · VISUAL PENDING |
| UX-10 Screen & Device Fleet | `PLANNED` | **não iniciar sem homologação** |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## DISPLAY 2.0 Gate

| Dimensão | Status |
|----------|--------|
| TECHNICAL | `HOMOLOGATED` |
| COMMERCIAL / VISUAL | **PENDING** |

## Decisões UX-8

- 0 migrations; duração efetiva = item.duration (player alinhado).
- MediaPicker multi-select (ordem = seleção) + bulk API.
- Delete playlist bloqueado se channel/schedule/display em uso.
- Preview admin local (StudioPreview), Play explícito, muted.
- StoreContext + `?playlist=` deep-link.
- Persistência por ação (Salvando/Salvo).

## Decisões UX-9

- 0 migrations; `/channels` = Programming Studio (nav “Programação”).
- `programming-overview` / `next` / conflicts estruturais — mesma `active_at` do player.
- PriorityBadge: Programação normal / Prioritária / Emergencial.
- Schedule.priority ≠ ScreenOverride.priority.
- Delete channel 409 se display/grupo; schedules soft-delete.
- StoreContext + `?channel=` deep-link.

## Débitos

- Display 2.0 visual gate.
- UX-7: pagination/virtualization.
- UX-8: virtualization timeline; layout preview; versioning.
- UX-9: drag/resize schedule; month view; publish; screen assignment → UX-10.

## Critérios UX-9

```text
Programming Studio ✓
StoreContext ✓
timeline Hoje/Semana ✓
Agora/Próximo = active_at ✓
conflitos AMBIGUOUS/RESOLVED ✓
default playlist + layout ✓
cross-store rejeitado ✓
build + testes ✓
VISUAL PENDING
```
