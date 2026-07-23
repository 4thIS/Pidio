import { describe, it, expect } from 'vitest'
import { mediaTypeOf, chunkRanges, CHUNK_SIZE } from './upload.js'

describe('mediaTypeOf', () => {
  it('확장자로 타입 판별', () => {
    expect(mediaTypeOf('clip.mp4')).toBe('video')
    expect(mediaTypeOf('photo.JPG')).toBe('photo')
    expect(mediaTypeOf('song.mp3')).toBe('music')
  })
  it('점이 여러 개여도 마지막 확장자 기준', () => {
    expect(mediaTypeOf('2026.졸업식.mkv')).toBe('video')
  })
  it('모르는 형식은 null', () => {
    expect(mediaTypeOf('memo.txt')).toBe(null)
    expect(mediaTypeOf('noext')).toBe(null)
  })
})

describe('chunkRanges', () => {
  it('딱 나눠떨어질 때', () => {
    expect(chunkRanges(10, 5)).toEqual([[0, 5], [5, 10]])
  })
  it('나머지가 있을 때 마지막은 잘린다', () => {
    expect(chunkRanges(12, 5)).toEqual([[0, 5], [5, 10], [10, 12]])
  })
  it('청크보다 작으면 1개', () => {
    expect(chunkRanges(3, 5)).toEqual([[0, 3]])
  })
  it('0바이트도 청크 1개', () => {
    expect(chunkRanges(0, 5)).toEqual([[0, 0]])
  })
  it('기본 청크 크기는 4MB', () => {
    expect(CHUNK_SIZE).toBe(4 * 1024 * 1024)
  })
})
