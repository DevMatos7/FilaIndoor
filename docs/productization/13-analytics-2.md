# UX-11 — Analytics 2.0

**Status:** READY FOR HOMOLOGATION  
**CODE VALIDATION:** PASS  
**VISUAL VALIDATION:** PENDING  

## Objetivo

Transformar `/analytics` em **Analytics 2.0** de gestão de atendimento: período, tendência e comparação — distinto do Command Center (agora).

## Semântica temporal

Datetimes **naive do servidor** (`utcnow`), igual ao restante do domínio.  
**Store timezone** permanece débito — sem segunda regra no React.

Período: `[from 00:00, to+1d 00:00)` inclusive nas datas civis.

## Data dictionary

| Métrica | Fonte | Fórmula | Unidade | Inclusões | Exclusões |
|---------|-------|---------|---------|-----------|-----------|
| Senhas emitidas | `Ticket.issued_at` | count | tickets | issued_at ∈ período | outras lojas |
| Atendimentos concluídos | `Ticket.completed_at` + status COMPLETED | count | tickets | completed_at ∈ período | não concluídos |
| Ausências (no-show) | `no_show_at` + status NO_SHOW | count | tickets | no_show_at ∈ período | cancelled, expired |
| Canceladas | `cancelled_at` | count | tickets | cancelled_at ∈ período | no-show |
| Espera (avg/median/P90/max) | `issued_at` → `called_at\|\|completed_at\|\|no_show_at\|\|cancelled_at` | mean / median / P90 linear / max | segundos | issued_at ∈ período **e** wait_end presente | missing → **não** vira 0 |
| Tempo de atendimento | `service_started_at` → `completed_at` | idem | segundos | completed_at ∈ período com ambos timestamps | sem `service_started` → omitido |
| Dentro do SLA | espera avaliável | green / evaluable; green = wait &lt; 600s | % | wait_end presente | unknown **não** é falha |
| SLA atenção / crítico | espera | 600–900 / ≥900 | count | avaliáveis | — |
| Throughput | completed | completed / horas do período | /h | — | — |
| Taxa conclusão | completed ÷ issued | cohorts distintos | % | — | períodos em aberto distorcem |
| Volume série | issued_at / completed_at | buckets hora (≤2d) ou dia | count | — | — |
| Demanda por horário | issued_at.hour | soma no período | count | — | — |
| Mix tipo | `ticket_type` | histogram issued | count | — | — |
| Por fila | agregação ponderada | mesmas fórmulas no subconjunto | — | — | P90 total ≠ média dos P90s |
| Por balcão | `terminal_id` em completed | count + service avg | — | só se houver IDs | sem terminal → seção indisponível |
| Por operador | `operator_id` | count completed | — | só IDs reais | sem gamificação |
| Frota atual | `DeviceService._compute_status` | ONLINE/DEGRADED/OFFLINE/DISABLED | snapshot | agora | **não** é uptime do período |

### Cohorts (oficial)

```text
issued     → issued_at ∈ [from, to+1d)
completed  → completed_at ∈ [from, to+1d) AND status=COMPLETED
no_show    → no_show_at ∈ período AND status=NO_SHOW
cancelled  → cancelled_at ∈ período
wait/SLA   → issued_at ∈ período + wait_end avaliável
service    → completed_at ∈ período + service_started_at + completed_at
```

### P90

Interpolação linear sobre **observações individuais** ordenadas (`_percentile`).  
Proibido: média dos P90s das filas.

### SLA

Hardcoded histórico: target **600s**, warning **900s** (não lê `QueuePriorityRule` nesta sprint).  
Numerador/denominador explícitos: `within_target` / `evaluable`.

### Zero ≠ missing

- No-show = 0 → nenhum no-show.  
- Espera média = `null` / UI `—` → nenhuma amostra avaliável.

## APIs

| Endpoint | Notas |
|----------|--------|
| `GET /analytics/overview?store_id&from&to&queue_id?&ticket_type?` | **novo** agregador |
| `GET /analytics/summary` | **preservado** (Command Center) |

## Frontend

- StoreContext; URL `?from=&to=&queue=&preset=`
- Presets: Hoje / Ontem / 7d / 30d / Personalizado
- `analyticsService.ts` + **recharts@2.15.0** (única dep. nova)
- Abas: Overview, Atendimento, Filas, Balcões, Saúde operacional
- Charts com `sr-only` summary + legend/labels
- Device snapshot rotulado **Situação atual da frota**

## Limitações explícitas

- Sem Proof of Play / impressões / conteúdo reproduzido
- Sem uptime histórico de TV
- Sem capacidade/presença de operador
- Sem heatmap / CSV export (débito)
- CC “Hoje” usa cohort issued-do-dia para completed; Analytics overview usa completed_at — documentado

## Migrations

**0.**

## Critérios

```text
data dictionary ✓
P90 individual ✓
zero ≠ missing ✓
store isolation ✓
device snapshot ≠ uptime ✓
recharts ✓
summary legado intacto ✓
build + testes ✓
VISUAL PENDING
```
