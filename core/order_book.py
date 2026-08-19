"""
OrderBook — the real bid/ask limit order book with price-time priority
matching. This is Module 2's core deliverable and the project's primary
methodological novelty: most phase-transition studies in this literature
use simplified Walrasian/equilibrium clearing, which assumes instant
re-balancing and can hide path-dependence by construction. A real order
book lets path-dependence (hysteresis, Module 6) actually surface if it
exists, because orders rest, queue, and get consumed over time instead
of clearing instantaneously.

Matching rules:
  - BUY orders match against the lowest-priced resting SELL orders.
  - SELL orders match against the highest-priced resting BUY orders.
  - At a given price level, orders are filled oldest-first (FIFO / time
    priority) — this is standard price-time priority, the same rule
    real exchanges use.
  - MARKET orders match immediately against whatever liquidity exists,
    walking through price levels until filled or the book runs dry.
  - LIMIT orders that cross the spread match immediately (same as a
    market order for the crossing portion); any unfilled remainder
    rests in the book at its limit price.

The book does NOT know about agent cash/holdings — it only matches
orders and returns Trade objects. The Simulation Engine (Module 3) is
responsible for applying trades back to agents via Agent.on_fill().
This separation keeps the book a pure, testable matching engine.
"""

from collections import deque

from core.order import Order, OrderType, Side
from core.trade import Trade


class OrderBook:
    def __init__(self):
        # price -> deque of resting Orders at that price, oldest first (time priority)
        self.bids: dict[float, deque[Order]] = {}
        self.asks: dict[float, deque[Order]] = {}

    # ------------------------------------------------------------------
    # Public read-only views
    # ------------------------------------------------------------------

    def best_bid(self) -> float | None:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> float | None:
        return min(self.asks.keys()) if self.asks else None

    def spread(self) -> float | None:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return None
        return round(ba - bb, 6)

    def mid_price(self) -> float | None:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is None or ba is None:
            return bb if bb is not None else ba
        return round((bb + ba) / 2, 6)

    def depth_at(self, side: Side, price: float) -> float:
        """Total resting quantity at a given price level, for a given side."""
        book = self.bids if side == Side.BUY else self.asks
        return sum(o.quantity for o in book.get(price, ()))

    def snapshot(self, levels: int = 5) -> dict:
        """A small serializable view of the book — used later by the
        Module 7 API to feed the React frontend's depth chart."""
        bid_prices = sorted(self.bids.keys(), reverse=True)[:levels]
        ask_prices = sorted(self.asks.keys())[:levels]
        return {
            "bids": [{"price": p, "quantity": self.depth_at(Side.BUY, p)} for p in bid_prices],
            "asks": [{"price": p, "quantity": self.depth_at(Side.SELL, p)} for p in ask_prices],
            "spread": self.spread(),
            "mid_price": self.mid_price(),
        }

    # ------------------------------------------------------------------
    # Order submission / matching
    # ------------------------------------------------------------------

    def submit(self, order: Order, round_number: int) -> list[Trade]:
        """
        Submit an order to the book. Returns the list of Trades generated
        (empty list if the order rested without matching, e.g. a
        non-crossing limit order).
        """
        if order.side == Side.BUY:
            return self._match_buy(order, round_number)
        else:
            return self._match_sell(order, round_number)

    def _match_buy(self, order: Order, round_number: int) -> list[Trade]:
        trades = []
        remaining = order.quantity

        while remaining > 1e-9:
            best_ask_price = self.best_ask()

            # Nothing to match against.
            if best_ask_price is None:
                break

            # Limit order that doesn't cross the spread -> stop matching, rest it.
            if order.order_type == OrderType.LIMIT and order.price < best_ask_price:
                break

            resting_queue = self.asks[best_ask_price]
            resting_order = resting_queue[0]  # oldest at this price level (time priority)

            fill_qty = min(remaining, resting_order.quantity)
            trades.append(Trade(
                buy_agent_id=order.agent_id,
                sell_agent_id=resting_order.agent_id,
                price=best_ask_price,          # trades execute at the RESTING order's price
                quantity=fill_qty,
                round_number=round_number,
                aggressor_side=Side.BUY,
            ))

            remaining -= fill_qty
            resting_order.quantity -= fill_qty

            if resting_order.quantity <= 1e-9:
                resting_queue.popleft()
                if not resting_queue:
                    del self.asks[best_ask_price]

        # Unfilled remainder: rest it if it's a LIMIT order, otherwise it's
        # simply unfilled (market orders don't rest — there was no liquidity).
        if remaining > 1e-9 and order.order_type == OrderType.LIMIT:
            order.quantity = remaining
            self.bids.setdefault(order.price, deque()).append(order)

        return trades

    def _match_sell(self, order: Order, round_number: int) -> list[Trade]:
        trades = []
        remaining = order.quantity

        while remaining > 1e-9:
            best_bid_price = self.best_bid()

            if best_bid_price is None:
                break

            if order.order_type == OrderType.LIMIT and order.price > best_bid_price:
                break

            resting_queue = self.bids[best_bid_price]
            resting_order = resting_queue[0]

            fill_qty = min(remaining, resting_order.quantity)
            trades.append(Trade(
                buy_agent_id=resting_order.agent_id,
                sell_agent_id=order.agent_id,
                price=best_bid_price,
                quantity=fill_qty,
                round_number=round_number,
                aggressor_side=Side.SELL,
            ))

            remaining -= fill_qty
            resting_order.quantity -= fill_qty

            if resting_order.quantity <= 1e-9:
                resting_queue.popleft()
                if not resting_queue:
                    del self.bids[best_bid_price]

        if remaining > 1e-9 and order.order_type == OrderType.LIMIT:
            order.quantity = remaining
            self.asks.setdefault(order.price, deque()).append(order)

        return trades

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def cancel_agent_orders(self, agent_id: str) -> int:
        """
        Remove all of an agent's resting orders from the book. Useful at
        the end of each round if you want a fresh book, or for agents
        that should not carry stale limit orders forward. Returns the
        number of orders removed.
        """
        removed = 0
        for book in (self.bids, self.asks):
            empty_prices = []
            for price, queue in book.items():
                before = len(queue)
                book[price] = deque(o for o in queue if o.agent_id != agent_id)
                removed += before - len(book[price])
                if not book[price]:
                    empty_prices.append(price)
            for price in empty_prices:
                del book[price]
        return removed

    def __repr__(self):
        return f"OrderBook(best_bid={self.best_bid()}, best_ask={self.best_ask()}, spread={self.spread()})"
