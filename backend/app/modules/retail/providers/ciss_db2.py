from __future__ import annotations

import re
from datetime import datetime, time
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.modules.retail.dto import (
    CanonicalPrice,
    CanonicalProduct,
    CanonicalPromotion,
    CanonicalStoreProduct,
)
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.timezone_util import promo_window_active, validate_iana_timezone


def _flag_true(value: Any) -> bool:
    return str(value or "").strip().upper() in {"T", "S", "Y", "1"}


def _flag_inactive(value: Any) -> bool:
    # FLAGINATIVO: T = inativo
    return str(value or "").strip().upper() == "T"


def _to_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day") and not isinstance(value, datetime):
        # date
        return datetime.combine(value, time.min)
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def product_key(id_produto: Any, id_sub: Any) -> str:
    return f"{int(id_produto)}:{int(id_sub or 0)}"


class CissDb2RetailProvider(RetailDataProvider):
    """Adapter DB2 CISS — READ ONLY. SQL não vaza para API/frontend."""

    name = "ciss_db2"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.schema = (self.settings.db2_schema or "DBA").strip()
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.schema):
            raise ValidationError("DB2_SCHEMA inválido")

    @property
    def configured(self) -> bool:
        return bool(self.settings.db2_conn_string or self.settings.ciss_db2_dsn)

    def capabilities(self) -> dict[str, Any]:
        return {
            **super().capabilities(),
            "configured": self.configured,
            "schema": self.schema,
            "note": "Configure DB2_CONN_STRING ou CISS_DB2_DSN",
        }

    def _connect(self):
        if not self.configured:
            raise ValidationError("DB2 não configurado")
        try:
            import pyodbc
        except ImportError as exc:  # pragma: no cover
            raise ValidationError("pyodbc não instalado no ambiente") from exc

        raw = self.settings.db2_conn_string or self.settings.ciss_db2_dsn
        if "Driver=" in raw or "DRIVER=" in raw:
            conn_str = raw
        else:
            parts = {k: v for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}
            driver = self.settings.db2_odbc_driver
            conn_str = (
                f"Driver={{{driver}}};"
                f"Database={parts.get('DATABASE')};"
                f"Hostname={parts.get('HOSTNAME')};"
                f"Port={parts.get('PORT', '50000')};"
                f"Protocol={parts.get('PROTOCOL', 'TCPIP')};"
                f"Uid={parts.get('UID')};"
                f"Pwd={parts.get('PWD')};"
            )
        timeout = int(self.settings.db2_query_timeout_seconds)
        return pyodbc.connect(conn_str, timeout=timeout)

    def _map_product_row(self, row: Any) -> CanonicalProduct:
        return CanonicalProduct(
            source_product_id=product_key(row[0], row[1]),
            description=str(row[2] or row[3] or "Produto").strip(),
            commercial_description=(str(row[3] or row[4] or "").strip() or None),
            gtin=(str(row[5]).strip() if row[5] else None),
            unit=(str(row[6]).strip() if row[6] else "UN"),
            section_code=str(row[7]) if row[7] is not None else None,
            group_code=str(row[8]) if row[8] is not None else None,
            subgroup_code=str(row[9]) if row[9] is not None else None,
            section_name=(str(row[10]).strip() if row[10] else None),
            group_name=(str(row[11]).strip() if row[11] else None),
            subgroup_name=(str(row[12]).strip() if row[12] else None),
            active=not _flag_inactive(row[13]),
            source_updated_at=_to_dt(row[14]),
        )

    def fetch_products(self, *, since: datetime | None = None, limit: int = 500) -> list[CanonicalProduct]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT g.IDPRODUTO, g.IDSUBPRODUTO, p.DESCRCOMPRODUTO, g.DESCRRESPRODUTO, g.SUBDESCRICAO,
                   g.CODBAR, p.EMBALAGEMSAIDA, p.IDSECAO, p.IDGRUPO, p.IDSUBGRUPO,
                   s.DESCRSECAO, gr.DESCRGRUPO, sg.DESCRSUBGRUPO, g.FLAGINATIVO,
                   COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) AS DTALT
            FROM {self.schema}.PRODUTO_GRADE g
            JOIN {self.schema}.PRODUTO p ON p.IDPRODUTO = g.IDPRODUTO
            LEFT JOIN {self.schema}.SECAO s ON s.IDSECAO = p.IDSECAO
            LEFT JOIN {self.schema}.GRUPO gr ON gr.IDGRUPO = p.IDGRUPO
            LEFT JOIN {self.schema}.SUBGRUPO sg ON sg.IDSUBGRUPO = p.IDSUBGRUPO
            WHERE 1=1
        """
        params: list[Any] = []
        if since:
            sql += " AND COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) > ?"
            params.append(since)
        sql += " ORDER BY COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) DESC FETCH FIRST ? ROWS ONLY"
        params.append(limit)

        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, params)
            return [self._map_product_row(row) for row in cur.fetchall()]
        finally:
            cn.close()

    def fetch_products_by_ids(self, source_product_ids: list[str]) -> list[CanonicalProduct]:
        """Fetch pontual por chave canônica — usado na reconciliação de amostra."""
        out: list[CanonicalProduct] = []
        if not source_product_ids:
            return out
        cn = self._connect()
        try:
            cur = cn.cursor()
            sql = f"""
                SELECT g.IDPRODUTO, g.IDSUBPRODUTO, p.DESCRCOMPRODUTO, g.DESCRRESPRODUTO, g.SUBDESCRICAO,
                       g.CODBAR, p.EMBALAGEMSAIDA, p.IDSECAO, p.IDGRUPO, p.IDSUBGRUPO,
                       s.DESCRSECAO, gr.DESCRGRUPO, sg.DESCRSUBGRUPO, g.FLAGINATIVO,
                       COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) AS DTALT
                FROM {self.schema}.PRODUTO_GRADE g
                JOIN {self.schema}.PRODUTO p ON p.IDPRODUTO = g.IDPRODUTO
                LEFT JOIN {self.schema}.SECAO s ON s.IDSECAO = p.IDSECAO
                LEFT JOIN {self.schema}.GRUPO gr ON gr.IDGRUPO = p.IDGRUPO
                LEFT JOIN {self.schema}.SUBGRUPO sg ON sg.IDSUBGRUPO = p.IDSUBGRUPO
                WHERE g.IDPRODUTO = ? AND g.IDSUBPRODUTO = ?
                FETCH FIRST 1 ROWS ONLY
            """
            for spid in source_product_ids:
                try:
                    a, b = spid.split(":", 1)
                    cur.execute(sql, int(a), int(b))
                except ValueError:
                    continue
                row = cur.fetchone()
                if row:
                    out.append(self._map_product_row(row))
            return out
        finally:
            cn.close()

    def fetch_prices_for_products(
        self,
        *,
        company_code: str,
        source_product_ids: list[str],
        store_timezone: str | None = None,
    ) -> list[CanonicalPrice]:
        """Preços/promo/qty apenas para SKUs informados (gate de reconciliação)."""
        tz = validate_iana_timezone(store_timezone) if store_timezone else None
        out: list[CanonicalPrice] = []
        if not source_product_ids:
            return out
        cn = self._connect()
        try:
            cur = cn.cursor()
            for spid in source_product_ids:
                try:
                    idprod, idsub = [int(x) for x in spid.split(":", 1)]
                except ValueError:
                    continue
                cur.execute(
                    f"""
                    SELECT CAST(VALPRECOVAREJO AS DOUBLE), CAST(VALPROMVAREJO AS DOUBLE),
                           DTINIPROMOCAOVAR, DTFIMPROMOCAOVAR, QTDMINPROMVAREJO,
                           COALESCE(DTALTERACAOVAR, DTALTERACAO)
                    FROM {self.schema}.POLITICA_PRECO_PRODUTO
                    WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
                      AND VALPRECOVAREJO IS NOT NULL AND VALPRECOVAREJO > 0
                    FETCH FIRST 1 ROWS ONLY
                    """,
                    int(company_code),
                    idprod,
                    idsub,
                )
                r = cur.fetchone()
                if not r:
                    continue
                regular = _num(r[0])
                promo = _num(r[1])
                starts, ends, min_qty, src_at = _to_dt(r[2]), _to_dt(r[3]), _num(r[4]), _to_dt(r[5])
                if regular is not None:
                    out.append(
                        CanonicalPrice(
                            spid,
                            "REGULAR",
                            regular,
                            source_ref=f"politica:{company_code}:{spid}:REGULAR",
                            source_updated_at=src_at,
                        )
                    )
                if promo is not None and promo > 0:
                    if not tz:
                        raise ValidationError("store_timezone obrigatório para avaliar vigência de promoção CISS")
                    out.append(
                        CanonicalPrice(
                            spid,
                            "PROMOTION",
                            promo,
                            min_qty=min_qty,
                            starts_at=starts,
                            expires_at=ends,
                            active=promo_window_active(starts, ends, tz),
                            source_ref=f"politica:{company_code}:{spid}:PROMOTION",
                            source_updated_at=src_at,
                        )
                    )
                cur.execute(
                    f"""
                    SELECT CAST(QTDPRODUTO AS DOUBLE), CAST(VALPRECOVAREJO AS DOUBLE), TIPOSTATUS, DTATUALIZACAO
                    FROM {self.schema}.PRODUTO_DESCONTO_QTDE
                    WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
                      AND VALPRECOVAREJO IS NOT NULL AND VALPRECOVAREJO > 0
                    ORDER BY QTDPRODUTO
                    """,
                    int(company_code),
                    idprod,
                    idsub,
                )
                for q in cur.fetchall():
                    if str(q[2] or "").upper() in {"I", "N"}:
                        continue
                    qty, amount = _num(q[0]), _num(q[1])
                    if qty is None or amount is None:
                        continue
                    out.append(
                        CanonicalPrice(
                            spid,
                            "QUANTITY",
                            amount,
                            min_qty=qty,
                            condition_text=f"A partir de {qty:g}",
                            source_ref=f"desconto_qtde:{company_code}:{spid}:{qty}",
                            source_updated_at=_to_dt(q[3]),
                        )
                    )
            return out
        finally:
            cn.close()

    def fetch_store_products(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT pe.IDPRODUTO, pe.IDSUBPRODUTO, pe.IDEMPRESA, pe.FLAGPERMITEVENDA, pe.DTALTERACAO
            FROM {self.schema}.PRODUTO_EMPRESA pe
            WHERE pe.IDEMPRESA = ?
        """
        params: list[Any] = [int(company_code)]
        if since:
            sql += " AND pe.DTALTERACAO > ?"
            params.append(since)
        sql += " ORDER BY pe.DTALTERACAO DESC FETCH FIRST ? ROWS ONLY"
        params.append(limit)
        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, params)
            return [
                CanonicalStoreProduct(
                    source_product_id=product_key(r[0], r[1]),
                    company_code=str(r[2]),
                    sellable=_flag_true(r[3]) or str(r[3]).upper() == "T",
                    available=True,
                    source_updated_at=_to_dt(r[4]),
                )
                for r in cur.fetchall()
            ]
        finally:
            cn.close()

    def fetch_prices(
        self,
        *,
        company_code: str,
        since: datetime | None = None,
        limit: int = 500,
        store_timezone: str | None = None,
    ) -> list[CanonicalPrice]:
        limit = max(1, min(limit, 10000))
        tz = validate_iana_timezone(store_timezone) if store_timezone else None
        # CAST AS DOUBLE: driver ODBC IBM devolve DECIMAL(15,6) sem escala
        # (ex.: 2.19 → Decimal('2190000')); CHAR/DOUBLE preservam o valor real.
        sql = f"""
            SELECT IDPRODUTO, IDSUBPRODUTO,
                   CAST(VALPRECOVAREJO AS DOUBLE) AS VALPRECOVAREJO,
                   CAST(VALPROMVAREJO AS DOUBLE) AS VALPROMVAREJO,
                   DTINIPROMOCAOVAR, DTFIMPROMOCAOVAR, QTDMINPROMVAREJO,
                   COALESCE(DTALTERACAOVAR, DTALTERACAO) AS DTALT
            FROM {self.schema}.POLITICA_PRECO_PRODUTO
            WHERE IDEMPRESA = ?
              AND VALPRECOVAREJO IS NOT NULL
              AND VALPRECOVAREJO > 0
        """
        params: list[Any] = [int(company_code)]
        if since:
            sql += " AND COALESCE(DTALTERACAOVAR, DTALTERACAO) > ?"
            params.append(since)
        sql += " ORDER BY COALESCE(DTALTERACAOVAR, DTALTERACAO) DESC FETCH FIRST ? ROWS ONLY"
        params.append(limit)

        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, params)
            out: list[CanonicalPrice] = []
            for r in cur.fetchall():
                spid = product_key(r[0], r[1])
                regular = _num(r[2])
                promo = _num(r[3])
                starts = _to_dt(r[4])
                ends = _to_dt(r[5])
                min_qty = _num(r[6])
                src_at = _to_dt(r[7])
                if regular is not None:
                    out.append(
                        CanonicalPrice(
                            spid,
                            "REGULAR",
                            regular,
                            source_ref=f"politica:{company_code}:{spid}:REGULAR",
                            source_updated_at=src_at,
                        )
                    )
                if promo is not None and promo > 0:
                    if not tz:
                        raise ValidationError(
                            "store_timezone obrigatório para avaliar vigência de promoção CISS"
                        )
                    out.append(
                        CanonicalPrice(
                            spid,
                            "PROMOTION",
                            promo,
                            min_qty=min_qty,
                            starts_at=starts,
                            expires_at=ends,
                            active=promo_window_active(starts, ends, tz),
                            source_ref=f"politica:{company_code}:{spid}:PROMOTION",
                            condition_text=(f"A partir de {min_qty:g}" if min_qty and min_qty > 1 else None),
                            source_updated_at=src_at,
                        )
                    )
            # quantity discounts — CAST AS DOUBLE also on QTDPRODUTO (ODBC scale bug: 50 → 50000)
            qsql = f"""
                SELECT IDPRODUTO, IDSUBPRODUTO,
                       CAST(QTDPRODUTO AS DOUBLE) AS QTDPRODUTO,
                       CAST(VALPRECOVAREJO AS DOUBLE) AS VALPRECOVAREJO,
                       TIPOSTATUS, DTATUALIZACAO
                FROM {self.schema}.PRODUTO_DESCONTO_QTDE
                WHERE IDEMPRESA = ?
                  AND VALPRECOVAREJO IS NOT NULL
                  AND VALPRECOVAREJO > 0
                FETCH FIRST ? ROWS ONLY
            """
            cur.execute(qsql, int(company_code), min(limit, 2000))
            for r in cur.fetchall():
                if str(r[4] or "").upper() in {"I", "N"}:  # inactive heuristics
                    continue
                qty = _num(r[2])
                amount = _num(r[3])
                if amount is None or qty is None:
                    continue
                spid = product_key(r[0], r[1])
                out.append(
                    CanonicalPrice(
                        spid,
                        "QUANTITY",
                        amount,
                        min_qty=qty,
                        condition_text=f"A partir de {qty:g}",
                        source_ref=f"desconto_qtde:{company_code}:{spid}:{qty}",
                        source_updated_at=_to_dt(r[5]),
                    )
                )
            return out[:limit]
        finally:
            cn.close()

    def fetch_promotions(
        self,
        *,
        company_code: str,
        since: datetime | None = None,
        limit: int = 500,
        store_timezone: str | None = None,
    ) -> list[CanonicalPromotion]:
        prices = self.fetch_prices(
            company_code=company_code, since=since, limit=limit, store_timezone=store_timezone
        )
        out: list[CanonicalPromotion] = []
        for p in prices:
            if p.price_kind != "PROMOTION":
                continue
            out.append(
                CanonicalPromotion(
                    source_product_id=p.source_product_id,
                    promo_amount=p.amount,
                    source_promotion_id=p.source_ref,
                    promotion_type="NORMAL" if not p.min_qty or p.min_qty <= 1 else "QUANTITY",
                    starts_at=p.starts_at,
                    expires_at=p.expires_at,
                    condition_text=p.condition_text,
                    active=p.active,
                    source_updated_at=p.source_updated_at,
                )
            )
        return out[:limit]

    def fetch_availability(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT IDEMPRESA, IDPRODUTO, IDSUBPRODUTO, SUM(QTDATUALESTOQUE) AS QTD
            FROM {self.schema}.PRODUTO_GRADE_SALDO_EST_VW
            WHERE IDEMPRESA = ?
            GROUP BY IDEMPRESA, IDPRODUTO, IDSUBPRODUTO
            FETCH FIRST ? ROWS ONLY
        """
        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, int(company_code), limit)
            out: list[CanonicalStoreProduct] = []
            for r in cur.fetchall():
                qty = _num(r[3]) or 0.0
                out.append(
                    CanonicalStoreProduct(
                        source_product_id=product_key(r[1], r[2]),
                        company_code=str(r[0]),
                        sellable=True,
                        available=qty > 0,
                        stock_qty=qty,
                    )
                )
            return out
        finally:
            cn.close()

    # Placeholder JPEG embedded in CISS for products without a real photo (LENGTH=4912, identical SHA).
    PLACEHOLDER_IMAGE_SHA256 = "0c2cba5fa5aa8a4552672c5aee88bd011e706ebd671596e7e5d268988923ce5e"
    PLACEHOLDER_IMAGE_LENGTH = 4912

    def _resolve_image_idcod(
        self, cur, *, source_product_id: str | None = None, gtin: str | None = None
    ) -> tuple[str, int, str | None] | None:
        """Return (idcodbarprod, length, source_product_id) or None."""
        spid = source_product_id
        if source_product_id:
            try:
                idprod, idsub = [int(x) for x in source_product_id.split(":", 1)]
            except ValueError:
                return None
            cur.execute(
                f"""
                SELECT CAST(G.IDCODBARPROD AS VARCHAR(32)), LENGTH(PET.FOTOPRINCIPAL)
                FROM {self.schema}.PRODUTO_GRADE G
                JOIN {self.schema}.PRODUTO_ESPECIFICACAO_TECNICA PET
                  ON PET.IDCODBARPROD = G.IDCODBARPROD
                WHERE G.IDPRODUTO=? AND G.IDSUBPRODUTO=?
                  AND PET.FOTOPRINCIPAL IS NOT NULL
                FETCH FIRST 1 ROW ONLY
                """,
                idprod,
                idsub,
            )
        elif gtin:
            cur.execute(
                f"""
                SELECT CAST(IDCODBARPROD AS VARCHAR(32)), LENGTH(FOTOPRINCIPAL)
                FROM {self.schema}.PRODUTO_ESPECIFICACAO_TECNICA
                WHERE CAST(IDCODBARPROD AS VARCHAR(32)) = ?
                  AND FOTOPRINCIPAL IS NOT NULL
                FETCH FIRST 1 ROW ONLY
                """,
                str(gtin),
            )
        else:
            return None
        row = cur.fetchone()
        if not row:
            return None
        return str(row[0]), int(row[1] or 0), spid

    def fetch_product_image_meta(
        self, *, source_product_id: str | None = None, gtin: str | None = None
    ) -> dict[str, Any] | None:
        """
        Cheap probe: LENGTH + first 32 bytes hex. Does NOT transfer full BLOB.
        fingerprint = "{length}:{head_hex}"
        """
        cn = self._connect()
        try:
            cur = cn.cursor()
            resolved = self._resolve_image_idcod(cur, source_product_id=source_product_id, gtin=gtin)
            if not resolved:
                return None
            idcod, length, spid = resolved
            if length <= 0:
                return {"usable": False, "reason": "empty", "length": length}
            if length == self.PLACEHOLDER_IMAGE_LENGTH:
                return {
                    "usable": False,
                    "reason": "placeholder_4912",
                    "length": length,
                    "idcodbarprod": idcod,
                    "source_product_id": spid,
                    "fingerprint": f"{length}:PLACEHOLDER",
                }
            cur.execute(
                f"""
                SELECT CAST(HEX(SUBSTR(FOTOPRINCIPAL,1,32)) AS VARCHAR(64))
                FROM {self.schema}.PRODUTO_ESPECIFICACAO_TECNICA
                WHERE CAST(IDCODBARPROD AS VARCHAR(32)) = ?
                """,
                idcod,
            )
            hx_row = cur.fetchone()
            head = str(hx_row[0]).strip().lower() if hx_row and hx_row[0] else ""
            return {
                "usable": True,
                "idcodbarprod": idcod,
                "source_product_id": spid,
                "length": length,
                "head_hex": head,
                "fingerprint": f"{length}:{head}",
            }
        finally:
            cn.close()

    def fetch_product_image_blob(
        self, *, source_product_id: str | None = None, gtin: str | None = None
    ) -> dict[str, Any] | None:
        """
        Read FOTOPRINCIPAL via HEX(SUBSTR) chunks (pyodbc does not support ODBC BLOB -98).
        Returns None for missing/placeholder images. Never exposes SQL to callers beyond dict meta.
        """
        import hashlib

        cn = self._connect()
        try:
            cur = cn.cursor()
            resolved = self._resolve_image_idcod(cur, source_product_id=source_product_id, gtin=gtin)
            if not resolved:
                return None
            idcod, length, spid = resolved
            if length <= 0 or length == self.PLACEHOLDER_IMAGE_LENGTH:
                return None

            # DB2 HEX(SUBSTR(blob, ?, ?)) rejects bound offsets (SQL0171N).
            # Inline integer literals; keep idcod as the only bind param.
            chunk = 512  # HEX expands 1:2 → VARCHAR(1024) fits safely
            parts: list[str] = []
            for start in range(1, length + 1, chunk):
                n = min(chunk, length - start + 1)
                cur.execute(
                    f"""
                    SELECT CAST(HEX(SUBSTR(FOTOPRINCIPAL, {int(start)}, {int(n)})) AS VARCHAR(1024))
                    FROM {self.schema}.PRODUTO_ESPECIFICACAO_TECNICA
                    WHERE CAST(IDCODBARPROD AS VARCHAR(32)) = ?
                    """,
                    idcod,
                )
                hx = cur.fetchone()
                if not hx or not hx[0]:
                    break
                parts.append(str(hx[0]).strip())
            raw = bytes.fromhex("".join(parts))
            if not raw:
                return None
            digest = hashlib.sha256(raw).hexdigest()
            if digest == self.PLACEHOLDER_IMAGE_SHA256:
                return None
            fmt = "UNKNOWN"
            mime = "application/octet-stream"
            if raw[:3] == b"\xff\xd8\xff":
                fmt, mime = "JPEG", "image/jpeg"
            elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                fmt, mime = "PNG", "image/png"
            else:
                return None
            head = raw[:32].hex()
            return {
                "idcodbarprod": idcod,
                "source_product_id": spid,
                "bytes": raw,
                "sha256": digest,
                "length": len(raw),
                "format": fmt,
                "mime_type": mime,
                "fingerprint": f"{len(raw)}:{head}",
            }
        finally:
            cn.close()

    def fetch_offer_campaigns(
        self, *, company_code: str, active_only: bool = True, limit: int = 50
    ) -> list[dict[str, Any]]:
        """PROMOCAO_GESTAO scoped for a company.

        Primary: PROMOCAO_GESTAO_EMPRESA.IDEMPRESA.
        Fallback: when the company has no *active-window* EMPRESA links (observed for
        IDEMPRESA=1 / Supermercado Real), include vigente campaigns that have at least
        one item with POLITICA_PRECO_PRODUTO for that IDEMPRESA. Never invents rows.
        """
        limit = max(1, min(limit, 200))
        company = int(company_code)
        window_sql = ""
        if active_only:
            window_sql = (
                " AND PG.DTINIPROMOCAO <= CURRENT TIMESTAMP"
                " AND PG.DTFIMPROMOCAO >= CURRENT TIMESTAMP"
            )
        cn = self._connect()
        try:
            cur = cn.cursor()
            # Does this company use EMPRESA junction for current window?
            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM {self.schema}.PROMOCAO_GESTAO_EMPRESA PE
                JOIN {self.schema}.PROMOCAO_GESTAO PG ON PG.IDPROMOCAO = PE.IDPROMOCAO
                WHERE PE.IDEMPRESA = ?
                  AND PE.FLAGINATIVO = 'F'
                  AND PG.FLAGINATIVO = 'F'
                  AND PG.DTINIPROMOCAO <= CURRENT TIMESTAMP
                  AND PG.DTFIMPROMOCAO >= CURRENT TIMESTAMP
                """,
                company,
            )
            empresa_active_links = int((cur.fetchone() or [0])[0] or 0)

            if empresa_active_links > 0:
                sql = f"""
                    SELECT PG.IDPROMOCAO, PG.DESCRPROMOCAO, PG.DTINIPROMOCAO, PG.DTFIMPROMOCAO,
                           PG.FLAGINATIVO, PG.DTALTERACAO
                    FROM {self.schema}.PROMOCAO_GESTAO PG
                    JOIN {self.schema}.PROMOCAO_GESTAO_EMPRESA PE
                      ON PE.IDPROMOCAO = PG.IDPROMOCAO
                     AND PE.IDEMPRESA = ?
                     AND PE.FLAGINATIVO = 'F'
                    WHERE PG.FLAGINATIVO = 'F'
                    {window_sql}
                    ORDER BY PG.DTINIPROMOCAO DESC
                    FETCH FIRST ? ROWS ONLY
                """
                cur.execute(sql, company, limit)
            else:
                # Company does not publish EMPRESA links for current offers —
                # scope by priced items at IDEMPRESA (Campo Novo / emp 1 pattern).
                sql = f"""
                    SELECT PG.IDPROMOCAO, PG.DESCRPROMOCAO, PG.DTINIPROMOCAO, PG.DTFIMPROMOCAO,
                           PG.FLAGINATIVO, PG.DTALTERACAO
                    FROM {self.schema}.PROMOCAO_GESTAO PG
                    WHERE PG.FLAGINATIVO = 'F'
                    {window_sql}
                      AND EXISTS (
                        SELECT 1
                        FROM {self.schema}.PROMOCAO_GESTAO_PRODUTO PGP
                        JOIN {self.schema}.POLITICA_PRECO_PRODUTO PPP
                          ON PPP.IDPRODUTO = PGP.IDPRODUTO
                         AND PPP.IDSUBPRODUTO = PGP.IDSUBPRODUTO
                         AND PPP.IDEMPRESA = ?
                        WHERE PGP.IDPROMOCAO = PG.IDPROMOCAO
                          AND PGP.FLAGINATIVO = 'F'
                      )
                    ORDER BY PG.DTINIPROMOCAO DESC
                    FETCH FIRST ? ROWS ONLY
                """
                cur.execute(sql, company, limit)

            out = []
            for r in cur.fetchall():
                out.append(
                    {
                        "source_offer_id": str(r[0]),
                        "name": str(r[1] or f"Oferta {r[0]}").strip(),
                        "starts_at": _to_dt(r[2]),
                        "expires_at": _to_dt(r[3]),
                        "active": not _flag_inactive(r[4]),
                        "source_updated_at": _to_dt(r[5]),
                        "scope_mode": "EMPRESA" if empresa_active_links > 0 else "PRICED_ITEMS",
                    }
                )
            return out
        finally:
            cn.close()

    def fetch_offer_items(
        self, *, company_code: str, source_offer_id: str, limit: int = 500
    ) -> list[dict[str, Any]]:
        from app.modules.retail.offer_price import OfferPriceResolver

        limit = max(1, min(limit, 2000))
        sql = f"""
            SELECT PGP.IDPRODUTO, PGP.IDSUBPRODUTO,
                   CAST(PGP.VALPRECO AS DOUBLE),
                   PGP.FLAGPRECOMANDATORIO,
                   CAST(PPV.VALGRAMAENTRADA AS DOUBLE),
                   CAST(PPP.VALPRECOVAREJO AS DOUBLE),
                   PV.IDCADEIAPRECO,
                   PGP.FLAGINATIVO
            FROM {self.schema}.PROMOCAO_GESTAO_PRODUTO PGP
            JOIN {self.schema}.PRODUTOS_VIEW PPV
              ON PPV.IDPRODUTO = PGP.IDPRODUTO AND PPV.IDSUBPRODUTO = PGP.IDSUBPRODUTO
            JOIN {self.schema}.PRODUTO_GRADE PV
              ON PV.IDPRODUTO = PGP.IDPRODUTO AND PV.IDSUBPRODUTO = PGP.IDSUBPRODUTO
            LEFT JOIN {self.schema}.POLITICA_PRECO_PRODUTO PPP
              ON PPP.IDPRODUTO = PGP.IDPRODUTO AND PPP.IDSUBPRODUTO = PGP.IDSUBPRODUTO
             AND PPP.IDEMPRESA = ?
            WHERE PGP.IDPROMOCAO = ?
              AND PGP.FLAGINATIVO = 'F'
            FETCH FIRST ? ROWS ONLY
        """
        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, int(company_code), int(source_offer_id), limit)
            out = []
            for r in cur.fetchall():
                priced = OfferPriceResolver.resolve(
                    val_preco=r[2], flag_preco_mandatorio=r[3], val_grama_entrada=r[4]
                )
                out.append(
                    {
                        "source_product_id": product_key(r[0], r[1]),
                        "raw_offer_price": float(priced.raw_offer_price) if priced.raw_offer_price is not None else None,
                        "offer_price": float(priced.effective_offer_price)
                        if priced.effective_offer_price is not None
                        else None,
                        "calculation_type": priced.calculation_type,
                        "regular_price": _num(r[5]),
                        "source_chain_id": str(r[6]) if r[6] is not None else None,
                        "active": not _flag_inactive(r[7]),
                    }
                )
            return out
        finally:
            cn.close()

    def fetch_price_chains(self, *, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT IDCADEIAPRECO, DESCRCADEIAPRECO, DESCRETIQUETAGONDOLA, DTALTERACAO,
                   IDPRODUTO, IDSUBPRODUTO
            FROM {self.schema}.PRODUTO_CADEIA_PRECO
            FETCH FIRST ? ROWS ONLY
        """
        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, limit)
            return [
                {
                    "source_chain_id": str(r[0]),
                    "description": str(r[1] or f"Cadeia {r[0]}").strip(),
                    "gondola_label": (str(r[2]).strip() if r[2] else None),
                    "source_updated_at": _to_dt(r[3]),
                    "source_product_id": product_key(r[4], r[5]) if r[4] is not None else None,
                }
                for r in cur.fetchall()
            ]
        finally:
            cn.close()

    def fetch_availability_for_products(
        self, *, company_code: str, source_product_ids: list[str]
    ) -> list[CanonicalStoreProduct]:
        out: list[CanonicalStoreProduct] = []
        if not source_product_ids:
            return out
        cn = self._connect()
        try:
            cur = cn.cursor()
            for spid in source_product_ids:
                try:
                    idprod, idsub = [int(x) for x in spid.split(":", 1)]
                except ValueError:
                    continue
                cur.execute(
                    f"""
                    SELECT CAST(SUM(QTDATUALESTOQUE) AS DOUBLE)
                    FROM {self.schema}.PRODUTO_GRADE_SALDO_EST_VW
                    WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
                    """,
                    int(company_code),
                    idprod,
                    idsub,
                )
                r = cur.fetchone()
                qty = _num(r[0]) if r and r[0] is not None else 0.0
                out.append(
                    CanonicalStoreProduct(
                        source_product_id=spid,
                        company_code=str(company_code),
                        sellable=True,
                        available=(qty or 0) > 0,
                        stock_qty=qty or 0.0,
                    )
                )
            return out
        finally:
            cn.close()
