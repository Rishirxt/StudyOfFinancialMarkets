"""
Circuit breaker mechanism for the market simulation.

A circuit breaker is a regulatory halt mechanism that pauses trading
for N rounds if the price moves more than X% within a rolling window.
This is directly policy-relevant: real exchanges (NYSE, NASDAQ, crypto
exchanges) use them. The scientific question here is:

  Do circuit breakers reduce hysteresis, or just delay the same outcome?

The CircuitBreaker object is attached to the simulation and checked
at the start of each round. When triggered, all agents' decide() calls
are skipped and a placeholder "HALTED" record is logged.

Parameters:
  price_move_threshold_pct: % move that triggers a halt (e.g. 5.0 = 5%)
  lookback_window: how many rounds back to check the price move (default 5)
  halt_duration: how many rounds trading is suspended (default 3)
"""

from dataclasses import dataclass, field
import math


@dataclass
class CircuitBreakerState:
    """Mutable state tracked across rounds."""
    is_halted: bool = False
    halt_remaining: int = 0
    halt_count: int = 0
    total_halted_rounds: int = 0
    halt_events: list[dict] = field(default_factory=list)  # {round, trigger_price, pct_move}
    resume_events: list[dict] = field(default_factory=list)  # {round, resumed_price}


class CircuitBreaker:
    def __init__(
        self,
        price_move_threshold_pct: float = 5.0,
        lookback_window: int = 5,
        halt_duration: int = 3,
    ):
        if not math.isfinite(price_move_threshold_pct) or price_move_threshold_pct <= 0:
            raise ValueError("Circuit-breaker threshold must be finite and greater than zero")
        if lookback_window < 1:
            raise ValueError("Circuit-breaker lookback must be at least one round")
        if halt_duration < 1:
            raise ValueError("Circuit-breaker halt duration must be at least one round")
        self.threshold_pct = price_move_threshold_pct
        self.lookback_window = lookback_window
        self.halt_duration = halt_duration
        self.state = CircuitBreakerState()

    def check_and_update(self, round_number: int, price_history: list[float]) -> bool:
        """
        Called at the start of each round BEFORE agents decide.
        Returns True if trading is halted this round.

        If currently in a halt, counts down. If not halted, checks
        whether the price move over the lookback window exceeds the
        threshold and triggers a new halt if so.
        """
        if self.state.is_halted:
            if self.state.halt_remaining > 0:
                self.state.halt_remaining -= 1
                self.state.total_halted_rounds += 1
                return True
            else:
                self.state.is_halted = False
                self.state.resume_events.append({"round": round_number, "resumed_price": price_history[-1]})
                return False

        # Check trigger condition
        if len(price_history) < self.lookback_window + 1:
            return False

        reference_price = price_history[-(self.lookback_window + 1)]
        current_price = price_history[-1]

        if reference_price <= 0:
            return False

        pct_move = abs((current_price - reference_price) / reference_price) * 100

        if pct_move >= self.threshold_pct:
            self.state.is_halted = True
            # The trigger round counts as the first halted round.
            self.state.halt_remaining = max(self.halt_duration - 1, 0)
            self.state.halt_count += 1
            self.state.total_halted_rounds += 1
            self.state.halt_events.append({
                "round": round_number,
                "trigger_price": current_price,
                "pct_move": round(pct_move, 3),
            })
            return True  # halted starting this round

        return False

    def reset(self):
        """Reset for a fresh experiment."""
        self.state = CircuitBreakerState()
