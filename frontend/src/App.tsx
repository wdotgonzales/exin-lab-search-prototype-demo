import { useEffect, useState } from 'react'

type Health = {
  status: string
  database: string
  pgvector?: string
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then(async (res) => {
        setHealth(await res.json())
        if (!res.ok) setError(`HTTP ${res.status}`)
      })
      .catch((err) => setError(String(err)))
  }, [])

  return (
    <main style={{ fontFamily: 'sans-serif', padding: 24 }}>
      <h1>Exin Lab Search</h1>
      <p>Deployed automatically via github actions</p>
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      <pre>{health ? JSON.stringify(health, null, 2) : 'Loading…'}</pre>
    </main>
  )
}
