"""
Trend-follower (chartist) agent.

Ignores fair value entirely — buys what's been going up, sells what's
been going down. This is the destabilizing force: crank up the ratio
of trend-followers (or their reaction_sensitivity) and the market
becomes prone to momentum-driven bubbles/crashes. That parameter is
the other axis of the Module 5 phase diagram and the dial used to
push the market past the instability threshold in Module 6.
"""

import random

from core.agent import Agent
from core.market_state import MarketState
from core.order import Order, OrderType, Side


class TrendFollower(Agent):
    def __init__(self, agent_id: str, lookback: int = 5, **kwargs):
        super().__init__(agent_id, **kwargs)
        self.lookback = lookback

    def decide(self, market: MarketState) -> Order | None:
        recent_returns = market.returns(self.lookback)
        if not recent_returns:
            return None  # not enough history yet to detect a trend

        momentum = sum(recent_returns) / len(recent_returns)

        # Dead-flat trend isn't worth acting on.
        if abs(momentum) < 1e-5:
            return None

        # reaction_sensitivity is the key destabilizing dial: higher values
        # mean this agent piles on harder for the same observed trend.
        base_qty = abs(momentum) * self.params.reaction_sensitivity * 100

        noise = 1.0 + random.uniform(-self.params.randomness, self.params.randomness)
        quantity = max(round(base_qty * noise, 2), 0.01)

        # Buys into upward momentum, sells into downward momentum —
        # the defining (and destabilizing) chartist behaviour.
        side = Side.BUY if momentum > 0 else Side.SELL

        return Order(
            agent_id=self.agent_id,
            side=side,
            order_type=OrderType.MARKET,  # chases the price, doesn't wait patiently
            quantity=quantity,
            round_submitted=market.round_number,
        )
