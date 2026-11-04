# UX-6C — Screen Override Engine

**Status:** READY FOR HOMOLOGATION  
**CODE VALIDATION:** PASS (após testes/build)  
**VISUAL VALIDATION:** PENDING  

## Objetivo

Separar conteúdo programado (Layout Engine / zones) de interrupções operacionais da TV.  
`ticket.called` deixa de depender de overlay hardcoded e passa por uma camada genérica de prioridade.

```
SCHEDULED CONTENT → LayoutResolver → Zones
SCREEN OVERRIDE ENGINE → OverrideResolver → OverrideRenderer
```

## Pre-flight UX-6B (unicidade global)

Verificado: índice parcial `uq_layout_templates_global_slug` em `layout_templates`  
(`UNIQUE(slug) WHERE store_id IS NULL`) já existe na migration UX-6B (`20261103_0013`).  
Migration UX-6C (`20261104_0014`) reforça de forma idempotente se ausente.  
`UNIQUE(store_id, slug)` sozinho **não** seria suficiente para `store_id=NULL` no PostgreSQL.

## Modelo `screen_overrides`

Campos: `id`, `store_id` (obrigatório), `override_type`, `priority`, `target_scope`, `target_id`,  
`payload` (JSON), `starts_at`, `expires_at` (obrigatório), `cancelled_at`, `dedupe_key`,  
`source_type`, `source_id`, `created_by_user_id`, `created_at`.

Ativo quando: `starts_at <= now AND expires_at > now AND cancelled_at IS NULL`.  
Sem scheduler de expiração — validade derivada do relógio.

## Priority model (fonte única backend)

Arquivo: `backend/app/modules/signage/override_priority.py`

| Tipo | Priority |
|------|----------|
| EMERGENCY | 400 |
| QUEUE_CALL | 300 |
| MANUAL | 200 |
| CAMPAIGN | 100 |
| BASE / SCHEDULED_CONTENT | 0 (não persistido) |

Cliente **não** define prioridade livre — o tipo determina a faixa.

**Distinção:** `Schedule.priority` (NORMAL/HIGH/EMERGENCY da agenda) ≠ `ScreenOverride.priority`.  
Unificação futura possível; não nesta sprint.

## Target scopes

`STORE` | `QUEUE` | `DISPLAY` | `CHANNEL`  
`STORE` → `target_id` NULL; demais → `target_id` obrigatório + validação mesma loja.  
`SCREEN_GROUP` **não** implementado (débito).

## Queue call integration

Após `call_next` / `recall` bem-sucedidos:

1. Cria `QUEUE_CALL` (~7s) best-effort  
2. Publica `ticket.called` / `ticket.recalled` **com** `data.override` embutido  
3. Falha no override → log; ticket permanece válido (sem rollback)

Core queue **nunca** depende de Digital Signage.

## WebSocket

| Evento | Uso |
|--------|-----|
| `ticket.called` / `ticket.recalled` + `override` | Queue call (dedupe única) |
| `screen.override.started` | EMERGENCY / MANUAL / CAMPAIGN |
| `screen.override.cancelled` | Cancelamento admin |

Eventos legados preservados. Frontend antigo ignora `override`.

## Player config

`GET /player/config` aditivo:

```json
{ "layout": {}, "active_overrides": [] }
```

Somente overrides ativos aplicáveis ao display, ordenados por prioridade.  
Cache antigo sem chave → fallback `[]`. Frontend sempre valida `expires_at`.

## Frontend

- `useOverrideManager` — seed config, WS, dedupe, timer `setTimeout` no próximo `expires_at`
- `OverrideResolver` — seleciona `currentOverride`
- `OverrideRenderer` — QUEUE_CALL / EMERGENCY / MANUAL / CAMPAIGN
- Layout permanece montado; override cobre com `z-index` (`DISPLAY_LAYER_Z.override = 40`)
- Legacy adapter: `ticket.*` sem `override` → QUEUE_CALL local ~7s
- TTS só QUEUE_CALL; dedupe por `override.id`

## Preemption

Prioridade maior cobre a menor; ao expirar/cancelar, o próximo válido retorna sem reiniciar a playlist base.

## Empate

`priority DESC`, `starts_at DESC`, `created_at DESC` — última chamada substitui anterior.

## API

- `GET /api/v1/screen-overrides`
- `POST /api/v1/screen-overrides` (não cria QUEUE_CALL)
- `POST /api/v1/screen-overrides/{id}/cancel`

Permissões: `signage.viewer` / `signage.editor` (+ queue manager/admin).

## Edge / clock

Timestamps UTC do backend + relógio local do device.  
Pequena dependência de skew documentada; sem NTP nesta sprint.

## Rolling deployment

| Mix | Comportamento |
|-----|----------------|
| FE antigo + BE novo | ignora `override` / `active_overrides`; overlay legado se ainda existir |
| FE novo + BE antigo | adapter legacy cria QUEUE_CALL local |

## Débitos

- Queue Call Buffer / FIFO arbitration  
- Visual editor de overrides  
- Screen groups como target  
- Override analytics / Proof of Play  
- Retail Media Campaign entity  
- Scheduled emergency workflows  

## Limitations

- Sem DELETE físico  
- Sem mídia emergencial complexa  
- CAMPAIGN ≠ entidade de campanha  
- Sem unificação Schedule.priority ↔ ScreenOverride  

## DISPLAY 2.0 Gate

UX-6A + UX-6B + UX-6C formam Display 2.0.  
Homologação comercial exige validação visual real (layouts + chamada + emergência em 1920×1080).  
Até lá: CODE PASS / VISUAL PENDING.
