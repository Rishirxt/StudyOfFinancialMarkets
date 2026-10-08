"""
Leveraged trend-follower agent with margin call mechanics.

This is the key agent for replicating 2008-style cascading liquidations.
Agents borrow to amplify their positions. When portfolio losses exceed
a margin threshold, they are force-liquidated — dumping holdings at
market price regardless of momentum signal. This is the independent
"scarring" mechanism that can produce genuine hysteresis even when
the basic trend-follower/fundamentalist model doesn't.

Margin call logic:
  - leverage_ratio: how many times their equity they can hold
    (e.g. 3.0 means they can hold $30k of stock with only $10k cash)
  - margin_call_threshold: fraction of initial equity below which
    forced liquidation is triggered (default 0.3 = 30%)

The cascading effect: if one leveraged agent dumps → price falls →
other leveraged agents' portfolio values fall → more margin calls →
more dumping → textbook liquidation spiral.
"""

import random
import math
from enum import Enum

from core.agent import Agent, AgentParams
from core.market_state import MarketState
from core.order import Order, OrderType, Side


class TraderStatus(str, Enum):
    ACTIVE = "active"
    MARGIN_CALL = "margin_call"
    LIQUIDATING = "liquidating"
    BANKRUPT = "bankrupt"


class LeveragedTrader(Agent):
    def __init__(
        self,
        agent_id: str,
        lookback: int = 5,
        leverage_ratio: float = 3.0,
        margin_call_threshold: float = 0.3,
        allow_short_selling: bool = False,
        initial_mark_price: float = 100.0,
        **kwargs,
    ):
        if leverage_ratio <= 0 or not math.isfinite(leverage_ratio):
            raise ValueError("Leverage ratio must be finite and greater than zero")
        if not 0 < margin_call_threshold < 1 or not math.isfinite(margin_call_threshold):
            raise ValueError("Margin-call threshold must be between zero and one")
        super().__init__(agent_id, **kwargs)
        self.lookback = lookback
        self.leverage_ratio = leverage_ratio
        self.margin_call_threshold = margin_call_threshold
        self.allow_short_selling = allow_short_selling
        if initial_mark_price <= 0 or not math.isfinite(initial_mark_price):
            raise ValueError("Initial mark price must be finite and greater than zero")
        self.initial_equity = self.params.initial_cash + self.params.initial_holdings * initial_mark_price
        self.in_margin_call = False
        self.status = TraderStatus.ACTIVE
        self.margin_call_round: int | None = None
        self.liquidation_round: int | None = None
        self.bankruptcy_round: int | None = None
        self.liquidation_quantity = 0.0
        self.liquidation_notional = 0.0
        self.max_equity = self.initial_equity
        self.events: list[dict] = []
        self._last_mark = initial_mark_price

    @property
    def drawdown(self) -> float:
        equity = self._equity(self._last_mark)
        return max(0.0, (self.max_equity - equity) / self.max_equity) if self.max_equity > 0 else 0.0

    def update_risk(self, round_number: int, mark_price: float, order_book=None) -> None:
        self._last_mark = mark_price
        equity = self._equity(mark_price)
        self.max_equity = max(self.max_equity, equity)
        if self.status == TraderStatus.BANKRUPT:
            if order_book is not None:
                order_book.cancel_agent_orders(self.agent_id)
            return
        if equity <= 0:
            self.status = TraderStatus.BANKRUPT
            self.bankruptcy_round = round_number
            self.events.append({"type": "bankruptcy", "round": round_number, "equity": equity})
            if order_book is not None:
                order_book.cancel_agent_orders(self.agent_id)
            return
        if self.status == TraderStatus.ACTIVE and equity < self.initial_equity * self.margin_call_threshold:
            self.status = TraderStatus.MARGIN_CALL
            self.in_margin_call = True
            self.margin_call_round = round_number
            self.events.append({"type": "margin_call", "round": round_number, "equity": equity})
            self.status = TraderStatus.LIQUIDATING
            self.liquidation_round = round_number

    def _equity(self, mark_price: float) -> float:
        """Current equity = cash + holdings * price (can go negative)."""
        return self.cash + self.holdings * mark_price

    def _is_margin_called(self, mark_price: float) -> bool:
        """True when equity has fallen below the margin call threshold."""
        equity = self._equity(mark_price)
        return equity < self.initial_equity * self.margin_call_threshold

    def decide(self, market: MarketState) -> Order | None:
        mark = market.last_price
        self.update_risk(market.round_number, mark)
        if self.status == TraderStatus.BANKRUPT:
            # Bankruptcy blocks new strategy orders. A forced close-out is the
            # sole exception and is retried while a long position remains.
            if self.holdings > 1e-6:
                return Order(self.agent_id, Side.SELL, OrderType.MARKET, self.holdings,
                             round_submitted=market.round_number)
            return None

        # --- FORCED LIQUIDATION: margin call overrides everything ---
        if self.status == TraderStatus.LIQUIDATING and self.holdings > 1e-6:
            # Dump all holdings at market — no negotiation
            qty = self.holdings
            return Order(
                agent_id=self.agent_id,
                side=Side.SELL,
                order_type=OrderType.MARKET,
                quantity=qty,
                round_submitted=market.round_number,
            )

        if self.status == TraderStatus.LIQUIDATING:
            return None

        # --- NORMAL: trend-following with leverage amplification ---
        recent_returns = market.returns(self.lookback)
        if not recent_returns:
            return None

        momentum = sum(recent_returns) / len(recent_returns)
        if abs(momentum) < 1e-5:
            return None

        # Leveraged position sizing: use leverage_ratio to amplify normal sizing
        base_qty = abs(momentum) * self.params.reaction_sensitivity * 100 * self.leverage_ratio
        noise = 1.0 + self.rng.uniform(-self.params.randomness, self.params.randomness)
        quantity = max(round(base_qty * noise, 2), 0.01)

        side = Side.BUY if momentum > 0 else Side.SELL
        if side == Side.SELL and not self.allow_short_selling:
            quantity = min(quantity, max(self.holdings, 0.0))
            if quantity <= 1e-6:
                return None

        # Don't buy if we'd blow past our leverage limit
        if side == Side.BUY:
            max_holdings_value = max(self._equity(mark), 0.0) * self.leverage_ratio
            current_holdings_value = self.holdings * mark
            remaining_capacity = max_holdings_value - current_holdings_value
            if remaining_capacity <= 0:
                return None  # already at leverage cap, sit out
            quantity = min(quantity, remaining_capacity / mark)

        return Order(
            agent_id=self.agent_id,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            round_submitted=market.round_number,
        )

    def on_fill(self, side, quantity: float, price: float, round_number: int | None = None) -> None:
        super().on_fill(side, quantity, price)
        if side == Side.SELL and self.status in (TraderStatus.LIQUIDATING, TraderStatus.BANKRUPT):
            self.liquidation_quantity += quantity
            self.liquidation_notional += quantity * price
            event_round = round_number or self.liquidation_round or self.bankruptcy_round
            self.events.append({"type": "liquidation_fill", "round": event_round, "quantity": quantity, "price": price})
            if self.holdings <= 1e-6:
                self.holdings = max(self.holdings, 0.0)
                was_bankrupt = self.status == TraderStatus.BANKRUPT
                self.status = TraderStatus.BANKRUPT if was_bankrupt or self._equity(price) <= 0 else TraderStatus.ACTIVE
                self.in_margin_call = self.status in (TraderStatus.MARGIN_CALL, TraderStatus.LIQUIDATING)
                if self.status == TraderStatus.BANKRUPT:
                    if self.bankruptcy_round is None:
                        self.bankruptcy_round = event_round
                        self.events.append({"type": "bankruptcy", "round": self.bankruptcy_round, "equity": self._equity(price)})
