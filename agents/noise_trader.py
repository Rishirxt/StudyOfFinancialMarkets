"""
Noise trader agent.

Trades somewhat randomly, representing uninformed/retail order flow.
Provides baseline liquidity and volatility so the book isn't just two
deterministic strategies fighting each other — real markets always
have a layer of "trades that aren't information-driven", and this
is the standard third leg in these models (see Lux; De Long et al.).
"""

import random

from core.agent import Agent
from core.market_state import MarketState
from core.order import Order, OrderType, Side


class NoiseTrader(Agent):
    def __init__(
        self,
        agent_id: str,
        trade_probability: float = 0.3,
        limit_order_probability: float = 0.6,
        **kwargs,
    ):
        super().__init__(agent_id, **kwargs)
        self.trade_probability = trade_probability
        # Fraction of the time this agent provides resting liquidity
        # (limit order near the current price) rather than taking it
        # (market order). Without some limit-order flow, the book can
        # start empty and market orders from trend-followers/noise
        # traders have nothing to match against — noise traders are the
        # agent type meant to supply that baseline liquidity, matching
        # the "baseline liquidity" role described in the module docstring.
        self.limit_order_probability = limit_order_probability

    def decide(self, market: MarketState) -> Order | None:
        # Not every noise trader acts every round — mirrors real sporadic
        # retail order flow rather than constant activity.
        if random.random() > self.trade_probability:
            return None

        side = random.choice([Side.BUY, Side.SELL])
        base_qty = random.uniform(0.5, 2.0) * self.params.aggressiveness
        quantity = round(base_qty, 2)

        if random.random() < self.limit_order_probability:
            # Provide liquidity: rest a limit order a small random offset
            # from the current price, on the correct side of the market
            # (bid below price, ask above) so it doesn't immediately
            # cross and self-trade against nothing.
            offset = random.uniform(0.1, 1.5)
            if side == Side.BUY:
                price = round(market.last_price - offset, 2)
            else:
                price = round(market.last_price + offset, 2)
            return Order(
                agent_id=self.agent_id,
                side=side,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=max(price, 0.01),
                round_submitted=market.round_number,
            )

        # Otherwise take liquidity: cross the spread immediately.
        return Order(
            agent_id=self.agent_id,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            round_submitted=market.round_number,
        )
