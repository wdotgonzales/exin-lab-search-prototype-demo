import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function App() {
  const [health, setHealth] = useState<string>('Loading…')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setHealth(`${d.status} · pgvector ${d.pgvector}`))
      .catch(() => setHealth('API unreachable'))
  }, [])

  return (
    <main className="mx-auto max-w-3xl space-y-8 p-10">
      <div className="space-y-2">
        <p className="text-[11px] uppercase tracking-[0.14em] text-primary">01 / Foundations</p>
        <h1 className="font-serif text-5xl">Exin Lab Search</h1>
        <p className="text-muted-foreground">API: {health}</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Theme check</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="q">Search</Label>
            <Input id="q" placeholder="M-042 tumour imaging" />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button>Search</Button>
            <Button variant="outline">Upload files</Button>
            <Button variant="ghost">Clear filters</Button>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-xs">
            <span className="rounded-md border border-entity-mouse/35 bg-entity-mouse/15 px-2 py-1 text-entity-mouse">M-042</span>
            <span className="rounded-md border border-entity-virus/35 bg-entity-virus/15 px-2 py-1 text-entity-virus">V-017</span>
            <span className="rounded-md border border-entity-experiment/35 bg-entity-experiment/15 px-2 py-1 text-entity-experiment">EXP-007</span>
            <span className="rounded-md border border-entity-cohort/35 bg-entity-cohort/15 px-2 py-1 text-entity-cohort">C-07</span>
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
