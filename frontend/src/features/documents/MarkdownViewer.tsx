import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { Skeleton } from '@/components/ui/skeleton'

import { useDocumentContentText } from './useDocumentContent'

export default function MarkdownViewer({ id }: { id: string }) {
  const { data, isPending, isError, error } = useDocumentContentText(id)

  if (isPending) return <Skeleton className="m-5 h-40" />
  if (isError) return <p className="p-5 text-sm text-muted-foreground">{error.message}</p>

  return (
    <div className="max-h-[720px] overflow-y-auto p-6 text-sm leading-relaxed">
      {/* react-markdown never runs raw HTML from the file, so uploads can't inject markup */}
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mt-2 mb-3 font-serif text-3xl" {...p} />,
          h2: (p) => <h2 className="mt-6 mb-2 text-lg font-semibold" {...p} />,
          h3: (p) => <h3 className="mt-4 mb-2 font-semibold" {...p} />,
          p: (p) => <p className="mb-3" {...p} />,
          ul: (p) => <ul className="mb-3 list-disc pl-5" {...p} />,
          ol: (p) => <ol className="mb-3 list-decimal pl-5" {...p} />,
          li: (p) => <li className="mb-1" {...p} />,
          a: (p) => <a className="text-primary underline" target="_blank" rel="noreferrer" {...p} />,
          code: (p) => <code className="rounded bg-muted px-1 font-mono text-xs" {...p} />,
          pre: (p) => <pre className="mb-3 overflow-x-auto rounded-lg bg-muted p-3" {...p} />,
          blockquote: (p) => (
            <blockquote className="mb-3 border-l-2 border-border pl-3 text-muted-foreground" {...p} />
          ),
          table: (p) => (
            <div className="mb-3 overflow-x-auto">
              <table className="border-collapse text-left" {...p} />
            </div>
          ),
          th: (p) => <th className="border border-border bg-card px-3 py-1.5 font-medium" {...p} />,
          td: (p) => <td className="border border-border px-3 py-1.5" {...p} />,
        }}
      >
        {data}
      </Markdown>
    </div>
  )
}
