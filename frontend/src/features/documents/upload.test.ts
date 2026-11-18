import { describe, expect, it } from 'vitest'

import { MAX_FILE_MB, validateFile } from './upload'

const file = (name: string, size = 10) => {
  const f = new File(['x'], name)
  Object.defineProperty(f, 'size', { value: size })
  return f
}

describe('validateFile', () => {
  it('accepts the six supported types, any case', () => {
    for (const name of ['a.pdf', 'b.DOCX', 'c.xlsx', 'd.csv', 'e.md', 'f.txt']) {
      expect(validateFile(file(name))).toBeNull()
    }
  })

  it('flags unsupported types and missing extensions', () => {
    expect(validateFile(file('cage.png'))).toMatch("PNG isn't supported")
    expect(validateFile(file('notes'))).toMatch('Files without an extension')
  })

  it('flags empty and too-large files', () => {
    expect(validateFile(file('empty.md', 0))).toMatch('empty')
    expect(validateFile(file('big.pdf', MAX_FILE_MB * 1024 * 1024 + 1))).toMatch(`${MAX_FILE_MB} MB`)
  })
})
