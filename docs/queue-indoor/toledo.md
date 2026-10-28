# Toledo

## Sprint 13 — Discovery

Checklist e inventário: [`docs/integrations/toledo-discovery.md`](../integrations/toledo-discovery.md)

## Sprint 14 — Adapter

- `NativeQueueProvider` — fonte da verdade da fila (QueueService)
- `ToledoProvider` — side-channels (`player_push`, `history`) só se confirmados
- Falha Toledo **nunca** bloqueia emissão/chamada nativa
- `TOLEDO_ENABLED=false` → modo efetivo `NATIVE` (adapter em standby)
- `TOLEDO_MOCK=true` — POC sem rede (testes)

### Env

| Variável | Default | Uso |
|----------|---------|-----|
| `TOLEDO_ENABLED` | `false` | Liga side-channels |
| `TOLEDO_MODE` | `NATIVE` | `NATIVE` \| `TOLEDO_DISPLAY` \| `TOLEDO_SYNC` \| `TOLEDO_FULL` |
| `TOLEDO_API_BASE_URL` | vazio | Base confirmada no discovery |
| `TOLEDO_API_KEY` | vazio | Secret (não versionar) |
| `TOLEDO_MOCK` | `false` | Simula push/histórico |

### API

- `GET /toledo/status` · `GET /toledo/adapter`
- `POST /toledo/adapter/test-push`
- `POST /toledo/adapter/sync-history`
