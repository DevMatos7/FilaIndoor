# UX-1 — Design System

**Status:** `READY FOR HOMOLOGATION`  
**Pacote:** `frontend/src/design-system/`  
**Ícones:** `lucide-react`

---

## 1. Objetivo

Fundação visual reutilizável (tokens + componentes + patterns) sem redesenhar o produto.

```text
tokens → Tailwind → componentes → páginas (migração gradual)
```

---

## 2. Estrutura

```text
design-system/
├── tokens/          colors, typography, spacing, radius, shadow, motion
├── components/      Button, Input, Select, Card, MetricCard, …
├── patterns/        DeviceStatus, QueueStatus, TicketBadge, SlaIndicator, MediaCard (+ MediaPicker/Studio em components/media)
├── utils/cn.ts
└── index.ts         barrel público
```

Import preferido:

```tsx
import { Button, Alert, PageHeader } from "../design-system";
```

---

## 3. Cores

### Brand (expandida)

| Token | Hex | Nota |
|-------|-----|------|
| 50–100 | `#f0f7f4` / `#dceee6` | preservados |
| 200–400 | `#b8d9cb` … `#5a9a7a` | novos |
| 500 / 700 / 900 | existentes | preservados |
| **800** | `#103a28` | **corrigido** (Pair.tsx) |
| 950 | `#071a12` | novo |

### Semânticos (Tailwind)

```text
surface / surface-muted / surface-elevated
semantic-{success|warning|danger|info}(+-bg|-border)
status-{online|degraded|offline|disabled}(+-bg)
queue-{waiting|called|serving|completed|no-show|cancelled}
sla-{ok|warning|critical}(+-bg)
```

Evitar nas **novas** UIs: `red-*` / `amber-*` / `emerald-*` ad-hoc.

---

## 4. Tipografia

| Token | Uso |
|-------|-----|
| `font-sans` (DM Sans) | Admin / DS |
| `font-display` (Source Serif 4) | Totem/Display (mantido) |
| `text-page-title` | PageHeader |
| `text-section-title` | seções |
| `text-metric` + `tabular-nums` | KPIs |
| `text-ticket-number` | senhas (TV/totem futuro) |

---

## 5. Componentes

| Componente | Variantes / notas |
|------------|-------------------|
| `Button` | primary, secondary, ghost, danger · sm/md/lg · loading · focus-visible |
| `IconButton` | aria-label obrigatório |
| `Input` / `Select` | label, hint, error, required, disabled |
| `Card` / `CardHeader` / `CardContent` | `interactive` opcional |
| `MetricCard` | label, value, hint, trend, status, icon |
| `PageHeader` | title, description, actions, breadcrumb slot |
| `Alert` | info/success/warning/danger + ícone lucide |
| `Badge` | tone + ícone opcional |
| `EmptyState` | icon, title, description, action (copy comercial) |
| `Skeleton.*` | Text, Line, Card, Metric |
| `Tabs` | tablist/tab ARIA |
| `Tooltip` | hover/focus leve |
| `Modal` / `Drawer` | ESC, overlay, aria-modal |
| `ConfirmDialog` | Modal + ações |
| `StatusDot` | cor + texto (nunca só cor) |

### Patterns

| Pattern | Entrada |
|---------|---------|
| `DeviceStatus` | ONLINE / DEGRADED / OFFLINE / DISABLED |
| `QueueStatus` | OPEN / PAUSED / CLOSED |
| `TicketBadge` | NORMAL / PRIORITY / PRIORITY_PLUS |
| `SlaIndicator` | OK / WARNING / CRITICAL |

Todos exibem **texto + ícone + cor**.

---

## 6. Acessibilidade

- `focus-visible` global (`index.css`) — outline brand, sem remover outline sem substituto
- Labels associados (`htmlFor` / `useId`)
- `aria-invalid`, `aria-describedby`, `aria-busy`, `role="alert|status|dialog|tablist"`
- Disabled real (`disabled` nativo)
- Status nunca só por cor

---

## 7. Páginas migradas (UX-1)

| Página | Uso do DS |
|--------|-----------|
| `Login.tsx` | Card, Input, Button, Alert |
| `Dashboard.tsx` | PageHeader, MetricCard, Alert, EmptyState, SkeletonMetric, Card, QueueStatus |

**Não migrados:** Totem, Operator, Display, Media, Playlists, Channels, Devices, Analytics (próximas sprints).

---

## 8. Exemplos

```tsx
<Button variant="primary" loading={busy}>Salvar</Button>

<Input label="E-mail" required error={err} />

<MetricCard label="Aguardando" value="13" hint="agora" />

<Alert variant="danger">Falha ao carregar.</Alert>

<EmptyState
  title="Nenhuma fila cadastrada"
  description="Cadastre uma fila para acompanhar a operação."
/>

<DeviceStatus status="ONLINE" />
```

---

## 9. Decisões

1. Tailwind continua como motor — tokens TS documentam e alimentam patterns.
2. Sem MUI/Chakra/shadcn; só `lucide-react`.
3. Modal/Drawer com portal + focus trap + ESC + scroll lock + restore (hardening UX-7). MediaCard é pattern real da biblioteca.
4. EmptyState novo não usa copy de seed/`/media`.
5. Source Serif mantida para customer-facing até UX-4/6.
6. **PriorityBadge** (UX-9): ícone + texto + cor para `NORMAL` / `HIGH` / `EMERGENCY` (Schedule). Não reutilizar para ScreenOverride.
7. **DeviceStatus** (UX-1/UX-10): fonte única de badge de saúde ONLINE/DEGRADED/OFFLINE/DISABLED no Fleet — não criar badge paralelo.

---

## 10. Débitos

- Tooltip sem posicionamento avançado
- Páginas legacy ainda com classes ad-hoc
- Screenshots live dependem de Docker (ver progress)
- MediaCard: thumbnails de vídeo via FFmpeg (futuro)
- ScheduleCard / TimelineItem ainda colocados em `Channels.tsx` (extrair se reuso)
