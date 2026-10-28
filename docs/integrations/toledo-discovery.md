# Toledo Discovery — Sprint 13

**Status:** discovery (sem integração operacional)  
**Data:** 2026-10-28  
**Feature flag:** `TOLEDO_ENABLED=false`  
**Regra:** não presumir endpoints; só registrar o que for confirmado no ambiente REAL.

---

## 1. Objetivo

Mapear o ambiente Toledo existente (quando houver) e comparar com a documentação pública MIT / MIT Cloud, para decidir no Sprint 14 quais endpoints o `ToledoProvider` pode implementar com segurança.

A fila nativa (`NATIVE`) permanece a fonte da verdade no MVP.

---

## 2. Inventário a preencher (por loja / ambiente)

| Item | Valor encontrado | Fonte | Confirmado? |
|------|------------------|-------|-------------|
| MGV version | _pendente_ | | ☐ |
| MIT version | _pendente_ | | ☐ |
| MIT Cloud (sim/não + URL) | _pendente_ | | ☐ |
| Licença / contrato | _pendente_ | | ☐ |
| Lojas Toledo vinculadas | _pendente_ | | ☐ |
| Players (MIT Player) | _pendente_ | | ☐ |
| API habilitada (sim/não) | _pendente_ | | ☐ |
| Base URL API | _pendente_ | | ☐ |
| Autenticação (JWT / chave) | _pendente_ | | ☐ |
| Chave de integração | _pendente_ (secret — não versionar) | | ☐ |
| Rede / VLAN / firewall | _pendente_ | | ☐ |
| Histórico de senhas via API | _pendente_ | | ☐ |
| Envio nº caixa → MIT Player | _pendente_ | | ☐ |
| Documentação oficial consultada | _pendente_ | | ☐ |

Preencher também no admin: **Toledo → Discovery** (persiste checklist sem secrets em texto claro opcional).

---

## 3. Documentação pública (referência — não confirma o ambiente)

Fontes públicas tipicamente citadas pela Toledo (validar URLs oficiais no momento da homologação):

- MIT Senha / MIT Cloud — portais e manuais do fabricante
- API de histórico / tempos de atendimento (autenticada)
- API de envio de informação a MIT Players (JWT + chave de integração)

**Atenção:** existência de docs públicas **não** implica que toda função do MIT Senha tenha endpoint equivalente, nem que o ambiente da REAL esteja habilitado.

---

## 4. Modos previstos (Sprint 14+)

| Modo | Descrição | MVP |
|------|-----------|-----|
| `NATIVE` | Fila e display 100% REAL Fila & Indoor | **Ativo** |
| `TOLEDO_DISPLAY` | Fila nossa; MIT só exibe | Desligado |
| `TOLEDO_SYNC` | Sync histórico/config | Desligado |
| `TOLEDO_FULL` | Só se APIs confirmadas cobrirem operação | Desligado |

`TOLEDO_ENABLED=false` força modo efetivo `NATIVE` independentemente do modo configurado.

---

## 5. Comparação discovery × docs oficiais

| Capacidade | Docs públicas (genérico) | Ambiente REAL | Decisão S14 |
|------------|--------------------------|---------------|-------------|
| Histórico / tempos | Possível via API autenticada | _não verificado_ | Implementar só se URL+auth confirmados |
| Player / caixa | Possível envio JWT | _não verificado_ | Stub até confirmação |
| Emissão / chamada de senha | Não assumir | _não verificado_ | Manter NATIVE |
| Offline loja | Nosso Edge (S11) | N/A Toledo | Não depender Toledo |

---

## 6. Riscos

1. Assumir endpoints e quebrar fila nativa — **mitigado:** flag off + fallback NATIVE.
2. Secrets no repositório — **mitigado:** só env / vault; discovery UI mascara chave.
3. Ambiente sem MIT Cloud — discovery registra “API desabilitada”; S14 não implementa FULL.

---

## 7. Gate do Sprint 13

- [x] Documento de discovery criado
- [x] Feature flag `TOLEDO_ENABLED=false`
- [x] Checklist persistível (admin)
- [x] Nenhum adapter operacional Toledo
- [x] Fila nativa inalterada

**Próximo (S14):** `ToledoProvider` apenas com endpoints **confirmados** neste discovery; falha Toledo nunca bloqueia fila nativa.
