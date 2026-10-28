import socket

from app.modules.printing.providers.base import PrintResult, PrinterProvider


class ESCPosPrinter(PrinterProvider):
    """Envia bytes ESC/POS via TCP raw (porta 9100 típica)."""

    name = "escpos"

    def __init__(self, host: str, port: int = 9100, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def print_bytes(self, data: bytes) -> PrintResult:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(data)
            return PrintResult(
                ok=True,
                provider=self.name,
                message=f"Enviado para {self.host}:{self.port}",
                raw_bytes_len=len(data),
            )
        except OSError as exc:
            return PrintResult(
                ok=False,
                provider=self.name,
                message=f"Falha ESC/POS: {exc}",
                raw_bytes_len=len(data),
            )
