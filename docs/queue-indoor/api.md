# API — REAL Fila & Indoor

Base: `/api/v1`

## Auth

- `POST /auth/login` (OAuth2 password form)
- `GET /auth/me`

Header de idempotência (operações críticas):

```http
Idempotency-Key: <uuid>
```

## Org

- `GET|POST /companies`
- `GET|POST /stores`
- `GET|POST /departments`

## Filas

- `GET /queues`
- `POST /queues`
- `GET /queues/{id}`
- `PATCH /queues/{id}` — nome, status, prefixes, pesos, totem, etc.; retorna settings
- `GET /queues/{id}/settings`
- `GET /queues/{id}/status`
- `GET /queues/{id}/waiting`
- `POST /queues/{id}/tickets`
- `POST /queues/{id}/next`

## Senhas / histórico

- `GET /tickets` — histórico paginado (`queue_id`, `status`, `ticket_type`, `search`, `limit`, `offset`)
- `GET /tickets/{id}` — timeline + `timings` (espera/atendimento/total)
- `POST /tickets/{id}/recall`
- `POST /tickets/{id}/start`
- `POST /tickets/{id}/complete`
- `POST /tickets/{id}/no-show`
- `POST /tickets/{id}/cancel`

## Dispositivos (admin)

- `GET /devices/overview` — terminais + displays
- `PATCH /displays/{id}` — `audio_enabled`, nome, ativo
- `PATCH /terminals/{id}` — nome, ativo

## Totem / player / WS

- `POST /kiosk/{queue_id}/tickets` — header `X-Kiosk-Token`
- `GET /player/config` — header/query token do display
- WebSocket `/ws/v1/store/{store_id}`

## Analytics (Sprint 6)

- `GET /analytics/summary?day=YYYY-MM-DD&queue_id=` — KPIs do dia (emitidas, concluídas, espera avg/mediana/P90, atendimento, ausências, SLA, série horária, fila atual)

## Mídia (Sprint 7)

- `GET /media?store_id=&media_type=`
- `GET /media/{id}`
- `POST /media` — multipart (`store_id`, `name`, `file`, `duration_seconds?`)
- `POST /media/web` — JSON `{ store_id, name, url, duration_seconds? }`
- `DELETE /media/{id}` — soft delete (`?hard=true` remove arquivo)
- Arquivos públicos: `/media/files/{store_id}/...`

## Playlists (Sprint 8)

- `GET|POST /playlists`
- `GET|PATCH|DELETE /playlists/{id}`
- `POST /playlists/{id}/items`
- `PATCH /playlists/{id}/items/reorder` — body `{ item_ids: [...] }`
- `PATCH|DELETE /playlists/{id}/items/{item_id}`
- `PATCH /displays/{id}` aceita `playlist_id`, `channel_id`, `screen_group_id`

## Canais & Agenda (Sprint 9)

- `GET|POST /channels`
- `GET|PATCH /channels/{id}`
- `GET /channels/{id}/now` — playlist vigente no instante
- `GET /channels/{id}/conflicts` — sobreposição mesma prioridade
- `POST /screen-groups`
- `POST|PATCH|DELETE /schedules`

## Devices (Sprint 10)

- `POST /devices/pairing` — gera código (sem auth)
- `POST /devices/enroll` — admin vincula código → loja
- `GET /devices` · `GET /devices/{id}`
- `GET /devices/{id}/heartbeats`
- `POST /devices/{id}/heartbeat` — `X-Device-UUID` ou `X-Display-Token`
- `POST /devices/{id}/enable` · `POST /devices/{id}/disable`
- `GET /devices/overview` — terminais + displays + fleet

## Edge / Offline (Sprint 11)

- `GET /edge/health`
- `GET /edge/snapshot?store_id=`
- `GET /edge/sync/status`
- `GET /edge/outbox`
- `POST /edge/outbox` — body `{ events: [...] }` (idempotente por `event_id`)
- `POST /edge/sync` · `POST /edge/sync/retry`

## Integrações CISS (Sprint 12)

- `GET /integrations/provider`
- `GET|POST /integrations`
- `POST /integrations/sync?store_id=`
- `GET /integrations/products` · `GET /integrations/snapshots?store_id=`
- `GET /integrations/sync-runs`
- `GET|POST /integrations/offers`
- `GET /integrations/offers/active?store_id=`
- `GET /integrations/offers/{id}/render` — snapshot local only

## Toledo (Sprint 13–14)

- `GET /toledo/status` — flag + modo efetivo + capabilities
- `GET|PUT /toledo/discovery` — checklist
- `GET /toledo/adapter` — native vs toledo caps
- `POST /toledo/adapter/test-push`
- `POST /toledo/adapter/sync-history`
- `TOLEDO_ENABLED=false` → `effective_mode=NATIVE` (fila intacta)

## REAL+ / Fila Virtual (Sprint 15)

- `GET /real-plus/queues/{id}/preview`
- `POST /real-plus/queues/{id}/tickets`
- `GET /real-plus/track/{token}`
- `POST /real-plus/track/{token}/check-in`
- `POST /real-plus/track/{token}/subscribe`
- `GET /real-plus/virtual-tickets` (admin)

## Health

- `GET /health`
- `GET /` — índice da API
