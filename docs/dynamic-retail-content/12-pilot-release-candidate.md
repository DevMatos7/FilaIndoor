# Pilot Release Candidate / Day-0

**Não é Module 7 nem feature.**  
Somente publicação do histórico homologado + runtime de instalação + hardware.

**Evidence / referência de produto:**

```
8b830b2
test(dynamic-retail): module 6 pilot readiness gate
```

O release do piloto deve ser rastreável a esse commit, ou a um commit posterior contendo **somente** correções de deployment/RC (sem feature adicional).

---

## GATE RC-1 — SOURCE CONTROL

- [ ] `origin/main` contém exatamente o HEAD homologado (ou tag apontando para ele)
- [ ] release/tag identificável (ex. `pilot-drc-rc1`)
- [ ] working tree clean
- [ ] **Só então:** `RELEASE DELIVERY: GO` (parcial; ainda falta RC-2…4 para instalação)

## GATE RC-2 — PILOT RUNTIME

- [ ] `APP_ENV=production`
- [ ] `RETAIL_PROVIDER=ciss_db2`
- [ ] ODBC IBM disponível no ambiente da API
- [ ] mock rejeitado (sem `RETAIL_ALLOW_MOCK_IN_PRODUCTION`)
- [ ] scheduler ativo  
→ fecha **P2-01**

## GATE RC-3 — MEDIA STORAGE

- [ ] import CISS grava no volume persistente
- [ ] API / nginx / player enxergam o mesmo `MediaAsset`
- [ ] restart de container preserva mídia  
→ fecha **P2-02**

## GATE RC-4 — HARDWARE

- [ ] TV / player real
- [ ] tablet / totem
- [ ] terminal operador
- [ ] impressora (se entrar no piloto)
- [ ] rede
- [ ] áudio
- [ ] QUEUE_CALL
- [ ] reboot / reconnect

---

## Depois dos quatro gates

| Decisão | Novo status esperado |
|---------|----------------------|
| RELEASE DELIVERY | **GO** |
| PILOT INSTALLATION | **GO** |

Fluxo: RC-1…RC-4 → configuração máquina/containers → hardware smoke → instalação assistida → observação operacional.

Próximos módulos nascem do que acontecer na loja — não de backlog teórico.
