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
| UX-7 Media Library 2.0 | `READY FOR HOMOLOGATION` | `09-media-library.md` · VISUAL PENDING |
| UX-8 Playlist Studio | `PLANNED` | **não iniciar sem homologação** |
| UX-9 Programming Studio | `PLANNED` | — |
| UX-10 Screen & Device Fleet | `PLANNED` | — |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## DISPLAY 2.0 Gate

| Dimensão | Status |
|----------|--------|
| TECHNICAL | `HOMOLOGATED` (UX-6A+6B+6C) |
| COMMERCIAL / VISUAL | **PENDING** — checklist 1920×1080 (footer/sidebar/queue_fullscreen/QUEUE_CALL/EMERGENCY) |

Falta de screenshots **não** bloqueia UX-7; bloqueia piloto/comercial do Display.

## Decisões UX-7

- 0 migrations; MediaAsset atual + `usage_count` calculado.
- StoreContext obrigatório; busca/filtro/sort client-side.
- Drawer novo conteúdo + details; ConfirmDialog delete.
- Focus trap/portal/restore obrigatório (débito UX-1 fechado).
- Delete bloqueado se asset em playlist.
- PATCH nome/notes/duration; sem replace de arquivo.

## Débitos (roadmap)

- Display 2.0 VISUAL GATE.
- UX-7: pagination/virtualization; FFmpeg thumbs; expiration/approval; duplicate; replace file.
- UX-8+: Playlist Studio consome Media Library.
- Git: push sequencial quando auth disponível.

## Critérios UX-7

```text
biblioteca visual + MediaCard ✓
StoreContext / AbortController ✓
busca / filtros / ordenação ✓
Drawer create IMAGE/VIDEO/WEB ✓
details + edit + delete seguro ✓
focus trap Drawer/Modal ✓
usage_count + store isolation ✓
APIs player/playlist preservadas ✓
build + testes ✓
VISUAL VALIDATION PENDING
```
