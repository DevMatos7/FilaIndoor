"""Offer price normalization — Decimal only, never float math for money."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


@dataclass(frozen=True)
class OfferPriceResult:
    raw_offer_price: Decimal | None
    effective_offer_price: Decimal | None
    calculation_type: str  # DIRECT | WEIGHT_CONVERTED | INVALID
    flag_preco_mandatorio: bool
    val_grama_entrada: Decimal | None


class OfferPriceResolver:
    """
    Semântica CISS (PROMOCAO_GESTAO_PRODUTO):

    if FLAGPRECOMANDATORIO == 'T':
        effective = VALPRECO × VALGRAMAENTRADA
    else:
        effective = VALPRECO
    """

    @staticmethod
    def resolve(
        *,
        val_preco: Any,
        flag_preco_mandatorio: Any,
        val_grama_entrada: Any = None,
    ) -> OfferPriceResult:
        raw = to_decimal(val_preco)
        flag = str(flag_preco_mandatorio or "").strip().upper() in {"T", "S", "Y", "1"}
        gram = to_decimal(val_grama_entrada)
        if raw is None:
            return OfferPriceResult(None, None, "INVALID", flag, gram)
        if flag:
            if gram is None:
                return OfferPriceResult(raw, None, "INVALID", flag, gram)
            return OfferPriceResult(raw, (raw * gram).quantize(Decimal("0.01")), "WEIGHT_CONVERTED", flag, gram)
        return OfferPriceResult(raw, raw.quantize(Decimal("0.01")), "DIRECT", flag, gram)
