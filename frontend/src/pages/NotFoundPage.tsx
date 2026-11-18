import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <section className="flex flex-col items-center gap-4 py-24 text-center">
      <h1 className="font-serif text-4xl">Page not found</h1>
      <p className="text-muted-foreground">The page you opened doesn't exist.</p>
      <Button asChild variant="outline"><Link to="/">Back to search</Link></Button>
    </section>
  )
}
