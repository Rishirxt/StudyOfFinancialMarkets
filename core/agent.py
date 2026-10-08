"""
Base Agent class.

Every trader type (fundamentalist, trend-follower, noise trader, and
eventually a human-controlled agent for Module 7) implements the same
interface: given the current MarketState, decide() returns an Order or
None (meaning "sit this round out").

This shared interface is what lets the Simulation Engine (Module 3) treat
every agent identically, regardless of the decision logic inside it.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import random

from core.market_state import MarketState
from core.order import Order


@dataclass
class AgentParams:
    """
    Shared tunable knobs. Not every agent uses every field — subclasses
    just read what's relevant to them. Centralizing them here makes the
    Module 5/6 parameter sweeps straightforward (one config object per agent).
    """
    initial_cash: float = 10_000.0
    initial_holdings: float = 0.0
    aggressiveness: float = 1.0       # scales order size / reaction strength
    reaction_sensitivity: float = 1.0  # how strongly the agent reacts to signals
    randomness: float = 0.0           # noise injected into decisions (0 = none)


class Agent(ABC):
    def __init__(self, agent_id: str, params: AgentParams | None = None, rng: random.Random | None = None):
        self.agent_id = agent_id
        self.params = params or AgentParams()
        self.cash = self.params.initial_cash
        self.holdings = self.params.initial_holdings
        self.rng = rng or random.Random()

    @abstractmethod
    def decide(self, market: MarketState) -> Order | None:
        """
        Look at the market state and return an Order to submit, or None
        to sit this round out. Must NOT mutate `market` — it's read-only.
        """
        raise NotImplementedError

    def on_fill(self, side, quantity: float, price: float, round_number: int | None = None) -> None:
        """
        Called by the order book / simulation engine when one of this
        agent's orders executes, so cash/holdings stay in sync.
        Module 2 wires this up properly; default bookkeeping lives here
        so every agent gets it for free.
        """
        from core.order import Side  # local import avoids a circular import
        if side == Side.BUY:
            self.cash -= quantity * price
            self.holdings += quantity
        else:
            self.cash += quantity * price
            self.holdings -= quantity

    def portfolio_value(self, mark_price: float) -> float:
        return self.cash + self.holdings * mark_price

    def __repr__(self):
        return f"{self.__class__.__name__}({self.agent_id}, cash={self.cash:.1f}, holdings={self.holdings:.2f})"
