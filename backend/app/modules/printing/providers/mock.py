from app.modules.printing.providers.base import PrintResult, PrinterProvider


class MockPrinter(PrinterProvider):
    """Impressora simulada — padrão Docker / testes."""

    name = "mock"
    last_jobs: list[bytes] = []

    def print_bytes(self, data: bytes) -> PrintResult:
        MockPrinter.last_jobs.append(data)
        return PrintResult(
            ok=True,
            provider=self.name,
            message="Impressão simulada com sucesso",
            raw_bytes_len=len(data),
        )

    @classmethod
    def clear(cls) -> None:
        cls.last_jobs.clear()
