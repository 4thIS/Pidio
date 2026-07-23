// src/schedule.js — 예약(스케줄) 순수 유틸 (vitest 대상)

export const WEEKDAYS = [
  { k: 'mon', label: '월' },
  { k: 'tue', label: '화' },
  { k: 'wed', label: '수' },
  { k: 'thu', label: '목' },
  { k: 'fri', label: '금' },
  { k: 'sat', label: '토' },
  { k: 'sun', label: '일' },
]

const LABEL = Object.fromEntries(WEEKDAYS.map((d) => [d.k, d.label]))

/** "mon,tue,wed" → "월화수" (정의된 요일 순서 유지) */
export function weekdaysText(csv) {
  const set = new Set((csv || '').split(',').filter(Boolean))
  return WEEKDAYS.filter((d) => set.has(d.k))
    .map((d) => d.label)
    .join('')
}

/** 예약 객체 → 사람이 읽는 요약. 없으면 ''. */
export function scheduleSummary(s) {
  if (!s) return ''
  if (s.sched_type === 'weekly') {
    return `매주 ${weekdaysText(s.weekdays)} ${s.start_time}~${s.end_time}`
  }
  return `${s.start_dt} ~ ${s.end_dt}`
}

/**
 * 저장 전 검증. 문제 없으면 null, 있으면 오류 메시지.
 * (겹침 여부는 서버가 409 로 판정 — 여기선 형식만.)
 */
export function validateSchedule(s) {
  if (s.sched_type === 'weekly') {
    if (!s.weekdays) return '요일을 하나 이상 선택해 주세요.'
    if (!s.start_time || !s.end_time) return '시간을 입력해 주세요.'
    if (s.start_time >= s.end_time) return '종료 시간이 시작 시간보다 뒤여야 합니다.'
    return null
  }
  if (!s.start_dt || !s.end_dt) return '시작·종료 일시를 입력해 주세요.'
  if (s.start_dt >= s.end_dt) return '종료 일시가 시작 일시보다 뒤여야 합니다.'
  return null
}

/** 선택된 요일 배열 ↔ csv */
export function toCsv(list) {
  const set = new Set(list)
  return WEEKDAYS.filter((d) => set.has(d.k))
    .map((d) => d.k)
    .join(',')
}
export function fromCsv(csv) {
  return (csv || '').split(',').filter(Boolean)
}
