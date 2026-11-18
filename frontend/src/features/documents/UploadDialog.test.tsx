import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UploadDialog } from './UploadDialog'

const file = (name: string) => new File(['%PDF-1.7'], name)

function openAndPick(files: File[]) {
  fireEvent.click(screen.getByRole('button', { name: /upload files/i }))
  const input = document.getElementById('upload-input') as HTMLInputElement
  fireEvent.change(input, { target: { files } })
}

describe('UploadDialog', () => {
  it('marks bad files and sends only the good ones', () => {
    const onUpload = vi.fn()
    render(<UploadDialog onUpload={onUpload} />)

    openAndPick([file('notes.pdf'), file('cage.png')])

    expect(screen.getByText(/PNG isn't supported, so it will be skipped/)).toBeInTheDocument()
    expect(screen.getByText('1 ready · 1 skipped')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Upload 1 file' }))
    expect(onUpload).toHaveBeenCalledWith([expect.objectContaining({ name: 'notes.pdf' })])
  })

  it('removes a staged file with its button', () => {
    render(<UploadDialog onUpload={vi.fn()} />)
    openAndPick([file('a.pdf'), file('b.pdf')])

    fireEvent.click(screen.getByRole('button', { name: 'Remove a.pdf' }))

    expect(screen.queryByText('a.pdf')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload 1 file' })).toBeEnabled()
  })
})
