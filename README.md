# Agent-Based Market Simulation — Hysteresis & Phase-Diagram Study

Simulated financial market where price emerges from the interaction of
fundamentalist, trend-following, and noise trader agents through a real
limit order book — no external market data or APIs required.

**Novelty:**
1. Tests whether the market exhibits **hysteresis** — does a crashed
   market recover to its original equilibrium, or settle into a new one,
   when the destabilizing parameter is reversed?
2. Uses a genuine **limit order book** instead of the simplified
   equilibrium price-clearing used in most prior phase-transition studies.

---

## 1. Prerequisites

- Python 3.11+ (uses modern type-hint syntax like `str | None`)
- pip

Check your version:
```bash
python3 --version
```

## 2. Setup from scratch

```bash
# 1. Unzip / clone the project, then cd into it
cd market_sim

# 2. Create and activate a virtual environment
python3 -m venv venv

# macOS / Linux:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

## 3. Verify the setup

**Important — always fully replace, never merge, when updating your local copy.**
If you're updating from an earlier version of this project, delete your existing
`market_sim` folder entirely and extract fresh, rather than copying new files on
top of an old folder. A partial overwrite can leave stale files mixed with new
ones, which is invisible until results silently diverge (e.g. inverted phase
diagram results, or unexpected agent IDs appearing in trade logs — both are
signs of a stale local file). Every module test's expected output in this
README was generated from a single, internally consistent version of the code —
if your output doesn't match, check for stale files before assuming a bug.

Run the Module 1 milestone check (confirms each agent type behaves correctly in isolation):
```bash
python -m tests.test_agents_module1
```
You should see `All Module 1 checks passed.` at the end.

Run the Module 2 milestone check (confirms the real limit order book matches correctly — price-time priority, partial fills, spread behavior, price impact):
```bash
python -m tests.test_order_book_module2
```
You should see `All Module 2 checks passed.` at the end.

Run the Module 3 milestone check (confirms the Simulation engine wires agents + order book correctly, is reproducible, and trades stay in sync with agent bookkeeping):
```bash
python -m tests.test_simulation_module3
```
You should see `All Module 3 checks passed.` at the end.

Run the Module 4 milestone check (validates against real S&P 500 data — confirms fat tails, honestly reports on volatility clustering):
```bash
python -m tests.test_validation_module4
```
You should see the real reference data confirm both stylized facts, and the simulated comparison print its results (see Module 4 findings below for the honest limitation this uncovered).

Run the end-to-end demo (now fully wired to the real Simulation engine and OrderBook — no placeholder logic remains):
```bash
python main.py
```
You should see a price series, spread narrowing over time as the book fills with resting liquidity, and a set of generated OHLCV candles.

## 4. Project structure

```
market_sim/
├── core/
│   ├── order.py              # Order, Side, OrderType data structures
│   ├── market_state.py       # Read-only market snapshot agents observe each round
│   ├── agent.py               # Base Agent class + AgentParams (shared config)
│   ├── order_book.py          # Real limit order book, price-time priority matching
│   ├── trade.py                # Trade result data structure
│   ├── candles.py              # OHLCV aggregation over trade windows
│   ├── simulation_config.py   # AgentSpec + SimulationConfig (reproducible experiment config)
│   ├── agent_factory.py        # Builds a population of agents from AgentSpecs
│   ├── simulation_result.py    # SimulationResult + RoundRecord (everything a run produced)
│   ├── simulation.py           # The round loop: agents + OrderBook -> price series
│   ├── batch_runner.py         # Runs many SimulationConfigs (used by Module 5/6 sweeps)
│   └── validation.py           # Stylized-fact checks: excess kurtosis, volatility clustering
├── data/
│   └── reference_sp500.csv     # Real daily S&P 500 closes, 2000-2019 (bundled, no live API)
├── agents/
│   ├── fundamentalist.py # Mean-reverts price toward fair value (stabilizing)
│   ├── trend_follower.py # Momentum-chasing (destabilizing force)
│   └── noise_trader.py   # Mix of limit (liquidity-providing) & market (liquidity-taking) orders
├── tests/
│   ├── test_agents_module1.py
│   ├── test_order_book_module2.py
│   ├── test_simulation_module3.py
│   └── test_validation_module4.py
├── main.py                # End-to-end demo — fully wired to the real Simulation engine
├── validation_report.png  # Generated comparison plots (real vs. simulated stylized facts)
├── requirements.txt
└── README.md
```

Run the Module 5 milestone check (small parameter sweep — confirms the phase diagram infrastructure works and produces a heatmap):
```bash
python -m tests.test_phase_diagram_module5
```
You should see 16 grid points run, and the extreme corner (12 trend-followers, high sensitivity) show clearly higher volatility than the calm corner (0 trend-followers, low sensitivity).

## 5. Module roadmap

| # | Module | Status |
|---|--------|--------|
| 1 | Agent Framework | ✅ Done |
| 2 | Order Book & Market Mechanism (real limit order book) | ✅ Done |
| 3 | Simulation Engine & Orchestration | ✅ Done |
| 4 | Validation Against Real Markets (stylized facts) | ✅ Done — see findings below |
| 5 | Phase Diagram Experiment | ✅ Done (small grid verified — see note below) |
| 6 | Hysteresis Experiment (core novelty) | Next |
| 4 | Validation Against Real Markets (stylized facts) | Pending |
| 5 | Phase Diagram Experiment | Pending |
| 6 | Hysteresis Experiment (core novelty) | Pending |
| 7 | React Frontend & Interactive Dashboard | Pending |
| 8 | Documentation & Write-up | Pending |

## 6. Module 4 findings (validation against real markets)

Reference data: bundled real daily S&P 500 closes, 2000-2019 (`data/reference_sp500.csv`,
sourced once and stored statically — no live API calls at runtime).

**Real reference data** (sanity check on the data itself): both stylized facts confirmed
strongly — excess kurtosis 8.64 (real markets have fat tails), and mean squared-return
autocorrelation (0.28) far exceeds the 95% significance band (±0.028), confirming genuine
volatility clustering.

**Simulated market, default config** (8 fundamentalists, 6 trend-followers, 8 noise traders):
- ✅ **Fat tails reproduced**: excess kurtosis 3.44 — fatter than a normal distribution, though
  weaker than the real market's 8.64 (expected — a small toy population won't reproduce
  decades of real crashes and regime changes 1:1).
- ❌ **Volatility clustering NOT reproduced**: squared-return autocorrelation (0.022) stays
  below raw-return autocorrelation (0.111) — the opposite of the real-data pattern. This was
  tested across a sweep of trend-follower ratios and reaction sensitivities (see
  `tests/test_validation_module4.py`) and holds throughout; more trend-following influence
  did not fix it, and in fact reduced kurtosis further.
- **Likely cause**: the academic models that reliably reproduce volatility clustering
  (Lux 1998; He & Li 2007) use an *endogenous strategy-switching* ("herding") mechanism —
  agents probabilistically switch between fundamentalist and chartist behavior based on
  relative recent profitability. This simulation uses a fixed population composition for
  the entire run, which appears insufficient on its own.
- **Status**: documented as a known limitation / candidate future extension, not silently
  patched over. This is a legitimate, reportable finding for the write-up (Module 8), not
  a bug to hide.

See `validation_report.png` for the full comparison (return distributions, squared-return
autocorrelation bar chart, simulated price series, kurtosis comparison).

## 7. Key design notes (carry these forward)

- `AgentParams.reaction_sensitivity` on `TrendFollower` is the primary
  dial used in the Module 5 phase diagram and the Module 6 hysteresis
  experiment (increase it past the instability threshold, then reverse it).
- Fundamentalists submit **limit** orders (patient, anchored near fair
  value); trend-followers and noise traders submit **market** orders
  (impulsive, cross the spread immediately). This distinction only
  matters once Module 2's real order book is in place — `main.py`'s
  current price mechanism is a placeholder and ignores order type.
- `main.py` is now fully wired to the real `Simulation` engine and
  `OrderBook` — no placeholder price mechanism remains.
- `OrderBook` is intentionally decoupled from agent cash/holdings — it
  only matches orders and returns `Trade` objects. `Simulation.run()`
  is what applies trades back to agents via `Agent.on_fill()`.
- Trades always execute at the **resting** order's price, not the
  incoming order's price — this is standard exchange behavior and
  matters for correctness of your price series.
- **Important fix from Module 3 testing**: the original `NoiseTrader`
  only submitted market orders, which meant an empty order book could
  never start trading (nothing to match against) — fundamentalists only
  quote when mispriced, and if the starting price equals fair value,
  nobody provides initial liquidity. `NoiseTrader` now mixes limit
  orders (providing liquidity) with market orders (taking it), matching
  its documented role as the baseline-liquidity agent type.
- **Reproducibility**: agents call the global `random` module directly
  inside `decide()`. `Simulation.__init__` seeds that global module from
  `config.seed`, not just a private RNG — this is what makes two runs
  with the same seed produce identical price series, which Module 5/6
  depend on for fair comparisons. Note this means `Simulation` runs are
  not safe to execute concurrently in the same process (they'd fight
  over the same global RNG state) — `batch_runner.py` runs them
  sequentially for exactly this reason.

## 8. Next step

Build Module 5 — the phase diagram experiment. Sweep trend-follower ratio and
reaction_sensitivity across a grid, define a quantitative instability metric, and
aggregate results into a 2D stability/instability heatmap. The Module 4 sweep code
(varying trend-follower count/sensitivity) is a useful starting point to generalize
into the full batch sweep infrastructure.
