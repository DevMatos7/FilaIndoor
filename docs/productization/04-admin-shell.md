# UX-2 — Admin Shell

## Estrutura

```text
layouts/
  AppLayout.tsx          StoreProvider + shell
  Sidebar.tsx            desktop / collapsed
  Topbar.tsx             loja + alertas + usuário
  Breadcrumbs.tsx
  MobileNavigation.tsx   Drawer DS
  StoreSwitcher.tsx
  navigation.ts          IA + active match
```

## Layout desktop

```text
[ Sidebar 272px | 72px collapsed ] [ Topbar ]
                                   [ Breadcrumb ]
                                   [ Page ≤1400px ]
```

## Sidebar

- Brand: **REAL** / Fila & Indoor (slot futuro para logo)
- Grupos com label uppercase + ícones Lucide
- Active: `bg-white/15` + texto + ícone + `aria-current="page"`
- Collapsed: ícones + Tooltip; preferência `localStorage` key `real-shell-sidebar`
- Tablet (768–1023): inicia collapsed se sem preferência salva

## Topbar

- StoreSwitcher (1 loja = texto; N = Select DS)
- Alertas: IconButton desabilitado + tooltip “em breve”
- User menu: `/auth/me` (nome/e-mail) + avatar inicial + **Sair** (desktop e mobile)

## Mobile

- Botão ☰ na Topbar
- `Drawer` (DS) com grupos/itens
- Navegação fecha o drawer
- ESC fecha (Drawer)

## Background admin

- Shell: `bg-surface-muted` / content `bg-surface` — enterprise clean
- Gradiente global removido do admin; Login usa `body.atmosphere-login`

## Acessibilidade

- focus-visible global (DS)
- aria-label nos IconButtons
- aria-current no item ativo
- keyboard: Tab, Enter, Escape (drawer/menu)
- status de nav não só por cor

## Responsividade alvo

```text
390×844 · 768×1024 · 1366×768 · 1920×1080
```
