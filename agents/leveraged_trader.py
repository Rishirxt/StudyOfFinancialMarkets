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

from core.agent import Agent, AgentParams
from core.market_state import MarketState
from core.order import Order, OrderType, Side


class LeveragedTrader(Agent):
    def __init__(
        self,
        agent_id: str,
        lookback: int = 5,
        leverage_ratio: float = 3.0,
        margin_call_threshold: float = 0.3,
        **kwargs,
    ):
        super().__init__(agent_id, **kwargs)
        self.lookback = lookback
        self.leverage_ratio = leverage_ratio
        self.margin_call_threshold = margin_call_threshold
        self.initial_equity = self.params.initial_cash
        self.in_margin_call = False

    def _equity(self, mark_price: float) -> float:
        """Current equity = cash + holdings * price (can go negative)."""
        return self.cash + self.holdings * mark_price

    def _is_margin_called(self, mark_price: float) -> bool:
        """True when equity has fallen below the margin call threshold."""
        equity = self._equity(mark_price)
        return equity < self.initial_equity * self.margin_call_threshold

    def decide(self, market: MarketState) -> Order | None:
        mark = market.last_price

        # --- FORCED LIQUIDATION: margin call overrides everything ---
        if self._is_margin_called(mark) and self.holdings > 1e-6:
            self.in_margin_call = True
            # Dump all holdings at market — no negotiation
            qty = round(self.holdings, 2)
            return Order(
                agent_id=self.agent_id,
                side=Side.SELL,
                order_type=OrderType.MARKET,
                quantity=qty,
                round_submitted=market.round_number,
            )

        self.in_margin_call = False

        # --- NORMAL: trend-following with leverage amplification ---
        recent_returns = market.returns(self.lookback)
        if not recent_returns:
            return None

        momentum = sum(recent_returns) / len(recent_returns)
        if abs(momentum) < 1e-5:
            return None

        # Leveraged position sizing: use leverage_ratio to amplify normal sizing
        base_qty = abs(momentum) * self.params.reaction_sensitivity * 100 * self.leverage_ratio
        noise = 1.0 + random.uniform(-self.params.randomness, self.params.randomness)
        quantity = max(round(base_qty * noise, 2), 0.01)

        side = Side.BUY if momentum > 0 else Side.SELL

        # Don't buy if we'd blow past our leverage limit
        if side == Side.BUY:
            max_holdings_value = (self._equity(mark) * self.leverage_ratio)
            current_holdings_value = self.holdings * mark
            if current_holdings_value >= max_holdings_value:
                return None  # already at leverage cap, sit out

        return Order(
            agent_id=self.agent_id,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            round_submitted=market.round_number,
        )
