# P0 — Release Candidate

**Status:** `IN PROGRESS`  
**Gate:** nenhuma instalação de loja (P1) sem P0 = PASS  
**RC publicada:** `rc-pilot-1` @ `95ae83a` — ver `rc-notes.md`

---

## Objetivo

Ter um artefato **reproduzível** e **identificável** do produto homologado (UX-0 → UX-12) pronto para instalação controlada.

---

## Checklist

| # | Item | Critério | Status |
|---|------|----------|--------|
| 1 | Histórico Productization commitado | UX-0…UX-12 + closure + FASE 2 no `main` | **PASS** |
| 2 | Push remoto | `origin/main` = RC | **PASS** |
| 3 | Tag RC | `rc-pilot-1` publicada | **PASS** |
| 4 | Build verificável | stack Docker na RC | PASS (ambiente local já validado na UX-12; revalidar no host da loja em P1) |
| 5 | Smoke E2E | 15/15 na prova UX-12 sobre a linhagem RC | **PASS** (não reexecutar obrigatório se SHA inalterado) |
| 6 | SLA do piloto documentado | 600s/900s confirmados **ou** política alternativa | **PENDING** decisão humana |
| 7 | Inventário da loja piloto | loja, filas, devices, tokens, contatos | **PENDING** (`02-install-checklist.md`) |
| 8 | Modo resiliência assinado | ONLINE-DEPENDENT aceito pela operação da loja | charter OK — **falta aceite formal da loja** |

---

## Publicação (concluída)

```text
git push origin main          → 95ae83a
git tag -a rc-pilot-1 … && git push origin rc-pilot-1
```

Histórico UX preservado (sem squash).

---

## Critério P0 = PASS

- [x] remoto atualizado  
- [x] tag `rc-pilot-1` publicada  
- [ ] SLA do piloto decidido por escrito  
- [ ] aceite ONLINE-DEPENDENT da operação da loja  
- [ ] inventário P1 preenchido  

**Release Delivery:** GO.  
**Instalação:** ainda bloqueada pelas 3 pendências humanas acima.

---

## Saída deste gate

Documento curto em `docs/pilot/rc-notes.md` com:

- SHA do commit RC  
- tag  
- data  
- quem aprovou SLA + resiliência  
- link para `02-install-checklist.md` preenchido  

Só então liberar **P1**.
