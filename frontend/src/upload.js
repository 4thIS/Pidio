// src/upload.js — 청크 업로드 클라이언트.
// 백엔드(Task 7.2): POST /api/upload/init → PUT /api/upload/{id}/chunk?index=N → POST /api/upload/{id}/complete
import { api, ApiError } from './api.js'

export const CHUNK_SIZE = 4 * 1024 * 1024 // 4MB

const VIDEO_EXT = ['mp4', 'mkv', 'mov', 'avi', 'm4v', 'webm']
const PHOTO_EXT = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
const MUSIC_EXT = ['mp3', 'flac', 'wav', 'm4a', 'aac', 'ogg']

/** 파일명 확장자로 미디어 타입 판별. 모르면 null. */
export function mediaTypeOf(filename) {
  const ext = String(filename).split('.').pop()?.toLowerCase() || ''
  if (VIDEO_EXT.includes(ext)) return 'video'
  if (PHOTO_EXT.includes(ext)) return 'photo'
  if (MUSIC_EXT.includes(ext)) return 'music'
  return null
}

/** size 를 chunkSize 로 나눈 [start,end) 목록. 0바이트면 빈 청크 1개. */
export function chunkRanges(size, chunkSize = CHUNK_SIZE) {
  if (size <= 0) return [[0, 0]]
  const out = []
  for (let start = 0; start < size; start += chunkSize) {
    out.push([start, Math.min(start + chunkSize, size)])
  }
  return out
}

/**
 * 파일 하나를 청크 업로드.
 * @param {File} file
 * @param {(percent:number)=>void} onProgress
 * @returns {Promise<{content_id:string}>}
 */
export async function uploadFile(file, onProgress = () => {}) {
  const type = mediaTypeOf(file.name)
  if (!type) throw new ApiError('지원하지 않는 파일 형식입니다.', 415)

  const { upload_id } = await api('/api/upload/init', {
    method: 'POST',
    body: { filename: file.name, size: file.size, type },
  })

  const ranges = chunkRanges(file.size)
  for (let i = 0; i < ranges.length; i++) {
    const [start, end] = ranges[i]
    const res = await fetch(`/api/upload/${upload_id}/chunk?index=${i}`, {
      method: 'PUT',
      credentials: 'same-origin',
      body: file.slice(start, end),
    })
    if (!res.ok) throw new ApiError('청크 전송에 실패했습니다.', res.status)
    onProgress(Math.round(((i + 1) / ranges.length) * 100))
  }

  return api(`/api/upload/${upload_id}/complete`, { method: 'POST' })
}
