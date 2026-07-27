<script setup>
// D-2 지금재생 바 — /events(SSE)로 받은 PlayerState 를 실시간 표시.
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { store } from '../store.js'
import { player as playerApi } from '../api.js'
import { formatTime } from '../format.js'

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
const repeat = computed(() => p.value?.repeat ?? 'off')
const shuffle = computed(() => p.value?.shuffle ?? false)
const isManual = computed(() => p.value?.mode === 'manual')
const currentId = computed(() => p.value?.current_id || null)
const scheduleActive = computed(() => !!p.value?.schedule_active)
const scheduleName = computed(() => p.value?.schedule_active_name || source.value)

// ---- 진행바 부드럽게(rAF 보간): SSE는 1초마다 오지만 화면은 매 프레임 서서히 ----
const smoothPos = ref(0)
let base = 0
let baseAt = 0
let raf = null
watch([pos, isPlaying, currentId], () => {
  base = pos.value
  baseAt = performance.now()
  smoothPos.value = base
})
function tick() {
  if (isPlaying.value && dur.value > 0) {
    smoothPos.value = Math.min(base + (performance.now() - baseAt) / 1000, dur.value)
  } else {
    smoothPos.value = pos.value
  }
  raf = requestAnimationFrame(tick)
}
onMounted(() => { raf = requestAnimationFrame(tick) })
onBeforeUnmount(() => cancelAnimationFrame(raf))
const pct = computed(() => (dur.value > 0 ? Math.min(100, (smoothPos.value / dur.value) * 100) : 0))

const failedIds = ref(new Set())
const thumbUrl = computed(() => {
  const id = currentId.value
  if (isStandby.value || !id || failedIds.value.has(id)) return null
  return `/thumb/${id}`
})
function onImgError() {
  const id = currentId.value
  if (id) failedIds.value = new Set(failedIds.value).add(id)
}

const notice = ref('')
async function run(fn) {
  notice.value = ''
  try { await fn() } catch { notice.value = '요청을 처리하지 못했습니다.' }
}
const playPause = () => run(() => playerApi.action(isPlaying.value ? 'pause' : 'resume'))
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
    <div class="th">
      <img v-if="thumbUrl" :key="currentId" :src="thumbUrl" alt="" @error="onImgError" />
      <svg v-else viewBox="0 0 24 24" class="thico" fill="none" stroke="currentColor" stroke-width="1.6">
        <rect x="2" y="4" width="20" height="14" rx="2" /><path d="M8 21h8M12 18v3" />
      </svg>
    </div>

    <div class="meta">
      <div class="t">{{ title }}</div>
      <div class="src">
        <template v-if="source">출처 · <b>{{ source }}</b></template>
        <span v-if="!store.connected" class="off">· 연결 끊김</span>
      </div>

      <div class="prog"><i :style="{ width: pct + '%' }"></i></div>
      <div class="time">
        <span>{{ formatTime(smoothPos) }}</span><span>{{ formatTime(dur) }}</span>
      </div>

      <div class="ctrl">
        <button class="cbtn" title="이전" @click="prev">
          <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="19,5 8,12 19,19" /><rect x="5" y="5" width="2.2" height="14" rx="1" /></svg>
        </button>
        <button class="cbtn play" :disabled="isStandby" :title="isPlaying ? '일시정지' : '재생'" @click="playPause">
          <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor"><rect x="6.5" y="5" width="4" height="14" rx="1.2" /><rect x="13.5" y="5" width="4" height="14" rx="1.2" /></svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor"><polygon points="7,4.5 20,12 7,19.5" /></svg>
        </button>
        <button class="cbtn" title="다음" @click="next">
          <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5,5 16,12 5,19" /><rect x="16.8" y="5" width="2.2" height="14" rx="1" /></svg>
        </button>

        <button class="cbtn ricon" :class="{ on: repeat !== 'off' }"
                :title="repeat === 'one' ? '한 개 반복' : repeat === 'all' ? '전체 반복' : '반복 꺼짐'"
                @click="cycleRepeat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="17 1 21 5 17 9" /><path d="M3 11V9a4 4 0 0 1 4-4h14" />
            <polyline points="7 23 3 19 7 15" /><path d="M21 13v2a4 4 0 0 1-4 4H3" />
          </svg>
          <span v-if="repeat === 'one'" class="one">1</span>
        </button>
        <button class="cbtn" :class="{ on: shuffle }" title="셔플" @click="toggleShuffle">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="16 3 21 3 21 8" /><line x1="4" y1="20" x2="21" y2="3" />
            <polyline points="21 16 21 21 16 21" /><line x1="15" y1="15" x2="21" y2="21" /><line x1="4" y1="4" x2="9" y2="9" />
          </svg>
        </button>

        <!-- 예약 재생 중 안내(셔플 오른쪽) -->
        <span v-if="scheduleActive && !isManual && isPlaying" class="sched">🕒 예약 재생 중<template v-if="scheduleName"> · <b>{{ scheduleName }}</b></template></span>

        <!-- 자동(예약) 복귀: 예약이 걸려 있는데 수동으로 다른 걸 보고 있을 때만 -->
        <button v-if="isManual && scheduleActive" class="manual" @click="resumeAuto">↩ 예약 재생으로 복귀</button>
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
  background: linear-gradient(120deg, var(--elev), var(--sf));
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
  color: rgba(255, 255, 255, 0.85);
  overflow: hidden;
}
.th .thico { width: 34px; height: 34px; }
.th img { width: 100%; height: 100%; object-fit: cover; }
.now.standby .th { background: var(--elev); color: var(--faint); }
.meta { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.t {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.src { font-size: 12px; color: var(--muted); margin-top: 3px; }
.src b { color: var(--teal); }
.src .off { color: var(--warn); margin-left: 4px; }
.prog {
  height: 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--muted) 25%, transparent);
  margin-top: auto;
  overflow: hidden;
}
.prog i { display: block; height: 100%; background: var(--accent); border-radius: 4px; }
.time {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--faint);
  margin-top: 5px;
}
.ctrl { display: flex; align-items: center; gap: 8px; margin-top: 11px; }
.cbtn {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
  display: grid;
  place-items: center;
  position: relative;
}
.cbtn svg { width: 18px; height: 18px; }
.cbtn.play { width: 40px; height: 40px; background: var(--accent); border-color: var(--accent); color: #fff; }
.cbtn.play svg { width: 20px; height: 20px; }
.cbtn.play:disabled { opacity: 0.5; cursor: default; }
.cbtn.on { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 50%, transparent); }
.cbtn .one {
  position: absolute;
  right: 4px;
  bottom: 3px;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
  background: var(--accent);
  color: #fff;
  border-radius: 50%;
  width: 12px;
  height: 12px;
  display: grid;
  place-items: center;
}
.sched {
  margin-left: 6px;
  font-size: 11px;
  color: var(--teal);
  background: color-mix(in srgb, var(--teal) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--teal) 40%, transparent);
  padding: 5px 10px;
  border-radius: 20px;
  white-space: nowrap;
}
.sched b { font-weight: 700; }
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
.notice { margin: 9px 0 0; font-size: 11.5px; color: var(--warn); }
@media (max-width: 620px) {
  .now { flex-direction: column; }
  .th { width: 100%; height: 120px; }
}
</style>
