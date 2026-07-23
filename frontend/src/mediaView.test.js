import { describe, it, expect } from 'vitest'
import { typeEmoji, typeLabel, thumbGradient } from './mediaView.js'

describe('typeEmoji / typeLabel', () => {
  it('타입별 이모지', () => {
    expect(typeEmoji('video')).toBe('🎬')
    expect(typeEmoji('photo')).toBe('🖼')
    expect(typeEmoji('music')).toBe('🎵')
  })
  it('타입별 한글', () => {
    expect(typeLabel('video')).toBe('동영상')
    expect(typeLabel('photo')).toBe('사진')
    expect(typeLabel('music')).toBe('음악')
  })
})

describe('thumbGradient', () => {
  it('linear-gradient 문자열을 낸다', () => {
    expect(thumbGradient({ content_id: 'v1', media_type: 'video' })).toMatch(/^linear-gradient/)
  })
  it('같은 id면 항상 같은 값(안정적)', () => {
    const a = thumbGradient({ content_id: 'p3', media_type: 'photo' })
    const b = thumbGradient({ content_id: 'p3', media_type: 'photo' })
    expect(a).toBe(b)
  })
})
