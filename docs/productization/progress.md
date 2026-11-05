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
| UX-9 Programming Studio | `CODE HOMOLOGATED` | `11-programming-studio.md` · VISUAL PENDING |
| UX-10 Screen & Device Fleet | `READY FOR HOMOLOGATION` | `12-screen-device-fleet.md` · VISUAL PENDING |
| UX-11 Analytics 2.0 | `PLANNED` | **não iniciar sem homologação** |
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

## Decisões UX-10

- 0 migrations; `GET /devices/fleet?store_id=` (FleetItem unifica Device+Display).
- Status = `DeviceService._compute_status` (90s/300s) — igual Command Center.
- `active` ≠ online; Programado agora ≠ Proof of Play.
- Channel assign só em Display; cross-store 422; tokens mascarados no fleet.
- Store timezone permanece débito arquitetural.

## Débitos

- Display 2.0 visual gate (COMMERCIAL/VISUAL PENDING).
- Store timezone.
- Proof of Play / playback_events.
- Device Commands / remote refresh-reboot-screenshot.
- ScreenGroup override target; fleet pagination.
- UX-7/8/9 débitos visuais e de edição avançada.

## Critérios UX-10

```text
Fleet /devices ✓
StoreContext ✓
status = CC ✓
channel assign ✓
cross-store 422 ✓
programmed ≠ confirmed ✓
token masked ✓
player config após channel ✓
build + testes ✓
VISUAL PENDING
```
