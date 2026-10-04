"""Tính báo giá từ danh mục — thuần tính toán, không I/O.

Công thức: `amount = unit_price × quantity` cho từng dòng; `total = Σ amount`. Đơn giá lấy từ
`CatalogItem` (có nguồn), KHÔNG BAO GIỜ từ đầu ra của mô hình ngôn ngữ.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

MAX_QUANTITY = 1000


class PricingError(ValueError):
    """Đầu vào không tính được — từ chối thay vì đoán."""


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    name: str
    unit_price: Decimal
    unit: str
    source: str
    source_ref: str


@dataclass(frozen=True)
class Selection:
    item_id: str
    quantity: int


@dataclass(frozen=True)
class QuoteLine:
    item_id: str
    quantity: int
    unit_price: Decimal
    amount: Decimal
    source: str
    source_ref: str


@dataclass(frozen=True)
class Quote:
    lines: tuple[QuoteLine, ...]
    total: Decimal


def compute_quote(selections: Sequence[Selection], catalog: Mapping[str, CatalogItem]) -> Quote:
    lines: list[QuoteLine] = []
    for selection in selections:
        item = catalog.get(selection.item_id)
        if item is None:
            raise PricingError(f"mã `{selection.item_id}` không có trong danh mục — không đoán đơn giá")
        if not item.source or not item.source_ref:
            raise PricingError(f"`{item.item_id}` thiếu nguồn — không hiển thị con số không có nguồn")
        if not 0 < selection.quantity <= MAX_QUANTITY:
            raise PricingError(f"số lượng {selection.quantity} ngoài khoảng 1..{MAX_QUANTITY}")
        amount = item.unit_price * selection.quantity
        lines.append(QuoteLine(item.item_id, selection.quantity, item.unit_price, amount, item.source, item.source_ref))
    return Quote(tuple(lines), sum((line.amount for line in lines), Decimal("0")))
