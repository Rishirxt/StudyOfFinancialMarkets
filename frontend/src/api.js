const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${path} failed (${res.status}): ${text}`)
  }
  return res.json()
}

export function runSimulation(params) {
  return post('/api/simulate', params)
}

export function runPhaseDiagram(params) {
  return post('/api/phase-diagram', params)
}

export function runHysteresis(params) {
  return post('/api/hysteresis', params)
}

