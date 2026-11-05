from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.dynamic_content.models import DynamicContentTemplate

SYSTEM_PRICE_TABLE_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "sys-dct-price-table-clean",
        "name": "Tabela limpa",
        "slug": "price_table_clean",
        "config": {
            "ui_name": "Tabela limpa",
            "default_items_per_page": 8,
            "min_items_per_page": 4,
            "max_items_per_page": 12,
            "row_density": "comfortable",
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "show_header": True,
            "columns": 1,
        },
    },
    {
        "id": "sys-dct-price-table-compact",
        "name": "Tabela compacta",
        "slug": "price_table_compact",
        "config": {
            "ui_name": "Tabela compacta",
            "default_items_per_page": 16,
            "min_items_per_page": 8,
            "max_items_per_page": 24,
            "row_density": "compact",
            "show_unit": True,
            "show_regular_price": False,
            "show_promo_badge": True,
            "show_header": True,
            "columns": 1,
        },
    },
    {
        "id": "sys-dct-price-table-two-columns",
        "name": "Tabela duas colunas",
        "slug": "price_table_two_columns",
        "config": {
            "ui_name": "Tabela duas colunas",
            "default_items_per_page": 12,
            "min_items_per_page": 6,
            "max_items_per_page": 20,
            "row_density": "comfortable",
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "show_header": True,
            "columns": 2,
        },
    },
    {
        "id": "sys-dct-price-table-promo",
        "name": "Tabela promocional",
        "slug": "price_table_promo",
        "config": {
            "ui_name": "Tabela promocional",
            "default_items_per_page": 6,
            "min_items_per_page": 3,
            "max_items_per_page": 10,
            "row_density": "emphasis",
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "show_header": True,
            "columns": 1,
            "emphasize_promo": True,
        },
    },
]


def ensure_system_templates(db: Session) -> None:
    for spec in SYSTEM_PRICE_TABLE_TEMPLATES:
        existing = db.get(DynamicContentTemplate, spec["id"])
        if existing:
            continue
        by_slug = db.scalar(
            select(DynamicContentTemplate).where(
                DynamicContentTemplate.store_id.is_(None),
                DynamicContentTemplate.slug == spec["slug"],
            )
        )
        if by_slug:
            continue
        db.add(
            DynamicContentTemplate(
                id=spec["id"],
                store_id=None,
                name=spec["name"],
                slug=spec["slug"],
                content_type="PRICE_TABLE",
                orientation="landscape",
                aspect_ratio="16:9",
                config=spec["config"],
                active=True,
                is_system=True,
            )
        )
    db.commit()
