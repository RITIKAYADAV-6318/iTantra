const API_BASE = 'http://localhost:8000'

export async function runPipeline({ bitrateKbps, noiseLevel, mode }) {
  const res = await fetch(`${API_BASE}/run_pipeline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bitrate_kbps: bitrateKbps,
      noise_level: noiseLevel,
      mode,
    }),
  })
  if (!res.ok) {
    throw new Error(`Pipeline call failed: ${res.status}`)
  }
  return res.json()
}
