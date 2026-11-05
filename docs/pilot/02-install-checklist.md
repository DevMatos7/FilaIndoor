# P1 — Instalação loja piloto

**Status:** `BLOCKED` — aguarda P0 PASS  
**Escopo:** 1 loja · versão = tag RC

---

## Inventário (preencher antes da instalação)

| Campo | Valor |
|-------|-------|
| Loja | _TBD_ |
| Timezone da loja | _TBD_ (deve coincidir com servidor no Piloto 1) |
| Filas no piloto | _TBD_ (ex.: Açougue) |
| Totem (hardware + URL) | _TBD_ |
| Operator (hardware + URL) | _TBD_ |
| Display / TV (token + layout) | _TBD_ |
| Impressora | _TBD_ |
| Rede (WAN/LAN, Wi‑Fi/cabo) | _TBD_ |
| Contato operação loja | _TBD_ |
| Contato TI / suporte remoto | _TBD_ |
| Commit / tag RC | _TBD_ |
| Data/hora go-live assistido | _TBD_ |

---

## Pré-voo técnico

- [ ] Stack sobe com a tag RC (Docker ou deploy acordado)
- [ ] Seed/config da loja: filas OPEN, kiosk token, display token, canal + playlist + layout
- [ ] Login admin da loja funciona
- [ ] Totem emite NORMAL e PRIORITY (1× cada)
- [ ] Operator: NEXT / RECALL / NO_SHOW / COMPLETE
- [ ] Display: mídia + QUEUE_CALL + (teste) EMERGENCY cancelado
- [ ] Command Center reflete a loja correta (StoreContext)
- [ ] Analytics carrega; SLA **não** usado como cobrança até confirmação (§ P0)
- [ ] Heartbeat / device status visível no Fleet ou CC
- [ ] Plano de rollback: tag/commit anterior + contato

---

## Aceite ONLINE-DEPENDENT

> Em caso de indisponibilidade do backend central, **novas emissões de senha podem falhar**.  
> O risco é aceito e será monitorado durante o piloto.

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Operação loja | | | |
| Responsável produto / TI | | | |

---

## Critério P1 = PASS

Instalação concluída, smoke na loja PASS, aceite resiliência assinado, operação assistida (P2) agendada para o primeiro dia útil completo.
