"""Validated human orders routed through the simulation's real order book."""

import math

from agents.human_trader import HumanTrader
from core.agent import Agent
from core.order import Order, OrderType, Side
from core.order_book import OrderBook
from core.trade import Trade


class HumanOrderError(ValueError):
    """An order rejected before it reaches the market."""


class HumanOrderManager:
    def __init__(self, trader: HumanTrader, order_book: OrderBook, agents: dict[str, Agent]):
        self.trader = trader
        self.order_book = order_book
        self.agents = agents
        self.last_trades: list[Trade] = []

    def _open_commitments(self) -> tuple[float, float]:
        buy_cash = 0.0
        sell_quantity = 0.0
        for book in (self.order_book.bids, self.order_book.asks):
            for queue in book.values():
                for order in queue:
                    if order.agent_id != self.trader.agent_id:
                        continue
                    if order.side == Side.BUY:
                        buy_cash += order.quantity * order.price
                    else:
                        sell_quantity += order.quantity
        return buy_cash, sell_quantity

    def _market_buy_cost(self, quantity: float) -> float:
        remaining = quantity
        cost = 0.0
        for price in sorted(self.order_book.asks):
            for ask in self.order_book.asks[price]:
                fill = min(remaining, ask.quantity)
                cost += fill * price
                remaining -= fill
                if remaining <= 1e-9:
                    return cost
        # Market orders are allowed to partially fill when depth runs out.
        return cost

    def submit(
        self,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None,
        round_number: int,
        halted: bool = False,
    ) -> dict:
        if halted:
            raise HumanOrderError("Trading is halted by the circuit breaker")
        if side not in ("buy", "sell"):
            raise HumanOrderError("Side must be BUY or SELL")
        if order_type not in ("market", "limit"):
            raise HumanOrderError("Order type must be MARKET or LIMIT")
        if not math.isfinite(quantity) or quantity <= 0:
            raise HumanOrderError("Quantity must be finite and greater than zero")
        if order_type == "limit" and (price is None or not math.isfinite(price) or price <= 0):
            raise HumanOrderError("A limit order requires a finite price greater than zero")

        side_enum = Side(side)
        kind = OrderType(order_type)
        reserved_cash, reserved_shares = self._open_commitments()
        if side_enum == Side.BUY:
            available_cash = self.trader.cash - reserved_cash
            needed_cash = quantity * price if kind == OrderType.LIMIT else self._market_buy_cost(quantity)
            if needed_cash > available_cash + 1e-8:
                raise HumanOrderError("Insufficient available cash for this order")
        elif quantity > self.trader.holdings - reserved_shares + 1e-8:
            raise HumanOrderError("Insufficient uncommitted holdings for this sell order")

        order = Order(
            agent_id=self.trader.agent_id,
            side=side_enum,
            order_type=kind,
            quantity=quantity,
            price=price if kind == OrderType.LIMIT else None,
            round_submitted=round_number,
        )
        trades = self.order_book.submit(order, round_number)
        self.last_trades = trades
        for trade in trades:
            self.apply_trade(trade)
        filled_quantity = sum(trade.quantity for trade in trades)
        remaining_quantity = max(quantity - filled_quantity, 0.0)
        return {
            "order_id": order.order_id,
            "status": "filled" if filled_quantity >= quantity - 1e-9 else "partially_filled" if trades else "accepted",
            "fills": [self.trade_dict(trade) for trade in trades],
            "remaining_quantity": round(remaining_quantity, 8) if kind == OrderType.LIMIT else 0.0,
            "portfolio": self.portfolio(self.order_book.mid_price() or (price or 100.0)),
        }

    def apply_trade(self, trade: Trade) -> None:
        buyer = self.agents.get(trade.buy_agent_id)
        seller = self.agents.get(trade.sell_agent_id)
        if buyer is None or seller is None:
            raise RuntimeError("Trade references an unknown market participant")
        buyer.on_fill(Side.BUY, trade.quantity, trade.price, trade.round_number)
        seller.on_fill(Side.SELL, trade.quantity, trade.price, trade.round_number)
        if trade.buy_agent_id == self.trader.agent_id or trade.sell_agent_id == self.trader.agent_id:
            self.trader.record_trade(self.trade_dict(trade))

    def trade_dict(self, trade: Trade) -> dict:
        return {
            "trade_id": trade.trade_id,
            "round": trade.round_number,
            "side": "buy" if trade.buy_agent_id == self.trader.agent_id else "sell",
            "price": trade.price,
            "quantity": trade.quantity,
            "buy_agent_id": trade.buy_agent_id,
            "sell_agent_id": trade.sell_agent_id,
        }

    def portfolio(self, mark_price: float) -> dict:
        equity = self.trader.portfolio_value(mark_price)
        return {
            "cash": round(self.trader.cash, 2),
            "holdings": round(self.trader.holdings, 6),
            "portfolio_value": round(equity, 2),
            "pnl": round(equity - self.trader.params.initial_cash, 2),
            "trade_history": self.trader.trade_history[-100:],
        }
