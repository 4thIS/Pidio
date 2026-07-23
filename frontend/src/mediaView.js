// src/mediaView.js — 미디어 표시용 순수 유틸

const V = ['#3a4a86,#5a86c4', '#514f8f,#7d6fc0']
const P = ['#7c3f6b,#c46a8e', '#8a5a2e,#c99a4a', '#3f7c5a,#6ac491']
const A = ['#2c3a44,#465a66', '#402c44,#664a6a']

function hash(s) {
  let h = 0
  for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return h
}

/** 타입+id 로 결정되는 안정적 썸네일 그라디언트(플레이스홀더). */
export function thumbGradient(item) {
  const arr = item.media_type === 'video' ? V : item.media_type === 'photo' ? P : A
  return `linear-gradient(135deg, ${arr[hash(item.content_id) % arr.length]})`
}

export function typeEmoji(t) {
  return t === 'video' ? '🎬' : t === 'photo' ? '🖼' : '🎵'
}

export function typeLabel(t) {
  return t === 'video' ? '동영상' : t === 'photo' ? '사진' : '음악'
}
