<script setup>
// 플레이리스트/재생목록 타임라인 에디터 — 화면 위 모달.
// 사진·동영상·음악을 셀로 한 줄 배치, 아래 '음악 레인'에서 노래 바를 좌우 핸들로
// 여러 사진 셀에 걸침. 걸친 사진들은 각각 (노래길이 / 걸친 사진 수)만큼 표시.
// 도메인 슬라이드쇼 블록(사진들+배경음악)으로 직렬화되어 저장·재생된다.
// fromQueue=true 면 현재 재생목록을 시드로 편집 → 새 플리로 저장.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import ScheduleModal from './ScheduleModal.vue'
import { scheduleSummary } from '../schedule.js'
import { playlists as plApi, media as mediaApi, folders as folderApi, player as playerApi } from '../api.js'
import { MOCK_MEDIA } from '../mock.js'
import { typeEmoji, thumbGradient } from '../mediaView.js'
import { formatTime } from '../format.js'

const props = defineProps({
  id: { type: [Number, String], default: null },
  justCreated: Boolean,
  fromQueue: Boolean,
})
const emit = defineEmits(['close', 'changed'])

const CELL_W = 96
const GAP = 12
const STRIDE = CELL_W + GAP

let _seq = 0
const nk = () => `s${++_seq}`

const pl = ref({ name: '', repeat_mode: 'off', shuffle: false, schedule: null })
const segments = ref([]) // {key, type:'video'|'photo'|'music', content_id, sec?}
const songs = ref([])    // {key, music_id, coverKeys:[photoKey,...]}
const allMedia = ref([])
const mediaMap = ref({})
const usingMock = ref(false)
const loading = ref(true)
const notice = ref('')
const editingName = ref(false)
const nameDraft = ref('')

const editable = computed(() => props.fromQueue || props.id != null)

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
  try {
    pickerFolders.value = await folderApi.list()
  } catch {
    pickerFolders.value = []
  }

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
  deserialize(blocks)
  loading.value = false
}

// ---- 블록 ⇄ (셀 + 노래) ----
function deserialize(blocks) {
  const segs = []
  const sgs = []
  for (const b of blocks) {
    if (b.kind === 'video') {
      segs.push({ key: nk(), type: 'video', content_id: b.video_id })
    } else {
      const photos = b.photos || []
      if (!photos.length && b.music_id) {
        segs.push({ key: nk(), type: 'music', content_id: b.music_id })
      } else {
        const keys = []
        for (const p of photos) {
          const k = nk()
          keys.push(k)
          segs.push({ key: k, type: 'photo', content_id: p.photo_id, sec: p.duration_sec || 5 })
        }
        if (b.music_id && keys.length) sgs.push({ key: nk(), music_id: b.music_id, coverKeys: keys })
      }
    }
  }
  segments.value = segs
  songs.value = sgs
}

function idxOf(key) {
  return segments.value.findIndex((s) => s.key === key)
}
function songBounds(sg) {
  const a = idxOf(sg.coverKeys[0])
  const b = idxOf(sg.coverKeys[sg.coverKeys.length - 1])
  return [Math.min(a, b), Math.max(a, b)]
}
function musicDur(mid) {
  return mediaMap.value[mid]?.duration || 0
}
function songCovering(i) {
  return songs.value.find((sg) => {
    const [a, b] = songBounds(sg)
    return i >= a && i <= b
  })
}
function perPhotoSec(sg) {
  const cnt = sg.coverKeys.length || 1
  const d = musicDur(sg.music_id)
  return d ? d / cnt : 0
}

function serialize() {
  const out = []
  const segs = segments.value
  let i = 0
  while (i < segs.length) {
    const s = segs[i]
    if (s.type === 'video') { out.push({ kind: 'video', video_id: s.content_id }); i++; continue }
    if (s.type === 'music') { out.push({ kind: 'slideshow', music_id: s.content_id, photos: [] }); i++; continue }
    const song = songCovering(i)
    if (song) {
      const [a, b] = songBounds(song)
      const cnt = b - a + 1
      const d = musicDur(song.music_id)
      const photos = []
      for (let j = a; j <= b; j++) photos.push({ photo_id: segs[j].content_id, duration_sec: cnt ? d / cnt : (d || 5) })
      out.push({ kind: 'slideshow', music_id: song.music_id, photos })
      i = b + 1
    } else {
      const photos = []
      while (i < segs.length && segs[i].type === 'photo' && !songCovering(i)) {
        photos.push({ photo_id: segs[i].content_id, duration_sec: segs[i].sec || 5 })
        i++
      }
      out.push({ kind: 'slideshow', music_id: null, photos })
    }
  }
  return out
}

// ---- 저장 ----
let saved = false
async function persist() {
  if (props.fromQueue || props.id == null) return // 큐 편집은 명시 저장만
  try {
    await plApi.save(props.id, {
      name: pl.value.name,
      repeat_mode: pl.value.repeat_mode,
      shuffle: pl.value.shuffle,
      blocks: serialize(),
    })
    saved = true
  } catch (e) {
    if (!usingMock.value) notify(e?.message || '저장에 실패했습니다.')
  }
}
async function saveAsNew() {
  const name = (prompt('새 플레이리스트 이름', pl.value.name || '재생목록') || '').trim()
  if (!name) return
  try {
    const r = await plApi.create(name)
    await plApi.save(r.id, {
      name,
      repeat_mode: pl.value.repeat_mode,
      shuffle: pl.value.shuffle,
      blocks: serialize(),
    })
    emit('changed')
    notify(`"${name}"으로 저장했습니다.`)
    setTimeout(close, 700)
  } catch (e) {
    notify(e?.message || '저장에 실패했습니다.')
  }
}

// ---- 셀 편집 ----
function healSongs() {
  songs.value = songs.value
    .map((sg) => {
      const positions = sg.coverKeys.map(idxOf).filter((i) => i >= 0).sort((a, b) => a - b)
      if (!positions.length) return null
      const start = positions[0]
      let end = start
      const posSet = new Set(positions)
      while (end + 1 < segments.value.length && posSet.has(end + 1) && segments.value[end + 1].type === 'photo') end++
      const keys = []
      for (let j = start; j <= end; j++) if (segments.value[j].type === 'photo') keys.push(segments.value[j].key)
      return keys.length ? { ...sg, coverKeys: keys } : null
    })
    .filter(Boolean)
}
function removeCell(i) {
  segments.value.splice(i, 1)
  healSongs()
  persist()
}
function setPhotoSec(seg, e) {
  const s = Number(e.target.value)
  if (s > 0) { seg.sec = s; persist() }
}

// 셀 순서 변경(드래그)
const dragIndex = ref(null)
const overIndex = ref(null)
function isCellDrag(e) {
  return [...(e.dataTransfer?.types || [])].includes('application/x-pidio-cell')
}
function onCellDragStart(i, e) {
  dragIndex.value = i
  e.dataTransfer.setData('application/x-pidio-cell', String(i))
  e.dataTransfer.effectAllowed = 'move'
}
function onCellDragOver(i, e) {
  if (!isCellDrag(e)) return
  e.preventDefault()
  overIndex.value = i
}
function onCellDrop(i, e) {
  if (!isCellDrag(e)) return
  e.preventDefault()
  const from = dragIndex.value
  dragIndex.value = null
  overIndex.value = null
  if (from === null || from === i) return
  const arr = [...segments.value]
  const [m] = arr.splice(from, 1)
  arr.splice(i, 0, m)
  segments.value = arr
  healSongs()
  persist()
}
function onCellDragEnd() {
  dragIndex.value = null
  overIndex.value = null
}

// ---- 노래 바 좌우 핸들 드래그 ----
const laneEl = ref(null)
let handleDrag = null // {sg, side}
function cellIndexAtX(x) {
  return Math.max(0, Math.min(segments.value.length - 1, Math.floor(x / STRIDE)))
}
function coveredByOthers(sg) {
  const set = new Set()
  for (const o of songs.value) {
    if (o === sg) continue
    const [a, b] = songBounds(o)
    for (let j = a; j <= b; j++) set.add(j)
  }
  return set
}
function startHandle(sg, side, e) {
  e.preventDefault()
  e.stopPropagation()
  handleDrag = { sg, side }
  window.addEventListener('pointermove', onHandleMove)
  window.addEventListener('pointerup', onHandleUp)
}
function onHandleMove(e) {
  if (!handleDrag || !laneEl.value) return
  const rect = laneEl.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  let idx = cellIndexAtX(x)
  const { sg, side } = handleDrag
  const [s0, s1] = songBounds(sg)
  const others = coveredByOthers(sg)
  const isFreePhoto = (j) => j >= 0 && j < segments.value.length && segments.value[j].type === 'photo' && !others.has(j)
  if (side === 'right') {
    let maxEnd = s0
    while (maxEnd + 1 < segments.value.length && isFreePhoto(maxEnd + 1)) maxEnd++
    const newEnd = Math.max(s0, Math.min(idx, maxEnd))
    setCover(sg, s0, newEnd)
  } else {
    let minStart = s1
    while (minStart - 1 >= 0 && isFreePhoto(minStart - 1)) minStart--
    const newStart = Math.min(s1, Math.max(idx, minStart))
    setCover(sg, newStart, s1)
  }
}
function onHandleUp() {
  window.removeEventListener('pointermove', onHandleMove)
  window.removeEventListener('pointerup', onHandleUp)
  handleDrag = null
  persist()
}
function setCover(sg, a, b) {
  const keys = []
  for (let j = a; j <= b; j++) if (segments.value[j].type === 'photo') keys.push(segments.value[j].key)
  if (keys.length) sg.coverKeys = keys
}
function removeSong(sg) {
  songs.value = songs.value.filter((s) => s !== sg)
  persist()
}
function barStyle(sg) {
  const [a, b] = songBounds(sg)
  return {
    left: a * STRIDE + 'px',
    width: (b - a + 1) * CELL_W + (b - a) * GAP + 'px',
  }
}

// ---- 추가 피커 ----
const picker = ref(null) // null | 'item' | 'song'
const PICKER_CATS = [
  { k: 'all', label: '전체' },
  { k: 'video', label: '🎬 동영상' },
  { k: 'photo', label: '🖼 사진' },
  { k: 'music', label: '🎵 음악' },
]
const pickerCat = ref('all')
const pickerFolders = ref([])
const pickerFolderIds = ref([])
function openItemPicker() {
  pickerCat.value = 'all'
  picker.value = 'item'
}
function openSongPicker() {
  picker.value = 'song'
}
async function setPickerCat(k) {
  pickerCat.value = k
  if (k.startsWith('folder:')) {
    try { pickerFolderIds.value = (await folderApi.get(Number(k.slice(7)))).content_ids } catch { pickerFolderIds.value = [] }
  }
}
const pickerList = computed(() => {
  if (picker.value === 'song') return allMedia.value.filter((m) => m.media_type === 'music')
  if (pickerCat.value.startsWith('folder:')) {
    const s = new Set(pickerFolderIds.value)
    return allMedia.value.filter((m) => s.has(m.content_id))
  }
  return pickerCat.value === 'all' ? allMedia.value : allMedia.value.filter((m) => m.media_type === pickerCat.value)
})
function choose(cid) {
  if (picker.value === 'song') addSong(cid)
  else addCell(cid)
  picker.value = null
}
function addCell(cid) {
  const m = mediaMap.value[cid]
  if (!m) return
  const seg = { key: nk(), type: m.media_type, content_id: cid }
  if (m.media_type === 'photo') seg.sec = m.photo_sec ?? 5
  segments.value.push(seg)
  persist()
}
function addSong(mid) {
  const covered = coveredByOthers({})
  let t = -1
  for (let i = 0; i < segments.value.length; i++) {
    if (segments.value[i].type === 'photo' && !covered.has(i)) { t = i; break }
  }
  if (t < 0) { notify('노래를 걸 사진 셀이 없습니다. 먼저 사진을 추가하세요.'); return }
  songs.value.push({ key: nk(), music_id: mid, coverKeys: [segments.value[t].key] })
  persist()
}

// ---- 셀 표시 헬퍼 ----
function segTitle(seg) {
  const m = mediaMap.value[seg.content_id]
  return m ? m.title : seg.content_id
}
function segThumb(seg) {
  if (seg.type === 'music') return null
  return `/thumb/${seg.content_id}`
}
function segEmoji(seg) {
  return seg.type === 'video' ? '🎬' : seg.type === 'music' ? '🎵' : '🖼'
}
function photoSecDisplay(i, seg) {
  const song = songCovering(i)
  if (song) return (perPhotoSec(song)).toFixed(1)
  return null // uncovered → editable
}
function coverStyle(cid) {
  return { backgroundImage: `url(/thumb/${cid})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundColor: '#1a2129' }
}

// ---- 헤더 ----
function startEditName() { nameDraft.value = pl.value.name; editingName.value = true }
function commitName() {
  if (!editingName.value) return
  editingName.value = false
  const t = nameDraft.value.trim()
  if (t && t !== pl.value.name) { pl.value.name = t; persist() }
}
function cycleRepeat() {
  pl.value.repeat_mode = { off: 'all', all: 'one', one: 'off' }[pl.value.repeat_mode]
  persist()
}
function toggleShuffle() { pl.value.shuffle = !pl.value.shuffle; persist() }
async function playNow() {
  if (props.id == null) return
  try { await plApi.play(props.id); notify('재생을 요청했습니다.') } catch { notify('재생 요청 실패.') }
}
const scheduleText = computed(() => scheduleSummary(pl.value?.schedule))
const schedOpen = ref(false)
function onSchedSaved(sched) { pl.value.schedule = sched; schedOpen.value = false; notify('예약을 저장했습니다.') }
function onSchedRemoved() { pl.value.schedule = null; schedOpen.value = false; notify('예약을 삭제했습니다.') }

async function close() {
  if (props.justCreated && !props.fromQueue && segments.value.length === 0 && !saved) {
    try { await plApi.remove(props.id) } catch { /* ignore */ }
  }
  emit('changed')
  emit('close')
}

let nt = null
function notify(msg) {
  notice.value = msg
  clearTimeout(nt)
  nt = setTimeout(() => (notice.value = ''), 2600)
}
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onHandleMove)
  window.removeEventListener('pointerup', onHandleUp)
})
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
        <p class="tip">사진 아래 <b>🎵 노래</b>를 추가하고 바 양끝을 잡아 여러 사진에 걸치면, 노래 길이 ÷ 사진 수로 각 사진이 표시됩니다.</p>

        <!-- 타임라인 -->
        <div class="tl">
          <div class="track">
            <div class="cells">
              <div
                v-for="(seg, i) in segments"
                :key="seg.key"
                class="cell"
                :class="[seg.type, { over: overIndex === i, dragging: dragIndex === i }]"
                :style="{ width: CELL_W + 'px' }"
                draggable="true"
                @dragstart="onCellDragStart(i, $event)"
                @dragover="onCellDragOver(i, $event)"
                @drop="onCellDrop(i, $event)"
                @dragend="onCellDragEnd"
                :title="segTitle(seg)"
              >
                <div class="cth" :style="segThumb(seg) && seg.type !== 'music' ? coverStyle(seg.content_id) : {}">
                  <span v-if="seg.type === 'music' || !segThumb(seg)" class="cemoji">{{ segEmoji(seg) }}</span>
                  <button class="crm" @click.stop="removeCell(i)" title="삭제">✕</button>
                  <!-- 사진 시간: 노래에 걸리면 자동, 아니면 편집 -->
                  <span v-if="seg.type === 'photo' && photoSecDisplay(i, seg) !== null" class="csec auto">{{ photoSecDisplay(i, seg) }}초</span>
                  <span v-else-if="seg.type === 'photo'" class="csec edit" @click.stop>
                    <input class="secin" type="number" min="1" step="1" :value="seg.sec" @change="setPhotoSec(seg, $event)" @click.stop />초
                  </span>
                </div>
                <div class="ct">{{ segTitle(seg) }}</div>
              </div>

              <button class="addcell" :style="{ width: CELL_W + 'px' }" @click="openItemPicker" title="사진·동영상·음악 추가">
                <span class="plus">＋</span><span class="al">추가</span>
              </button>
            </div>

            <!-- 음악 레인 -->
            <div ref="laneEl" class="lane" :style="{ minWidth: segments.length * STRIDE + 'px' }">
              <div v-for="sg in songs" :key="sg.key" class="songbar" :style="barStyle(sg)" :title="segTitle({ content_id: sg.music_id })">
                <span class="h left" @pointerdown="startHandle(sg, 'left', $event)"></span>
                <span class="slabel">🎵 {{ mediaMap[sg.music_id]?.title || '음악' }} · {{ formatTime(perPhotoSec(sg)) }}/장</span>
                <button class="srm" @click="removeSong(sg)" title="노래 제거">✕</button>
                <span class="h right" @pointerdown="startHandle(sg, 'right', $event)"></span>
              </div>
              <div v-if="!songs.length" class="laneempty">음악 레인 — 아래 “🎵 노래”로 사진에 노래를 걸어보세요</div>
            </div>
          </div>
        </div>

        <div class="addrow">
          <button class="addbtn song" @click="openSongPicker">🎵 노래 추가</button>
        </div>
        <div v-if="!segments.length" class="hint">＋ 로 사진·동영상·음악을 담아 목록을 만드세요.</div>
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

      <!-- 항목/노래 피커 -->
      <div v-if="picker" class="picker-ov" @click.self="picker = null">
        <div class="picker">
          <div class="ph-head">
            <b>{{ picker === 'song' ? '노래 선택' : '항목 추가' }}</b>
            <button class="x2" @click="picker = null">✕</button>
          </div>
          <div v-if="picker === 'item'" class="ph-cats">
            <button v-for="c in PICKER_CATS" :key="c.k" class="cat" :class="{ on: pickerCat === c.k }" @click="setPickerCat(c.k)">{{ c.label }}</button>
            <span v-if="pickerFolders.length" class="catdiv"></span>
            <button v-for="f in pickerFolders" :key="'pf' + f.id" class="cat" :class="{ on: pickerCat === 'folder:' + f.id }" @click="setPickerCat('folder:' + f.id)">📁 {{ f.name }}</button>
          </div>
          <div class="ph-list">
            <button v-for="m in pickerList" :key="m.content_id" class="pick" @click="choose(m.content_id)">
              <span class="pt" :style="m.thumb_url ? coverStyle(m.content_id) : { background: thumbGradient(m) }">
                <span v-if="!m.thumb_url">{{ typeEmoji(m.media_type) }}</span>
              </span>
              <span class="pn">{{ m.title }}</span>
              <span v-if="m.media_type !== 'photo'" class="pd">{{ formatTime(m.duration) }}</span>
            </button>
            <div v-if="!pickerList.length" class="empty">해당 항목이 없습니다.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-active .sheet, .modal-leave-active .sheet { transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .sheet, .modal-leave-to .sheet { transform: translateY(14px) scale(0.97); }

.pd-ov {
  position: fixed;
  inset: 0;
  background: rgba(6, 9, 11, 0.66);
  backdrop-filter: blur(2px);
  display: grid;
  place-items: center;
  z-index: 25;
  padding: 24px;
}
.sheet {
  width: 860px;
  max-width: 100%;
  max-height: 88vh;
  overflow-y: auto;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
}
.dbar {
  display: flex; align-items: center; gap: 10px;
  padding: 13px 16px; border-bottom: 1px solid var(--bd);
  background: #151c21; border-radius: 16px 16px 0 0; position: sticky; top: 0; z-index: 4;
}
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

/* 타임라인 */
.tl { overflow-x: auto; padding: 12px 16px 6px; }
.track { display: inline-block; }
.cells { display: flex; gap: 12px; align-items: flex-start; }
.cell {
  flex: none; border-radius: 10px; padding: 4px; border: 1px solid transparent; cursor: grab; position: relative;
}
.cell.dragging { opacity: 0.4; }
.cell.over::before { content: ''; position: absolute; left: -7px; top: 3px; bottom: 3px; width: 3px; border-radius: 2px; background: var(--teal); }
.cell .cth {
  height: 66px; border-radius: 7px; background: #1a2129; position: relative;
  display: grid; place-items: center; overflow: hidden;
}
.cell.music .cth { background: linear-gradient(135deg, #3a4a86, #7c3f6b); }
.cell .cemoji { font-size: 22px; }
.cell .crm {
  position: absolute; right: 4px; top: 4px; width: 20px; height: 20px; border-radius: 6px; border: none;
  background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 11px; display: grid; place-items: center;
  opacity: 0; transition: opacity 0.15s, background 0.15s; z-index: 2;
}
.cell:hover .crm { opacity: 1; }
.cell .crm:hover { background: #c0392b; }
.cell .csec {
  position: absolute; left: 4px; bottom: 4px; font-size: 9px; color: #fff;
  background: rgba(0, 0, 0, 0.72); border-radius: 4px; padding: 1px 4px; display: flex; align-items: center; gap: 1px;
}
.cell .csec.auto { background: color-mix(in srgb, var(--teal) 75%, #000); font-weight: 700; }
.cell .csec .secin {
  width: 22px; background: transparent; border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.5);
  color: #fff; font-family: var(--font-mono); font-size: 10px; text-align: right; padding: 0; -moz-appearance: textfield;
}
.cell .csec .secin::-webkit-outer-spin-button, .cell .csec .secin::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.cell .ct { font-size: 10.5px; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
.addcell {
  flex: none; height: 66px; border: 1px dashed var(--bd); border-radius: 10px; background: transparent;
  color: var(--muted); display: grid; place-items: center; align-content: center; gap: 2px;
}
.addcell .plus { font-size: 20px; color: var(--teal); }
.addcell .al { font-size: 10px; }

/* 음악 레인 */
.lane { position: relative; height: 34px; margin-top: 8px; border-top: 1px dashed var(--bd); padding-top: 8px; }
.laneempty { font-size: 10.5px; color: var(--faint); padding-top: 4px; }
.songbar {
  position: absolute; top: 8px; height: 26px; border-radius: 7px;
  background: color-mix(in srgb, var(--accent) 30%, #1a2129);
  border: 1px solid var(--accent); display: flex; align-items: center; gap: 4px; padding: 0 3px;
  overflow: hidden;
}
.songbar .slabel { flex: 1; font-size: 9.5px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px; }
.songbar .h { width: 9px; align-self: stretch; cursor: ew-resize; flex: none; border-radius: 4px; background: var(--accent); }
.songbar .h:hover { background: #fff; }
.songbar .srm { border: none; background: rgba(0, 0, 0, 0.4); color: #fff; font-size: 9px; width: 16px; height: 16px; border-radius: 4px; flex: none; }

.addrow { display: flex; gap: 8px; padding: 8px 16px 4px; flex-wrap: wrap; }
.addbtn { font-size: 11.5px; padding: 8px 13px; border-radius: 8px; border: 1px dashed var(--bd); color: var(--muted); background: transparent; }
.addbtn.song { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 45%, transparent); }
.hint { font-size: 11.5px; color: var(--faint); font-style: italic; padding: 0 16px 18px; margin: -2px 0 0; }
.empty { color: var(--faint); font-size: 13px; padding: 24px; text-align: center; }

/* 피커 */
.picker-ov { position: fixed; inset: 0; background: rgba(8, 11, 13, 0.7); display: grid; place-items: center; z-index: 30; padding: 20px; }
.picker { width: 380px; max-width: 100%; max-height: 70vh; display: flex; flex-direction: column; background: var(--sf); border: 1px solid var(--bd); border-radius: 13px; overflow: hidden; }
.ph-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--bd); }
.ph-head .x2 { border: none; background: transparent; color: var(--faint); font-size: 14px; }
.ph-cats { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; padding: 9px 10px; border-bottom: 1px solid var(--bd); }
.ph-cats .cat { font-size: 11px; padding: 4px 10px; border-radius: 16px; border: 1px solid var(--bd); background: var(--elev); color: var(--muted); }
.ph-cats .cat.on { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.ph-cats .catdiv { width: 1px; align-self: stretch; background: var(--bd); margin: 1px 2px; }
.ph-list { overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.pick { display: flex; align-items: center; gap: 10px; padding: 7px 9px; border-radius: 8px; border: 1px solid transparent; background: transparent; color: var(--text); text-align: left; }
.pick:hover { background: var(--elev); border-color: var(--bd); }
.pick .pt { width: 40px; height: 28px; border-radius: 5px; display: grid; place-items: center; font-size: 14px; flex: none; overflow: hidden; }
.pick .pn { flex: 1; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pick .pd { font-family: var(--font-mono); font-size: 10.5px; color: var(--faint); }
</style>
