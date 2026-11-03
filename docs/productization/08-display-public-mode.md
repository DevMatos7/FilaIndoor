# UX-6A — Display Public Mode

## Objetivo

Transformar `/display/:queueId` em experiência pública de **Digital Signage + chamada de fila** da loja REAL, sem telemetria técnica na TV.

## Fluxo atual (auditoria)

```text
boot
  → GET /player/config (X-Display-Token)
  → apply playlist + queue snapshot
  → WebSocket /ws/v1/store/{store_id}
  → heartbeat POST /devices/{id}/heartbeat @30s
  → playlist cycle by duration_seconds
  → ticket.called | ticket.recalled → overlay ~7s + TTS
  → queue.updated → refresh config
  → WS close → reconnect 2.5s (silencioso na UI)
  → config fail → cache 1h (Edge) → senão unavailable
```

### Dependências

| Peça | Origem |
|------|--------|
| Config | `GET /api/v1/player/config` |
| Playlist | channel/schedule → playlist → assets |
| WS | `ws_path` no config |
| TTS | `speechSynthesis` + `audio.template` |
| Heartbeat | device vinculado ao display |
| Cache | `edgeOffline` (`player_config`) |

## Arquitetura do player (pública)

```text
DisplayShell (100vw × 100dvh, overflow hidden)
  ├── MediaPlayer          (IMAGE | VIDEO | WEB | Fallback)
  ├── QueueFooter          (departamento + senha)
  └── QueueCallOverlay     (chamada full-screen ~7s)
```

Serviço auxiliar: `frontend/src/services/displayPlayer.ts`  
(config, heartbeat, speak, WS URL)

**Não há** LayoutResolver / zones / screen_overrides nesta sprint.

## Player states

| Estado | UI |
|--------|----|
| `boot` | DisplayBoot (wordmark REAL) |
| `ready` | mídia + footer |
| `fallback` | DisplayFallback branded (sem `/media`) |
| `unavailable` | DisplayUnavailable (token/config) |

Overlay de chamada é **ortogonal** a esses estados.

## Media behavior

- IMAGE: `object-cover`, fade leve  
- VIDEO: autoplay, muted, playsInline, preload  
- WEB: iframe full-bleed, sem chrome  
- Falha de asset → skip id + avança (log console; sem erro na TV)  
- Playlist vazia / todos inválidos → Fallback branded  

## Queue footer

Hierarquia: senha → departamento → “Senha em atendimento” / “Aguardando próxima chamada” → última chamada secundária.  
Sem `—` gigante. Tipografia DM Sans + `tabular-nums` + `clamp()` para 1080p/4K.

## Queue overlay

- Full-screen brand overlay ~7s (timer pré-existente)  
- Prioridade só se `ticket_type` vier no evento WS (não inferir prefixo)  
- Mídia permanece montada atrás; ao sair do overlay retoma sem reiniciar playlist  
- Nova chamada durante overlay: **substitui** e reinicia timer (comportamento pré-existente; documentado — UX-6C pode evoluir fila)

## TTS / áudio

Preservados. `?audio=1` force. Master/audio status **nunca** na UI pública.

## WebSocket

Preservado: ping 20s, reconnect 2.5s, dedupe `event_id` (cap 500). Reconnect **invisível** ao cliente.

## Edge / cache

Cache transparente. Mensagens “Modo cache local / Edge offline” removidas da TV; log interno apenas.

## Public copy

Sem: API, WS, token, playlist, channel, `/media`, conectando, áudio on/off.

## Responsive / TV

| Alvo | Nota |
|------|------|
| 1920×1080 | primário 16:9 |
| 3840×2160 | escala via `clamp` / vw/vh |
| 1080×1920 | sanity (não quebra); portrait completo = UX-6B |
| Safe zone | `.display-safe` ~3%+ |

## Limitações

- Sem Layout Engine / templates / zones  
- Sem clock, ticker, produto/preço  
- Sem rota diagnostics Display (Fleet/UX-10)  
- Portrait não otimizado  
- VISUAL VALIDATION pode ficar PENDING sem capturas reais  

## Evolução UX-6B

A engine de layouts está documentada em [`08b-layout-engine.md`](./08b-layout-engine.md).

Composição atual:

```text
DisplayShell → LayoutResolver → Zones
             → QueueCallOverlay (ainda global; UX-6C)
```

`MediaPlayer`, `QueueCallOverlay`, WS/TTS/heartbeat preservados.  
`QueueFooter` evoluiu para variantes via `QueueZone`.
