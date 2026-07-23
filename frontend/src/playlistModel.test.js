import { describe, it, expect } from 'vitest'
import { normalizeBlocks, serializeBlocks } from './playlistModel.js'

const server = [
  { kind: 'video', video_id: 'v1' },
  { kind: 'slideshow', music_id: 'a1', photos: [{ photo_id: 'p1', duration_sec: 5 }] },
  { kind: 'slideshow', music_id: null, photos: [] },
]

describe('normalizeBlocks', () => {
  it('_key 를 블록/사진에 부여한다', () => {
    const n = normalizeBlocks(server)
    expect(n[0]._key).toBeTruthy()
    expect(n[1].photos[0]._key).toBeTruthy()
  })
  it('music_id 누락은 null 로', () => {
    const n = normalizeBlocks([{ kind: 'slideshow', photos: [] }])
    expect(n[0].music_id).toBe(null)
  })
})

describe('serializeBlocks', () => {
  it('_key 를 떼고 계약 형태로 되돌린다(왕복 일치)', () => {
    const out = serializeBlocks(normalizeBlocks(server))
    expect(out).toEqual(server)
  })
  it('duration_sec 을 숫자로 강제', () => {
    const n = normalizeBlocks([{ kind: 'slideshow', music_id: null, photos: [{ photo_id: 'p1', duration_sec: '7' }] }])
    expect(serializeBlocks(n)[0].photos[0].duration_sec).toBe(7)
  })
})
