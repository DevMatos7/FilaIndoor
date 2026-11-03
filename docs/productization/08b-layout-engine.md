# UX-6B — Layout Engine

## Objetivo

Engine **data-driven** para composição da TV:

```text
Player → LayoutResolver → LayoutTemplate → Zones → ZoneRenderer
```

Sem página React por layout. Sem editor visual. Sem screen_overrides (UX-6C).

## Modelo de dados

### `layout_templates`

| Campo | Notas |
|-------|--------|
| id | string 36 |
| store_id | NULL = system/global |
| name, slug | slug técnico estável |
| orientation | LANDSCAPE \| PORTRAIT |
| aspect_ratio | 16:9, 9:16, … |
| background / config | JSON |
| active, is_system | bool |

Índices: `(store_id, slug)` unique; **partial unique** `slug` WHERE `store_id IS NULL`.

### `layout_zones`

Percentuais 0–100: `x,y,width,height` (`Numeric(5,2)`), `zone_type`, `z_index`, `config` JSON.  
FK `layout_template_id` → CASCADE.

Validação: `x,y >= 0`, `w,h > 0`, `x+w <= 100`, `y+h <= 100`.

### Channel (compat)

- `layout` (**legacy string**, preservado)  
- `layout_template_id` nullable FK ON DELETE SET NULL  

## Coordinate system

Viewport relativo: `left/top/width/height` em `%`. Portrait-safe (não assume landscape).

## Zone types

| Type | Renderer |
|------|----------|
| MEDIA | MediaPlayer (1 por layout) |
| QUEUE | QueueZone (`footer` \| `sidebar` \| `fullscreen`) |
| TEXT | TextZone |
| CLOCK | ClockZone (hora local) |
| TICKER | TickerZone (texto estático MVP) |

Unknown zone → log + ignore (player continua).

## System templates

| Slug | Composição |
|------|------------|
| `fullscreen_media` | MEDIA 100×100 |
| `media_queue_footer` | MEDIA 100×82 + QUEUE footer 18 |
| `media_queue_sidebar` | MEDIA 72×100 + QUEUE sidebar 28 |
| `queue_fullscreen` | QUEUE fullscreen 100×100 |

`store_id=NULL`, `is_system=true`. Seed na migration + `LayoutService.ensure_system_templates()` (idempotente).

## Legacy mapping

Auditoria: único valor legado no código/default = `queue_media_split`.

```text
queue_media_split → media_queue_footer
```

Valores desconhecidos: tenta slug; senão default `media_queue_footer`.

## Layout resolution (backend)

1. `channel.layout_template_id` (active)  
2. legacy `channel.layout` → map  
3. system `media_queue_footer`  
4. emergency payload hard-coded  

Frontend: se `layout` ausente/ inválido (cache Edge antigo) → `EMERGENCY_LAYOUT` (= footer UX-6A).

## Player contract (aditivo)

`GET /player/config` inclui:

```json
"layout": { "id", "slug", "name", "orientation", "aspect_ratio", "background", "config", "zones": [...] }
```

Campos anteriores preservados. `channel.layout` agora reflete o valor real do canal.

## APIs

```http
GET /api/v1/layout-templates?store_id=
GET /api/v1/layout-templates/{id}
```

Read-only. Sem CRUD visual.

Channel create/update aceita `layout_template_id` opcional.

## Frontend architecture

```text
DisplayShell
  ├── LayoutResolver
  │     └── ZoneRenderer*
  └── QueueCallOverlay   ← global, acima (UX-6C)
```

## Edge / cache / rolling deploy

| Cenário | Comportamento |
|---------|----------------|
| Backend novo + frontend novo | layout resolvido |
| Cache antigo sem `layout` | emergency footer |
| Frontend antigo + backend novo | ignora chave `layout` |
| Canal só com `queue_media_split` | map → media_queue_footer |

## Migration

- Revision: `20261103_0013`  
- Revises: `20261028_0012`  
- Upgrade: tables + FK + seed system  
- Downgrade: drop FK column + tables (não apaga canais)

## Limitations / débitos

- QueueCallOverlay ainda hardcoded (UX-6C)  
- Ticker sem marquee  
- Sem templates portrait dedicados (`media_queue_portrait` futuro)  
- Sem editor admin  
- VISUAL VALIDATION pode ficar PENDING  

## Riscos mitigados

Layout inválido / zones vazias / MEDIA duplicada / template inativo / cache antigo / canal sem template → fallbacks.  
TV nunca fica preta por erro de layout.
