"""Layout ESC/POS do ticket impresso (Sprint 2)."""

from __future__ import annotations

from datetime import datetime


ESC = b"\x1b"
GS = b"\x1d"


def _line(text: str = "") -> bytes:
    return (text + "\n").encode("cp850", errors="replace")


def build_ticket_receipt(
    *,
    store_name: str,
    department_name: str,
    display_number: str,
    ticket_type: str,
    issued_at: datetime,
    people_ahead: int,
    estimated_wait_seconds: int,
) -> bytes:
    tipo = "ATENDIMENTO PRIORITÁRIO" if ticket_type in {"PRIORITY", "PRIORITY_PLUS"} else "ATENDIMENTO NORMAL"
    wait_min = max(1, round(estimated_wait_seconds / 60)) if estimated_wait_seconds else 1
    when = issued_at.strftime("%d/%m/%Y %H:%M")

    parts: list[bytes] = [
        ESC + b"@",  # init
        ESC + b"a\x01",  # center
        ESC + b"!\x18",  # double height/width-ish
        _line(store_name.upper()),
        ESC + b"!\x00",
        _line(department_name.upper()),
        _line(""),
        _line("SENHA"),
        ESC + b"!\x30",
        _line(display_number),
        ESC + b"!\x00",
        _line(""),
        _line(tipo),
        _line(when),
        _line(""),
        _line(f"Pessoas aguardando: {people_ahead}"),
        _line(f"Espera estimada: {wait_min} min"),
        _line(""),
        _line("Acompanhe sua senha nas TVs."),
        _line("Obrigado pela preferencia."),
        _line(""),
        _line(""),
        GS + b"V\x00",  # full cut
    ]
    return b"".join(parts)


def receipt_preview_text(
    *,
    store_name: str,
    department_name: str,
    display_number: str,
    ticket_type: str,
    issued_at: datetime,
    people_ahead: int,
    estimated_wait_seconds: int,
) -> str:
    tipo = "ATENDIMENTO PRIORITÁRIO" if ticket_type in {"PRIORITY", "PRIORITY_PLUS"} else "ATENDIMENTO NORMAL"
    wait_min = max(1, round(estimated_wait_seconds / 60)) if estimated_wait_seconds else 1
    return "\n".join(
        [
            store_name.upper(),
            department_name.upper(),
            "",
            "SENHA",
            display_number,
            "",
            tipo,
            issued_at.strftime("%d/%m/%Y %H:%M"),
            "",
            f"Pessoas aguardando: {people_ahead}",
            f"Espera estimada: {wait_min} min",
            "",
            "Acompanhe sua senha nas TVs.",
            "Obrigado pela preferência.",
        ]
    )
