# Módulo 1 — Retail Data Foundation

## O que entregamos

Fundação auditável CISS → Postgres **sem** PRICE_TABLE / player dinâmico.

- Mapping `retail_store_sources` (store ↔ IDEMPRESA)
- Modelo canônico: products, store_products, prices (REGULAR/PROMOTION/QUANTITY), promotions
- Sync + watermark + sync_runs
- Freshness FRESH/DEGRADED/STALE/FAILED
- Health / sync / reconcile / products APIs
- Provider `mock` (testes) + `ciss_db2` (ODBC read-only)
- CLI `python -m app.tools.retail_data_sync`
- UI `/retail-content` — saúde + mapeamento + sync
- Timezone da loja validado (IANA) no sync/mapping (`stores.timezone` já existia)

## Migration

`20261105_0015` → revises `20261104_0014`

## Config

| Env | Default | Uso |
|-----|---------|-----|
| `RETAIL_PROVIDER` | `mock` | `mock` \| `ciss_db2` |
| `DB2_CONN_STRING` | vazio | ODBC sem DRIVER= |
| `DB2_SCHEMA` | `DBA` | schema |
| `RETAIL_WARN_AFTER_SECONDS` | 300 | degraded |
| `RETAIL_HARD_STOP_AFTER_SECONDS` | 900 | stale |

## Segurança

- DB2 read-only
- Health sem host/senha/SQL
- TV/player não usam este módulo ainda

## Não incluído (Módulo 2+)

PRICE_TABLE · PRODUCT_GRID · Playlist DYNAMIC · ProductMedia download · PoP
