// src/format.js — 순수 유틸 (vitest 테스트 대상)

/** 초 → "mm:ss" (1시간 이상이면 "h:mm:ss"). 잘못된 값은 "00:00". */
export function formatTime(sec) {
  if (!sec || sec < 0 || !isFinite(sec)) return '00:00'
  const total = Math.floor(sec)
  const s = total % 60
  const m = Math.floor(total / 60) % 60
  const h = Math.floor(total / 3600)
  const pad = (n) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

/** 진행률(%) 0~100. duration 이 0/음수면 0. */
export function progressPercent(pos, dur) {
  if (!dur || dur <= 0) return 0
  return Math.min(100, Math.max(0, (pos / dur) * 100))
}
