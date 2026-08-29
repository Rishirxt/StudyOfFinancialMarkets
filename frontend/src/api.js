const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

async function post(path, body) {
  const url = `${BASE_URL}${path}`
  console.log('[API] POST', url)
  console.log('[API] Request body', body)

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const responseText = await res.text()

  try {
    const json = responseText ? JSON.parse(responseText) : null
    console.log('[API] Response', { status: res.status, url, data: json })
    if (!res.ok) {
      throw new Error(`${path} failed (${res.status}): ${responseText}`)
    }
    return json
  } catch (error) {
    console.error('[API] Failed to parse response', { url, status: res.status, responseText })
    if (!res.ok) {
      throw new Error(`${path} failed (${res.status}): ${responseText}`)
    }
    throw error
  }
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

