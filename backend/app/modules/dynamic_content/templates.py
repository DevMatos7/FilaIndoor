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
        "content_type": "PRICE_TABLE",
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
        "content_type": "PRICE_TABLE",
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
        "content_type": "PRICE_TABLE",
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
        "content_type": "PRICE_TABLE",
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

SYSTEM_VISUAL_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "sys-dct-product-grid-2x2",
        "name": "Grade 2×2",
        "slug": "product_grid_2x2",
        "content_type": "PRODUCT_GRID",
        "config": {
            "ui_name": "Grade 2×2",
            "columns": 2,
            "rows": 2,
            "default_items_per_page": 4,
            "min_items_per_page": 4,
            "max_items_per_page": 4,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "image_fit": "contain",
            "show_header": True,
        },
    },
    {
        "id": "sys-dct-product-grid-3x2",
        "name": "Grade 3×2",
        "slug": "product_grid_3x2",
        "content_type": "PRODUCT_GRID",
        "config": {
            "ui_name": "Grade 3×2",
            "columns": 3,
            "rows": 2,
            "default_items_per_page": 6,
            "min_items_per_page": 6,
            "max_items_per_page": 6,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "image_fit": "contain",
            "show_header": True,
        },
    },
    {
        "id": "sys-dct-product-grid-4x2",
        "name": "Grade 4×2",
        "slug": "product_grid_4x2",
        "content_type": "PRODUCT_GRID",
        "config": {
            "ui_name": "Grade 4×2",
            "columns": 4,
            "rows": 2,
            "default_items_per_page": 8,
            "min_items_per_page": 8,
            "max_items_per_page": 8,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": False,
            "show_promo_badge": True,
            "image_fit": "contain",
            "show_header": True,
        },
    },
    {
        "id": "sys-dct-product-hero-clean",
        "name": "Destaque limpo",
        "slug": "product_hero_clean",
        "content_type": "PRODUCT_HERO",
        "config": {
            "ui_name": "Produto em destaque",
            "default_items_per_page": 1,
            "min_items_per_page": 1,
            "max_items_per_page": 1,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": False,
            "image_fit": "contain",
            "show_header": True,
            "hero_layout": "clean",
        },
    },
    {
        "id": "sys-dct-product-hero-promo",
        "name": "Destaque promocional",
        "slug": "product_hero_promo",
        "content_type": "PRODUCT_HERO",
        "config": {
            "ui_name": "Produto em oferta",
            "default_items_per_page": 1,
            "min_items_per_page": 1,
            "max_items_per_page": 1,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "image_fit": "contain",
            "show_header": True,
            "hero_layout": "promo",
            "emphasize_promo": True,
        },
    },
    {
        "id": "sys-dct-promotion-board-2x2",
        "name": "Painel promocional 2×2",
        "slug": "promotion_board_2x2",
        "content_type": "PROMOTION_BOARD",
        "config": {
            "ui_name": "Painel promocional 2×2",
            "columns": 2,
            "rows": 2,
            "default_items_per_page": 4,
            "min_items_per_page": 4,
            "max_items_per_page": 4,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "image_fit": "contain",
            "show_header": True,
            "emphasize_promo": True,
            "default_promotion_only": True,
        },
    },
    {
        "id": "sys-dct-promotion-board-3x2",
        "name": "Painel promocional 3×2",
        "slug": "promotion_board_3x2",
        "content_type": "PROMOTION_BOARD",
        "config": {
            "ui_name": "Painel promocional 3×2",
            "columns": 3,
            "rows": 2,
            "default_items_per_page": 6,
            "min_items_per_page": 6,
            "max_items_per_page": 6,
            "show_image": True,
            "show_unit": True,
            "show_regular_price": True,
            "show_promo_badge": True,
            "image_fit": "contain",
            "show_header": True,
            "emphasize_promo": True,
            "default_promotion_only": True,
        },
    },
]

ALLOWED_CONTENT_TYPES = {"PRICE_TABLE", "PRODUCT_GRID", "PRODUCT_HERO", "PROMOTION_BOARD"}


def ensure_system_templates(db: Session) -> None:
    for spec in SYSTEM_PRICE_TABLE_TEMPLATES + SYSTEM_VISUAL_TEMPLATES:
        existing = db.get(DynamicContentTemplate, spec["id"])
        if existing:
            # keep config fresh for system templates (idempotent upgrades)
            if existing.is_system:
                existing.config = spec["config"]
                existing.content_type = spec["content_type"]
                existing.name = spec["name"]
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
                content_type=spec["content_type"],
                orientation="landscape",
                aspect_ratio="16:9",
                config=spec["config"],
                active=True,
                is_system=True,
            )
        )
    db.commit()
