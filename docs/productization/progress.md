# Productization — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| UX-0 Auditoria visual / baseline | `HOMOLOGATED` | `00-current-state.md` |
| UX-1 Design System | `HOMOLOGATED` | `03-design-system.md` |
| UX-2 App Shell + IA | `READY FOR HOMOLOGATION` | `02-information-architecture.md` · `04-admin-shell.md` |
| UX-3 Command Center | `PLANNED` | Aguardando autorização |
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

## Decisões UX-2

- Sidebar hierárquica por domínio; URLs existentes preservadas (sem `/indoor/*`).
- StoreContext com prioridade `?store=` → localStorage → primeira loja.
- Media migrada ao StoreContext; demais telas com **legacy store selector** (débito).
- Logout disponível no menu do usuário (mobile incluso).
- Background admin limpo; Login mantém atmosfera.
- Focus trap Modal/Drawer permanece débito até UX-7/10.

## Critérios UX-2

```text
sidebar hierárquica ✓
topbar + store switcher ✓
StoreContext ✓
breadcrumbs ✓
mobile drawer ✓
collapsed sidebar ✓
DS utilizado ✓
rotas preservadas ✓
customer-facing intacto ✓
build PASS ✓
docs ✓
```
