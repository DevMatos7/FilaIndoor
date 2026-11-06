# Module 6 — Pilot Readiness Report

**Projeto:** DevMatos7/FilaIndoor  
**Fase:** Dynamic Retail Content / CISS Price & Product Engine  
**Gate HEAD (pré-commit Module 6):** `25a402a` (+ working tree Module 6)  
**Decisão produto:** **CONDITIONAL GO**  
**Release delivery:** **NO-GO** (branch local ahead de `origin/main`; push não autorizado neste gate)

---

## Escopo do piloto

| Inclui | Exclui |
|--------|--------|
| 1 loja — Loja Campo Novo (IDEMPRESA 1, America/Cuiaba) | Automatic stock filtering |
| Queue / Totem / Operator / Display | Proof of Play |
| PRICE_TABLE, PRODUCT_GRID, PRODUCT_HERO, PROMOTION_BOARD | Retail Media / billing |
| CISS products, prices, offers, images | AI / forecasting |
| Automation enabled | Device Commands |
| Playlist mista MEDIA + Dynamic | Template Builder livre |

### Condições operacionais

1. **Stock:** produtos **não** são retirados automaticamente por saldo.  
2. **Imagem:** CISS quando disponível; sem foto → fallback; override MANUAL preservado.  
3. **Oferta:** PROMOTION_BOARD `CISS_OFFER` só com campanhas ativas no escopo da empresa (EMPRESA junction **ou** fallback PRICED_ITEMS quando a empresa não publica vínculos ativos — caso IDEMPRESA=1).  
4. **Rollback:** desativar DynamicContent/playlist dinâmica → MEDIA + fila. Queue não depende do Retail Engine.  
5. **Kill switch:** `RETAIL_PROVIDER` / desligar scheduler; remover itens DYNAMIC da playlist segura.  
6. **Fallback:** manter playlist só-MEDIA pronta.

### Monitoramento

sync failures · freshness · price mismatches · player failures · WS reconnects · image import failures · offer sync failures

---

## Correções aplicadas no Module 6 (não features novas)

1. Import de imagem **incremental** (`LENGTH+head` fingerprint → sem re-leitura de BLOB).  
2. HEX(SUBSTR) com offsets literais (corrige SQL0171N).  
3. Ofertas IDEMPRESA=1: fallback por itens com preço na loja quando não há vínculos EMPRESA vigentes.  
4. P0 descrições: nunca usar `source_product_id` como label TV + repair 4777 SKUs.

---

## Evidências-chave

| Gate | Resultado |
|------|-----------|
| Real price (≥32 comparáveis) | PASS · 0 mismatch |
| Real CISS offer | PASS · campanha 19152 + 127 itens |
| Real CISS image | PASS · identity OK · TV com JPEG CISS |
| Image sync #2 | blob_reads=0 · bytes=0 |
| Production mock guard | PASS |
| Stale safety / WS / ETag | PASS (M5 + DRC6 soft) |
| Playwright DRC6 | PASS |
| Backend suites DRC | PASS |
| Frontend build | PASS |
| Migrations → `20261106_0020` head | PASS |
| Hardware físico | **PENDING** |

### Image sync (amostra gate)

| | Sync 1 | Sync 2 |
|--|--------|--------|
| meta_probes | 25 | 25 |
| blob_reads | 0* | 0 |
| bytes | 0* | 0 |
| unchanged | 5 | 5 |

\*Após primeira materialização amostral em script dedicado: sync1 leu BLOBs novos; segundo ciclo fingerprint-only.

### Cobertura

- Produtos ativos (snapshot gate): ~6,8k  
- Links CISS PRIMARY no gate: 5+ (crescendo por ciclo; amostra visual suficiente)  
- Campanhas vigentes sincronizadas: 30 · itens: 310  

---

## Homologação final

| Módulo | Status |
|--------|--------|
| 1 Retail Data Foundation | FINAL HOMOLOGATED |
| 2 Price Table Engine | FINAL HOMOLOGATED |
| 3 Dynamic Playlist & Player | FINAL HOMOLOGATED |
| 4 Product Visual Engine | FINAL HOMOLOGATED |
| 5 Automation & Resilience | FINAL HOMOLOGATED |
| 5R CISS Offers & Images | FINAL HOMOLOGATED |
| 6 Final Pilot Gate | **CONDITIONAL GO** |

---

## Riscos / dívida

- Deploy piloto deve usar **API com ODBC + RETAIL_PROVIDER=ciss_db2** (não o compose mock).  
- Volume de media host↔container precisa alinhamento.  
- Cobertura de imagem completa é gradual (cap 200/ciclo).  
- Push para `origin/main` pendente de autorização explícita.
