import { ApiError, messageFrom } from '@/lib/api'

// Mirrors the backend limits; the server still checks everything itself.
export const MAX_FILE_MB = 25
export const MAX_FILES = 20
export const ALLOWED = ['pdf', 'docx', 'xlsx', 'csv', 'md', 'txt']
export const ACCEPT = ALLOWED.map((ext) => `.${ext}`).join(',')

export type UploadResult = {
  accepted: { filename: string; document_id: string }[]
  skipped: { filename: string; reason: string; document_id: string | null }[]
  rejected: { filename: string; reason: string }[]
}

/** Why the file will be skipped, or null if it looks fine. */
export function validateFile(file: File): string | null {
  const dot = file.name.lastIndexOf('.')
  const ext = dot > 0 ? file.name.slice(dot + 1).toLowerCase() : ''
  if (!ALLOWED.includes(ext)) {
    return `${ext ? ext.toUpperCase() : 'Files without an extension'} isn't supported, so it will be skipped`
  }
  if (file.size === 0) return 'The file is empty, so it will be skipped'
  if (file.size > MAX_FILE_MB * 1024 * 1024) {
    return `Larger than ${MAX_FILE_MB} MB, so it will be skipped`
  }
  return null
}

function parseBody(text: string): unknown {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text // e.g. an HTML 502 page from nginx
  }
}

/** POST one file with upload progress (fetch can't report upload progress). */
export function uploadFile(file: File, onProgress: (fraction: number) => void): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', new URL('/api/documents', window.location.origin))
    xhr.withCredentials = true
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    xhr.onload = () => {
      const body = parseBody(xhr.responseText)
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as UploadResult)
      else reject(new ApiError(xhr.status, messageFrom(body, `Upload failed (${xhr.status})`), body))
    }
    xhr.onerror = () => reject(new Error('Network error'))

    const form = new FormData()
    form.append('files', file)
    xhr.send(form)
  })
}
