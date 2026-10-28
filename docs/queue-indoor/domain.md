# Domínio — Fila (Sprint 1)

## Entidades

- `Company` → `Store` → `Department` → `Queue`
- `QueuePriorityRule` (1:1 com fila)
- `QueueSequence` (contador por `queue_id` + `ticket_type` + `period_key`)
- `Ticket` + `TicketEvent` (event sourcing leve)
- `IdempotencyRecord`

## Status da senha

```text
WAITING → CALLED → SERVING → COMPLETED
CALLED → NO_SHOW
WAITING → CANCELLED
WAITING → EXPIRED
```

Transições inválidas levantam `InvalidTransitionError` (HTTP 422).

## Tipos

`NORMAL`, `PRIORITY`, `PRIORITY_PLUS`, `CUSTOM` (MVP usa NORMAL/PRIORITY).

## Numeração

Transacional via `queue_sequences` + `SELECT FOR UPDATE`.  
Nunca `MAX(number)+1` sem lock.

Display: `{prefix}{number:0digits}` — ex. `A023`, `P008`.  
Reset padrão: `DAILY` (`period_key` = data ISO).

## QueueSelectionEngine

Policies:

- `FIFOQueuePolicy`
- `WeightedPriorityPolicy` (MVP: 3 normal / 1 prioritária)
- `MaxWaitPolicy` (override se prioridade ≥ `priority_max_wait_seconds`, padrão 600s)

A rota HTTP **não** contém regra de prioridade — apenas o service/engine.
