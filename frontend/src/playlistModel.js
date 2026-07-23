// src/playlistModel.js — 플레이리스트 블록 모델 (순수 유틸, vitest 대상)
// 편집기 내부에선 드래그 안정성을 위해 _key(고유키)를 붙이고,
// 저장 시엔 _key 등 표시용 필드를 떼고 계약(video/slideshow) 형태로 직렬화한다.

let _seq = 0
const newKey = () => `k${++_seq}`

/** 서버 blocks → 편집기용(_key 부여, 필드 정규화). */
export function normalizeBlocks(blocks) {
  return (blocks || []).map((b) =>
    b.kind === 'video'
      ? { _key: newKey(), kind: 'video', video_id: b.video_id }
      : {
          _key: newKey(),
          kind: 'slideshow',
          music_id: b.music_id ?? null,
          photos: (b.photos || []).map((p) => ({
            _key: newKey(),
            photo_id: p.photo_id,
            duration_sec: p.duration_sec,
          })),
        },
  )
}

/** 편집기 blocks → 서버 저장용(표시 필드 제거). */
export function serializeBlocks(blocks) {
  return blocks.map((b) =>
    b.kind === 'video'
      ? { kind: 'video', video_id: b.video_id }
      : {
          kind: 'slideshow',
          music_id: b.music_id ?? null,
          photos: b.photos.map((p) => ({
            photo_id: p.photo_id,
            duration_sec: Number(p.duration_sec) || 0,
          })),
        },
  )
}

/** 새 빈 슬라이드쇼(음악) 라인. */
export function newSlideshow(music_id = null) {
  return { _key: newKey(), kind: 'slideshow', music_id, photos: [] }
}

/** 새 동영상 블록. */
export function newVideo(video_id) {
  return { _key: newKey(), kind: 'video', video_id }
}

/** 새 사진 엔트리. */
export function newPhoto(photo_id, duration_sec = 5) {
  return { _key: newKey(), photo_id, duration_sec }
}
