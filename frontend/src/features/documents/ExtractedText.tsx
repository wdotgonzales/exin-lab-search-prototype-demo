import { Skeleton } from '@/components/ui/skeleton'

import { useDocumentText } from './useDocument'

/** The text the indexer sees, grouped by page or sheet. */
export function ExtractedText({ id }: { id: string }) {
  const { data, isPending, isError, error } = useDocumentText(id)

  if (isPending) {
    return (
      <div className="flex flex-col gap-3 p-5">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
      </div>
    )
  }
  if (isError) {
    return (
      <div className="flex flex-col gap-1 p-5 text-sm">
        <p>Preview not available for this file.</p>
        <p className="text-muted-foreground">{error.message} Use Open original instead.</p>
      </div>
    )
  }
  if (data.sections.length === 0) {
    return <p className="p-5 text-sm text-muted-foreground">No text was found in this file.</p>
  }
  return (
    <div className="flex max-h-[720px] flex-col gap-6 overflow-y-auto p-5">
      {data.sections.map((s, i) => (
        <section key={`${s.page ?? 0}-${i}`} className="flex flex-col gap-2">
          {(s.label || s.page) && (
            <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              {s.label ?? `Page ${s.page}`}
            </h3>
          )}
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{s.text}</p>
        </section>
      ))}
      {data.truncated && (
        <p className="text-xs text-muted-foreground">
          Showing the first 200,000 characters. Open the original for the rest.
        </p>
      )}
    </div>
  )
}
