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

Fonte canônica no host: `backend/.env` (não versionar senha).

| Env | Default | Uso |
|-----|---------|-----|
| `RETAIL_PROVIDER` | `mock` | `mock` \| `ciss_db2` |
| `DB2_CONN_STRING` | vazio | ODBC **sem** `DRIVER=` (`DATABASE=…;HOSTNAME=…;PORT=…;UID=…;PWD=…;SCHEMA=…`) |
| `DB2_SCHEMA` | `DBA` | schema |
| `DB2_FALLBACK_HOST` | vazio | host de fallback (documental / futuro) |
| `DB2_FALLBACK_PORT` | `50044` | porta fallback |
| `IBM_DB_HOME` | vazio | path do cliente IBM (Linux/Docker futuro) |
| `DB2_ODBC_DRIVER` | `IBM DB2 ODBC DRIVER` | nome do driver ODBC no host |
| `RETAIL_WARN_AFTER_SECONDS` | 300 | degraded |
| `RETAIL_HARD_STOP_AFTER_SECONDS` | 900 | stale |

### Como usar o DB2 real

1. No `backend/.env`: `RETAIL_PROVIDER=ciss_db2` + `DB2_CONN_STRING` preenchido.
2. Host Windows precisa do **IBM DB2 ODBC DRIVER** (já validado na auditoria DRC-1).
3. Mapear loja → `IDEMPRESA` em `/retail-content` (ex.: `1` = Supermercado Real).
4. Sync: UI “Sincronizar agora” **ou**  
   `python -m app.tools.retail_data_sync --store <uuid> --full`
5. **Docker `filaindoor_api`:** ainda **não** inclui driver DB2 — sync CISS real roda no host até o Módulo 5/infra.

### Validação host (2026-11-05)

| Check | Resultado |
|-------|-----------|
| ODBC 64-bit | `IBM DB2 ODBC DRIVER` + `… - DB2COPY1` presentes |
| `scripts/validate_ciss_db2_sync.py --company 1 --limit 20` | **PASS** |
| Preços sample | `123.58` / `155.87` / `128.98` (após `CAST AS DOUBLE`) |
| Postgres | products + prices ativos na loja Campo Novo (`company_code=1`) |

**Bug de escala:** `pyodbc` + IBM ODBC devolve `DECIMAL` sem escala (ex. `2.19` → `2190000`; qty `50` → `50000`). Fix: `CAST(... AS DOUBLE)` em preços e `QTDPRODUTO`.

## Gate 1R (fechamento)

Ver [`03-real-ciss-reconciliation.md`](./03-real-ciss-reconciliation.md).

- Mapping real Campo Novo ↔ IDEMPRESA 1  
- Gertec vs política: **CONFIRMED** (50/50)  
- Amostra 31 SKUs: preço/unidade/promo/qty/API **100% MATCH**  
- Estoque: **PARTIALLY CONFIRMED** (soma empresa; sem `location_code`)  
- Promo ativa e multi-tier qty: **NOT AVAILABLE IN SAMPLE** (não fabricado)

## Segurança

- DB2 read-only
- Health sem host/senha/SQL
- TV/player não usam este módulo ainda

## Não incluído (Módulo 2+)

PRICE_TABLE · PRODUCT_GRID · Playlist DYNAMIC · ProductMedia download · PoP
