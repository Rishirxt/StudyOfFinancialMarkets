"""
Module 2 milestone check.

Verifies the order book behaves like a real exchange:
  - Non-crossing limit orders rest in the book instead of trading.
  - A crossing order matches immediately at the resting order's price.
  - Price-time priority: oldest order at a price level fills first.
  - Partial fills work correctly (large incoming order eats through
    multiple resting orders, remainder rests if it's a limit order).
  - Spread narrows with more resting liquidity, widens with less.
  - A large market order visibly moves the price (walks the book).

Run with:  python -m tests.test_order_book_module2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.order import Order, OrderType, Side
from core.order_book import OrderBook


def check_resting_and_crossing():
    print("--- Resting vs. crossing orders ---")
    book = OrderBook()

    # A limit BUY below any ask should just rest, no trade.
    trades = book.submit(Order("a1", Side.BUY, OrderType.LIMIT, quantity=10, price=99.0), round_number=1)
    assert trades == [], "Non-crossing limit order should not trade"
    assert book.best_bid() == 99.0
    print(f"  resting buy@99      -> book: {book}")

    # A limit SELL above the bid should also just rest.
    trades = book.submit(Order("a2", Side.SELL, OrderType.LIMIT, quantity=10, price=101.0), round_number=1)
    assert trades == []
    assert book.best_ask() == 101.0
    print(f"  resting sell@101    -> book: {book}")
    print(f"  spread              -> {book.spread()} (expect 2.0)")
    assert book.spread() == 2.0

    # A crossing market BUY should trade immediately against the resting ask.
    trades = book.submit(Order("a3", Side.BUY, OrderType.MARKET, quantity=5), round_number=2)
    assert len(trades) == 1, "Market order should match the resting ask"
    assert trades[0].price == 101.0, "Trade should execute at the resting order's price"
    assert trades[0].quantity == 5
    print(f"  market buy qty=5    -> {trades[0]}")
    print(f"  remaining ask depth -> {book.depth_at(Side.SELL, 101.0)} (expect 5.0)")
    assert book.depth_at(Side.SELL, 101.0) == 5.0


def check_price_time_priority():
    print("\n--- Price-time priority (FIFO at same price) ---")
    book = OrderBook()

    # Two sell orders at the same price, submitted in order -> first one should fill first.
    book.submit(Order("seller_early", Side.SELL, OrderType.LIMIT, quantity=5, price=100.0), round_number=1)
    book.submit(Order("seller_late", Side.SELL, OrderType.LIMIT, quantity=5, price=100.0), round_number=1)

    trades = book.submit(Order("buyer", Side.BUY, OrderType.MARKET, quantity=5), round_number=2)
    assert trades[0].sell_agent_id == "seller_early", "Oldest order at the price level should fill first"
    print(f"  first fill went to  -> {trades[0].sell_agent_id} (expect seller_early)")

    trades2 = book.submit(Order("buyer2", Side.BUY, OrderType.MARKET, quantity=5), round_number=3)
    assert trades2[0].sell_agent_id == "seller_late"
    print(f"  second fill went to -> {trades2[0].sell_agent_id} (expect seller_late)")


def check_partial_fill_and_walk_the_book():
    print("\n--- Partial fills & walking the book ---")
    book = OrderBook()

    # Build a thin book: small qty at 100, more at 101, more at 102.
    book.submit(Order("s1", Side.SELL, OrderType.LIMIT, quantity=2, price=100.0), round_number=1)
    book.submit(Order("s2", Side.SELL, OrderType.LIMIT, quantity=3, price=101.0), round_number=1)
    book.submit(Order("s3", Side.SELL, OrderType.LIMIT, quantity=10, price=102.0), round_number=1)

    # A big market buy should walk through all three levels.
    trades = book.submit(Order("big_buyer", Side.BUY, OrderType.MARKET, quantity=8), round_number=2)
    prices_hit = [t.price for t in trades]
    print(f"  8-unit market buy walked prices -> {prices_hit} (expect [100.0, 101.0, 102.0])")
    assert prices_hit == [100.0, 101.0, 102.0]
    assert sum(t.quantity for t in trades) == 8
    print(f"  remaining depth at 102.0        -> {book.depth_at(Side.SELL, 102.0)} (expect 7.0)")
    assert book.depth_at(Side.SELL, 102.0) == 7.0


def check_spread_liquidity_relationship():
    print("\n--- Spread narrows with liquidity, widens with thin markets ---")

    thin_book = OrderBook()
    thin_book.submit(Order("b1", Side.BUY, OrderType.LIMIT, quantity=1, price=95.0), round_number=1)
    thin_book.submit(Order("s1", Side.SELL, OrderType.LIMIT, quantity=1, price=105.0), round_number=1)
    print(f"  thin book spread   -> {thin_book.spread()}")

    liquid_book = OrderBook()
    liquid_book.submit(Order("b1", Side.BUY, OrderType.LIMIT, quantity=1, price=99.0), round_number=1)
    liquid_book.submit(Order("b2", Side.BUY, OrderType.LIMIT, quantity=1, price=99.5), round_number=1)
    liquid_book.submit(Order("s1", Side.SELL, OrderType.LIMIT, quantity=1, price=100.5), round_number=1)
    liquid_book.submit(Order("s2", Side.SELL, OrderType.LIMIT, quantity=1, price=100.0), round_number=1)
    print(f"  liquid book spread -> {liquid_book.spread()}")

    assert liquid_book.spread() < thin_book.spread(), "More competitive resting orders should narrow the spread"


def check_large_order_moves_price():
    print("\n--- Large order visibly moves the price ---")
    book = OrderBook()
    for i, price in enumerate([100.0, 100.5, 101.0, 101.5, 102.0]):
        book.submit(Order(f"s{i}", Side.SELL, OrderType.LIMIT, quantity=2, price=price), round_number=1)

    mid_before = book.mid_price()
    trades = book.submit(Order("whale", Side.BUY, OrderType.MARKET, quantity=8), round_number=2)
    last_trade_price = trades[-1].price
    print(f"  best ask before -> 100.0, last fill price -> {last_trade_price}")
    assert last_trade_price > 100.0, "Large order should walk the book to higher prices"
    print(f"  book after      -> {book}")


if __name__ == "__main__":
    check_resting_and_crossing()
    check_price_time_priority()
    check_partial_fill_and_walk_the_book()
    check_spread_liquidity_relationship()
    check_large_order_moves_price()
    print("\nAll Module 2 checks passed.")
