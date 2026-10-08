"""Portfolio and bookkeeping for the person controlling a live session."""

from core.agent import Agent, AgentParams
from core.market_state import MarketState
from core.order import Order


class HumanTrader(Agent):
    """A normal market participant whose orders are supplied interactively."""

    def __init__(self, agent_id: str = "human", params: AgentParams | None = None):
        super().__init__(agent_id, params or AgentParams(initial_cash=10_000.0))
        self.trade_history: list[dict] = []

    def decide(self, market: MarketState) -> Order | None:
        return None

    def record_trade(self, trade: dict) -> None:
        self.trade_history.append(trade)
