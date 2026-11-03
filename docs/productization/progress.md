# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `READY FOR HOMOLOGATION` | `03-design-system.md` · lucide-react · Login + Dashboard |
| UX-2 App Shell + IA | `PLANNED` | Aguardando autorização |
| UX-3 Command Center | `PLANNED` | — |
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

## Decisões UX-1

- Design System em `frontend/src/design-system/` + tokens no Tailwind.
- `brand-800` (#103a28) adicionado — corrige Pair.tsx.
- Dependência única nova: `lucide-react`.
- Migração validação: Login + Dashboard (não Command Center).
- `npm run build` PASS.
- Screenshots live: stack Docker não estava disponível nesta sprint; inventário documentado.

## Critérios UX-1

```text
design-system/ ✓
tokens ✓
brand-800 ✓
componentes obrigatórios ✓
Login usa DS ✓
Dashboard usa DS ✓
build PASS ✓
sem API / migration / rotas quebradas ✓
```
