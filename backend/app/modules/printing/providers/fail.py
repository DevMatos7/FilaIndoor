from app.modules.printing.providers.base import PrintResult, PrinterProvider


class FailPrinter(PrinterProvider):
    """Força falha de impressão (testes / homologação)."""

    name = "fail"

    def print_bytes(self, data: bytes) -> PrintResult:
        return PrintResult(
            ok=False,
            provider=self.name,
            message="Impressora offline (simulada)",
            raw_bytes_len=len(data),
        )
