import { describe, it, expect } from 'vitest'
import { formatTime, progressPercent } from './format.js'

describe('formatTime', () => {
  it('mm:ss 형식', () => {
    expect(formatTime(134)).toBe('02:14')
    expect(formatTime(5)).toBe('00:05')
  })
  it('1시간 이상은 h:mm:ss', () => {
    expect(formatTime(3725)).toBe('1:02:05')
  })
  it('0/음수/NaN 은 00:00', () => {
    expect(formatTime(0)).toBe('00:00')
    expect(formatTime(-5)).toBe('00:00')
    expect(formatTime(NaN)).toBe('00:00')
  })
})

describe('progressPercent', () => {
  it('절반', () => {
    expect(progressPercent(60, 120)).toBe(50)
  })
  it('duration 0 이면 0', () => {
    expect(progressPercent(10, 0)).toBe(0)
  })
  it('범위를 벗어나면 0~100 으로 클램프', () => {
    expect(progressPercent(200, 100)).toBe(100)
    expect(progressPercent(-10, 100)).toBe(0)
  })
})
