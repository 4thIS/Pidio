<script setup>
// D-2 지금재생 바 — /events(SSE)로 받은 PlayerState 를 실시간 표시.
import { computed, ref } from 'vue'
import { store } from '../store.js'
import { player as playerApi } from '../api.js'
import { formatTime, progressPercent } from '../format.js'

// player 가 null 이면 대기(standby) 기본값으로 취급.
const p = computed(() => store.player)
const status = computed(() => p.value?.status ?? 'standby')
const isStandby = computed(() => status.value === 'standby' || !p.value)
const isPlaying = computed(() => status.value === 'playing')

const title = computed(() =>
  p.value?.current_title || (isStandby.value ? '재생 중인 항목 없음' : '제목 없음'),
)
const source = computed(() => p.value?.source_label || (isStandby.value ? '대기 중' : ''))
const pos = computed(() => p.value?.position_sec ?? 0)
const dur = computed(() => p.value?.duration_sec ?? 0)
const pct = computed(() => progressPercent(pos.value, dur.value))
const repeat = computed(() => p.value?.repeat ?? 'off')
const shuffle = computed(() => p.value?.shuffle ?? false)
const isManual = computed(() => p.value?.mode === 'manual')

const notice = ref('')
async function run(fn) {
  notice.value = ''
  try {
    await fn()
  } catch {
    notice.value = '요청을 처리하지 못했습니다.'
  }
}

const playPause = () =>
  run(() => playerApi.action(isPlaying.value ? 'pause' : 'resume'))
const next = () => run(() => playerApi.action('next'))
const prev = () => run(() => playerApi.action('prev'))
const resumeAuto = () => run(() => playerApi.action('resume_auto'))
const cycleRepeat = () => {
  const order = { off: 'all', all: 'one', one: 'off' }
  return run(() => playerApi.repeat(order[repeat.value]))
}
const toggleShuffle = () => run(() => playerApi.shuffle(!shuffle.value))
</script>

<template>
  <section class="now" :class="{ standby: isStandby }">
    <div class="th">{{ isStandby ? '🖥️' : '🎬' }}</div>

    <div class="meta">
      <div class="t">{{ title }}</div>
      <div class="src">
        <template v-if="source">출처 · <b>{{ source }}</b></template>
        <span v-if="!store.connected" class="off">· 연결 끊김</span>
      </div>

      <div class="prog"><i :style="{ width: pct + '%' }"></i></div>
      <div class="time">
        <span>{{ formatTime(pos) }}</span><span>{{ formatTime(dur) }}</span>
      </div>

      <div class="ctrl">
        <button class="cbtn" title="이전" @click="prev">⏮</button>
        <button class="cbtn play" :disabled="isStandby" :title="isPlaying ? '일시정지' : '재생'" @click="playPause">
          {{ isPlaying ? '⏸' : '▶' }}
        </button>
        <button class="cbtn" title="다음" @click="next">⏭</button>

        <button class="cbtn" :class="{ on: repeat !== 'off' }"
                :title="repeat === 'one' ? '한 개 반복' : repeat === 'all' ? '전체 반복' : '반복 꺼짐'"
                @click="cycleRepeat">
          {{ repeat === 'one' ? '🔂' : '🔁' }}
        </button>
        <button class="cbtn" :class="{ on: shuffle }" title="셔플" @click="toggleShuffle">🔀</button>

        <button v-if="isManual" class="manual" @click="resumeAuto">↩ 자동 모드로 복귀</button>
      </div>

      <p v-if="notice" class="notice">{{ notice }}</p>
    </div>
  </section>
</template>

<style scoped>
.now {
  display: flex;
  gap: 15px;
  padding: 15px 16px;
  background: linear-gradient(120deg, #1d262c, #182025);
  border-bottom: 1px solid var(--bd);
}
.th {
  width: 150px;
  height: 86px;
  border-radius: 9px;
  background: linear-gradient(135deg, #3a4a86, #7c3f6b);
  flex: none;
  display: grid;
  place-items: center;
  font-size: 26px;
}
.now.standby .th {
  background: #212a31;
  color: var(--faint);
}
.meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.t {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.src {
  font-size: 12px;
  color: var(--muted);
  margin-top: 3px;
}
.src b { color: var(--teal); }
.src .off { color: var(--warn); margin-left: 4px; }
.prog {
  height: 6px;
  border-radius: 4px;
  background: #2b353d;
  margin-top: auto;
  overflow: hidden;
}
.prog i {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 4px;
  transition: width 0.3s linear;
}
.time {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--faint);
  margin-top: 5px;
}
.ctrl {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 11px;
}
.cbtn {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
  display: grid;
  place-items: center;
  font-size: 15px;
}
.cbtn.play {
  width: 40px;
  height: 40px;
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-size: 16px;
}
.cbtn.play:disabled {
  opacity: 0.5;
  cursor: default;
}
.cbtn.on {
  color: var(--accent);
  border-color: color-mix(in srgb, var(--accent) 50%, transparent);
}
.manual {
  margin-left: auto;
  font-size: 11.5px;
  font-weight: 600;
  padding: 7px 12px;
  border-radius: 20px;
  background: color-mix(in srgb, var(--teal) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--teal) 45%, transparent);
  color: var(--teal);
}
.notice {
  margin: 9px 0 0;
  font-size: 11.5px;
  color: var(--warn);
}
@media (max-width: 620px) {
  .now { flex-direction: column; }
  .th { width: 100%; height: 120px; }
}
</style>
