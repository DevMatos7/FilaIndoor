from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PrintResult:
    ok: bool
    provider: str
    message: str = ""
    raw_bytes_len: int = 0


class PrinterProvider(ABC):
    name: str = "base"

    @abstractmethod
    def print_bytes(self, data: bytes) -> PrintResult:
        raise NotImplementedError
