# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `HOMOLOGATED` | `03-design-system.md` |
| UX-2 App Shell + IA | `HOMOLOGATED` | `02-information-architecture.md` · `04-admin-shell.md` |
| UX-3 Command Center | `HOMOLOGATED` | `05-command-center.md` |
| UX-4 Totem 2.0 | `HOMOLOGATED` | `06-totem.md` |
| UX-5 Operator 2.0 | `HOMOLOGATED` | `07-operator.md` |
| UX-6A Display Public Mode | `READY FOR HOMOLOGATION` | `08-display-public-mode.md` · **VISUAL VALIDATION PENDING** |
| UX-6B Layout Engine | `PLANNED` | — |
| UX-6C Screen Override | `PLANNED` | — |
| UX-7 Media Library | `PLANNED` | — |
| UX-8 Playlist Studio | `PLANNED` | — |
| UX-9 Programming Studio | `PLANNED` | — |
| UX-10 Screen & Device Fleet | `PLANNED` | — |
| UX-11 Analytics 2.0 | `PLANNED` | — |
| UX-12 Playwright + Visual QA | `PLANNED` | — |

## Decisões UX-6A

- Public mode: zero telemetria na TV (WS/áudio/token/cache/media path).
- Layout conceitual preservado: Media + QueueFooter (+ CallOverlay).
- Componentização prepara UX-6B sem LayoutResolver ainda.
- Asset failure → skip + avançar; fallback branded.
- Overlay ~7s / TTS / WS / heartbeat / cache preservados.
- `CODE VALIDATION = PASS` · `VISUAL VALIDATION = PENDING` (sem capturas reais).

## Débitos (roadmap)

- UX-4: Offline issue real / Edge local ticketing.
- UX-5+: Operator Presence / Capacity.
- UX-5: NEXT `auto_complete_current=true` (contrato legado — documentar em operação).
- UX-6A: **Visual validation** quando ambiente de captura estiver disponível.
- UX-6B/C: Layout Engine + Screen Overrides.
- Git: publicar commits UX-0→UX-6A individualmente quando auth estiver ok.

## Critérios UX-6A

```text
Display public mode ✓
telemetria removida da TV ✓
MediaPlayer IMAGE/VIDEO/WEB ✓
footer + overlay modernos ✓
WS/TTS/heartbeat/dedupe ✓
fallback / unavailable branded ✓
build PASS ✓
docs ✓
VISUAL VALIDATION PENDING
```
