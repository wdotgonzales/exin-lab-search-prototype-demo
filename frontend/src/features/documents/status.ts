import type { DocumentStatus } from './useDocuments'

type StatusInfo = { label: string; hint: string; badge: string; dot: string }

/** "Search status": can the assistant use this file yet? (Uploading only stores it.) */
export const STATUS_INFO: Record<DocumentStatus, StatusInfo> = {
  pending: {
    label: 'Waiting to index',
    hint: 'Uploaded. It will be searchable in a moment.',
    badge: 'border-border text-muted-foreground',
    dot: 'bg-muted-foreground',
  },
  processing: {
    label: 'Indexing…',
    hint: 'Reading the file and preparing it for search.',
    badge: 'border-primary/40 bg-primary/15 text-primary',
    dot: 'bg-primary',
  },
  indexed: {
    label: 'Searchable',
    hint: 'The assistant can find and cite this file.',
    // mouse green from our palette
    badge: 'border-[#A9D1B9]/35 bg-[#A9D1B9]/12 text-[#A9D1B9]',
    dot: 'bg-[#A9D1B9]',
  },
  failed: {
    label: "Can't read file",
    hint: 'The file could not be prepared for search.',
    badge: 'border-destructive/40 bg-destructive/12 text-destructive',
    dot: 'bg-destructive',
  },
}

export const STATUS_ORDER: DocumentStatus[] = ['pending', 'processing', 'indexed', 'failed']
