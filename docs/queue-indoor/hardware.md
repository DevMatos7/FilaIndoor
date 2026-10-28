# Hardware / Impressão — Sprint 2

## PrinterProvider

| Provider | Uso |
|----------|-----|
| `mock` | Padrão Docker / homologação sem impressora |
| `escpos` | TCP raw porta 9100 (`PRINTER_HOST` / `PRINTER_PORT`) |
| `fail` | Simula impressora offline (header `X-Print-Provider: fail` ou env) |

Variáveis:

```text
PRINT_PROVIDER=mock
PRINTER_HOST=host.docker.internal
PRINTER_PORT=9100
PRINTER_TIMEOUT_SECONDS=3
```

## Regra crítica

Emissão da senha **não depende** da impressora.  
Falha de print → senha permanece válida + estado `printer_error` no totem.
