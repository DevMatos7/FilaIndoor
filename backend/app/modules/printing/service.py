from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.printing.providers.base import PrintResult, PrinterProvider
from app.modules.printing.providers.escpos import ESCPosPrinter
from app.modules.printing.providers.fail import FailPrinter
from app.modules.printing.providers.mock import MockPrinter
from app.modules.printing.receipt import build_ticket_receipt, receipt_preview_text
from app.modules.queue.models.entities import PrintJob, Queue, Ticket


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_printer_provider(override: str | None = None) -> PrinterProvider:
    settings = get_settings()
    name = (override or settings.print_provider or "mock").lower()
    if name == "escpos":
        return ESCPosPrinter(
            host=settings.printer_host,
            port=settings.printer_port,
            timeout=settings.printer_timeout_seconds,
        )
    if name == "fail":
        return FailPrinter()
    return MockPrinter()


class PrintService:
    def __init__(self, db: Session, provider: PrinterProvider | None = None):
        self.db = db
        self.provider = provider or get_printer_provider()

    def print_ticket(
        self,
        *,
        queue: Queue,
        ticket: Ticket,
        store_name: str,
        department_name: str,
        people_ahead: int,
        estimated_wait_seconds: int,
    ) -> dict[str, Any]:
        payload = build_ticket_receipt(
            store_name=store_name,
            department_name=department_name,
            display_number=ticket.display_number,
            ticket_type=ticket.ticket_type,
            issued_at=ticket.issued_at,
            people_ahead=people_ahead,
            estimated_wait_seconds=estimated_wait_seconds,
        )
        preview = receipt_preview_text(
            store_name=store_name,
            department_name=department_name,
            display_number=ticket.display_number,
            ticket_type=ticket.ticket_type,
            issued_at=ticket.issued_at,
            people_ahead=people_ahead,
            estimated_wait_seconds=estimated_wait_seconds,
        )

        job = PrintJob(
            queue_id=queue.id,
            ticket_id=ticket.id,
            provider=self.provider.name,
            status="PENDING",
            payload_preview=preview,
        )
        self.db.add(job)
        self.db.flush()

        result: PrintResult = self.provider.print_bytes(payload)
        job.status = "SUCCESS" if result.ok else "FAILED"
        job.error_message = None if result.ok else result.message
        job.finished_at = utcnow()
        self.db.commit()

        return {
            "ok": result.ok,
            "provider": result.provider,
            "message": result.message,
            "job_id": job.id,
            "preview": preview if self.provider.name == "mock" else None,
        }
