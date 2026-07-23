// src/mock.js — 백엔드 /api/media(Phase 8) 완성 전까지 쓰는 샘플 미디어.
// media 라우터가 생기면 Library 가 실제 데이터로 자동 전환하고 이 목록은 안 쓰인다.
export const MOCK_MEDIA = [
  { content_id: 'v1', media_type: 'video', title: '입장 행진 영상.mp4', duration: 150, thumb_url: '/thumb/v1', available: true },
  { content_id: 'v2', media_type: 'video', title: '축하영상 2026.mp4', duration: 320, thumb_url: '/thumb/v2', available: true },
  { content_id: 'v3', media_type: 'video', title: '교장선생님 축사.mp4', duration: 72, thumb_url: '/thumb/v3', available: true },
  { content_id: 'p1', media_type: 'photo', title: '단체사진_01.jpg', duration: null, thumb_url: '/thumb/p1', available: true },
  { content_id: 'p2', media_type: 'photo', title: '시상식_02.jpg', duration: null, thumb_url: '/thumb/p2', available: true },
  { content_id: 'p3', media_type: 'photo', title: '운동장_풍경.jpg', duration: null, thumb_url: '/thumb/p3', available: true },
  { content_id: 'a1', media_type: 'music', title: '축가 - 합창단.mp3', duration: 228, thumb_url: null, available: true },
  { content_id: 'a2', media_type: 'music', title: '교가.mp3', duration: 245, thumb_url: null, available: true },
]

export const mediaById = (id) => MOCK_MEDIA.find((m) => m.content_id === id) || null

// 플레이리스트 목록/상세 (백엔드 /api/playlists 는 Phase 8 → 그 전 폴백)
export const MOCK_PLAYLISTS = [
  { id: 1, name: '졸업식', item_count: 8, total_sec: 1120, repeat_mode: 'all', shuffle: false, cover: ['v1', 'p1', 'p2'], schedule: { sched_type: 'weekly', weekdays: 'mon,tue,wed,thu,fri', start_time: '12:00', end_time: '13:00' } },
  { id: 2, name: '점심시간 BGM', item_count: 24, total_sec: 4320, repeat_mode: 'all', shuffle: true, cover: ['a1', 'a2', 'p3'], schedule: null },
  { id: 3, name: '체육대회 사진', item_count: 40, total_sec: 200, repeat_mode: 'off', shuffle: false, cover: ['p2', 'p3', 'p1'], schedule: null },
]

export const MOCK_PLAYLIST_DETAIL = {
  1: {
    id: 1, name: '졸업식', repeat_mode: 'all', shuffle: false,
    schedule: { sched_type: 'weekly', weekdays: 'mon,tue,wed,thu,fri', start_time: '12:00', end_time: '13:00' },
    blocks: [
      { kind: 'video', video_id: 'v1' },
      { kind: 'slideshow', music_id: 'a1', photos: [{ photo_id: 'p1', duration_sec: 5 }, { photo_id: 'p2', duration_sec: 5 }, { photo_id: 'p3', duration_sec: 3 }] },
      { kind: 'slideshow', music_id: null, photos: [{ photo_id: 'p1', duration_sec: 4 }, { photo_id: 'p2', duration_sec: 4 }] },
    ],
  },
  2: {
    id: 2, name: '점심시간 BGM', repeat_mode: 'all', shuffle: true, schedule: null,
    blocks: [{ kind: 'slideshow', music_id: 'a1', photos: [] }, { kind: 'slideshow', music_id: 'a2', photos: [] }],
  },
  3: {
    id: 3, name: '체육대회 사진', repeat_mode: 'off', shuffle: false, schedule: null,
    blocks: [{ kind: 'slideshow', music_id: null, photos: [{ photo_id: 'p2', duration_sec: 5 }, { photo_id: 'p3', duration_sec: 5 }] }],
  },
}
