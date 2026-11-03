# UX-5 — Operator 2.0

## Objetivo

Transformar `/operator/:queueId` em **botoeira operacional digital**:
mínimo de toques, máxima legibilidade, feedback imediato, baixa carga cognitiva.

Não é dashboard, admin ou CRUD.

## Fluxo login

1. Tela operacional: REAL → Acesso ao atendimento → Usuário / Senha → Entrar  
2. `POST /auth/login` (form urlencoded) — contrato preservado  
3. JWT em `localStorage.token` (não exibido na UI)

## Terminal selection

1. `GET /queues/:id` → `department_id`  
2. `GET /terminals?department_id=` (somente `active`)  
3. 1 balcão → auto-seleção  
4. N balcões → cards touch (ou `<select>` se > 8)  
5. Persistência: `localStorage.operator_terminal` + `?terminal=`  
6. Menu: **Trocar balcão** / **Sair** (secundário; sem link Admin)

## Estados derivados (sem presence model)

| UI | Condição |
|----|----------|
| PRONTO | sem ticket SERVING/CALLED no terminal |
| ATENDENDO | ticket atual no terminal |
| ENCERRADO | `panel.status === CLOSED` |
| PAUSADO | `panel.status === PAUSED` |

**Débito futuro:** Operator Presence / Capacity (`AVAILABLE` / `SERVING` / `PAUSED` / `OFFLINE` persistente).

## Ready

- Copy: “Pronto para atender / Chame a próxima senha”  
- NEXT em máxima evidência  
- Disabled se fila vazia, CLOSED ou PAUSED

## Serving

- Senha dominante (`tabular-nums`)  
- Timer local a partir de `elapsed_seconds` + tick 1s  
- Prioritário: ícone Accessibility + texto + badge (não só cor)

## Ações (contratos preservados)

| Ação | Endpoint | Notas |
|------|----------|-------|
| NEXT | `POST /queues/:id/next` | `auto_complete_current: true`, `auto_start: true` (**já existia**) + Idempotency-Key |
| RECALL | `POST /tickets/:id/recall` | só com ticket; feedback “Senha X rechamada” |
| NO_SHOW | `POST /tickets/:id/no-show` | sem modal; proteção por posição + danger + ícone + texto |
| COMPLETE | `POST /tickets/:id/complete` | feedback “Atendimento finalizado” → volta a Pronto |

Estado da senha **sempre** confirmado pelo servidor após a ação (`loadPanel`). Feedback visual “Chamando…” é apenas UI.

### Decisão NO_SHOW

Sem confirmação modal: no balcão a ação é frequente; o risco de toque acidental é mitigado por contraste/ícone/rótulo e afastamento do NEXT. Reavaliar se operação reportar incidentes.

## Queue summary

Discreto no rodapé: `N aguardando · M prioritárias` ou “Fila sem espera no momento”.

## Feedback / errors

- Sucesso breve (toast ~2.2s)  
- Erro comercial: “Não foi possível executar a ação. Tente novamente.”  
- Refresh falho com snapshot: “Conexão instável” (não apaga ticket/timer)  
- `busyRef` + botão disabled = anti double-tap

## Polling

`GET /queues/:id/operator-panel?terminal_id=` a cada **4s** (mecanismo atual preservado). Sem WebSocket novo.

## Responsive

- `100dvh`, safe-area  
- Alvos: NEXT ≥ ~104px; secundários ≥ 72px  
- Alvos: 360×800, 390×844, 768×1024 (+ landscape razoável)

## Acessibilidade

- DM Sans, contraste alto, `aria-label` nas ações  
- focus-visible, status textual, `prefers-reduced-motion`  
- Teclado: Tab / Enter / Space

## APIs

Somente reutilização. Sem migration. Sem alteração de Queue Engine.

## Componentes

```text
frontend/src/components/operator/
  OperatorShell, OperatorHeader, OperatorLogin, TerminalSelector,
  CurrentTicket, PrimaryAction, SecondaryActions, QueueSummary,
  OperatorFeedback, types
```

## Débitos registrados

1. **Operator Presence / Capacity** — modelo persistente futuro  
2. **UX-4 Edge** — offline issue real / local ticketing ainda não emite senha local  
3. **Totem diagnostics** — agora valida `/auth/me` + roles admin/manager (endurecido nesta sprint)
