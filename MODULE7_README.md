# Module 7 — React Frontend & Backend API

## What's here

```
backend/
  __init__.py
  api.py            # FastAPI app — wraps core/ modules as REST endpoints
frontend/
  package.json
  vite.config.js
  index.html
  src/
    main.jsx
    App.jsx                        # main dashboard layout + controls
    index.css                      # design tokens (trading-terminal theme)
    api.js                         # fetch wrapper for the backend
    components/
      CandlestickChart.jsx         # custom SVG candlestick + volume
      PhaseDiagramHeatmap.jsx      # Module 5 sweep, rendered as a heatmap
      HysteresisChart.jsx          # Module 6 forward/reverse experiment
```

## Where to place these folders

Drop `backend/` and `frontend/` directly into your project root, alongside
your existing `core/`, `agents/`, `tests/` folders:

```
AG-Market/
├── core/
├── agents/
├── tests/
├── backend/     <- new
├── frontend/    <- new
├── main.py
└── requirements.txt   <- updated: uncomment fastapi/uvicorn/httpx, or use the new one provided
```

## Running it

**1. Backend** (from the project root, with your venv active):
```bash
pip install -r requirements.txt
uvicorn backend.api:app --reload --port 8000
```
Visit `http://localhost:8000/api/health` — should return `{"status": "ok"}`.
Interactive API docs: `http://localhost:8000/docs`.

**2. Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`.

Both need to be running at the same time — the frontend calls the backend
at `localhost:8000` (see `frontend/src/api.js` if you need to change the port).

## What it does

- **Population & run controls**: sliders for agent counts and trend-follower
  reaction sensitivity, feeding directly into `core/simulation_config.py`'s
  `SimulationConfig` — no simulation logic lives in the backend, it's a thin
  wrapper around the existing `core/` modules.
- **Price action panel**: real candlestick chart (custom SVG, not a library
  approximation) built from `core/candles.py`'s OHLCV aggregation, with the
  most recent candle subtly pulsing to suggest a live market.
- **Phase diagram panel**: runs Module 5's sweep on demand, renders the
  volatility heatmap.
- **Hysteresis panel**: runs Module 6's forward/reverse experiment on demand,
  plots price and applied sensitivity together with the pre/post comparison
  stats — this is your core novelty result, now visualized end to end.

## Known scope limits (documented, not hidden)

- **No live step-by-step order injection yet.** The project objective lists
  this as optional ("a human user can inject their own orders..."). The
  current backend runs a full simulation in one batch request. Adding live
  injection needs a stateful session (server holds one `OrderBook` + agent
  population between requests, stepping one round at a time) — a real
  architectural addition, not a small tweak, and a reasonable "next
  iteration" item rather than something to rush into this pass.
- **Phase diagram and hysteresis panels use fixed default parameters**
  in this first pass (matching the values from Modules 5/6's milestone
  checks). Exposing those as additional sliders is a small, safe follow-up
  once the core dashboard is confirmed working end to end on your machine.
