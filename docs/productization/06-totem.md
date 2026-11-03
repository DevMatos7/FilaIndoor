# UX-4 — Totem 2.0

## Objetivo

Transformar `/totem/:queueId` em experiência de autoatendimento kiosk da marca **REAL**:
simples, rápida, confiável, comercial e acessível — sem parecer admin/CRUD.

## Visual hierarchy

1. Wordmark **REAL**  
2. Nome comercial do departamento  
3. Prompt de ação (“Como deseja ser atendido?”)  
4. Botões NORMAL / PRIORITÁRIO (touch 100px+)  
5. Pessoas aguardando / ETA só com dados reais  
6. Orientação discreta no rodapé  

Tipografia operacional: **DM Sans**. Source Serif 4 não é usada em senha/ações.

## State machine

```text
boot
  ↓
idle ──click──► processing ──print ok──► success ──timer≈4s──► idle
                     │
                     ├──print fail──► printer_error ──timer≈7s──► idle
                     └──create fail─► server_error ──retry/timer──► idle

closed / offline / unavailable  → sem emissão (padrão TotemUnavailable)
```

Estados preservados: `idle`, `processing`, `success`, `printer_error`, `offline`, `server_error`.  
Derivados: `boot`, `closed` (fila ≠ OPEN), `unavailable` (token ausente).

## Fluxo normal / prioritário

- Mesma API `POST /kiosk/{queueId}/tickets` com `type` NORMAL | PRIORITY.  
- `busyRef` + botões disabled impedem double-tap / duplicata.  
- Idempotency-Key por toque preservada.  
- Prioritário: ícone Accessibility + texto + descrição + contraste (não só cor).

## Impressão

- Ticket é criado **antes** da impressão (backend).  
- `print.ok` → sucesso “Senha impressa”.  
- `print.ok === false` → senha registrada + “A impressão não foi concluída” (sem mensagem técnica).  
- Não reemite automaticamente.

## Edge / offline

- Cache + outbox (`edgeOffline`) preservados.  
- Cliente **nunca** vê “Edge”, “API”, “modo offline”, “localhost”.  
- Sem rede e sem emissão possível → indisponibilidade comercial.  
- Falha de create com `store_id` ainda enfileira outbox; UI mostra erro comercial + retry.

## Diagnostics

- Rota: `/totem/:queueId/diagnostics`  
- Proteção: sessão admin (`localStorage.token`); redirect `/login`.  
- Token kiosk: CONFIGURADO/AUSENTE ou mascarado — nunca completo.  
- Dados: queue id, dept, API, health, outbox, cache, versão.

## Responsividade

- Portrait-first: 768×1024, 800×1280 (+ 1024×1366 razoável).  
- `min-h-[100dvh]`, safe-area padding, sem scroll no fluxo normal.

## Acessibilidade

- Contraste alto, texto grande, alvos ≥ 64–100px.  
- `aria-label` nos botões; status textual; focus-visible.  
- Tab / Enter / Space funcionais.  
- `prefers-reduced-motion` nas animações adicionadas.  
- Prioridade não depende só de cor.

## Copy rules

| Evitar | Preferir |
|--------|----------|
| ticket / queue / offline mode | senha / atendimento / aguardando |
| token / API / Edge | (omitir no público) |
| ESC/POS / USB error | “A impressão não foi concluída” |

## APIs (inalteradas)

```http
GET  /api/v1/kiosk/{queueId}/status
POST /api/v1/kiosk/{queueId}/tickets
```

Poll de status: 30s. ETA só se `waiting_count > 0` e segundos > 0 (sem `Math.max(1,…)` inventado).

## Componentes

```text
frontend/src/components/totem/
  TotemShell, TotemHeader, TotemBoot, ServiceChoice,
  TotemProcessing, TicketSuccess, TotemError,
  TotemUnavailable, TotemStatusInfo, types
```

## Fora de escopo

Operator/Display 2.0, áudio novo, analytics novo, editor visual de tema, migrations, PIN complexo.
