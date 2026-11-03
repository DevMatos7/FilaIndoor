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
| UX-6B Layout Engine | `READY FOR HOMOLOGATION` | `08b-layout-engine.md` · **VISUAL VALIDATION PENDING** |
| UX-6C Screen Override | `PLANNED` | — |
| UX-7 Media Library | `PLANNED` | — |
| UX-8 Playlist Studio | `PLANNED` | — |
| UX-9 Programming Studio | `PLANNED` | — |
| UX-10 Screen & Device Fleet | `PLANNED` | — |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## Decisões UX-6B

- Layout data-driven: `layout_templates` + `layout_zones` (percentuais).
- `Channel.layout` legado preservado; `layout_template_id` aditivo.
- System templates: fullscreen_media, media_queue_footer, media_queue_sidebar, queue_fullscreen.
- Legacy map: `queue_media_split` → `media_queue_footer`.
- Player config aditivo com `layout`; cache antigo → emergency footer.
- QueueCallOverlay permanece global (débito UX-6C).
- Validação visual completa recomendada após UX-6C.

## Débitos (roadmap)

- UX-4: Offline issue / Edge local ticketing.
- UX-5+: Operator Presence / Capacity; NEXT auto_complete legado.
- UX-6A/6B: **VISUAL VALIDATION PENDING** (completar pós UX-6C).
- UX-6C: Screen Override (substituir QueueCallOverlay hardcoded).
- Git: push sequencial UX-0→UX-6B quando auth disponível.

## Critérios UX-6B

```text
migration + system templates ✓
legacy channel.layout preservado ✓
LayoutService resolve ✓
player config aditivo ✓
LayoutResolver + ZoneRenderer ✓
4 layouts ✓
fallback / cache antigo ✓
build PASS ✓
testes backend ✓
VISUAL VALIDATION PENDING
```
