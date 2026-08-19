"""
Order and related data structures.

Kept deliberately simple in Module 1 — agents just need to be able to
express "I want to buy/sell N units, at this price (or at market)".
The Order Book (Module 2) is what gives these teeth.
"""

from dataclasses import dataclass, field
from enum import Enum
from itertools import count

_order_ids = count(1)


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"   # execute immediately at best available price
    LIMIT = "limit"      # sit in the book until matched or cancelled


@dataclass
class Order:
    agent_id: str
    side: Side
    order_type: OrderType
    quantity: float
    price: float | None = None   # None for MARKET orders
    order_id: int = field(default_factory=lambda: next(_order_ids))
    round_submitted: int | None = None

    def __post_init__(self):
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("Limit orders must specify a price")
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")

    def __repr__(self):
        price_str = f"@{self.price:.2f}" if self.price is not None else "@MKT"
        return f"Order#{self.order_id}({self.agent_id}, {self.side.value}, {self.quantity}{price_str})"
