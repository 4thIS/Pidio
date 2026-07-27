// src/api.js — 백엔드 호출 래퍼
// - JSON 요청/응답 처리
// - 401(인증 만료)이면 store.authed=false 로 표시 → 앱이 로그인 화면으로 전환
import { store } from './store.js'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * fetch 래퍼. 실패(2xx 아님) 시 ApiError 를 던진다.
 * @param {string} path 예: '/api/login'
 * @param {{method?:string, body?:any, headers?:object}} opts
 */
export async function api(path, { method = 'GET', body, headers } = {}) {
  const options = { method, credentials: 'same-origin', headers: { ...headers } }
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  const res = await fetch(path, options)

  // 응답 본문(JSON) 파싱 시도 (본문 없을 수 있음)
  let data = null
  try {
    data = await res.json()
  } catch {
    /* 본문 없음 */
  }

  if (res.status === 401) {
    // 세션이 없거나 만료됨 → 전역 상태를 로그아웃으로
    store.authed = false
  }

  if (!res.ok) {
    const detail = (data && data.detail) || res.statusText || '요청에 실패했습니다.'
    throw new ApiError(detail, res.status)
  }

  return data
}

// 인증 관련 호출
export const auth = {
  /** 현재 세션 확인. 성공 시 {authenticated:true}, 미인증이면 401 → ApiError */
  me: () => api('/api/me'),
  /** 로그인. 최초 로그인이면 이 비번으로 설정됨. */
  login: (password) => api('/api/login', { method: 'POST', body: { password } }),
  /** 로그아웃 */
  logout: () => api('/api/logout', { method: 'POST' }),
}

// 미디어 목록/제목 (백엔드 라우터는 Phase 8/Task 8.1 에서 구현 → 그 전엔 404 → Library가 샘플로 폴백)
export const media = {
  list: (type = 'all') => api(`/api/media?type=${encodeURIComponent(type)}`),
  patchTitle: (id, custom_title) =>
    api(`/api/media/${id}`, { method: 'PATCH', body: { custom_title } }),
  setPhotoSec: (id, sec) =>
    api(`/api/media/${id}/photo_sec`, { method: 'PATCH', body: { sec } }),
  remove: (id) => api(`/api/media/${id}`, { method: 'DELETE' }),
}

// 선택 재생 (Phase 8/Task 8.4)
export const play = {
  selection: (content_ids, { repeat = 'off', shuffle = false } = {}) =>
    api('/api/play/selection', { method: 'POST', body: { content_ids, repeat, shuffle } }),
}

// 플레이리스트 CRUD/재생 (Phase 8/Task 8.2)
export const playlists = {
  list: () => api('/api/playlists'),
  get: (id) => api(`/api/playlists/${id}`),
  create: (name) => api('/api/playlists', { method: 'POST', body: { name } }),
  save: (id, data) => api(`/api/playlists/${id}`, { method: 'PUT', body: data }),
  remove: (id) => api(`/api/playlists/${id}`, { method: 'DELETE' }),
  play: (id) => api(`/api/playlists/${id}/play`, { method: 'POST' }),
  add: (id, contentIds) => api(`/api/playlists/${id}/add`, { method: 'POST', body: { content_ids: contentIds } }),
  reorder: (ids) => api('/api/playlists/reorder', { method: 'POST', body: { ids } }),
}

// 폴더 (전체목록 수동 그룹)
export const folders = {
  list: () => api('/api/folders'),
  get: (id) => api(`/api/folders/${id}`),
  create: (name) => api('/api/folders', { method: 'POST', body: { name } }),
  remove: (id, deleteMedia = false) =>
    api(`/api/folders/${id}?delete_media=${deleteMedia ? 'true' : 'false'}`, { method: 'DELETE' }),
  addItems: (id, contentIds) =>
    api(`/api/folders/${id}/items`, { method: 'POST', body: { content_ids: contentIds } }),
  removeItem: (id, contentId) =>
    api(`/api/folders/${id}/items/${contentId}`, { method: 'DELETE' }),
  reorder: (ids) => api('/api/folders/reorder', { method: 'POST', body: { ids } }),
}

// 설정 (Phase 8/Task 8.5)
export const settings = {
  get: () => api('/api/settings'),
  save: (data) => api('/api/settings', { method: 'PUT', body: data }),
  changePassword: (old_password, new_password) =>
    api('/api/settings/password', { method: 'POST', body: { old: old_password, new: new_password } }),
}

// 예약 (Phase 8/Task 8.3). 같은 타입 겹침 시 서버가 409.
export const schedule = {
  set: (playlistId, sched) =>
    api(`/api/playlists/${playlistId}/schedule`, { method: 'PUT', body: sched }),
  remove: (playlistId) =>
    api(`/api/playlists/${playlistId}/schedule`, { method: 'DELETE' }),
}

// 재생 제어 호출 (백엔드 라우터는 Phase 8/Task 8.4 에서 구현 → 그 전엔 404)
export const player = {
  queue: () => api('/api/player/queue'),
  queueBlocks: () => api('/api/player/queue/blocks'),
  queueAdd: (contentIds) => api('/api/player/queue/add', { method: 'POST', body: { content_ids: contentIds } }),
  queueRemove: (index) => api('/api/player/queue/remove', { method: 'POST', body: { index } }),
  setPhotoSec: (index, sec) => api('/api/player/queue/photo_sec', { method: 'POST', body: { index, sec } }),
  saveQueue: (name) => api('/api/player/queue/save', { method: 'POST', body: { name } }),
  /** action ∈ next|prev|pause|resume|stop|resume_auto */
  action: (name) => api(`/api/player/${name}`, { method: 'POST' }),
  jump: (index) => api('/api/player/jump', { method: 'POST', body: { index } }),
  repeat: (mode) => api('/api/player/repeat', { method: 'POST', body: { mode } }),
  shuffle: (on) => api('/api/player/shuffle', { method: 'POST', body: { on } }),
  reorder: (from, to) => api('/api/player/queue/reorder', { method: 'POST', body: { from, to } }),
}
