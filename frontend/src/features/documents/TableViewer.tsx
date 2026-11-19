import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

import { documentKey } from './useDocument'

type Sheet = { name: string; rows: string[][]; truncated: boolean }

const isNumber = (value: string) => value !== '' && !Number.isNaN(Number(value))

export function TableViewer({ id }: { id: string }) {
  const [active, setActive] = useState(0)
  const { data, isPending, isError, error } = useQuery({
    queryKey: [...documentKey(id), 'table'],
    queryFn: () => api<{ sheets: Sheet[] }>(`/documents/${id}/table`),
    staleTime: Infinity,
    retry: false,
  })

  if (isPending) return <Skeleton className="m-5 h-40" />
  if (isError) {
    return (
      <p className="p-5 text-sm text-muted-foreground">
        {error.message} Try Extracted text or Open original.
      </p>
    )
  }

  const sheet = data.sheets[Math.min(active, data.sheets.length - 1)]
  const [header = [], ...body] = sheet?.rows ?? []
  // a column is numeric when every filled cell in it is a number
  const numeric = header.map((_, c) => {
    const values = body.map((row) => row[c] ?? '').filter((v) => v !== '')
    return values.length > 0 && values.every(isNumber)
  })

  return (
    <div className="flex flex-col">
      {data.sheets.length > 1 && (
        <div role="group" aria-label="Sheets" className="flex gap-1 overflow-x-auto border-b border-border px-3">
          {data.sheets.map((s, i) => (
            <button
              key={s.name}
              type="button"
              aria-pressed={i === active}
              onClick={() => setActive(i)}
              className={cn(
                'h-10 shrink-0 border-b-2 px-3 text-sm font-medium',
                i === active
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}

      {!sheet || sheet.rows.length === 0 ? (
        <p className="p-5 text-sm text-muted-foreground">This sheet is empty.</p>
      ) : (
        <div className="max-h-[680px] overflow-auto">
          <table className="w-max min-w-full border-collapse text-sm">
            <thead className="sticky top-0 z-10 bg-card">
              <tr>
                {header.map((cell, i) => (
                  <th
                    key={i}
                    scope="col"
                    className={cn(
                      'border-b border-border px-3 py-2 font-medium whitespace-nowrap text-muted-foreground',
                      numeric[i] ? 'text-right' : 'text-left',
                    )}
                  >
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, r) => (
                <tr key={r} className="border-b border-border/60 hover:bg-muted/40">
                  {header.map((_, c) => (
                    <td
                      key={c}
                      className={cn(
                        'px-3 py-1.5 whitespace-nowrap',
                        numeric[c] && 'text-right tabular-nums',
                      )}
                    >
                      {row[c] ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sheet?.truncated && (
        <p className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
          Showing the first 500 rows and 50 columns. Open the original for everything.
        </p>
      )}
    </div>
  )
}
