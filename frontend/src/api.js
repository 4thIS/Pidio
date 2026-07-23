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

// 재생 제어 호출 (백엔드 라우터는 Phase 8/Task 8.4 에서 구현 → 그 전엔 404)
export const player = {
  /** action ∈ next|prev|pause|resume|stop|resume_auto */
  action: (name) => api(`/api/player/${name}`, { method: 'POST' }),
  jump: (index) => api('/api/player/jump', { method: 'POST', body: { index } }),
  repeat: (mode) => api('/api/player/repeat', { method: 'POST', body: { mode } }),
  shuffle: (on) => api('/api/player/shuffle', { method: 'POST', body: { on } }),
}
