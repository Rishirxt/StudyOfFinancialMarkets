"""
MarketState — the read-only snapshot of the market that every agent
sees before deciding on an action each round.

Keeping this as its own object (rather than passing the whole order book
around) means agents can never accidentally mutate market internals, and
it gives us one clean place to add fields (best bid/ask, spread, etc.)
as Module 2 builds out the real order book.
"""

from dataclasses import dataclass, field


@dataclass
class MarketState:
    round_number: int
    last_price: float
    price_history: list[float] = field(default_factory=list)

    # Populated once Module 2's real order book exists; harmless placeholders
    # for now so agents can already be written against the final interface.
    best_bid: float | None = None
    best_ask: float | None = None

    def price_at(self, rounds_ago: int) -> float | None:
        """Convenience: price N rounds ago, or None if not enough history."""
        if rounds_ago <= 0 or rounds_ago > len(self.price_history):
            return None
        return self.price_history[-rounds_ago]

    def returns(self, window: int) -> list[float]:
        """Simple returns over the last `window` rounds, oldest first."""
        prices = self.price_history[-(window + 1):]
        if len(prices) < 2:
            return []
        return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
