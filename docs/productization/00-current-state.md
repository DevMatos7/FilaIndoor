# UX-0 — Estado atual do frontend (baseline)

**Projeto:** REAL Fila & Indoor  
**Data da auditoria:** 2026-11-03  
**Escopo:** auditoria visual/UX — **sem alteração de UI**  
**Gate:** `UX-0 READY FOR HOMOLOGATION`

---

## 1. Resumo executivo

O frontend é um **MVP técnico funcional**: React 18 + Vite 6 + TypeScript + Tailwind 3 + React Router 6 + Axios.

- **27 arquivos** em `frontend/src` (páginas monolíticas, 1 layout, 2 services).
- **Não existe** pasta `design-system/`, biblioteca de ícones, StoreContext, testes frontend (Vitest/RTL/Playwright) nem charts.
- Navegação admin é **lista plana** de 12 itens.
- Contextos customer-facing (Totem / Operator / Display) já têm layouts distintos — bom ponto de partida.
- Gap principal: **identidade comercial, hierarquia, componentes reutilizáveis, CMS visual, Display público limpo**.

---

## 2. Stack frontend

| Item | Valor |
|------|--------|
| React | 18.3 |
| Vite | 6.x |
| TypeScript | 5.6 |
| Tailwind | 3.4 |
| Router | react-router-dom 6.26 |
| HTTP | axios |
| Ícones | **nenhum** (lucide-react ausente) |
| Charts | **nenhum** (Recharts ausente) |
| Testes FE | **nenhum** (`package.json` só `dev` / `build` / `preview`) |
| Design system | **inexistente** |

---

## 3. Mapa de rotas

### Públicas / device

| Rota | Página | Contexto |
|------|--------|----------|
| `/login` | `Login.tsx` | Auth admin |
| `/totem/:queueId` | `Totem.tsx` | Cliente (kiosk) |
| `/operator/:queueId` | `Operator.tsx` | Operador |
| `/display/:queueId` | `Display.tsx` | TV / player |
| `/pair` | `Pair.tsx` | Pareamento device |
| `/real-plus/:queueId` | `RealPlus.tsx` | Cliente REAL+ |

### Admin (protegido — `AppLayout`)

| Rota | Página | Função atual |
|------|--------|--------------|
| `/` | `Dashboard.tsx` | KPIs + lista de filas |
| `/analytics` | `Analytics.tsx` | KPIs + SLA + horário |
| `/queues` | `Queues.tsx` | Lista filas |
| `/queues/:queueId` | `QueueDetail.tsx` | Detalhe / ao vivo |
| `/queues/:queueId/settings` | `QueueSettings.tsx` | Config fila |
| `/history` | `History.tsx` | Histórico tickets |
| `/media` | `Media.tsx` | Upload + lista textual |
| `/playlists` | `Playlists.tsx` | Editor + drag + preview |
| `/channels` | `Channels.tsx` | Canais + agendas CRUD |
| `/devices` | `Devices.tsx` | Overview devices/displays |
| `/edge` | `Edge.tsx` | Edge / outbox |
| `/integrations` | `Integrations.tsx` | CISS |
| `/toledo` | `Toledo.tsx` | Toledo discovery/adapter |
| `/real-plus` | `RealPlusAdmin.tsx` | Admin fila virtual |

Catch-all: `*` → `/`.

---

## 4. Navegação atual (`AppLayout`)

Ordem flat (sidebar escura `brand-900`):

```text
Dashboard · Analytics · Filas · Histórico · Mídias · Playlists
Canais · Dispositivos · Edge · CISS · Toledo · REAL+
```

### Problemas de IA (information architecture)

- Não há agrupamento OPERAÇÃO / ATENDIMENTO / INDOOR / DISPOSITIVOS / INSIGHTS / INTEGRAÇÕES.
- Sem topbar, breadcrumb, seletor de loja global, alertas, avatar.
- Mobile: nav horizontal scroll — utilizável, mas sem hierarquia.
- Logout só visível em `lg+`.
- Branding admin: “REAL Fila / Atendimento & Indoor” — ok para interno; customer-facing já usa “REAL” no Totem/Display.

---

## 5. Tokens / identidade visual

### Tailwind extend (`tailwind.config.js`)

```text
brand.50  #f0f7f4
brand.100 #dceee6
brand.500 #1f6b4a
brand.700 #154a34
brand.900 #0c2b1e
ink       #14201a
sand      #f3f6f4
```

### Tipografia

- Display: **Source Serif 4** (`font-display`)
- Body: **DM Sans** (`font-sans` / body)
- Google Fonts via `index.html`

### Background global (`index.css`)

- Gradientes radiais verdes sobre `sand` — atmosfera suave, porém **genérica** e aplicada a todo admin.

### Débitos de token

| Débito | Detalhe |
|--------|---------|
| Escala incompleta | Sem `brand-200/300/400/600/800` formais |
| `brand-800` usado | `Pair.tsx` usa `from-brand-800` — **classe inexistente** no theme (cor cai no fallback Tailwind/indefinido) |
| Cores ad-hoc | `red-*`, `amber-*`, `emerald-*`, `slate-*` espalhados sem aliases semânticos (`success`, `danger`, `online`…) |
| Sem tokens de spacing/radius/shadow/motion | Tudo inline via utilitários |
| Sem `surface` / `text-muted` semânticos | Padrão `bg-white/80` + `text-ink/70` repetido |

---

## 6. Componentização

### O que existe

- Páginas **autocontidas** (estado + fetch + markup na mesma tela).
- `Analytics.tsx` define um `Kpi` local — **não compartilhado** com Dashboard.
- Services: `api.ts` (axios + interceptor 401), `edgeOffline.ts` (cache/outbox kiosk).

### O que **não** existe

```text
Button, Input, Select, Badge, Card, MetricCard, PageHeader,
EmptyState, Alert, Skeleton, Tabs, Drawer, Modal, Tooltip,
FilterBar, DataTable, StatusDot, ConfirmDialog,
QueueStatus, DeviceStatus, MediaCard, PlaylistItem,
ScreenPreview, SlaIndicator, TicketBadge
```

### Repetições críticas

| Padrão | Onde |
|--------|------|
| `GET /stores` + `<select>` local | Media, Playlists, Channels, Devices, Edge, Integrations (**6×**) |
| Header `h1.font-display` + subtítulo | Quase todas as páginas admin |
| Alert `border-red-200 bg-red-50` | Dashboard, Media, Channels, Devices, Login… |
| Card `border border-brand-100 bg-white/80 p-4` | Dashboard, Analytics, Media… |
| `fmtSec` duplicado | Dashboard + Analytics |

---

## 7. Auditoria por tela obrigatória

### 7.1 Dashboard (`Dashboard.tsx` ~113 LOC)

**Entrega atual:** 6 KPIs do dia + cards de filas (nome, status, estratégia, prefixos).

**Gaps vs Command Center (PRD):**

- Sem operação ao vivo por departamento (espera média, P90, SLA, operadores).
- Sem device health, “agora nas telas”, alertas, fluxo horário.
- KPI “Maior espera” existe; faltam P90, serve rate, operadores ativos.
- Empty state menciona seed — linguagem de desenvolvimento.

### 7.2 Totem (`Totem.tsx`)

**Pontos fortes:**

- Estados claros: idle / processing / success / printer_error / offline / server_error.
- Marca “REAL” + departamento.
- Botões grandes touch; prioridade com cor âmbar + `aria-label`.
- Success ~4s (`scheduleIdle(4000)`).
- Edge offline com cache/outbox.

**Gaps Totem 2.0:**

- Idle não mostra espera estimada **dentro** dos botões (“aprox. X min”).
- Mensagens técnicas possíveis: token ausente no footer, “Sistema operando localmente”, print message.
- Sem modo diagnóstico `/diagnostics`.
- Prioridade ainda muito dependente de cor (âmbar).

### 7.3 Operator (`Operator.tsx`)

**Pontos fortes:**

- Foco operacional: senha grande, timer `tabular-nums`, NEXT / RECALL / NO_SHOW / COMPLETE.
- Login embutido; seleção de terminal.

**Gaps:**

- Sem status AVAILABLE/SERVING/PAUSED.
- Link “Admin” na header — ruído para balcão.
- Layout escuro ok; tipografia/tamanho de alvos ainda melhoráveis para tablet.
- Sem `active_operators` / capacity.

### 7.4 Display (`Display.tsx` ~344 LOC — maior página)

**Pontos fortes:**

- Split media + footer de senha; overlay de chamada; TTS; WS + heartbeat; playlist IMAGE/VIDEO/WEB.

**Problemas Display público (críticos para productization):**

| Problema | Evidência |
|----------|-----------|
| Info técnica na TV | Badge “Ao vivo / Conectando / Reconectando · Áudio / Sem áudio” |
| Mensagem interna | “Sem mídia na loja — cadastre em `/media`” |
| Erro técnico | “Modo cache local (edge offline)”, “Informe ?token=” |
| Layout fixo | Sem Layout Engine / zones / templates |
| Override hardcoded | Overlay local 7s — não há `screen_overrides` |

### 7.5 Media (`Media.tsx`)

- Biblioteca = **lista textual**, não grid visual com thumbnails.
- Upload e WEB em formulários lado a lado (CRUD, não “Novo conteúdo” drawer).
- Preview lateral básico (bom embrião).
- Sem filtros Imagem/Vídeo/Web; sem menu ações (duplicar, add playlist).

### 7.6 Playlists (`Playlists.tsx`)

- Já tem drag-and-drop, duração, preview cíclico — **base forte para Playlist Studio**.
- Lista ainda textual (ícone `⠿`, sem thumbnails).
- Sem duração total agregada, sem seletor 16:9 / 9:16 de layout.

### 7.7 Channels (`Channels.tsx`)

- CRUD técnico: canal, agenda (time + dias + NORMAL/HIGH/EMERGENCY), grupos.
- Conflitos via `/channels/:id/now` — útil, UI pouco visual.
- Sem timeline do dia / Scheduling Studio.

### 7.8 Devices (`Devices.tsx`)

- Overview misturando terminals + displays + managed devices.
- Status badges com cores ad-hoc (`STATUS_STYLE`).
- Sem Fleet tipado (Telas / Totens / Impressoras / Edge), sem drawer de detalhe rico, sem `device_commands`.

### 7.9 Analytics (`Analytics.tsx`)

- KPIs, SLA green/yellow/red, hourly bars **CSS-only**, waiting list, by operator.
- Sem Recharts; sem abas Visão Geral / Espera / Atendimento / SLA / Operadores / Volume.
- Sem comparações hoje×ontem / loja×loja.

---

## 8. Responsividade (observado no código)

| Contexto | Abordagem atual | Lacunas |
|----------|-----------------|---------|
| Admin | `lg:grid` sidebar; grids `sm/xl/2xl` | Sem drawer mobile dedicado; logout hidden &lt; lg |
| Totem | `max-w-3xl`, botões `min-h-[140px]`, tipografia `sm:` | Não há testes 800×1280 / 10–11" |
| Operator | `max-w-3xl`, botões altos | Falta validação 360–390 mobile + tablet |
| Display | `flex-[1.35]` + footer; tipografia `sm:text-8xl/9xl` | Sem scaling explícito 4K / portrait 9:16 |

### Breakpoints a usar em UX-12 (Playwright / visual QA)

```text
390×844
768×1024
1366×768
1920×1080
3840×2160
+ Totem: 800×1280
+ Display portrait: 1080×1920
```

---

## 9. Acessibilidade

| Aspecto | Estado |
|---------|--------|
| `lang="pt-BR"` | OK |
| Labels em forms | Parcial (muitos `label` ok) |
| `role="alert"` / `status` | Pontual (Login, Dashboard, Operator…) |
| Focus visible | Default browser; sem ring design system |
| Status só por cor | Prioridade Totem; SLA Analytics; device badges |
| Keyboard / drawers / modals | N/A (não há modal/drawer) |
| WCAG AA contraste | Brand verde escuro em branco tende OK; âmbar/branco a validar |

---

## 10. Estados (loading / empty / error / offline)

| Tela | Loading | Empty | Error | Offline |
|------|---------|-------|-------|---------|
| Dashboard | texto | dashed box | alert | — |
| Media/Playlists/Channels | texto | texto | alert | — |
| Totem | processing UI | — | server_error | offline state |
| Display | implícito | fallback REAL + texto técnico | texto âmbar | badge WS |
| Operator | — | “—” senha | alert | — |

Sem **Skeleton**, sem empty ilustrado comercial.

---

## 11. Dívida visual

1. Sem design system → inconsistência inevitável.
2. Serif display em KPIs densos pode competir com leitura operacional (PRD pede sans no admin).
3. Cards sem radius/shadow padronizados; alguns `rounded-2xl` só em customer-facing.
4. Nav flat parece “lista de módulos do MVP”.
5. Indoor = 3 CRUDs separados (Media / Playlists / Channels), não workflow.
6. Display expõe telemetria ao cliente.
7. `brand-800` quebrado em Pair.
8. Gradiente global admin pouco “enterprise clean”.

---

## 12. Dívida UX / produto

1. Sem StoreContext → usuário reescolhe loja a cada tela.
2. Dashboard ≠ Command Center (10s para entender a loja).
3. Indoor sem Visão geral / Telas / Templates / Publicação.
4. Fleet misturado; sem comandos remotos UI.
5. Analytics sem gráficos profissionais nem comparativos.
6. Sem Proof of Play / playback_events (backend+UI).
7. REAL+ / CISS / Toledo no mesmo nível flat da nav — dilui operação.

---

## 13. Reutilizações possíveis (para UX-1+)

| Ativo atual | Evolução sugerida |
|-------------|-------------------|
| Paleta brand verde REAL | Expandir tokens semânticos (não trocar marca) |
| DM Sans | Manter como sans admin; revisar uso de Source Serif |
| Totem state machine | Preservar; só skin + copy |
| Operator actions | Preservar contrato API; layout 2.0 |
| Display WS + overlay + playlist | Extrair LayoutResolver / OverrideEngine |
| Playlists drag + preview | Base do Playlist Studio |
| Channels priority + conflicts | Base do Scheduling Studio |
| Devices STATUS_STYLE | Virar `StatusDot` / DeviceStatus |
| Analytics KPIs + SLA + hourly | Alimentar Command Center + Analytics 2.0 |
| `api` 401 interceptor | Manter |
| `edgeOffline` | Manter para Totem/Display |

---

## 14. Riscos de regressão

| Área | Risco | Mitigação |
|------|-------|-----------|
| Rotas públicas | Quebrar totem/operator/display em loja | Preservar paths; feature flags visuais |
| Kiosk token / display token | Auth headers | Não alterar contratos no UX-1/2 |
| Playlist reorder | Drag otimista | Manter API `/items/reorder` |
| WS events | Overlay / áudio | Extrair com testes Playwright (UX-12) |
| Store selects | Migração StoreContext | Gradual, query `?store=` |
| Tailwind classes ad-hoc | Refactor visual | Tokens primeiro; migrar tela a tela |

---

## 15. Screenshots baseline

**Status nesta auditoria:** Docker/web **offline** no momento da UX-0 (`localhost:5180` / `8010` indisponíveis).  
Playwright **não instalado** (conforme regra UX-0: não instalar nesta etapa).

### Inventário a capturar assim que o ambiente subir (baseline visual)

| ID | Tela | URL sugerida | Notas |
|----|------|--------------|-------|
| B01 | Login | `/login` | Form admin |
| B02 | Dashboard | `/` | KPIs + filas |
| B03 | Analytics | `/analytics` | Barras CSS |
| B04 | Media | `/media` | Lista textual |
| B05 | Playlists | `/playlists` | Preview + drag |
| B06 | Channels | `/channels` | Form agenda |
| B07 | Devices | `/devices` | Overview |
| B08 | Totem idle | `/totem/:id?token=` | Dois botões |
| B09 | Totem success | (após emitir) | Senha grande |
| B10 | Operator | `/operator/:id` | Botoeira |
| B11 | Display | `/display/:id?token=` | Media + footer + badge WS |
| B12 | App shell mobile | `/` @ 390px | Nav horizontal |

Pasta sugerida futura: `docs/productization/screenshots/ux-0/`.

---

## 16. Plano UX-1 (próxima sprint — **não iniciar sem autorização**)

1. Criar `frontend/src/design-system/` (tokens + componentes do PRD §7).
2. Adicionar `lucide-react` (única lib de ícones).
3. Expandir tokens de cor (incluir alias semânticos + corrigir escala brand).
4. Migrar **apenas validação**: Login + 1 página admin leve (ex.: Dashboard header/KPIs) para consumir DS — **sem** redesenhar Command Center.
5. `npm run build` + testes backend existentes; documentar ausência de testes FE.
6. Commit: `feat(productization): UX-1 design system`.
7. Gate: `UX-1 READY FOR HOMOLOGATION` → PARAR.

---

## 17. Gate UX-0

| Critério | Status |
|----------|--------|
| Rotas catalogadas | ✓ |
| Screens obrigatórias analisadas | ✓ |
| Cores / tipografia / Tailwind | ✓ |
| Componentes / repetições | ✓ |
| Responsividade / a11y / débitos | ✓ |
| `docs/productization/00-current-state.md` | ✓ |
| UI não modificada | ✓ |
| Plano UX-1 | ✓ |

```text
UX-0
READY FOR HOMOLOGATION
```
