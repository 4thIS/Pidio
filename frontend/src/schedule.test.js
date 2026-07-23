import { describe, it, expect } from 'vitest'
import { weekdaysText, scheduleSummary, validateSchedule, toCsv, fromCsv } from './schedule.js'

describe('weekdaysText', () => {
  it('csv 를 한글 요일로', () => {
    expect(weekdaysText('mon,tue,wed,thu,fri')).toBe('월화수목금')
  })
  it('입력 순서와 무관하게 요일 순서 유지', () => {
    expect(weekdaysText('sun,mon')).toBe('월일')
  })
  it('빈 값은 빈 문자열', () => {
    expect(weekdaysText('')).toBe('')
  })
})

describe('scheduleSummary', () => {
  it('반복 시간대형', () => {
    expect(
      scheduleSummary({ sched_type: 'weekly', weekdays: 'mon,tue', start_time: '12:00', end_time: '13:00' }),
    ).toBe('매주 월화 12:00~13:00')
  })
  it('날짜 구간형', () => {
    expect(
      scheduleSummary({ sched_type: 'date_range', start_dt: '2026-08-01 09:00', end_dt: '2026-08-07 18:00' }),
    ).toBe('2026-08-01 09:00 ~ 2026-08-07 18:00')
  })
  it('없으면 빈 문자열', () => {
    expect(scheduleSummary(null)).toBe('')
  })
})

describe('validateSchedule', () => {
  it('정상 weekly 는 null', () => {
    expect(validateSchedule({ sched_type: 'weekly', weekdays: 'mon', start_time: '12:00', end_time: '13:00' })).toBe(null)
  })
  it('요일 미선택 거부', () => {
    expect(validateSchedule({ sched_type: 'weekly', weekdays: '', start_time: '12:00', end_time: '13:00' })).toMatch(/요일/)
  })
  it('종료가 시작보다 빠르면 거부', () => {
    expect(validateSchedule({ sched_type: 'weekly', weekdays: 'mon', start_time: '13:00', end_time: '12:00' })).toMatch(/종료/)
  })
  it('날짜형 종료<시작 거부', () => {
    expect(validateSchedule({ sched_type: 'date_range', start_dt: '2026-08-07 18:00', end_dt: '2026-08-01 09:00' })).toMatch(/종료/)
  })
})

describe('toCsv / fromCsv', () => {
  it('왕복 일치(요일 순서로 정렬)', () => {
    expect(toCsv(['fri', 'mon'])).toBe('mon,fri')
    expect(fromCsv('mon,fri')).toEqual(['mon', 'fri'])
  })
})
