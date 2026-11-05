# FASE 2 — PILOTO OPERACIONAL

**Status:** `OPEN`  
**Abertura:** 2026-11-05  
**Pré-requisito da Productization:** HOMOLOGATED (`docs/productization/17-productization-closure.md`)

---

## Objetivo

Provar, em **uma loja real supervisionada**, que o produto:

1. opera sem falha crítica (fila + Indoor), e  
2. **melhora a operação** (gestão, pessoas, hardware),

antes de qualquer rollout multi-loja.

Não é produção ampla. Não é sprint de features.

---

## Escopo do Piloto 1

| Dimensão | Decisão |
|----------|---------|
| Lojas | **1** (controlada) |
| Timezone | **1** (servidor alinhado) |
| Resiliência | **ONLINE-DEPENDENT** |
| Se backend cair | novas emissões **podem interromper** |
| Risco offline | **ACEITO E MONITORADO** |
| Browser / player | controlado (Chromium-first) |
| Versão | commit/tag Release Candidate identificável |

### Fora de escopo nesta fase

Proof of Play · Device Commands · Store Timezone · Operator Presence · Edge Local Ticketing · Retail Media · Layout Editor · Forecasting/IA · novas features de produto.

Se a loja mostrar queda de rede frequente → Edge Local Ticketing vira **primeira sprint pós-piloto**, não feature “durante” o P2.

---

## Gates

| Gate | Nome | Status |
|------|------|--------|
| **P0** | Release Candidate | `IN PROGRESS` |
| **P1** | Instalação loja piloto | `BLOCKED` (aguarda P0) |
| **P2** | Operação assistida | `PLANNED` |
| **P3** | Observação 7 / 14 / 30 dias | `PLANNED` |
| **P4** | Lições e defeitos reais | `PLANNED` |
| **P5** | Go / No-Go para rollout | `PLANNED` |
| **P6** | Roadmap pós-piloto por evidência | `PLANNED` |

---

## Condições de instalação (carry-over Productization)

Antes de P1:

1. **Release Delivery GO** — `main` publicado; RC tag/commit fixo.  
2. **Continuidade offline** — formalizada como ONLINE-DEPENDENT (acima).  
3. **SLA** — confirmar se 600s / 900s são oficiais para o piloto; senão ajustar política antes de usar Analytics como cobrança gerencial.  
4. **Condições operacionais** — 1 loja · 1 timezone · player/browser definidos · versão RC.

---

## O que medir (mínimo)

Ver `03-measurement-plan.md`.

| Área | Foco |
|------|------|
| Fila | emissão, double-ticket, atendimento, prioridade, espera, no-show, Operator, chamadas |
| Indoor | reprodução contínua, QUEUE_CALL sobre mídia, WS, heartbeat, reconexão, playlist/programação, player |
| Hardware | TV, Totem, terminal operador, impressora, rede, dia inteiro |
| Pessoas | quantas vezes alguém pergunta “como usa?” |
| Gestão | Command Center / Analytics gerando **ação** real |

O piloto falha se só “não der erro” e ninguém usar o produto para decidir nada.

---

## Critério de sucesso (visão P5)

**GO rollout** somente se:

- P0 = 0 críticos de produção no período  
- fluxos atendimento + Indoor estáveis no dia a dia  
- evidência de valor operacional (gestão/pessoas)  
- débitos priorizados por evidência (não por wishlist)

Caso contrário: **NO-GO** ou **GO CONDICIONAL** com escopo explícito.
