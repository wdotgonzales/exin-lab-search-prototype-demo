import type { ReactNode } from 'react'

// [3] citation markers, and lab IDs such as M-042, V-019, EXP-007, C-07
const TOKEN = /(\[\d+\])|\b((?:EXP|M|V|C)-\d{2,4})\b/g

type Props = {
  text: string
  onCite: (n: number) => void
}

/** The answer as plain text, with clickable [n] markers and highlighted lab IDs. */
export function AnswerText({ text, onCite }: Props) {
  const parts: ReactNode[] = []
  let last = 0
  for (const match of text.matchAll(TOKEN)) {
    const index = match.index ?? 0
    if (index > last) parts.push(text.slice(last, index))
    if (match[1]) {
      const n = Number(match[1].slice(1, -1))
      parts.push(
        <button
          key={index}
          type="button"
          onClick={() => onCite(n)}
          aria-label={`Show source ${n}`}
          className="mx-0.5 inline-flex items-center rounded bg-primary/15 px-1.5 align-baseline text-xs font-medium text-primary hover:bg-primary/25"
        >
          {n}
        </button>,
      )
    } else {
      parts.push(
        <span
          key={index}
          className="rounded bg-emerald-500/15 px-1.5 py-px font-mono text-[13px] text-emerald-700 dark:text-emerald-300"
        >
          {match[2]}
        </span>,
      )
    }
    last = index + match[0].length
  }
  if (last < text.length) parts.push(text.slice(last))

  return <p className="text-sm leading-relaxed whitespace-pre-line">{parts}</p>
}
