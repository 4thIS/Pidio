// src/store.js — 앱 전역 반응형 상태 (순수 상태 + SSE 연결; api를 import하지 않아 순환참조 없음)
import { reactive } from 'vue'

export const store = reactive({
  // 시작 시 세션 확인이 끝났는지 (끝나기 전엔 로딩 화면)
  ready: false,
  // 로그인 되어 있는지
  authed: false,
  // 실시간 재생 상태(PlayerState). 아직 아무 것도 안 왔으면 null → "대기"로 표시.
  player: null,
  // SSE 연결 상태
  connected: false,
})

// ---- SSE (/events) 구독 -----------------------------------------------------
let es = null

/** /events 에 연결해 PlayerState 를 실시간 수신. 이미 연결돼 있으면 무시. */
export function connectEvents() {
  if (es) return
  es = new EventSource('/events')
  es.onopen = () => {
    store.connected = true
  }
  es.onmessage = (ev) => {
    try {
      store.player = JSON.parse(ev.data)
    } catch {
      /* 형식이 아니면 무시 */
    }
  }
  es.onerror = () => {
    // 브라우저 EventSource 가 자동 재연결하므로 표시만 갱신.
    store.connected = false
  }
}

/** 연결 종료(로그아웃 시). */
export function disconnectEvents() {
  if (es) {
    es.close()
    es = null
  }
  store.connected = false
  store.player = null
}
