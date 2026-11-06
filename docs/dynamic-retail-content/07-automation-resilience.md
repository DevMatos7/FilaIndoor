# Module 5 — Automation & Resilience

## Objetivo

Sincronização automática CISS → detecção de mudança → invalidação direcionada → WebSocket store-scoped → player refetch (ETag/`valid_until`) sem intervenção humana, sem preço stale e sem mock silencioso em produção.

## Scheduler

- Motor único: **APScheduler** (`BackgroundScheduler`), iniciado no startup FastAPI.
- Flag: `RETAIL_AUTOMATION_ENABLED` (default `true` em runtime; **`false` em pytest**).
- Jobs por entidade: `PRODUCT` / `PRICE` / `PROMOTION` / `AVAILABILITY`.
- Intervalos (config, não hardcoded):
  - `RETAIL_SYNC_PRODUCT_SECONDS` (default 900)
  - `RETAIL_SYNC_PRICE_SECONDS` (default 60)
  - `RETAIL_SYNC_PROMOTION_SECONDS` (default 60)
  - `RETAIL_SYNC_AVAILABILITY_SECONDS` (default 180)
- Escopo: somente `retail_store_sources.active = true` e `source_system = CISS`.
- Shutdown gracioso no evento FastAPI shutdown.

## Concurrency / multi-worker

- Lock lógico: `retail-sync:{store_id}:{entity}`
- Postgres: `pg_try_advisory_lock` / `pg_advisory_unlock` em **conexão dedicada**
  (não reutiliza o Session pool — `commit` durante o sync não pode orphanar o lock)
- SQLite/testes: `threading.Lock` non-blocking
- Segunda execução → `SKIPPED` (não lê DB2 em paralelo)
- Liberação garantida em success / failure / exception + `conn.close()`

## RetailSyncRun.trigger

| Trigger | Origem |
|---------|--------|
| `SCHEDULED` | APScheduler |
| `MANUAL` | Admin “Sincronizar agora” |
| `CLI` | reserved |

## Watermark

- Avança **somente após commit** de sucesso.
- Falha: valor anterior preservado; `consecutive_failures++`; `last_error_at` setado.

## Change detection → Impact → Invalidation

1. Sync retorna `changed_product_ids` por entidade.
2. `DynamicContentImpactResolver` resolve conteúdos afetados (MANUAL / HYBRID / AUTOMATIC).
3. `DynamicInvalidationService`:
   - marca snapshots `data_version = dirty:…`, `publishable=false` (lazy regen)
   - publica WS `dynamic_content.invalidated` **somente na loja** (nunca global)
4. Payload WS mínimo: `{ dynamic_content_id, reason, version, store_id }` — **sem preço**.

## Player

- WS = sinal; HTTP/ETag = fonte de verdade.
- Invalidation → cache dirty → prefetch → aplica no **boundary de página** (ou ao sair de QUEUE_CALL).
- STALE/FAILED/empty → skip urgente (sem esperar boundary comercial).
- Cache utilizável só se `now < valid_until` e não dirty.
- Rede offline + cache válido → mantém; cache expirado → não exibe preço.
- Recuperação automática no próximo fetch (sem reload de página).
- Shrink de páginas: índice seguro via módulo (`pageIndex % pageCount`).

## valid_until / promoção temporal

Mínimo entre:

- janela soft de freshness (`RETAIL_WARN_AFTER_SECONDS`, capped)
- próximo `promotion.starts_at`
- `promotion.expires_at + 1s` (**end inclusive**, semântica Module 1R)
- Timezone: `Store.timezone` (nunca browser / nunca hardcode SP)

## Freshness (≠ sync interval)

- `RETAIL_WARN_AFTER_SECONDS` (default 300)
- `RETAIL_HARD_STOP_AFTER_SECONDS` (default 900)
- Estados: `FRESH` / `DEGRADED` / `STALE` / `FAILED` / `UNKNOWN`
- Health expõe `consecutive_failures`, `last_success_at`, `last_failure_at`, alerts derivados

## Production mock guard

| Ambiente | `RETAIL_PROVIDER=mock` |
|----------|-------------------------|
| DEV / TEST | permitido |
| `APP_ENV=production` | **proibido** (fail-fast `ValidationError`; scheduler não inicia) |

Escape hatch explícito apenas: `RETAIL_ALLOW_MOCK_IN_PRODUCTION=true` (log warning).

Docker Compose usa mock com `APP_ENV=development` — adequado a QA; produção nunca herda silenciosamente.

## Commercial Availability Decision

**STOCK COMMERCIAL SOURCE: NOT CONFIRMED**

Motivo: `PRODUTO_GRADE_SALDO_EST_VW` expõe múltiplos `IDLOCALESTOQUE` sem mapeamento operacional comprovado (área comercial vs depósito vs reserva) para Loja Campo Novo. Soma por empresa reconciliou pontualmente, mas **não** prova disponibilidade comercial anunciável.

**STOCK FILTER: DISABLED BY DESIGN**

`available_only=true` continua rejeitado ponta a ponta.

## Observabilidade

Logs: `retail.sync.scheduled|started|completed|failed`, `dynamic.invalidated`, player `dynamic.prefetched|cache.*|stale.skipped`.

## Critérios

Ver relatório Module 5 no chat / `progress.md`.

## Module 5R (fontes CISS)

Scheduler reutilizado para `OFFER` / `PRODUCT_IMAGE` / `PRICE_CHAIN`.  
Detalhes e gates: [08-ciss-offers-images.md](./08-ciss-offers-images.md).
