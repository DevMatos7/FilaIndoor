# P0 — Release Candidate

**Status:** `IN PROGRESS`  
**Gate:** nenhuma instalação de loja (P1) sem P0 = PASS

---

## Objetivo

Ter um artefato **reproduzível** e **identificável** do produto homologado (UX-0 → UX-12) pronto para instalação controlada.

---

## Checklist

| # | Item | Critério | Status |
|---|------|----------|--------|
| 1 | Histórico Productization commitado | UX-0…UX-12 + closure docs no `main` local | PENDING (commit de closure + FASE 2) |
| 2 | Push remoto | `origin/main` contém os commits do RC | **NO-GO atual** — `main` ahead do remote |
| 3 | Tag RC | Tag anotada, ex.: `rc-pilot-1` apontando ao commit do piloto | PENDING |
| 4 | Build verificável | `frontend` build + stack Docker sobe na versão tagged | PENDING pós-push |
| 5 | Smoke pós-tag | `npm run test:e2e` (ou subset crítico) na RC | PENDING |
| 6 | SLA do piloto documentado | 600s/900s confirmados **ou** política corrigida registrada | PENDING decisão humana |
| 7 | Inventário da loja piloto | loja, filas, devices, tokens, contatos | PENDING (`02-install-checklist.md`) |
| 8 | Modo resiliência assinado | ONLINE-DEPENDENT registrado e aceito pela operação | DECIDIDO (charter) — falta aceite formal da loja |

---

## Commits a publicar (mínimo)

No momento da abertura da FASE 2, o local estava **ahead 12** de `origin/main`, incluindo:

- UX-3 … UX-12 (productization)
- `test(productization): UX-12 playwright visual QA` (`bc40690`)
- + commits de closure / FASE 2 (este ciclo)

**Não** squashar a série UX. Push fast-forward preferencial.

---

## Comandos de referência (quando auth OK)

```bash
# 1) garantir working tree limpa / commits de closure
git status

# 2) publicar
git push -u origin main

# 3) tag RC (após smoke local na HEAD desejada)
git tag -a rc-pilot-1 -m "Release Candidate Piloto 1 — Productization HOMOLOGATED, ONLINE-DEPENDENT"
git push origin rc-pilot-1
```

---

## Critério P0 = PASS

- [ ] remoto atualizado  
- [ ] tag `rc-pilot-1` (ou nome acordado) publicada  
- [ ] SLA do piloto decidido por escrito  
- [ ] aceite ONLINE-DEPENDENT da operação da loja  
- [ ] inventário P1 preenchido  

Enquanto o push falhar por autenticação: **P0 permanece FAIL / BLOCKED** — produto apto, **instalação proibida**.

---

## Saída deste gate

Documento curto em `docs/pilot/rc-notes.md` com:

- SHA do commit RC  
- tag  
- data  
- quem aprovou SLA + resiliência  
- link para `02-install-checklist.md` preenchido  

Só então liberar **P1**.
