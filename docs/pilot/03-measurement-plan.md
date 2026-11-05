# Plano de medição — Piloto 1

**Objetivo:** evidência de que o produto **melhora a operação**, não só que “não quebra”.

---

## 1. Fila

| Métrica / observação | Como coletar | Frequência |
|----------------------|--------------|------------|
| Emissões (NORMAL / PRIORITY) | Analytics + contagem operacional | diário |
| Double-ticket / duplicata suspeita | relato + log / suporte | por incidente |
| Tempo até NEXT / atendimento | Analytics wait + observação Operator | diário / amostral |
| No-show | Analytics + Operator | diário |
| Estabilidade Operator (travas, stale, erro API) | relato + console se disponível | por turno |
| Chamadas no Display legíveis | observação no salão | amostral 2×/dia |

**Sinais de alarme:** duplicata confirmada · Operator inutilizável · chamada ilegível recorrente.

---

## 2. Indoor

| Métrica / observação | Como coletar | Frequência |
|----------------------|--------------|------------|
| Player “preto” / trava | observação TV | contínuo / relato |
| QUEUE_CALL sobre mídia | observação no momento da chamada | amostral |
| Reconexão após queda breve de rede | teste controlado 1× na 1ª semana | 1× |
| Heartbeat / status frota | Fleet / CC | diário |
| Playlist / programação “Agora” coerente | Programming vs tela | 2×/semana |

**Sinais de alarme:** TV preta prolongada · override não cobre · programação ≠ tela de forma recorrente.

---

## 3. Hardware & rede

| Item | Observar |
|------|----------|
| TV | brilho, cabo, sleep, áudio se TTS |
| Totem | touch, impressora, energia |
| Terminal Operator | teclado/touch, rede |
| Rede | quedas, latência percebida, Wi‑Fi vs cabo |
| Dia inteiro | pico de almoço / final de tarde |

Registrar **número e duração** de incidentes de conectividade — alimenta a decisão Edge pós-piloto.

---

## 4. Pessoas

Contar (simples, papel ou planilha):

- vezes que **cliente** perguntou como tirar senha / onde olhar  
- vezes que **funcionário** pediu ajuda no Operator / Totem / TV  
- workarounds inventados (“anota no papel”, “não usa prioridade”)

Meta qualitativa: curva decrescente na 1ª → 2ª semana.

---

## 5. Gestão (valor)

Para Command Center e Analytics, anotar **ações tomadas** por causa do produto, por exemplo:

- abriu caixa / chamou reforço por fila alta  
- ajustou playlist / emergência  
- desabilitou device offline  
- mudou processo após ver no-show / espera  

Se em 14 dias **zero ações** derivadas do produto → sinal forte de NO-GO de valor (mesmo com estabilidade técnica).

---

## 6. Cadência de revisão

| Marco | Gate | Foco |
|-------|------|------|
| Dia 1–2 | P2 | operação assistida, incendios |
| Dia 7 | P3 parcial | estabilidade + primeiras lições |
| Dia 14 | P3 | valor gestão + pessoas |
| Dia 30 | P3 → P4/P5 | Go/No-Go rollout + backlog evidenciado |

Template de defeitos reais: reutilizar severidade P0–P3 de `docs/productization/15-qa-defects.md`, em `docs/pilot/defects.md` (criar no P2).
