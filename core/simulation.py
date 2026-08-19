"""
Simulation — the real round loop, replacing main.py's naive_clear()
placeholder. This is where Module 1's agents and Module 2's OrderBook
actually meet:

  each round:
    1. build a MarketState snapshot from current order book + price history
    2. ask every agent to decide() (in randomized order, so no agent
       type has a structural first-mover advantage every round)
    3. submit each resulting order to the OrderBook
    4. apply every resulting Trade back to the two agents via on_fill()
    5. determine the round's closing price and log everything

Reproducibility matters here because Module 5 (phase diagram) and
Module 6 (hysteresis) need to compare runs fairly — same seed must
produce the same price series every time.
"""

import random

from core.agent_factory import build_population
from core.market_state import MarketState
from core.order import Side
from core.order_book import OrderBook
from core.simulation_config import SimulationConfig
from core.simulation_result import RoundRecord, SimulationResult


class Simulation:
    def __init__(self, config: SimulationConfig, round_hook=None):
        """
        round_hook: optional callable(round_number) -> None, invoked at the
        start of every round before agents decide. Module 6 (hysteresis)
        uses this to mutate a shared AgentParams value (e.g. trend-follower
        reaction_sensitivity) according to a ramp schedule, while a SINGLE
        continuous order book and price history persist across the whole
        run — genuine path-dependence testing requires this continuity;
        independent runs per parameter value (as in Module 5's sweep)
        cannot show hysteresis by construction. Defaults to None so
        Modules 1-5 behavior is completely unchanged.
        """
        self.config = config
        self.round_hook = round_hook
        self.order_book = OrderBook()
        self.agents = build_population(config.agent_specs)
        self.agents_by_id = {a.agent_id: a for a in self.agents}

        # Agents (Fundamentalist/TrendFollower/NoiseTrader) call the
        # global `random` module directly inside decide(), rather than
        # taking an injected RNG. Seeding it globally here — instead of
        # only seeding a private self.rng used for shuffling — is what
        # actually makes an entire run reproducible for a given seed.
        # (seed=None reseeds from system entropy, same as unseeded random.)
        random.seed(config.seed)

    def run(self) -> SimulationResult:
        price_history = [self.config.starting_price]
        trades_log = []
        rounds_log = []

        for r in range(1, self.config.num_rounds + 1):
            if self.round_hook is not None:
                self.round_hook(r)

            market = MarketState(
                round_number=r,
                last_price=price_history[-1],
                price_history=price_history[:],
                best_bid=self.order_book.best_bid(),
                best_ask=self.order_book.best_ask(),
            )

            # Randomize decision order each round so no agent type gets a
            # structural first-mover advantage — important for fairness
            # once we start sweeping agent-mix ratios in Module 5/6.
            shuffled_agents = self.agents[:]
            random.shuffle(shuffled_agents)

            orders_this_round = 0
            trades_this_round = []

            for agent in shuffled_agents:
                order = agent.decide(market)
                if order is None:
                    continue
                order.round_submitted = r
                orders_this_round += 1

                fills = self.order_book.submit(order, r)
                for trade in fills:
                    buyer = self.agents_by_id[trade.buy_agent_id]
                    seller = self.agents_by_id[trade.sell_agent_id]
                    buyer.on_fill(Side.BUY, trade.quantity, trade.price)
                    seller.on_fill(Side.SELL, trade.quantity, trade.price)
                    trades_this_round.append(trade)

            trades_log.extend(trades_this_round)

            # Closing price for the round: last traded price if anything
            # traded, otherwise the book's mid-price (quotes moved even
            # without a trade), otherwise carry the last price forward
            # (a fully quiet round).
            if trades_this_round:
                new_price = trades_this_round[-1].price
            else:
                mid = self.order_book.mid_price()
                new_price = mid if mid is not None else price_history[-1]

            price_history.append(new_price)

            rounds_log.append(RoundRecord(
                round_number=r,
                price=new_price,
                best_bid=self.order_book.best_bid(),
                best_ask=self.order_book.best_ask(),
                spread=self.order_book.spread(),
                num_orders=orders_this_round,
                num_trades=len(trades_this_round),
            ))

        return SimulationResult(
            run_id=self.config.run_id,
            price_history=price_history,
            trades=trades_log,
            rounds_log=rounds_log,
            agents=self.agents,
            order_book=self.order_book,
        )