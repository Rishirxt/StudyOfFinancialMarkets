"""
Candle — OHLCV aggregation over a window of simulation rounds.

Not a separate module in its own right — this is a small utility that
sits on top of Module 2's Trade log. The Simulation Engine (Module 3)
will feed it a stream of Trades; it groups them into fixed-size windows
(e.g. every 5 or 10 rounds = one candle) and produces standard OHLCV
bars, the same format any real trading chart uses.

Why this matters for the project specifically:
  - Module 4 (validation): volatility clustering is visually obvious on
    a candlestick chart (wide candles bunching together) in a way a
    plain line chart doesn't show well.
  - Module 6 (hysteresis): the forward crash + reverse recovery path is
    much clearer to a viewer as a candlestick chart than a line chart.
  - Module 7 (frontend): a candlestick chart is what a real trading UI
    looks like — stronger demo than a line chart.
"""

from dataclasses import dataclass, field

from core.trade import Trade


@dataclass
class Candle:
    window_start_round: int
    window_end_round: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    trade_count: int = 0

    def __repr__(self):
        return (f"Candle(rounds {self.window_start_round}-{self.window_end_round}, "
                f"O={self.open:.2f} H={self.high:.2f} L={self.low:.2f} C={self.close:.2f}, "
                f"vol={self.volume:.1f})")


def trades_to_candles(trades: list[Trade], window_size: int, last_known_price: float | None = None) -> list[Candle]:
    """
    Aggregate a chronological list of Trades into OHLCV candles, one per
    `window_size` rounds.

    `last_known_price` is used as the open/close/high/low for any window
    that had zero trades (a quiet window still needs a flat candle, the
    same way real markets show a flat bar when nothing traded) — pass in
    the most recent price before the trade log starts, e.g. the starting
    price of the simulation.
    """
    if not trades:
        return []

    trades = sorted(trades, key=lambda t: (t.round_number, t.trade_id))
    first_round = trades[0].round_number
    last_round = trades[-1].round_number

    candles = []
    carry_price = last_known_price if last_known_price is not None else trades[0].price

    window_start = (first_round - 1) - ((first_round - 1) % window_size) + 1
    while window_start <= last_round:
        window_end = window_start + window_size - 1
        window_trades = [t for t in trades if window_start <= t.round_number <= window_end]

        if window_trades:
            prices = [t.price for t in window_trades]
            candle = Candle(
                window_start_round=window_start,
                window_end_round=window_end,
                open=window_trades[0].price,
                high=max(prices),
                low=min(prices),
                close=window_trades[-1].price,
                volume=sum(t.quantity for t in window_trades),
                trade_count=len(window_trades),
            )
            carry_price = candle.close
        else:
            # No trades this window -> flat candle at the last known price,
            # same convention real exchanges use for illiquid periods.
            candle = Candle(
                window_start_round=window_start,
                window_end_round=window_end,
                open=carry_price,
                high=carry_price,
                low=carry_price,
                close=carry_price,
                volume=0.0,
                trade_count=0,
            )

        candles.append(candle)
        window_start = window_end + 1

    return candles
