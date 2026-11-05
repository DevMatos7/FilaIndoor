# Dynamic Retail Content — PRD (resumo operacional)

**Fase:** Dynamic Retail Content / CISS Price & Product Engine  
**Status:** MÓDULO 1 em execução  
**Dependência:** Productization UX-0→UX-12 HOMOLOGATED  
**Piloto FASE 2:** permanece aberto em paralelo (`docs/pilot/`); DRC não substitui o piloto operacional.

## Princípio

CISS (read-only) → Retail Data Foundation (Postgres) → Dynamic Content → Playlist → Player → Override (senha).

A TV **nunca** consulta DB2. Preço **nunca** é digitado no Indoor no MVP.

## Módulos

| Módulo | Nome | Status |
|--------|------|--------|
| 1 | Retail Data Foundation | **IN PROGRESS** |
| 2 | Price Table Engine | NOT STARTED |
| 3 | Player + Playlist Dynamic | NOT STARTED |
| 4 | Product Visual Engine | NOT STARTED |
| 5 | Automation & Resilience | NOT STARTED |
| 6 | Visual QA / Pilot Gate | NOT STARTED |

## Compliance

TV = comunicação comercial **complementar**. Não substitui etiquetagem física sob rotação sem validação jurídica.

PRD completo: mensagem de produto / homologação Productization (fonte de escopo). Este arquivo é o índice operacional no repo.
