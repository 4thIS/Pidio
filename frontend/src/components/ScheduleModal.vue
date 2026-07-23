<script setup>
// D-5 예약 폼/수정 모달.
// 토글: 날짜 구간형(date_range) ↔ 반복 시간대형(weekly)
// 저장 시 같은 타입끼리 겹치면 서버가 409 → 경고 표시.
import { ref, computed } from 'vue'
import { schedule as schedApi, ApiError } from '../api.js'
import { WEEKDAYS, validateSchedule, toCsv, fromCsv } from '../schedule.js'

const props = defineProps({
  playlistId: [Number, String],
  modelValue: { type: Object, default: null }, // 기존 예약(없으면 신규)
})
const emit = defineEmits(['saved', 'removed', 'close'])

const existing = props.modelValue
const type = ref(existing?.sched_type || 'weekly')
const days = ref(fromCsv(existing?.weekdays) || [])
const startTime = ref(existing?.start_time || '12:00')
const endTime = ref(existing?.end_time || '13:00')
const startDt = ref(existing?.start_dt || '')
const endDt = ref(existing?.end_dt || '')

const error = ref('')
const busy = ref(false)

function toggleDay(k) {
  days.value = days.value.includes(k) ? days.value.filter((d) => d !== k) : [...days.value, k]
}

const payload = computed(() =>
  type.value === 'weekly'
    ? { sched_type: 'weekly', weekdays: toCsv(days.value), start_time: startTime.value, end_time: endTime.value }
    : { sched_type: 'date_range', start_dt: startDt.value, end_dt: endDt.value },
)

async function save() {
  error.value = ''
  const msg = validateSchedule(payload.value)
  if (msg) {
    error.value = msg
    return
  }
  busy.value = true
  try {
    await schedApi.set(props.playlistId, payload.value)
    emit('saved', payload.value)
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      error.value = '⚠ 같은 유형의 다른 예약과 시간이 겹칩니다. 시간을 조정해 주세요.'
    } else if (e instanceof ApiError && e.status === 404) {
      // 백엔드 예약 라우터는 Phase 8 → 화면에는 반영해 편집 흐름 확인 가능
      emit('saved', payload.value, { offline: true })
    } else {
      error.value = '저장에 실패했습니다.'
    }
  } finally {
    busy.value = false
  }
}

async function removeSchedule() {
  busy.value = true
  try {
    await schedApi.remove(props.playlistId)
    emit('removed')
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) emit('removed', { offline: true })
    else error.value = '삭제에 실패했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="ov" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-label="예약 설정">
      <div class="mh">
        <b>🕒 {{ existing ? '예약 수정' : '예약 설정' }}</b>
        <button class="x" @click="emit('close')" aria-label="닫기">✕</button>
      </div>

      <div class="mb">
        <div class="toggle">
          <button :class="{ on: type === 'date_range' }" @click="type = 'date_range'">날짜 구간형</button>
          <button :class="{ on: type === 'weekly' }" @click="type = 'weekly'">반복 시간대형</button>
        </div>

        <!-- 반복 시간대형 -->
        <template v-if="type === 'weekly'">
          <p class="fl">요일 (다중 선택)</p>
          <div class="days">
            <button
              v-for="d in WEEKDAYS"
              :key="d.k"
              class="day"
              :class="{ on: days.includes(d.k), we: d.k === 'sat' || d.k === 'sun' }"
              @click="toggleDay(d.k)"
            >
              {{ d.label }}
            </button>
          </div>
          <p class="fl">시간대</p>
          <div class="times">
            <input v-model="startTime" type="time" class="tinput" />
            <span class="tilde">~</span>
            <input v-model="endTime" type="time" class="tinput" />
          </div>
        </template>

        <!-- 날짜 구간형 -->
        <template v-else>
          <p class="fl">시작 일시</p>
          <input v-model="startDt" type="datetime-local" class="tinput full" />
          <p class="fl" style="margin-top: 14px">종료 일시</p>
          <input v-model="endDt" type="datetime-local" class="tinput full" />
        </template>

        <p v-if="error" class="warn">{{ error }}</p>

        <div class="mfoot">
          <button v-if="existing" class="del" :disabled="busy" @click="removeSchedule">🗑 삭제</button>
          <div class="grow"></div>
          <button class="cancel" @click="emit('close')">취소</button>
          <button class="save" :disabled="busy" @click="save">{{ busy ? '저장 중…' : '저장' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ov {
  position: fixed;
  inset: 0;
  background: rgba(8, 11, 13, 0.72);
  display: grid;
  place-items: center;
  z-index: 30;
  padding: 20px;
}
.modal {
  width: 400px;
  max-width: 100%;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.mh {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--bd);
}
.mh b { font-size: 14px; }
.mh .x { border: none; background: transparent; color: var(--faint); font-size: 14px; }
.mb { padding: 16px; }
.toggle {
  display: flex;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 9px;
  padding: 3px;
  margin-bottom: 16px;
}
.toggle button {
  flex: 1;
  text-align: center;
  font-size: 12px;
  padding: 7px;
  border-radius: 6px;
  color: var(--muted);
  border: none;
  background: transparent;
}
.toggle button.on { background: var(--accent); color: #fff; font-weight: 600; }
.fl {
  font-size: 11px;
  color: var(--muted);
  margin: 0 0 7px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: var(--font-mono);
}
.days { display: flex; gap: 5px; margin-bottom: 16px; }
.day {
  flex: 1;
  text-align: center;
  font-size: 12px;
  padding: 8px 0;
  border-radius: 7px;
  border: 1px solid var(--bd);
  color: var(--muted);
  background: transparent;
}
.day.we { color: #c46a8e; }
.day.on { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.times { display: flex; align-items: center; gap: 9px; }
.tilde { color: var(--faint); }
.tinput {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 9px 11px;
  font-family: var(--font-mono);
  font-size: 13px;
  text-align: center;
  color: var(--text);
  color-scheme: dark;
}
.tinput.full { width: 100%; }
.warn {
  font-size: 11.5px;
  color: var(--warn);
  background: color-mix(in srgb, var(--warn) 13%, transparent);
  border: 1px solid color-mix(in srgb, var(--warn) 40%, transparent);
  padding: 8px 11px;
  border-radius: 8px;
  margin: 14px 0 0;
}
.mfoot { display: flex; align-items: center; gap: 9px; margin-top: 16px; }
.grow { flex: 1; }
.del {
  color: var(--danger);
  border: 1px solid color-mix(in srgb, var(--danger) 40%, transparent);
  background: transparent;
  padding: 9px 13px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}
.cancel { color: var(--muted); padding: 9px 14px; font-size: 12px; border: none; background: transparent; }
.save {
  background: var(--accent);
  color: #fff;
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  border: none;
}
.save:disabled, .del:disabled { opacity: 0.6; }
</style>
