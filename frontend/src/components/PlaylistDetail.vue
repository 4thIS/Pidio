<script setup>
// 플레이리스트 상세 — 화면 위 모달 박스. 내용은 가로 썸네일 카드(재생목록 패널과 동일 톤).
// 편집(추가/삭제/순서변경/옵션)은 즉시 저장. 새로 만든 뒤 빈 채로 닫으면 자동 삭제.
import { ref, computed, onMounted } from 'vue'
import ScheduleModal from './ScheduleModal.vue'
import { scheduleSummary } from '../schedule.js'
import { playlists as plApi, media as mediaApi, folders as folderApi } from '../api.js'
import { MOCK_MEDIA, MOCK_PLAYLIST_DETAIL } from '../mock.js'
import { normalizeBlocks, serializeBlocks, newSlideshow, newVideo, newPhoto } from '../playlistModel.js'
import { typeEmoji, thumbGradient } from '../mediaView.js'
import { formatTime } from '../format.js'

const props = defineProps({ id: [Number, String], justCreated: Boolean })
const emit = defineEmits(['close', 'changed'])

const pl = ref(null)
const blocks = ref([])
const allMedia = ref([])
const mediaMap = ref({})
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
    list = MOCK_MEDIA
  }
  allMedia.value = list
  mediaMap.value = Object.fromEntries(list.map((m) => [m.content_id, m]))
  try {
    pickerFolders.value = await folderApi.list()
  } catch {
    pickerFolders.value = []
  }
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

// ---- 블록 → 표시(썸네일/제목) ----
function bcid(b) {
  return b.kind === 'video' ? b.video_id : (b.photos && b.photos.length ? b.photos[0].photo_id : b.music_id)
}
function btitle(b) {
  const m = mediaMap.value[bcid(b)]
  return m ? m.title : (bcid(b) || '(빈 항목)')
}
function bthumb(b) {
  const m = mediaMap.value[bcid(b)]
  return m && m.thumb_url ? m.thumb_url : null
}
function bemoji(b) {
  if (b.kind === 'video') return '🎬'
  return b.photos && b.photos.length ? '🖼' : '🎵'
}
function bdur(b) {
  const m = mediaMap.value[bcid(b)]
  return m && m.media_type !== 'photo' ? formatTime(m.duration) : ''
}
function coverStyle(cid) {
  return { backgroundImage: `url(/thumb/${cid})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundColor: '#1a2129' }
}

// ---- 저장(모든 편집은 즉시 반영) ----
let saved = false
async function persist() {
  try {
    await plApi.save(props.id, {
      name: pl.value.name,
      repeat_mode: pl.value.repeat_mode,
      shuffle: pl.value.shuffle,
      blocks: serializeBlocks(blocks.value),
    })
    saved = true
  } catch (e) {
    if (usingMock.value) notify('저장됨(서버 미연결 · 화면만 반영).')
    else notify(e?.message || '저장에 실패했습니다.')
  }
}

// ---- 헤더 컨트롤 ----
function startEditName() {
  nameDraft.value = pl.value.name
  editingName.value = true
}
function commitName() {
  if (!editingName.value) return
  editingName.value = false
  const t = nameDraft.value.trim()
  if (t && t !== pl.value.name) {
    pl.value.name = t
    persist()
  }
}
function cycleRepeat() {
  const order = { off: 'all', all: 'one', one: 'off' }
  pl.value.repeat_mode = order[pl.value.repeat_mode]
  persist()
}
function toggleShuffle() {
  pl.value.shuffle = !pl.value.shuffle
  persist()
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
const schedOpen = ref(false)
function onSchedSaved(sched) {
  pl.value.schedule = sched
  schedOpen.value = false
  notify('예약을 저장했습니다.')
}
function onSchedRemoved() {
  pl.value.schedule = null
  schedOpen.value = false
  notify('예약을 삭제했습니다.')
}

// ---- 항목 추가(피커) ----
const picker = ref(false)
const PICKER_CATS = [
  { k: 'all', label: '전체' },
  { k: 'video', label: '🎬 동영상' },
  { k: 'photo', label: '🖼 사진' },
  { k: 'music', label: '🎵 음악' },
]
const pickerCat = ref('all') // 'all'|'video'|'photo'|'music'|'folder:<id>'
const pickerFolders = ref([])
const pickerFolderIds = ref([])
function openPicker() {
  pickerCat.value = 'all'
  picker.value = true
}
async function setPickerCat(k) {
  pickerCat.value = k
  if (k.startsWith('folder:')) {
    try {
      const f = await folderApi.get(Number(k.slice(7)))
      pickerFolderIds.value = f.content_ids
    } catch {
      pickerFolderIds.value = []
    }
  }
}
const pickerList = computed(() => {
  if (pickerCat.value.startsWith('folder:')) {
    const s = new Set(pickerFolderIds.value)
    return allMedia.value.filter((m) => s.has(m.content_id))
  }
  return pickerCat.value === 'all'
    ? allMedia.value
    : allMedia.value.filter((m) => m.media_type === pickerCat.value)
})
function blockFromMedia(cid) {
  const m = mediaMap.value[cid]
  if (!m) return null
  if (m.media_type === 'video') return newVideo(cid)
  if (m.media_type === 'photo') {
    const b = newSlideshow(null)
    b.photos.push(newPhoto(cid))
    return b
  }
  return newSlideshow(cid) // music → 음악 라인
}
function choose(cid) {
  const b = blockFromMedia(cid)
  if (b) {
    blocks.value.push(b)
    persist()
  }
  picker.value = false
}

// ---- 항목 삭제 ----
function removeBlock(i) {
  blocks.value.splice(i, 1)
  persist()
}

// ---- 드래그로 순서변경 ----
const dragIndex = ref(null)
const overIndex = ref(null)
function isBlockDrag(e) {
  return [...(e.dataTransfer?.types || [])].includes('application/x-pidio-plblock')
}
function onCardDragStart(i, e) {
  dragIndex.value = i
  e.dataTransfer.setData('application/x-pidio-plblock', String(i))
  e.dataTransfer.effectAllowed = 'move'
}
function onCardDragOver(i, e) {
  if (!isBlockDrag(e)) return
  e.preventDefault()
  overIndex.value = i
}
function onCardDrop(i, e) {
  if (!isBlockDrag(e)) return
  e.preventDefault()
  const from = dragIndex.value
  dragIndex.value = null
  overIndex.value = null
  if (from === null || from === i) return
  const [moved] = blocks.value.splice(from, 1)
  blocks.value.splice(i, 0, moved)
  persist()
}
function onCardDragEnd() {
  dragIndex.value = null
  overIndex.value = null
}

// ---- 닫기(빈 새 목록이면 삭제) ----
async function close() {
  if (props.justCreated && blocks.value.length === 0 && !saved) {
    try {
      await plApi.remove(props.id)
    } catch {
      /* ignore */
    }
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
          <button class="pen" @click="startEditName" aria-label="이름 수정">✎</button>
        </div>
        <div class="grow"></div>
        <span v-if="notice" class="notice">{{ notice }}</span>
        <button class="x" @click="close" aria-label="닫기">✕</button>
      </div>

      <div v-if="loading" class="empty">불러오는 중…</div>

      <template v-else>
        <div class="ctrls">
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

        <div v-if="scheduleText" class="banner">🕒 <b>{{ scheduleText }}</b> 자동 재생</div>
        <p v-if="usingMock" class="mock">샘플 데이터 · 서버 미연결</p>

        <div class="strip">
          <div
            v-for="(b, i) in blocks"
            :key="b._key"
            class="qc"
            :class="{
              dragging: dragIndex === i,
              'ins-before': overIndex === i && dragIndex !== null && dragIndex > i,
              'ins-after': overIndex === i && dragIndex !== null && dragIndex < i,
            }"
            draggable="true"
            @dragstart="onCardDragStart(i, $event)"
            @dragover="onCardDragOver(i, $event)"
            @drop="onCardDrop(i, $event)"
            @dragend="onCardDragEnd"
            :title="btitle(b)"
          >
            <div class="th" :style="bthumb(b) ? coverStyle(bcid(b)) : {}">
              <span v-if="!bthumb(b)" class="emoji">{{ bemoji(b) }}</span>
              <span v-if="bdur(b)" class="dur">{{ bdur(b) }}</span>
              <button class="rm" @click.stop="removeBlock(i)" title="삭제">🗑</button>
            </div>
            <div class="t">{{ btitle(b) }}</div>
          </div>

          <button class="addcard" @click="openPicker" title="항목 추가">
            <span class="plus">＋</span><span class="al">추가</span>
          </button>
        </div>
        <div v-if="!blocks.length" class="hint">＋ 로 동영상·사진·음악을 담아 목록을 만드세요.</div>
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

      <!-- 항목 피커 -->
      <div v-if="picker" class="picker-ov" @click.self="picker = false">
        <div class="picker">
          <div class="ph-head">
            <b>항목 추가</b>
            <button class="x2" @click="picker = false">✕</button>
          </div>
          <div class="ph-cats">
            <button
              v-for="c in PICKER_CATS"
              :key="c.k"
              class="cat"
              :class="{ on: pickerCat === c.k }"
              @click="setPickerCat(c.k)"
            >
              {{ c.label }}
            </button>
            <span v-if="pickerFolders.length" class="catdiv"></span>
            <button
              v-for="f in pickerFolders"
              :key="'pf' + f.id"
              class="cat"
              :class="{ on: pickerCat === 'folder:' + f.id }"
              @click="setPickerCat('folder:' + f.id)"
            >
              📁 {{ f.name }}
            </button>
          </div>
          <div class="ph-list">
            <button v-for="m in pickerList" :key="m.content_id" class="pick" @click="choose(m.content_id)">
              <span class="pt" :style="m.thumb_url ? coverStyle(m.content_id) : { background: thumbGradient(m) }">
                <span v-if="!m.thumb_url">{{ typeEmoji(m.media_type) }}</span>
              </span>
              <span class="pn">{{ m.title }}</span>
              <span v-if="m.media_type !== 'photo'" class="pd">{{ formatTime(m.duration) }}</span>
            </button>
            <div v-if="!pickerList.length" class="empty">이 카테고리에 담을 미디어가 없습니다.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 열림 애니메이션 (App 의 <Transition name="modal">) */
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
  width: 760px;
  max-width: 100%;
  max-height: 88vh;
  overflow-y: auto;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
}
.dbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--bd);
  background: #151c21;
  border-radius: 16px 16px 0 0;
  position: sticky;
  top: 0;
  z-index: 2;
}
.nmwrap { display: flex; align-items: center; gap: 5px; min-width: 0; }
.dt { font-size: 16px; font-weight: 720; letter-spacing: -0.01em; }
.pen { opacity: 0.55; border: none; background: transparent; color: var(--muted); font-size: 12px; }
.nmwrap:hover .pen { opacity: 1; }
.nmedit { background: var(--bg); border: 1px solid var(--teal); border-radius: 6px; color: var(--text); font-size: 15px; font-weight: 700; padding: 4px 8px; }
.grow { flex: 1; }
.notice { font-size: 11.5px; color: var(--teal); }
.x { border: none; background: var(--elev); color: var(--muted); font-size: 13px; width: 30px; height: 30px; border-radius: 8px; }
.ctrls { display: flex; align-items: center; gap: 9px; padding: 13px 16px 4px; flex-wrap: wrap; }
.btn { font-size: 12px; font-weight: 600; padding: 7px 12px; border-radius: 8px; border: 1px solid var(--bd); background: var(--elev); color: var(--text); }
.btn.acc { background: var(--accent); border-color: var(--accent); color: #fff; }
.opt { font-size: 11.5px; font-weight: 600; padding: 6px 11px; border-radius: 8px; border: 1px solid var(--bd); background: var(--elev); color: var(--muted); }
.opt.on { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 50%, transparent); }
.banner { margin: 8px 16px 0; padding: 8px 12px; border-radius: 9px; font-size: 11.5px; background: color-mix(in srgb, var(--teal) 13%, transparent); border: 1px solid color-mix(in srgb, var(--teal) 40%, transparent); }
.banner b { color: var(--teal); }
.mock { margin: 8px 16px 0; font-size: 10.5px; color: var(--warn); font-family: var(--font-mono); }

/* 가로 썸네일 스트립 */
.strip {
  display: flex;
  gap: 10px;
  align-items: stretch;
  padding: 14px 16px 16px;
  overflow-x: auto;
}
.qc {
  width: 132px;
  flex: none;
  border-radius: 10px;
  padding: 4px;
  border: 1px solid transparent;
  cursor: grab;
  position: relative;
}
.qc.dragging { opacity: 0.4; }
.qc.ins-before::before,
.qc.ins-after::after {
  content: '';
  position: absolute;
  top: 4px;
  bottom: 4px;
  width: 3px;
  border-radius: 2px;
  background: var(--teal);
}
.qc.ins-before::before { left: -5px; }
.qc.ins-after::after { right: -5px; }
.qc .th {
  height: 76px;
  border-radius: 7px;
  background: #1a2129;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.qc .emoji { font-size: 22px; }
.qc .dur { position: absolute; left: 5px; bottom: 5px; font-family: var(--font-mono); font-size: 9px; background: rgba(0, 0, 0, 0.6); color: #fff; padding: 1px 5px; border-radius: 4px; }
.qc .rm {
  position: absolute;
  right: 5px;
  top: 5px;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: none;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 12px;
  display: grid;
  place-items: center;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}
.qc:hover .rm { opacity: 1; }
.qc .rm:hover { background: #c0392b; }
.qc .t { font-size: 11px; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
.addcard {
  width: 88px;
  flex: none;
  border: 1px dashed var(--bd);
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  display: grid;
  place-items: center;
  gap: 3px;
  align-content: center;
}
.addcard .plus { font-size: 22px; color: var(--teal); }
.addcard .al { font-size: 11px; }
.hint { font-size: 11.5px; color: var(--faint); font-style: italic; padding: 0 16px 18px; margin: -6px 0 0; }
.empty { color: var(--faint); font-size: 13px; padding: 24px; text-align: center; }

/* 피커 */
.picker-ov { position: fixed; inset: 0; background: rgba(8, 11, 13, 0.7); display: grid; place-items: center; z-index: 30; padding: 20px; }
.picker { width: 380px; max-width: 100%; max-height: 70vh; display: flex; flex-direction: column; background: var(--sf); border: 1px solid var(--bd); border-radius: 13px; overflow: hidden; }
.ph-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--bd); }
.ph-head .x2 { border: none; background: transparent; color: var(--faint); font-size: 14px; }
.ph-cats {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  padding: 9px 10px;
  border-bottom: 1px solid var(--bd);
}
.ph-cats .cat {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 16px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--muted);
}
.ph-cats .cat.on { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.ph-cats .catdiv { width: 1px; align-self: stretch; background: var(--bd); margin: 1px 2px; }
.ph-list { overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.pick { display: flex; align-items: center; gap: 10px; padding: 7px 9px; border-radius: 8px; border: 1px solid transparent; background: transparent; color: var(--text); text-align: left; }
.pick:hover { background: var(--elev); border-color: var(--bd); }
.pick .pt { width: 40px; height: 28px; border-radius: 5px; display: grid; place-items: center; font-size: 14px; flex: none; overflow: hidden; }
.pick .pn { flex: 1; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pick .pd { font-family: var(--font-mono); font-size: 10.5px; color: var(--faint); }
</style>
