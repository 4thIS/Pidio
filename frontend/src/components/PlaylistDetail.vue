<script setup>
// D-4 플레이리스트 상세 — 헤더 + 음악 라인 편집기 + 저장(PUT).
import { ref, computed, onMounted } from 'vue'
import MusicLane from './MusicLane.vue'
import ScheduleModal from './ScheduleModal.vue'
import { scheduleSummary } from '../schedule.js'
import { playlists as plApi, media as mediaApi } from '../api.js'
import { MOCK_MEDIA, MOCK_PLAYLIST_DETAIL } from '../mock.js'
import { normalizeBlocks, serializeBlocks, newSlideshow, newVideo, newPhoto } from '../playlistModel.js'
import { typeEmoji, thumbGradient } from '../mediaView.js'
import { formatTime } from '../format.js'

const props = defineProps({ id: [Number, String] })
const emit = defineEmits(['close'])

const pl = ref(null)
const blocks = ref([])
const allMedia = ref([])
const mediaMap = ref({})
const usingMock = ref(false)
const loading = ref(true)
const saving = ref(false)
const notice = ref('')
const picker = ref(null) // { kind:'video'|'music'|'photo', block? }

onMounted(load)
async function load() {
  loading.value = true
  // 미디어(제목/피커용)
  let list
  try {
    list = await mediaApi.list('all')
    if (!Array.isArray(list) || !list.length) list = MOCK_MEDIA
  } catch {
    list = MOCK_MEDIA
  }
  allMedia.value = list
  mediaMap.value = Object.fromEntries(list.map((m) => [m.content_id, m]))
  // 상세
  let d
  try {
    d = await plApi.get(props.id)
  } catch {
    usingMock.value = true
    d = MOCK_PLAYLIST_DETAIL[props.id] || {
      id: props.id, name: '새 목록', repeat_mode: 'off', shuffle: false, schedule: null, blocks: [],
    }
  }
  pl.value = { id: d.id, name: d.name, repeat_mode: d.repeat_mode, shuffle: d.shuffle, schedule: d.schedule || null }
  blocks.value = normalizeBlocks(d.blocks)
  loading.value = false
}

// ---- 헤더 컨트롤 ----
function cycleRepeat() {
  const order = { off: 'all', all: 'one', one: 'off' }
  pl.value.repeat_mode = order[pl.value.repeat_mode]
}
function toggleShuffle() {
  pl.value.shuffle = !pl.value.shuffle
}
async function playNow() {
  try {
    await plApi.play(props.id)
    notify('재생을 요청했습니다.')
  } catch {
    notify('재생 요청을 처리하지 못했습니다.')
  }
}

const scheduleText = computed(() => scheduleSummary(pl.value?.schedule))

// ---- 예약 모달 ----
const schedOpen = ref(false)
function onSchedSaved(sched, opts) {
  pl.value.schedule = sched
  schedOpen.value = false
  notify(opts?.offline ? '예약 저장됨(서버 미연결 · 화면만 반영).' : '예약을 저장했습니다.')
}
function onSchedRemoved(opts) {
  pl.value.schedule = null
  schedOpen.value = false
  notify(opts?.offline ? '예약 삭제됨(서버 미연결 · 화면만 반영).' : '예약을 삭제했습니다.')
}

// ---- 편집 ----
function addMusicLane() {
  blocks.value.push(newSlideshow(null))
}
function removeBlock(block) {
  blocks.value = blocks.value.filter((b) => b !== block)
}
function openPicker(kind, block = null) {
  picker.value = { kind, block }
}
const pickerItems = computed(() => {
  if (!picker.value) return []
  const t = picker.value.kind === 'music' ? 'music' : picker.value.kind === 'video' ? 'video' : 'photo'
  return allMedia.value.filter((m) => m.media_type === t)
})
function choose(id) {
  const p = picker.value
  if (p.kind === 'video') blocks.value.push(newVideo(id))
  else if (p.kind === 'music') p.block.music_id = id
  else if (p.kind === 'photo') p.block.photos.push(newPhoto(id))
  picker.value = null
}

// ---- 저장 ----
async function save() {
  saving.value = true
  const payload = {
    name: pl.value.name,
    repeat_mode: pl.value.repeat_mode,
    shuffle: pl.value.shuffle,
    blocks: serializeBlocks(blocks.value),
  }
  try {
    await plApi.save(props.id, payload)
    notify('저장했습니다.')
  } catch {
    notify(usingMock.value ? '저장됨(서버 미연결 · 화면만 반영).' : '저장에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

let nt = null
function notify(msg) {
  notice.value = msg
  clearTimeout(nt)
  nt = setTimeout(() => (notice.value = ''), 2800)
}
</script>

<template>
  <div class="detail">
    <div class="dbar">
      <button class="back" @click="emit('close')">← 목록</button>
      <div class="grow"></div>
      <span v-if="notice" class="notice">{{ notice }}</span>
      <button class="save" :disabled="saving" @click="save">{{ saving ? '저장 중…' : '💾 저장' }}</button>
    </div>

    <div v-if="loading" class="empty">불러오는 중…</div>

    <template v-else>
      <div class="dhead">
        <span class="dt">{{ pl.name }}</span>
        <button class="btn acc" @click="playNow">▶ 재생</button>
        <button class="opt" :class="{ on: pl.repeat_mode !== 'off' }" @click="cycleRepeat">
          {{ pl.repeat_mode === 'one' ? '🔂 한개반복' : pl.repeat_mode === 'all' ? '🔁 전체반복' : '🔁 반복꺼짐' }}
        </button>
        <button class="opt" :class="{ on: pl.shuffle }" @click="toggleShuffle">🔀 셔플</button>
        <div class="grow"></div>
        <button class="opt" :class="{ on: pl.schedule }" @click="schedOpen = true">
          🕒 {{ pl.schedule ? '예약됨' : '예약' }}
        </button>
      </div>

      <div v-if="scheduleText" class="banner">
        🕒 <b>{{ scheduleText }}</b> 자동 재생
        <button class="edit-sched" @click="schedOpen = true">✏ 예약 수정</button>
      </div>
      <p v-if="usingMock" class="mock">샘플 데이터 · 서버 미연결</p>

      <div class="lanes">
        <MusicLane
          v-for="b in blocks"
          :key="b._key"
          :block="b"
          :media-map="mediaMap"
          @pick-music="openPicker('music', $event)"
          @add-photo="openPicker('photo', $event)"
          @remove="removeBlock"
        />
        <div v-if="!blocks.length" class="empty">라인이 없습니다. 아래에서 추가하세요.</div>
      </div>

      <div class="addrow">
        <button class="addbtn" @click="addMusicLane">＋ 음악 라인 추가</button>
        <button class="addbtn" @click="openPicker('video')">＋ 동영상 추가</button>
      </div>
      <p class="hint">사진의 ⠿ 를 잡아 다른 음악 라인으로 끌어다 놓으면 배경음악이 바뀌어요.</p>
    </template>

    <!-- 예약 모달 -->
    <ScheduleModal
      v-if="schedOpen"
      :playlist-id="id"
      :model-value="pl.schedule"
      @saved="onSchedSaved"
      @removed="onSchedRemoved"
      @close="schedOpen = false"
    />

    <!-- 미디어 피커 -->
    <div v-if="picker" class="picker-ov" @click.self="picker = null">
      <div class="picker">
        <div class="ph-head">
          <b>{{ picker.kind === 'video' ? '동영상' : picker.kind === 'music' ? '배경음악' : '사진' }} 선택</b>
          <button class="x" @click="picker = null">✕</button>
        </div>
        <div class="ph-list">
          <button v-if="picker.kind === 'music'" class="pick none" @click="picker.block.music_id = null; picker = null">
            🔇 음악 없음
          </button>
          <button v-for="m in pickerItems" :key="m.content_id" class="pick" @click="choose(m.content_id)">
            <span class="pt" :style="{ background: thumbGradient(m) }">{{ typeEmoji(m.media_type) }}</span>
            <span class="pn">{{ m.title }}</span>
            <span v-if="m.media_type !== 'photo'" class="pd">{{ formatTime(m.duration) }}</span>
          </button>
          <div v-if="!pickerItems.length" class="empty">해당 유형의 미디어가 없습니다.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail { min-height: 100%; }
.dbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-bottom: 1px solid var(--bd);
  background: #151c21;
}
.back {
  font-size: 12px;
  font-weight: 600;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.grow { flex: 1; }
.notice { font-size: 11.5px; color: var(--teal); }
.save {
  font-size: 12px;
  font-weight: 640;
  padding: 8px 15px;
  border-radius: 8px;
  border: none;
  background: var(--accent);
  color: #fff;
}
.save:disabled { opacity: 0.6; }
.dhead {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 14px 16px;
  flex-wrap: wrap;
}
.dt { font-size: 17px; font-weight: 720; letter-spacing: -0.01em; }
.btn {
  font-size: 12px;
  font-weight: 600;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.btn.acc { background: var(--accent); border-color: var(--accent); color: #fff; }
.opt {
  font-size: 11.5px;
  font-weight: 600;
  padding: 6px 11px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--muted);
}
.opt.on { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 50%, transparent); }
.banner {
  margin: 0 16px;
  padding: 9px 13px;
  border-radius: 9px;
  font-size: 11.5px;
  background: color-mix(in srgb, var(--teal) 13%, transparent);
  border: 1px solid color-mix(in srgb, var(--teal) 40%, transparent);
}
.banner b { color: var(--teal); }
.edit-sched {
  margin-left: 8px;
  font-size: 10.5px;
  border: 1px solid color-mix(in srgb, var(--teal) 45%, transparent);
  background: transparent;
  color: var(--teal);
  border-radius: 6px;
  padding: 2px 8px;
}
.mock {
  margin: 10px 16px 0;
  font-size: 10.5px;
  color: var(--warn);
  font-family: var(--font-mono);
}
.lanes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px 4px;
}
.addrow { display: flex; gap: 8px; padding: 8px 16px 4px; flex-wrap: wrap; }
.addbtn {
  font-size: 11.5px;
  padding: 8px 13px;
  border-radius: 8px;
  border: 1px dashed var(--bd);
  color: var(--muted);
  background: transparent;
}
.hint { font-size: 11px; color: var(--faint); font-style: italic; padding: 4px 16px 20px; margin: 0; }
.empty { color: var(--faint); font-size: 13px; padding: 18px; text-align: center; }

/* picker */
.picker-ov {
  position: fixed;
  inset: 0;
  background: rgba(8, 11, 13, 0.7);
  display: grid;
  place-items: center;
  z-index: 20;
  padding: 20px;
}
.picker {
  width: 380px;
  max-width: 100%;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 13px;
  overflow: hidden;
}
.ph-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid var(--bd);
}
.ph-head .x { border: none; background: transparent; color: var(--faint); font-size: 14px; }
.ph-list { overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.pick {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  text-align: left;
}
.pick:hover { background: var(--elev); border-color: var(--bd); }
.pick .pt { width: 40px; height: 28px; border-radius: 5px; display: grid; place-items: center; font-size: 14px; flex: none; }
.pick .pn { flex: 1; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pick .pd { font-family: var(--font-mono); font-size: 10.5px; color: var(--faint); }
.pick.none { color: var(--muted); font-size: 12.5px; padding: 9px; }
</style>
