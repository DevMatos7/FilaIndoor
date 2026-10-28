from datetime import datetime

from app.modules.printing.providers.fail import FailPrinter
from app.modules.printing.providers.mock import MockPrinter
from app.modules.printing.receipt import build_ticket_receipt, receipt_preview_text


def test_receipt_contains_number_and_type():
    raw = build_ticket_receipt(
        store_name="Real Supermercado",
        department_name="Açougue",
        display_number="A023",
        ticket_type="NORMAL",
        issued_at=datetime(2026, 10, 27, 15, 32),
        people_ahead=6,
        estimated_wait_seconds=720,
    )
    assert b"A023" in raw
    assert b"ATENDIMENTO NORMAL" in raw
    preview = receipt_preview_text(
        store_name="Real Supermercado",
        department_name="Açougue",
        display_number="P008",
        ticket_type="PRIORITY",
        issued_at=datetime(2026, 10, 27, 15, 32),
        people_ahead=2,
        estimated_wait_seconds=300,
    )
    assert "P008" in preview
    assert "PRIORIT" in preview


def test_mock_printer_ok():
    MockPrinter.clear()
    result = MockPrinter().print_bytes(b"hello")
    assert result.ok is True
    assert len(MockPrinter.last_jobs) == 1


def test_fail_printer():
    result = FailPrinter().print_bytes(b"x")
    assert result.ok is False
    assert "offline" in result.message.lower()
