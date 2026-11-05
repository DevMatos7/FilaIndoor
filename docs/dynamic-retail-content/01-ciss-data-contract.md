# CISS Data Contract — Auditoria DB2 (read-only)

**Data:** 2026-11-05  
**Ambiente:** `DATABASE=SUPEREAL` · schema `DBA` · host DataCISS  
**Método:** ODBC IBM DB2 DRIVER · queries somente leitura · sem dump de credenciais  

**Referência operacional confirmada (negócio):** tabela de preço = `POLITICA_PRECO_PRODUTO`; view de cadastro = `PRODUTOS_VIEW` (sync canônico permanece em `PRODUTO`/`PRODUTO_GRADE` + política).

## Integração pré-existente no repo

| Artefato | Estado |
|----------|--------|
| `CISSDB2Provider` | Stub (retorna vazio) |
| `CISSApiProvider` | HTTP genérico (endpoints não confirmados no CISS real) |
| `MockERPProvider` | Demo açougue |
| `erp_products` / `erp_product_store_snapshots` | Sprint 12 — snapshot simples |
| Env legado | `CISS_DB2_DSN`, `ERP_PROVIDER` |
| Env operacional | `DB2_CONN_STRING`, `DB2_SCHEMA` (`.env` local) |

**Decisão Módulo 1:** novo domínio `retail_*` canônico + adapter DB2 real; não misturar SQL CISS no player/frontend.

---

## Mapeamento canônico confirmado

| CANONICAL | CISS TABLE | CISS FIELD | JOIN / FILTER | SEMÂNTICA | NULL |
|-----------|------------|------------|---------------|-----------|------|
| company_code | `EMPRESA` | `IDEMPRESA` | PK | Filial/empresa CISS (1=Supermercado Real, 2=Atacado…) | N |
| company_name | `EMPRESA` | `NOMEFANTASIA` / `RAZAOSOCIAL` | | Nome fantasia | Y |
| source_product_id | `PRODUTO` / `PRODUTO_GRADE` | `IDPRODUTO` + `IDSUBPRODUTO` | grade PK composta | SKU interno CISS = `"{idproduto}:{idsubproduto}"` | N |
| description | `PRODUTO` | `DESCRCOMPRODUTO` | | Descrição comercial principal | N |
| commercial_description | `PRODUTO_GRADE` | `DESCRRESPRODUTO` / `SUBDESCRICAO` | | Descrição resumida/grade | Y |
| gtin | `PRODUTO_GRADE` | `CODBAR` / `IDCODBARPROD` | | EAN/GTIN | Y |
| unit | `PRODUTO` | `EMBALAGEMSAIDA` | | Unidade de venda (ex. KG, UN) — 2 chars | N |
| section_code | `PRODUTO` | `IDSECAO` | → `SECAO.DESCRSECAO` | Seção mercadológica | N |
| group_code | `PRODUTO` | `IDGRUPO` | → `GRUPO` | Grupo | N |
| subgroup_code | `PRODUTO` | `IDSUBGRUPO` | → `SUBGRUPO` | Subgrupo | N |
| active (master) | `PRODUTO_GRADE` | `FLAGINATIVO` | `T`=inativo · `F`=ativo | Flag CISS T/F | N |
| sellable_store | `PRODUTO_EMPRESA` | `FLAGPERMITEVENDA` | `IDEMPRESA`+`IDPRODUTO`(+sub) | Comercializável na empresa | N |
| regular_price | `POLITICA_PRECO_PRODUTO` | `VALPRECOVAREJO` → **`CAST(... AS DOUBLE)`** | por `IDEMPRESA`+produto+sub | Preço varejo vigente da loja. ODBC IBM devolve DECIMAL sem escala (2.19→2190000); DOUBLE corrige. | Y |
| promotion_price | `POLITICA_PRECO_PRODUTO` | `VALPROMVAREJO` → **`CAST(... AS DOUBLE)`** | idem | Preço promo varejo (mesma correção de escala) | Y |
| promotion_start | `POLITICA_PRECO_PRODUTO` | `DTINIPROMOCAOVAR` | DATE | Início promo varejo | Y |
| promotion_end | `POLITICA_PRECO_PRODUTO` | `DTFIMPROMOCAOVAR` | DATE | Fim promo varejo | Y |
| promo_min_qty | `POLITICA_PRECO_PRODUTO` | `QTDMINPROMVAREJO` | | Qtd mínima promo | Y |
| price_source_updated_at | `POLITICA_PRECO_PRODUTO` | `DTALTERACAO` / `DTALTERACAOVAR` | | Watermark de preço | Y |
| quantity_price | `PRODUTO_DESCONTO_QTDE` | `VALPRECOVAREJO` + `QTDPRODUTO` → **`CAST(... AS DOUBLE)`** | `IDEMPRESA` · ignora `TIPOSTATUS` I/N | Preço por quantidade (ODBC também corrompe escala de QTD) | N amount |
| stock_qty | `PRODUTO_GRADE_SALDO_EST_VW` | `QTDATUALESTOQUE` | `IDEMPRESA`+produto+sub (+local) | Saldo | N |
| image_path | `PRODUTO_GRADE_IMAGENS` | `PATHIMAGEM` | `FLAGIMAGEMPADRAO` | Path no ERP — **não** baixamos binário no Módulo 1 | Y |

---

## Contagens observadas (auditoria)

| Tabela | COUNT aproximado |
|--------|------------------|
| PRODUTO | 85 760 |
| PRODUTO_GRADE | 103 142 |
| PRODUTO_EMPRESA | 14 946 |
| POLITICA_PRECO_PRODUTO | 721 994 |
| PRODUTO_DESCONTO_QTDE | 187 969 |
| PRODUTO_GRADE_SALDO_EST_VW | 284 815 |
| PRODUTO_GRADE_IMAGENS | 3 344 |
| SECAO / GRUPO / SUBGRUPO | 23 / 115 / 912 |
| PRODUTO_PRECO_DIA | **0** (não usar como fonte) |
| CAMPANHA_PROMOCIONAL* | **0** (não usar no MVP) |

---

## Campos / fontes NÃO confirmadas como verdade de preço na loja

| Item | Status |
|------|--------|
| `PRODUTO_GRADE.VALPRECOVAREJO` como preço **por loja** | **NOT CONFIRMED** — existe no grade; política por empresa é a fonte confirmada para TV |
| `PRODUTO_PRECO_DIA` | vazia — **NOT CONFIRMED** uso operacional |
| `CAMPANHA_PROMOCIONAL` | vazia neste DB — **NOT CONFIRMED** |
| Preço “efetivo” PDV (frontbox) vs política | **CONFIRMED** via `EMP1_BUSCA_PRECO_GERTEC_VW` ↔ `POLITICA_PRECO_PRODUTO.VALPRECOVAREJO` (50/50 MATCH, empresa 1). UI frontbox ainda sem screenshot. |
| Imagem utilizável via URL pública | **NOT CONFIRMED** — só path; ProductMedia no Módulo 4 |
| `LOCAL_ESTOQUE` table | **NOT PRESENT**; saldo via view |
| Timestamp incremental universal confiável | Parcial — usar `DTALTERACAO` / `DTALTERACAOVAR` com watermark; full scan controlado se necessário |

---

## Regra de chave de produto

```text
source_system = CISS
source_product_id = "{IDPRODUTO}:{IDSUBPRODUTO}"
```

Exemplo: `12345:0`

---

## Store mapping

Nunca assumir `store.id == IDEMPRESA`.

Usar `retail_store_sources`:
- `store_id` (UUID app)
- `company_code` = `IDEMPRESA` (string)
- `location_code` opcional (local de estoque preferencial) — **NOT CONFIRMED** default por loja  
- Estoque canônico atual = **soma** `QTDATUALESTOQUE` por `IDEMPRESA`+SKU (múltiplos `IDLOCALESTOQUE`)

---

## Segurança

- READ ONLY  
- Credenciais só em env/secret  
- Health/APIs nunca retornam DSN, senha, SQL  
- Queries com timeout + `FETCH FIRST` / filtros por empresa
