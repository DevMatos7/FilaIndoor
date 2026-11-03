# UX-3 — Command Center

## Objetivo

Transformar `/` (Dashboard) em **monitoramento operacional** da loja selecionada,
capaz de responder em ~10s:

- Quantas pessoas estão esperando?
- Existe fila crítica?
- Quanto estamos esperando?
- Estamos atendendo?
- Algum equipamento offline?
- Existe problema que exige ação?
- O que está rodando nas telas?

Não é tela de relatório — prioriza **agora**, desvios, espera, capacidade observável e ações.

## Information Architecture

| Item | Decisão |
|------|---------|
| Início | = Command Center (`/`) |
| Central da operação | **não existe** (evitar duplicata) |
| Ao vivo | fora desta sprint; só se houver UX distinta |

## Hierarquia da página

1. Header (`PageHeader`) + status AO VIVO / Atualizar  
2. KPI strip + SLA  
3. Filas ao vivo \| Atenção necessária + Saúde dos dispositivos  
4. Fluxo de atendimentos (horário)  
5. Agora nas telas \| Ações rápidas  

## Componentes

| Peça | Origem |
|------|--------|
| PageHeader, MetricCard, Card, Alert, Badge, EmptyState, Skeleton* | Design System (UX-1) |
| QueueStatus, SlaIndicator, StatusDot | DS patterns |
| `HourlyFlowChart` | `frontend/src/components/command-center/` (SVG/CSS simples) |
| Camada de dados | `frontend/src/services/commandCenter.ts` |

## Fontes de dados

Endpoint agregador **read-only**:

```http
GET /api/v1/operations/overview?store_id=<uuid>
```

Reutiliza internamente:

- `QueueService.queue_status` (filas da loja via departamentos)
- `AnalyticsService.summary_for_store` (KPIs do dia, SLA, hourly)
- `DeviceService.list_devices` + Displays/Terminals
- `EdgeService.sync_status`
- `ScheduleService.active_at` + canais (conteúdo atual)

Filtro aditivo em Analytics: `store_id` (retrocompatível).

Sem migration. Sem alteração de regra de fila.

## Derivações

### Ordenação de filas

```text
CRÍTICO → ATENÇÃO → NORMAL → SEM FILA (aberta) → FECHADA
```

Critério: `sla_level` + `status` + `waiting_count`.

### SLA de fila (operacional)

- CLOSED → OK  
- PAUSED com aguardando → WARNING  
- waiting ≥ 15 ou espera ≥ 900s → CRITICAL  
- waiting ≥ 8 ou espera ≥ 600s → WARNING  

### Alertas (derived view)

Gerados no agregador a partir de filas, devices (OFFLINE/DEGRADED; DISABLED ignorado),
Edge degradado e SLA vermelho do dia. Sem tabela/engine de alertas.

### Conteúdo

Canal + playlist/agenda ativos via `active_at`. Sem inventar “campanha”.

### Terminais

Usa **balcões ativos** (`Terminal.active`). Não inventa “operadores ativos”.

## Refresh

| Comportamento | Valor |
|---------------|-------|
| Auto refresh | 30s |
| TTL “Ao vivo” | 45s |
| Manual | botão Atualizar |
| Aba oculta | pausa (`document.visibilityState`) |
| Race | AbortController + store id corrente |
| Stale | mantém último snapshot + badge |

## Live status

| Estado | Quando |
|--------|--------|
| AO VIVO | dados frescos |
| ATUALIZANDO | request em voo |
| DADOS DESATUALIZADOS | TTL excedido ou refresh falhou com snapshot |
| ERRO PARCIAL | `sections.* === error` |
| ERRO | falha total sem snapshot |

## Resiliência / seções

Backend captura falhas por bloco (`metrics`, `queues`, `devices`, `content`) e
devolve `sections`. UI mostra alerta discreto no painel afetado.

## Loading / Empty / Error

- Loading: `SkeletonMetric` + `SkeletonCard`
- Empty filas / devices: copy operacional (sem mencionar API/seed)
- Erro total: `Alert` danger
- Erro parcial: alerta no painel
- Stale: mantém dados + warning

## Responsividade

| Viewport | Layout |
|----------|--------|
| Desktop / 1366×768 | grid 12 cols — KPIs + filas + alertas no topo |
| Tablet ~768 | 2 colunas quando apropriado |
| Mobile 390 | 1 coluna — alertas / filas / KPIs / devices |

## Acessibilidade

- headings semânticos (`h2` por seção)
- focus-visible em cards/links
- status com texto (Badge / StatusDot)
- gráfico com `aria-label` + resumo `sr-only`
- `aria-busy` no skeleton

## Fora de escopo (não feito)

Totem/Operator/Display 2.0, Layout Engine, Media/Playlist/Scheduling Studio,
Fleet 2.0, Analytics 2.0, Proof of Play, WebSocket obrigatório, Recharts/Vitest/RTL/Playwright.
