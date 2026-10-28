# Integração CISS / ERP — Sprint 12

## Princípios

- Fila **não depende** do CISS.
- CISS enriquece **Video Indoor** (ofertas dinâmicas).
- **Nunca gravar** no ERP a partir deste módulo (MVP).
- Signage/TV **nunca** consulta CISS por frame — só snapshot local.

## Camada

```text
ERPProvider (interface)
  ├─ MockERPProvider          (demo açougue)
  ├─ CISSApiProvider          (CISSLive/API — read-only)
  └─ CISSDB2Provider          (DB2 stub read-only)

IntegrationService.sync_store
  → erp_products
  → erp_product_store_snapshots

CampaignService.render
  → product_offer_templates + snapshot local
```

## Variáveis

| Env | Default | Uso |
|-----|---------|-----|
| `ERP_PROVIDER` | `mock` | `mock` \| `ciss_api` \| `ciss_db2` |
| `CISS_API_BASE_URL` | vazio | Base da API |
| `CISS_API_KEY` | vazio | Token |
| `CISS_DB2_DSN` | vazio | DSN (só leitura) |
| `ERP_PRICE_SYNC_MINUTES` | 10 | Frequência sugerida |
| `ERP_STOCK_SYNC_MINUTES` | 20 | Frequência sugerida |

## Gate

Nenhuma gravação no CISS. Adapters não expõem write; `writes_forbidden: true`.
