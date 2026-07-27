<script setup>
// 플레이리스트/재생목록 편집 모달 — 공용 Timeline 에디터를 감싸는 셸.
// id 있으면 그 플리를 편집(즉시 저장). fromQueue 면 현재 큐를 시드로 편집 → 새 플리로 저장.
import { ref, computed, onMounted } from 'vue'
import Timeline from './Timeline.vue'
import ScheduleModal from './ScheduleModal.vue'
import { scheduleSummary } from '../schedule.js'
import { playlists as plApi, media as mediaApi, folders as folderApi, player as playerApi } from '../api.js'
import { dialog } from '../dialog.js'
import { MOCK_MEDIA } from '../mock.js'

const props = defineProps({
  id: { type: [Number, String], default: null },
  justCreated: Boolean,
  fromQueue: Boolean,
})
const emit = defineEmits(['close', 'changed'])

const pl = ref({ name: '', repeat_mode: 'off', shuffle: false, schedule: null })
const initialBlocks = ref([])
const latestBlocks = ref([])
const allMedia = ref([])
const mediaMap = ref({})
const pickerFolders = ref([])
const usingMock = ref(false)
const loading = ref(true)
const notice = ref('')
const editingName = ref(false)
const nameDraft = ref('')

onMounted(load)
async function load() {
  loading.value = true
  let list
  try {
    const data = await mediaApi.list('all')
    list = Array.isArray(data) ? data : []
  } catch {
    usingMock.value = true
    list = MOCK_MEDIA
  }
  allMedia.value = list
  mediaMap.value = Object.fromEntries(list.map((m) => [m.content_id, m]))
  try { pickerFolders.value = await folderApi.list() } catch { pickerFolders.value = [] }

  let blocks = []
  if (props.fromQueue) {
    try {
      const d = await playerApi.queueBlocks()
      blocks = d.blocks || []
      pl.value = { name: '재생목록', repeat_mode: d.repeat_mode || 'off', shuffle: !!d.shuffle, schedule: null }
    } catch {
      pl.value = { name: '재생목록', repeat_mode: 'off', shuffle: false, schedule: null }
    }
  } else {
    try {
      const d = await plApi.get(props.id)
      pl.value = { name: d.name, repeat_mode: d.repeat_mode, shuffle: d.shuffle, schedule: d.schedule || null }
      blocks = d.blocks || []
    } catch {
      usingMock.value = true
      pl.value = { name: '새 목록', repeat_mode: 'off', shuffle: false, schedule: null }
    }
  }
  initialBlocks.value = blocks
  latestBlocks.value = blocks
  loading.value = false
}

// ---- Timeline 변경 → 저장 ----
let saved = false
function onBlocks(blocks) {
  latestBlocks.value = blocks
  if (!props.fromQueue && props.id != null) persist()
}
async function persist() {
  try {
    await plApi.save(props.id, {
      name: pl.value.name, repeat_mode: pl.value.repeat_mode,
      shuffle: pl.value.shuffle, blocks: latestBlocks.value,
    })
    saved = true
  } catch (e) {
    if (!usingMock.value) notify(e?.message || '저장에 실패했습니다.')
  }
}
async function saveAsNew() {
  const name = ((await dialog.prompt('새 플레이리스트로 저장', pl.value.name || '재생목록', { placeholder: '플레이리스트 이름' })) || '').trim()
  if (!name) return
  try {
    const r = await plApi.create(name)
    await plApi.save(r.id, {
      name, repeat_mode: pl.value.repeat_mode, shuffle: pl.value.shuffle, blocks: latestBlocks.value,
    })
    emit('changed')
    notify(`"${name}"으로 저장했습니다.`)
    setTimeout(close, 700)
  } catch (e) {
    notify(e?.message || '저장에 실패했습니다.')
  }
}

// ---- 헤더 ----
function startEditName() { nameDraft.value = pl.value.name; editingName.value = true }
function commitName() {
  if (!editingName.value) return
  editingName.value = false
  const t = nameDraft.value.trim()
  if (t && t !== pl.value.name) { pl.value.name = t; if (!props.fromQueue && props.id != null) persist() }
}
function cycleRepeat() {
  pl.value.repeat_mode = { off: 'all', all: 'one', one: 'off' }[pl.value.repeat_mode]
  if (!props.fromQueue && props.id != null) persist()
}
function toggleShuffle() { pl.value.shuffle = !pl.value.shuffle; if (!props.fromQueue && props.id != null) persist() }
async function playNow() {
  if (props.id == null) return
  try { await plApi.play(props.id); notify('재생을 요청했습니다.') } catch { notify('재생 요청 실패.') }
}
const scheduleText = computed(() => scheduleSummary(pl.value?.schedule))
const schedOpen = ref(false)
function onSchedSaved(sched) { pl.value.schedule = sched; schedOpen.value = false; notify('예약을 저장했습니다.') }
function onSchedRemoved() { pl.value.schedule = null; schedOpen.value = false; notify('예약을 삭제했습니다.') }

async function close() {
  if (props.justCreated && !props.fromQueue && latestBlocks.value.length === 0 && !saved) {
    try { await plApi.remove(props.id) } catch { /* ignore */ }
  }
  emit('changed')
  emit('close')
}

let nt = null
function notify(msg) { notice.value = msg; clearTimeout(nt); nt = setTimeout(() => (notice.value = ''), 2600) }
</script>

<template>
  <div class="pd-ov" @click.self="close">
    <div class="sheet">
      <div class="dbar">
        <div v-if="editingName" class="nmwrap">
          <input v-model="nameDraft" class="nmedit" @keyup.enter="commitName" @blur="commitName" @keyup.esc="editingName = false" />
        </div>
        <div v-else class="nmwrap" @dblclick="startEditName">
          <span class="dt">{{ pl?.name }}</span>
          <span v-if="fromQueue" class="qbadge">재생목록 편집</span>
          <button class="pen" @click="startEditName" aria-label="이름 수정">✎</button>
        </div>
        <div class="grow"></div>
        <span v-if="notice" class="notice">{{ notice }}</span>
        <button v-if="fromQueue" class="saveq" @click="saveAsNew">💾 새 플리로 저장</button>
        <button class="x" @click="close" aria-label="닫기">✕</button>
      </div>

      <div v-if="loading" class="empty">불러오는 중…</div>

      <template v-else>
        <div class="ctrls">
          <button v-if="!fromQueue" class="btn acc" @click="playNow">▶ 재생</button>
          <button class="opt" :class="{ on: pl.repeat_mode !== 'off' }" @click="cycleRepeat">
            {{ pl.repeat_mode === 'one' ? '🔂 한개반복' : pl.repeat_mode === 'all' ? '🔁 전체반복' : '🔁 반복꺼짐' }}
          </button>
          <button class="opt" :class="{ on: pl.shuffle }" @click="toggleShuffle">🔀 셔플</button>
          <div class="grow"></div>
          <button v-if="!fromQueue" class="opt" :class="{ on: pl.schedule }" @click="schedOpen = true">
            🕒 {{ pl.schedule ? '예약됨' : '예약' }}
          </button>
        </div>
        <div v-if="scheduleText" class="banner">🕒 <b>{{ scheduleText }}</b> 자동 재생</div>
        <p class="tip">셀을 드래그해 순서를 바꾸고, <b>음악 셀을 사진 아래 “음악 줄”로 끌어다 놓으면</b> 그 사진의 배경음악이 됩니다. 노래 바 양끝을 잡아 여러 사진에 걸치면 노래 길이 ÷ 사진 수로 표시돼요.</p>

        <div class="tlbox">
          <Timeline
            :blocks="initialBlocks"
            :media-map="mediaMap"
            :all-media="allMedia"
            :picker-folders="pickerFolders"
            @change="onBlocks"
          />
        </div>
      </template>

      <ScheduleModal
        v-if="schedOpen"
        :playlist-id="id"
        :model-value="pl.schedule"
        @saved="onSchedSaved"
        @removed="onSchedRemoved"
        @close="schedOpen = false"
      />
    </div>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-active .sheet, .modal-leave-active .sheet { transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .sheet, .modal-leave-to .sheet { transform: translateY(14px) scale(0.97); }
.pd-ov { position: fixed; inset: 0; background: rgba(6, 9, 11, 0.66); backdrop-filter: blur(2px); display: grid; place-items: center; z-index: 25; padding: 24px; }
.sheet { width: 860px; max-width: 100%; max-height: 88vh; overflow-y: auto; background: var(--bg); border: 1px solid var(--bd); border-radius: 16px; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55); }
.dbar { display: flex; align-items: center; gap: 10px; padding: 13px 16px; border-bottom: 1px solid var(--bd); background: var(--topbar); border-radius: 16px 16px 0 0; position: sticky; top: 0; z-index: 4; }
.nmwrap { display: flex; align-items: center; gap: 6px; min-width: 0; }
.dt { font-size: 16px; font-weight: 720; letter-spacing: -0.01em; }
.qbadge { font-size: 10px; font-weight: 700; color: var(--teal); background: color-mix(in srgb, var(--teal) 15%, transparent); border-radius: 6px; padding: 2px 7px; }
.pen { opacity: 0.55; border: none; background: transparent; color: var(--muted); font-size: 12px; }
.nmwrap:hover .pen { opacity: 1; }
.nmedit { background: var(--bg); border: 1px solid var(--teal); border-radius: 6px; color: var(--text); font-size: 15px; font-weight: 700; padding: 4px 8px; }
.grow { flex: 1; }
.notice { font-size: 11.5px; color: var(--teal); }
.saveq { font-size: 12px; font-weight: 640; padding: 7px 13px; border-radius: 8px; border: none; background: var(--accent); color: #fff; }
.x { border: none; background: var(--elev); color: var(--muted); font-size: 13px; width: 30px; height: 30px; border-radius: 8px; }
.ctrls { display: flex; align-items: center; gap: 9px; padding: 13px 16px 4px; flex-wrap: wrap; }
.btn { font-size: 12px; font-weight: 600; padding: 7px 12px; border-radius: 8px; border: 1px solid var(--bd); background: var(--elev); color: var(--text); }
.btn.acc { background: var(--accent); border-color: var(--accent); color: #fff; }
.opt { font-size: 11.5px; font-weight: 600; padding: 6px 11px; border-radius: 8px; border: 1px solid var(--bd); background: var(--elev); color: var(--muted); }
.opt.on { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 50%, transparent); }
.banner { margin: 8px 16px 0; padding: 8px 12px; border-radius: 9px; font-size: 11.5px; background: color-mix(in srgb, var(--teal) 13%, transparent); border: 1px solid color-mix(in srgb, var(--teal) 40%, transparent); }
.banner b { color: var(--teal); }
.tip { margin: 10px 16px 0; font-size: 11px; color: var(--faint); }
.tip b { color: var(--teal); }
.tlbox { padding: 12px 16px 16px; }
.empty { color: var(--faint); font-size: 13px; padding: 24px; text-align: center; }
</style>
