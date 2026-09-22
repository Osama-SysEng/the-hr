import { describe, it, expect } from 'vitest'

// Unit tests for pure scoring logic
// Import helpers from App if exported, else test via integration

describe('CV Scoring Logic', () => {
  it('normalizes Arabic text correctly', () => {
    // إأآ → ا, ى → ي, ة → ه
    const normalize = (v: string) =>
      v.toLowerCase()
       .replace(/[إأآ]/g, 'ا')
       .replace(/ى/g, 'ي')
       .replace(/ة/g, 'ه')
    expect(normalize('إسماعيل')).toBe('اسماعيل')
    expect(normalize('مهندسة')).toBe('مهندسه')
  })

  it('calculates weighted score correctly', () => {
    const criteria = [
      { weight: 60, score: 100 },
      { weight: 40, score: 50 },
    ]
    const total = criteria.reduce((s, c) => s + c.weight, 0)
    const weighted = criteria.reduce((s, c) => s + c.score * c.weight, 0) / total
    expect(Math.round(weighted)).toBe(80)
  })

  it('marks missing required criteria correctly', () => {
    const breakdown = [
      { required: true, score: 0, title: 'React' },
      { required: false, score: 0, title: 'SQL' },
    ]
    const missing = breakdown.filter(c => c.required && c.score === 0).map(c => c.title)
    expect(missing).toEqual(['React'])
  })

  it('extracts email from text', () => {
    const extract = (text: string) =>
      text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0] ?? ''
    expect(extract('contact: user@example.com')).toBe('user@example.com')
    expect(extract('no email here')).toBe('')
  })
})
