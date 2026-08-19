"""
Trade — the result of a successful match in the order book.
Logged by the OrderBook and consumed by the Simulation Engine (Module 3)
to update agent cash/holdings and the price history.
"""

from dataclasses import dataclass, field
from itertools import count

from core.order import Side

_trade_ids = count(1)


@dataclass
class Trade:
    buy_agent_id: str
    sell_agent_id: str
    price: float
    quantity: float
    round_number: int
    trade_id: int = field(default_factory=lambda: next(_trade_ids))
    # Which resting order was hit — useful for debugging/analysis later.
    aggressor_side: Side = Side.BUY

    def __repr__(self):
        return (f"Trade#{self.trade_id}(round={self.round_number}, "
                f"{self.quantity}@{self.price:.2f}, "
                f"buyer={self.buy_agent_id}, seller={self.sell_agent_id})")
