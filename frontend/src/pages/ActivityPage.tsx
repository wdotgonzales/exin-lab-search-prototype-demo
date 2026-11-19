import { useSearchParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ACTIVITY_PAGE_SIZE,
  type ActivityGroup,
  type AuditEntry,
  useActivity,
} from '@/features/activity/useActivity'
import { useMe } from '@/features/auth/useAuth'
import { formatBytes, formatDate } from '@/features/documents/format'
import { Pagination } from '@/features/documents/Pagination'
import { cn } from '@/lib/utils'

const HIDE_ON_PHONES = 'hidden md:table-cell'

const GROUPS: { value: ActivityGroup | null; label: string }[] = [
  { value: null, label: 'All' },
  { value: 'signins', label: 'Sign-ins' },
  { value: 'uploads', label: 'Uploads' },
  { value: 'deletes', label: 'Deletes' },
  { value: 'accounts', label: 'Accounts' },
]

const BADGE = 'inline-flex h-6 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium whitespace-nowrap'
const ACTIONS: Record<string, { label: string; tone: string }> = {
  'user.login': { label: 'Signed in', tone: 'border-sky-400/35 bg-sky-400/10 text-sky-200' },
  'user.login_failed': { label: 'Failed sign-in', tone: 'border-red-400/40 bg-red-400/10 text-red-300' },
  'user.created': { label: 'Created an account', tone: 'border-border bg-muted/40 text-foreground/80' },
  'document.upload': { label: 'Uploaded a file', tone: 'border-emerald-300/35 bg-emerald-300/10 text-emerald-200' },
  'document.delete': { label: 'Deleted a file', tone: 'border-primary/40 bg-primary/15 text-primary' },
  'document.reindex': { label: 'Re-indexed a file', tone: 'border-border bg-muted/40 text-foreground/80' },
  'source.sync': { label: 'Synced a source', tone: 'border-border bg-muted/40 text-foreground/80' },
}

function details(entry: AuditEntry): string {
  const m = entry.metadata
  if (entry.action === 'user.login_failed') return entry.actor_known ? 'Known email' : 'Unknown email'
  if (entry.action === 'user.created') return typeof m.role === 'string' ? `Role: ${m.role}` : ''
  const parts: string[] = []
  if (typeof m.file_type === 'string') parts.push(m.file_type.toUpperCase())
  if (typeof m.size_bytes === 'number') parts.push(formatBytes(m.size_bytes))
  return parts.join(' · ')
}

function who(entry: AuditEntry): string {
  if (entry.actor_email) return entry.actor_email
  return entry.action === 'user.created' ? 'Command line' : '—'
}

export function ActivityPage() {
  const { data: me } = useMe()
  const isAdmin = me?.role === 'admin'
  const [params, setParams] = useSearchParams()
  const group = (GROUPS.find((g) => g.value === params.get('group'))?.value ?? null) as ActivityGroup | null
  const page = Math.max(1, Number(params.get('page')) || 1)
  const { data, isPending, isError, refetch, isRefetching } = useActivity(group, page, isAdmin)

  const setView = (next: { group?: ActivityGroup | null; page?: number }) =>
    setParams((prev) => {
      const out = new URLSearchParams(prev)
      if ('group' in next) {
        if (next.group) out.set('group', next.group)
        else out.delete('group')
        out.delete('page')
      }
      if (next.page && next.page > 1) out.set('page', String(next.page))
      else if (next.page) out.delete('page')
      return out
    })

  if (me && !isAdmin) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="font-serif text-4xl">Admins only</h1>
        <p className="text-sm text-muted-foreground">The activity history is available to lab admins.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs tracking-[0.14em] text-primary uppercase">Activity</p>
        <h1 className="font-serif text-5xl leading-tight">Activity history</h1>
        <p className="text-sm text-muted-foreground">
          Who signed in, uploaded or deleted what, and when. Entries can&apos;t be edited or removed.
        </p>
      </div>

      <section aria-label="Activity" className="overflow-hidden rounded-xl border border-border">
        <div className="flex flex-wrap items-center gap-3 border-b border-border bg-card/40 px-4 py-3">
          <div role="group" aria-label="Show" className="flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1">
            {GROUPS.map((g) => (
              <button
                key={g.label}
                type="button"
                aria-pressed={group === g.value}
                onClick={() => setView({ group: g.value })}
                className={cn(
                  'h-8 rounded-md px-3 text-sm font-medium',
                  group === g.value ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {g.label}
              </button>
            ))}
          </div>
          {data && (
            <span className="ml-auto text-sm text-muted-foreground">
              {data.total} {data.total === 1 ? 'entry' : 'entries'}
            </span>
          )}
        </div>

        {isPending ? (
          <div className="flex flex-col gap-3 p-4" aria-label="Loading activity">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center gap-3 px-4 py-12 text-center text-sm text-muted-foreground">
            <p>We couldn&apos;t load the activity history.</p>
            <Button variant="outline" onClick={() => refetch()} disabled={isRefetching}>
              {isRefetching ? 'Retrying…' : 'Retry'}
            </Button>
          </div>
        ) : data.items.length === 0 ? (
          <p className="px-4 py-12 text-center text-sm text-muted-foreground">Nothing recorded yet.</p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Who</TableHead>
                  <TableHead>What</TableHead>
                  <TableHead className={HIDE_ON_PHONES}>File or account</TableHead>
                  <TableHead className={HIDE_ON_PHONES}>Details</TableHead>
                  <TableHead className={HIDE_ON_PHONES}>From (IP)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((entry) => {
                  const action = ACTIONS[entry.action] ?? { label: entry.action, tone: 'border-border' }
                  const failed = entry.action === 'user.login_failed'
                  return (
                    <TableRow key={entry.id} className={cn(failed && 'bg-red-400/5')}>
                      <TableCell className="whitespace-nowrap text-muted-foreground">
                        {formatDate(entry.created_at)}
                      </TableCell>
                      <TableCell className={cn('max-w-56 truncate', failed && 'text-red-300')}>
                        {who(entry)}
                      </TableCell>
                      <TableCell>
                        <span className={cn(BADGE, action.tone)}>{action.label}</span>
                      </TableCell>
                      <TableCell className={cn(HIDE_ON_PHONES, 'max-w-72 truncate font-mono text-xs')}>
                        {entry.target_label ?? '—'}
                      </TableCell>
                      <TableCell className={cn(HIDE_ON_PHONES, 'text-muted-foreground')}>
                        {details(entry) || '—'}
                      </TableCell>
                      <TableCell className={cn(HIDE_ON_PHONES, 'font-mono text-xs text-muted-foreground')}>
                        {entry.ip_address ?? '—'}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
            <Pagination
              page={page}
              pageSize={ACTIVITY_PAGE_SIZE}
              total={data.total}
              onChange={(p) => setView({ page: p })}
            />
          </>
        )}
      </section>
    </div>
  )
}
