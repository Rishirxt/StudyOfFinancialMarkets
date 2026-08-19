"""
Fundamentalist agent.

Believes the asset has a "true" fair value and trades to push the price
toward it: buys when the market price is below fair value, sells when
above. This is the stabilizing force in the simulation — its strength
relative to trend-followers is one of the two axes in the Module 5
phase diagram.
"""

import random

from core.agent import Agent, AgentParams
from core.market_state import MarketState
from core.order import Order, OrderType, Side


class Fundamentalist(Agent):
    def __init__(self, agent_id: str, fair_value: float, params: AgentParams | None = None):
        super().__init__(agent_id, params)
        self.fair_value = fair_value

    def decide(self, market: MarketState) -> Order | None:
        mispricing = self.fair_value - market.last_price
        # No meaningful mispricing → no reason to trade this round.
        if abs(mispricing) < 1e-6:
            return None

        # Larger mispricing => larger, more confident order.
        # aggressiveness scales how hard this agent leans into the gap.
        base_qty = abs(mispricing) * self.params.aggressiveness

        # Small amount of noise so identical fundamentalists don't all
        # act in perfect lockstep every round.
        noise = 1.0 + random.uniform(-self.params.randomness, self.params.randomness)
        quantity = max(round(base_qty * noise, 2), 0.01)

        side = Side.BUY if mispricing > 0 else Side.SELL

        # Fundamentalists trade as limit orders anchored near fair value —
        # they're patient, not chasing the current price.
        limit_price = round(market.last_price + mispricing * 0.5, 2)

        return Order(
            agent_id=self.agent_id,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=limit_price,
            round_submitted=market.round_number,
        )
