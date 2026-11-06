# Module 6 — Pilot Defect Register

**Homologação:** P0=0 · P1=0 · P2=5 · P3=2  
P2/P3 **não** reabrem desenvolvimento de produto antes do piloto.

## P0

*Nenhum aberto.*

| ID | Título | Status | Correção |
|----|--------|--------|----------|
| DRC6-P0-01 | Descrição TV = `source_product_id` | **FIXED** | Bloqueio estrutural + repair 4777 SKUs |
| DRC6-P0-02 | `data_version` `dirty:` empilhado → VARCHAR(80) + sync crash | **FIXED** (hotfix pós-`8b830b2`) | Poison fixo `dirty` + `rollback` no scheduler |

## P1

*Nenhum aberto.*

## P2 — classificação pós-homologação

| ID | Título | Tratamento | Nota |
|----|--------|------------|------|
| DRC6-P2-01 | API em `RETAIL_PROVIDER=mock` | **Condição obrigatória de instalação (RC-2)** | Não é débito “para depois”; piloto exige `ciss_db2` |
| DRC6-P2-02 | Media host ≠ volume do player | **Condição obrigatória de instalação (RC-3)** | Import CISS e player devem ver o mesmo storage |
| DRC6-P2-03 | Cobertura imagem CISS gradual | **Aceito no piloto** | Fallback existe; 2º sync sem BLOB massivo |
| DRC6-P2-04 | Race screenshot Hero/Grid | **QA/polish** | Payload/fluxo reais OK; não falha de player |
| DRC6-P2-05 | JPEG CISS ~200×200 | **Aceito · observar em Hero/4K** | Sem IA/upscale antes de evidência operacional |

## P3

| ID | Título | Tratamento |
|----|--------|------------|
| DRC6-P3-01 | Copy admin / polish | Adiar |
| DRC6-P3-02 | Scripts `_m6_debug_*` | Fora do runtime |

## Aceites explícitos (CONDITIONAL GO)

- STOCK FILTER: **DISABLED BY DESIGN** — TV não garante disponibilidade de estoque
- PHYSICAL HARDWARE: PENDING → Gate RC-4
- RELEASE DELIVERY: NO-GO até RC-1 (`origin/main` = HEAD homologado)
- Cobertura de imagem parcial com fallback visual
