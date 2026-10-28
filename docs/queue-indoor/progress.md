# REAL Fila & Indoor — Progresso

| Sprint | Status | Notas |
|--------|--------|-------|
| F0 Auditoria | `PASS` | Greenfield |
| S1–S14 | `PASS` | Fila → Indoor → CISS → Toledo |
| S15 REAL+ / Fila Virtual | `READY FOR HOMOLOGATION` | Remoto, posição, check-in, avisos |

## Decisões

- Docker: 5180 / 8010 / 5455
- REAL+ usa `TicketSource.REAL_PLUS` na mesma fila nativa
- Push = stub in-app (`PUSH_STUB`); FCM/APNs fora deste sprint
- `REAL_PLUS_ENABLED=true` no Docker

## Sprint 15 — entregáveis

- Tabelas `virtual_tickets` + `virtual_notifications`
- API preview / issue / track / check-in / subscribe
- App cliente `/real-plus/:queueId`
- Admin **REAL+** com link público e lista

### Homologação sugerida

1. Admin → **REAL+** → Abrir app cliente
2. Retirar senha → ver número e posição
3. Ativar avisos → check-in “Cheguei na loja”
4. Confirmar senha aparece na fila/operator normalmente
