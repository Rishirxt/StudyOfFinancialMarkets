/**
 * useMarketStream — React hook for the WebSocket live simulation stream.
 *
 * Opens a WebSocket to ws://localhost:8000/ws/simulate-live, sends the
 * simulation config as the first message, then listens for streaming
 * round-by-round market data and accumulates it into React state.
 *
 * Enhanced with:
 *   - Indian Rupee (₹) event messages & formatting
 *   - Live pause / resume buffering
 *   - Status indicators
 */

import { useState, useRef, useCallback, useEffect } from 'react'

const WS_URL = `ws://${window.location.hostname}:8000/ws/simulate-live`

export function useMarketStream() {
  const wsRef = useRef(null)
  const [status, setStatus] = useState('idle')
  const [isPaused, setIsPaused] = useState(false)
  const [priceHistory, setPriceHistory] = useState([])
  const [candles, setCandles] = useState([])
  const [orderBook, setOrderBook] = useState(null)
  const [agentWealth, setAgentWealth] = useState([])
  const [eventLog, setEventLog] = useState([])
  const [circuitBreaker, setCircuitBreaker] = useState(null)
  const [currentRound, setCurrentRound] = useState(0)
  const [totalRounds, setTotalRounds] = useState(0)
  const [latestPrice, setLatestPrice] = useState(100)
  const [priceDirection, setPriceDirection] = useState('flat')
  const [marginCallCount, setMarginCallCount] = useState(0)
  
  const prevPriceRef = useRef(100)
  const isPausedRef = useRef(false)
  const messageQueueRef = useRef([])
  const drainIntervalRef = useRef(null)

  const addEvent = useCallback((round, type, message) => {
    setEventLog(log => {
      const entry = { id: `${round}-${type}-${Date.now()}-${Math.random()}`, round, type, message }
      return [entry, ...log].slice(0, 80)
    })
  }, [])

  const processMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'init': {
        setTotalRounds(msg.num_rounds)
        setLatestPrice(msg.starting_price)
        prevPriceRef.current = msg.starting_price
        setPriceHistory([{ round: 0, price: msg.starting_price }])
        setStatus('running')
        addEvent(0, 'init', `🇮🇳 NSE/BSE Simulator Session opened. ${msg.num_rounds} rounds, ${
          Object.entries(msg.agent_counts)
            .filter(([, v]) => v > 0)
            .map(([k, v]) => `${v} ${k.replace('_', ' ')}s`)
            .join(', ')
        }`)
        break
      }

      case 'round':
      case 'halt': {
        const price = msg.price
        const prev = prevPriceRef.current
        const dir = price > prev ? 'up' : price < prev ? 'down' : 'flat'
        prevPriceRef.current = price

        setPriceDirection(dir)
        setLatestPrice(price)
        setCurrentRound(msg.round)
        setOrderBook(msg.order_book)
        setAgentWealth(msg.agent_wealth || [])

        setPriceHistory(h => [...h, { round: msg.round, price }])

        if (msg.candle) {
          setCandles(c => [...c, msg.candle])
        }

        if (msg.circuit_breaker) {
          setCircuitBreaker(msg.circuit_breaker)
        }

        if (msg.type === 'halt') {
          setStatus('halted')
          if (msg.circuit_breaker?.halt_events?.length > 0) {
            const last = msg.circuit_breaker.halt_events[msg.circuit_breaker.halt_events.length - 1]
            addEvent(msg.round, 'circuit_breaker',
              `⚡ SEBI CIRCUIT FILTER HIT: ${last.pct_move.toFixed(1)}% price move. Trading suspended.`)
          }
        } else {
          setStatus('running')
        }

        if (msg.margin_call_agents && msg.margin_call_agents.length > 0) {
          setMarginCallCount(n => n + msg.margin_call_agents.length)
          addEvent(msg.round, 'margin_call',
            `🔴 MARGIN CALL: ${msg.margin_call_agents.length} agent(s) squared-off at ₹${price.toFixed(2)}`)
        }

        if (msg.num_trades >= 10) {
          const move = (((price - prev) / prev) * 100).toFixed(2)
          addEvent(msg.round, 'high_volume',
            `📊 Round ${msg.round}: ${msg.num_trades} fills @ ₹${price.toFixed(2)} (${dir === 'up' ? '+' : ''}${move}%)`)
        }
        break
      }

      case 'done': {
        setStatus('done')
        setCurrentRound(totalRounds || msg.total_rounds)
        addEvent(msg.total_rounds, 'done',
          `✅ Market Session Concluded. Final price ₹${msg.final_price.toFixed(2)} across ${msg.total_trades} trades.`)
        if (msg.circuit_breaker_summary?.halt_count > 0) {
          addEvent(msg.total_rounds, 'summary',
            `⚡ Circuit breaker triggered ${msg.circuit_breaker_summary.halt_count} time(s) during session.`)
        }
        if (wsRef.current) {
          wsRef.current.close()
        }
        break
      }

      case 'error': {
        setStatus('error')
        addEvent(0, 'error', `❌ Simulation Error: ${msg.message}`)
        if (wsRef.current) {
          wsRef.current.close()
        }
        break
      }

      default:
        break
    }
  }, [addEvent, totalRounds])

  // Pause / Resume drainage
  useEffect(() => {
    isPausedRef.current = isPaused
    if (!isPaused && messageQueueRef.current.length > 0) {
      if (!drainIntervalRef.current) {
        drainIntervalRef.current = setInterval(() => {
          if (isPausedRef.current) return
          if (messageQueueRef.current.length === 0) {
            clearInterval(drainIntervalRef.current)
            drainIntervalRef.current = null
            return
          }
          const nextMsg = messageQueueRef.current.shift()
          processMessage(nextMsg)
        }, 150)
      }
    } else if (isPaused && drainIntervalRef.current) {
      clearInterval(drainIntervalRef.current)
      drainIntervalRef.current = null
    }

    return () => {
      if (drainIntervalRef.current) {
        clearInterval(drainIntervalRef.current)
        drainIntervalRef.current = null
      }
    }
  }, [isPaused, processMessage])

  const pause = useCallback(() => {
    setIsPaused(true)
    isPausedRef.current = true
  }, [])

  const resume = useCallback(() => {
    setIsPaused(false)
    isPausedRef.current = false
  }, [])

  const stop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (drainIntervalRef.current) {
      clearInterval(drainIntervalRef.current)
      drainIntervalRef.current = null
    }
    messageQueueRef.current = []
    setIsPaused(false)
    isPausedRef.current = false
    setStatus('idle')
  }, [])

  const start = useCallback((config) => {
    if (wsRef.current) {
      wsRef.current.close()
    }
    if (drainIntervalRef.current) {
      clearInterval(drainIntervalRef.current)
      drainIntervalRef.current = null
    }
    messageQueueRef.current = []
    setIsPaused(false)
    isPausedRef.current = false

    // Reset all state
    setPriceHistory([])
    setCandles([])
    setOrderBook(null)
    setAgentWealth([])
    setEventLog([])
    setCircuitBreaker(null)
    setCurrentRound(0)
    setMarginCallCount(0)
    prevPriceRef.current = 100

    setStatus('connecting')

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify(config))
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (isPausedRef.current) {
        messageQueueRef.current.push(msg)
      } else {
        processMessage(msg)
      }
    }

    ws.onerror = () => {
      setStatus('error')
      addEvent(0, 'error', '❌ WebSocket connection error. Ensure backend is running on port 8000.')
    }

    ws.onclose = () => {
      wsRef.current = null
      setStatus(s => s === 'running' || s === 'connecting' || s === 'halted' ? 'idle' : s)
    }
  }, [addEvent, processMessage])

  return {
    status,
    isPaused,
    priceHistory,
    candles,
    orderBook,
    agentWealth,
    eventLog,
    circuitBreaker,
    currentRound,
    totalRounds,
    latestPrice,
    priceDirection,
    marginCallCount,
    pause,
    resume,
    start,
    stop,
  }
}
