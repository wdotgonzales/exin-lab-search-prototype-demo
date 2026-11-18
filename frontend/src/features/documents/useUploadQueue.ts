import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { ApiError } from '@/lib/api'

import { uploadFile } from './upload'
import { documentsKey } from './useDocuments'

export type UploadState = 'waiting' | 'uploading' | 'done' | 'skipped' | 'rejected' | 'failed'

export type UploadItem = {
  key: string
  name: string
  size: number
  state: UploadState
  progress: number
  message?: string
  documentId?: string | null
}

export const FINISHED: UploadState[] = ['done', 'skipped', 'rejected', 'failed']

export function useUploadQueue() {
  const queryClient = useQueryClient()
  const [items, setItems] = useState<UploadItem[]>([])

  const update = useCallback((key: string, patch: Partial<UploadItem>) => {
    setItems((prev) => prev.map((item) => (item.key === key ? { ...item, ...patch } : item)))
  }, [])

  const clear = useCallback(() => setItems([]), [])

  const start = useCallback(
    async (files: File[]) => {
      const batch = files.map((file, i) => ({
        file,
        key: `${Date.now()}-${i}-${file.name}`,
      }))
      setItems((prev) => [
        ...prev.filter((item) => !FINISHED.includes(item.state)),
        ...batch.map(({ file, key }) => ({
          key,
          name: file.name,
          size: file.size,
          state: 'waiting' as const,
          progress: 0,
        })),
      ])

      for (const { file, key } of batch) {
        update(key, { state: 'uploading' })
        try {
          const result = await uploadFile(file, (progress) => update(key, { progress }))
          const [accepted] = result.accepted
          const [skipped] = result.skipped
          const [rejected] = result.rejected
          if (accepted) update(key, { state: 'done', progress: 1, documentId: accepted.document_id })
          else if (skipped)
            update(key, { state: 'skipped', message: skipped.reason, documentId: skipped.document_id })
          else update(key, { state: 'rejected', message: rejected?.reason ?? 'Not uploaded.' })
        } catch (err) {
          const message =
            err instanceof ApiError && err.status < 500 ? err.message : 'Upload failed. Try again.'
          update(key, { state: 'failed', message })
        }
        void queryClient.invalidateQueries({ queryKey: documentsKey })
      }
    },
    [queryClient, update],
  )

  return { items, start, clear }
}
