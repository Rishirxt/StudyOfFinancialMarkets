const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

async function post(path, body) {
  const url = `${BASE_URL}${path}`

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const responseText = await res.text()

  try {
    const json = responseText ? JSON.parse(responseText) : null
    if (!res.ok) {
      throw new Error(`${path} failed (${res.status}): ${responseText}`)
    }
    return json
  } catch (error) {
    if (!res.ok) {
      throw new Error(`${path} failed (${res.status}): ${responseText}`)
    }
    throw error
  }
}

export function runSimulation(params) {
  return post('/api/simulate', params)
}

export function runLiveSimulation(params) {
  return post('/api/simulate-live', params)
}

export function runLeverageExperiment(params) {
  return post('/api/simulate-leverage', params)
}

export function runCircuitBreakerExperiment(params) {
  return post('/api/simulate-circuit-breaker', params)
}

export function fetchAgentWealth(params) {
  return post('/api/agent-wealth', params)
}

export function runPhaseDiagram(params) {
  return post('/api/phase-diagram', params)
}

export function runHysteresis(params) {
  return post('/api/hysteresis', params)
}

