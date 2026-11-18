import { useHealth } from '@/features/health/useHealth'
import { Skeleton } from '@/components/ui/skeleton'

export function HomePage() {
  const health = useHealth()

  return (
    <section className="space-y-3">
      <p className="text-[11px] uppercase tracking-[0.14em] text-primary">Search</p>
      <h1 className="font-serif text-5xl">Search your lab data</h1>
      <div className="text-sm text-muted-foreground">
        {health.isPending && <Skeleton className="h-4 w-48" />}
        {health.isError && <span className="text-destructive">API unreachable: {health.error.message}</span>}
        {health.isSuccess && <span>API {health.data.status} · pgvector {health.data.pgvector}</span>}
      </div>
    </section>
  )
}
