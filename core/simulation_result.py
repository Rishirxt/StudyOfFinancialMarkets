"""
SimulationResult — everything a completed run produced, in one place.
Maps directly onto the ER diagram: price_history/rounds_log -> ROUND,
trades -> TRADE, agents -> AGENT. Module 4/5/6 all consume this object.
"""

from dataclasses import dataclass, field

from core.order_book import OrderBook
from core.trade import Trade


@dataclass
class RoundRecord:
    round_number: int
    price: float
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    num_orders: int
    num_trades: int


@dataclass
class SimulationResult:
    run_id: str
    price_history: list[float] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    rounds_log: list[RoundRecord] = field(default_factory=list)
    agents: list = field(default_factory=list)
    order_book: OrderBook | None = None

    def returns(self) -> list[float]:
        p = self.price_history
        if len(p) < 2:
            return []
        return [(p[i] - p[i - 1]) / p[i - 1] for i in range(1, len(p))]

    def to_dataframe(self):
        """Convenience for Module 4/5 analysis — requires pandas."""
        import pandas as pd
        return pd.DataFrame([{
            "round": r.round_number,
            "price": r.price,
            "best_bid": r.best_bid,
            "best_ask": r.best_ask,
            "spread": r.spread,
            "num_orders": r.num_orders,
            "num_trades": r.num_trades,
        } for r in self.rounds_log])
