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
| UX-10 Screen & Device Fleet | `CODE HOMOLOGATED` | `12-screen-device-fleet.md` · VISUAL PENDING |
| UX-11 Analytics 2.0 | `READY FOR HOMOLOGATION` | `13-analytics-2.md` · VISUAL PENDING |
| UX-12 Playwright + Visual QA | `PLANNED` | **não iniciar sem homologação** |

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

## Decisões UX-11

- 0 migrations; `GET /analytics/overview` com cohorts documentados.
- P90 sobre observações individuais; zero ≠ missing.
- SLA 600/900s auditável (numerador/denominador); unknown ≠ falha.
- Device snapshot = “Situação atual da frota” (não uptime do período).
- Dependência frontend: `recharts@2.15.0`.
- `/analytics/summary` preservado para Command Center.

## Débitos

- Display 2.0 visual gate (COMMERCIAL/VISUAL PENDING).
- Store timezone.
- Proof of Play / playback_events / uptime histórico.
- CSV export, heatmap, forecasting, capacidade operador.
- Device Commands; ScreenGroup override; débitos visuais UX-6…10.

## Critérios UX-11

```text
Analytics 2.0 ✓
data dictionary ✓
P90 correto ✓
SLA auditável ✓
StoreContext + período ✓
queue filter ✓
device snapshot rotulado ✓
sem PoP / sem uptime fake ✓
build + testes ✓
VISUAL PENDING
```
