<script setup>
// 공용 타임라인 에디터 — 플리 편집 모달과 현재 재생목록(라이브)에서 함께 사용.
// 사진·동영상·음악을 셀로 한 줄 배치, 아래 '음악 줄'에서 음악 셀을 사진 아래로 끌면
// 그 사진의 배경음악(노래 바)이 됨. 바 양끝 핸들로 여러 사진에 걸침.
// blocks(도메인 블록 dict[])를 받아 편집하고, 변경 시 change(blocks)로 되돌려준다.
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { folders as folderApi } from '../api.js'
import { typeEmoji, thumbGradient } from '../mediaView.js'
import { formatTime } from '../format.js'

const props = defineProps({
  blocks: { type: Array, default: () => [] },
  mediaMap: { type: Object, default: () => ({}) },
  allMedia: { type: Array, default: () => [] },
  pickerFolders: { type: Array, default: () => [] },
  currentId: { type: String, default: null },
  enableJump: { type: Boolean, default: false },
  seedKey: { default: 0 },
})
const emit = defineEmits(['change', 'activate'])

const CELL_W = 96
const GAP = 12
const STRIDE = CELL_W + GAP

let _seq = 0
const nk = () => `s${++_seq}`

const segments = ref([]) // {key, type:'video'|'photo'|'music', content_id, sec?}
const songs = ref([])    // {key, music_id, coverKeys:[photoKey,...]}

onMounted(() => deserialize(props.blocks))
watch(() => props.seedKey, () => deserialize(props.blocks))

function deserialize(blocks) {
  const segs = []
  const sgs = []
  for (const b of blocks || []) {
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

function idxOf(key) { return segments.value.findIndex((s) => s.key === key) }
function songBounds(sg) {
  const a = idxOf(sg.coverKeys[0])
  const b = idxOf(sg.coverKeys[sg.coverKeys.length - 1])
  return [Math.min(a, b), Math.max(a, b)]
}
function musicDur(mid) { return props.mediaMap[mid]?.duration || 0 }
function songCovering(i) {
  return songs.value.find((sg) => { const [a, b] = songBounds(sg); return i >= a && i <= b })
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
function emitChange() { emit('change', serialize()) }

// 셀 i가 속한 블록 인덱스(라이브 점프용)
function blockIndexOf(cellIdx) {
  const segs = segments.value
  let bi = -1
  let i = 0
  while (i < segs.length) {
    const s = segs[i]
    if (s.type === 'video' || s.type === 'music') {
      bi++; if (i === cellIdx) return bi; i++; continue
    }
    const song = songCovering(i)
    if (song) {
      const [a, b] = songBounds(song); bi++
      if (cellIdx >= a && cellIdx <= b) return bi
      i = b + 1
    } else {
      const start = i; bi++
      while (i < segs.length && segs[i].type === 'photo' && !songCovering(i)) i++
      if (cellIdx >= start && cellIdx < i) return bi
    }
  }
  return bi
}

// ---- 셀 편집 ----
function healSongs() {
  songs.value = songs.value.map((sg) => {
    const positions = sg.coverKeys.map(idxOf).filter((i) => i >= 0).sort((a, b) => a - b)
    if (!positions.length) return null
    const start = positions[0]
    let end = start
    const posSet = new Set(positions)
    while (end + 1 < segments.value.length && posSet.has(end + 1) && segments.value[end + 1].type === 'photo') end++
    const keys = []
    for (let j = start; j <= end; j++) if (segments.value[j].type === 'photo') keys.push(segments.value[j].key)
    return keys.length ? { ...sg, coverKeys: keys } : null
  }).filter(Boolean)
}
function removeCell(i) { segments.value.splice(i, 1); healSongs(); emitChange() }
function setPhotoSec(seg, e) { const s = Number(e.target.value); if (s > 0) { seg.sec = s; emitChange() } }
function onCellClick(i) { if (props.enableJump) emit('activate', blockIndexOf(i)) }

const dragIndex = ref(null)
const overIndex = ref(null)
function isCellDrag(e) { return [...(e.dataTransfer?.types || [])].includes('application/x-pidio-cell') }
function onCellDragStart(i, e) {
  dragIndex.value = i
  e.dataTransfer.setData('application/x-pidio-cell', String(i))
  e.dataTransfer.effectAllowed = 'move'
}
function onCellDragOver(i, e) { if (!isCellDrag(e)) return; e.preventDefault(); overIndex.value = i }
function onCellDrop(i, e) {
  if (!isCellDrag(e)) return
  e.preventDefault()
  const from = dragIndex.value
  dragIndex.value = null; overIndex.value = null
  if (from === null || from === i) return
  const arr = [...segments.value]
  const [m] = arr.splice(from, 1)
  arr.splice(i, 0, m)
  segments.value = arr
  healSongs(); emitChange()
}
function onCellDragEnd() { dragIndex.value = null; overIndex.value = null }

// ---- 음악 셀 → 음악 줄(사진 아래)로 드롭 → 배경음악 ----
const laneEl = ref(null)
const laneOver = ref(false)
function cellIndexAtX(x) { return Math.max(0, Math.min(segments.value.length - 1, Math.floor(x / STRIDE))) }
function onLaneDragOver(e) { if (!isCellDrag(e)) return; e.preventDefault(); laneOver.value = true }
function onLaneDrop(e) {
  laneOver.value = false
  if (!isCellDrag(e)) return
  e.preventDefault()
  const from = Number(e.dataTransfer.getData('application/x-pidio-cell'))
  const seg = segments.value[from]
  if (!seg || seg.type !== 'music') { flash('음악 파일만 사진 아래에 걸 수 있어요.'); return }
  const rect = laneEl.value.getBoundingClientRect()
  const targetIdx = cellIndexAtX(e.clientX - rect.left)
  const target = segments.value[targetIdx]
  if (!target || target.type !== 'photo') { flash('사진 셀 아래에 놓아야 노래가 걸립니다.'); return }
  const targetKey = target.key
  const musicId = seg.content_id
  segments.value.splice(from, 1)
  const tIdx = idxOf(targetKey)
  if (songCovering(tIdx)) {
    segments.value.push({ key: nk(), type: 'music', content_id: musicId })
    flash('그 사진엔 이미 노래가 걸려 있어요.')
    return
  }
  songs.value.push({ key: nk(), music_id: musicId, coverKeys: [targetKey] })
  healSongs(); emitChange()
}

// ---- 노래 바 좌우 핸들 ----
let handleDrag = null
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
  e.preventDefault(); e.stopPropagation()
  handleDrag = { sg, side }
  window.addEventListener('pointermove', onHandleMove)
  window.addEventListener('pointerup', onHandleUp)
}
function onHandleMove(e) {
  if (!handleDrag || !laneEl.value) return
  const rect = laneEl.value.getBoundingClientRect()
  const idx = cellIndexAtX(e.clientX - rect.left)
  const { sg, side } = handleDrag
  const [s0, s1] = songBounds(sg)
  const others = coveredByOthers(sg)
  const isFreePhoto = (j) => j >= 0 && j < segments.value.length && segments.value[j].type === 'photo' && !others.has(j)
  if (side === 'right') {
    let maxEnd = s0
    while (maxEnd + 1 < segments.value.length && isFreePhoto(maxEnd + 1)) maxEnd++
    setCover(sg, s0, Math.max(s0, Math.min(idx, maxEnd)))
  } else {
    let minStart = s1
    while (minStart - 1 >= 0 && isFreePhoto(minStart - 1)) minStart--
    setCover(sg, Math.min(s1, Math.max(idx, minStart)), s1)
  }
}
function onHandleUp() {
  window.removeEventListener('pointermove', onHandleMove)
  window.removeEventListener('pointerup', onHandleUp)
  handleDrag = null
  emitChange()
}
function setCover(sg, a, b) {
  const keys = []
  for (let j = a; j <= b; j++) if (segments.value[j].type === 'photo') keys.push(segments.value[j].key)
  if (keys.length) sg.coverKeys = keys
}
function removeSong(sg) {
  const [, b] = songBounds(sg)
  songs.value = songs.value.filter((s) => s !== sg)
  segments.value.splice(b + 1, 0, { key: nk(), type: 'music', content_id: sg.music_id })
  healSongs(); emitChange()
}
function barStyle(sg) {
  const [a, b] = songBounds(sg)
  return { left: a * STRIDE + 'px', width: (b - a + 1) * CELL_W + (b - a) * GAP + 'px' }
}

// ---- 추가 피커 ----
const picker = ref(false)
const PICKER_CATS = [
  { k: 'all', label: '전체' },
  { k: 'video', label: '🎬 동영상' },
  { k: 'photo', label: '🖼 사진' },
  { k: 'music', label: '🎵 음악' },
]
const pickerCat = ref('all')
const pickerFolderIds = ref([])
function openItemPicker() { pickerCat.value = 'all'; picker.value = true }
async function setPickerCat(k) {
  pickerCat.value = k
  if (k.startsWith('folder:')) {
    try { pickerFolderIds.value = (await folderApi.get(Number(k.slice(7)))).content_ids } catch { pickerFolderIds.value = [] }
  }
}
const pickerList = computed(() => {
  if (pickerCat.value.startsWith('folder:')) {
    const s = new Set(pickerFolderIds.value)
    return props.allMedia.filter((m) => s.has(m.content_id))
  }
  return pickerCat.value === 'all' ? props.allMedia : props.allMedia.filter((m) => m.media_type === pickerCat.value)
})
function choose(cid) {
  const m = props.mediaMap[cid]
  picker.value = false
  if (!m) return
  const seg = { key: nk(), type: m.media_type, content_id: cid }
  if (m.media_type === 'photo') seg.sec = m.photo_sec ?? 5
  segments.value.push(seg)
  emitChange()
}

// ---- 표시 헬퍼 ----
function segTitle(seg) { const m = props.mediaMap[seg.content_id]; return m ? m.title : seg.content_id }
function segThumb(seg) { return seg.type === 'music' ? null : `/thumb/${seg.content_id}` }
function segEmoji(seg) { return seg.type === 'video' ? '🎬' : seg.type === 'music' ? '🎵' : '🖼' }
function photoSecDisplay(i) { const song = songCovering(i); return song ? perPhotoSec(song).toFixed(1) : null }
function coverStyle(cid) { return { backgroundImage: `url(/thumb/${cid})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundColor: '#1a2129' } }

const notice = ref('')
let nt = null
function flash(msg) { notice.value = msg; clearTimeout(nt); nt = setTimeout(() => (notice.value = ''), 2400) }

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onHandleMove)
  window.removeEventListener('pointerup', onHandleUp)
})

defineExpose({ openItemPicker })
</script>

<template>
  <div class="tlwrap">
    <p v-if="notice" class="tlnotice">{{ notice }}</p>
    <div class="tl">
      <div class="track">
        <div class="cells">
          <div
            v-for="(seg, i) in segments"
            :key="seg.key"
            class="cell"
            :class="[seg.type, { over: overIndex === i, dragging: dragIndex === i, cur: seg.content_id === currentId }]"
            :style="{ width: CELL_W + 'px' }"
            draggable="true"
            @dragstart="onCellDragStart(i, $event)"
            @dragover="onCellDragOver(i, $event)"
            @drop="onCellDrop(i, $event)"
            @dragend="onCellDragEnd"
            :title="segTitle(seg)"
          >
            <div class="cth" :style="segThumb(seg) && seg.type !== 'music' ? coverStyle(seg.content_id) : {}" @click="onCellClick(i)">
              <span v-if="seg.type === 'music' || !segThumb(seg)" class="cemoji">{{ segEmoji(seg) }}</span>
              <span v-if="seg.content_id === currentId" class="curbadge">▶</span>
              <button class="crm" @click.stop="removeCell(i)" title="삭제">✕</button>
              <span v-if="seg.type === 'photo' && photoSecDisplay(i) !== null" class="csec auto">{{ photoSecDisplay(i) }}초</span>
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

        <div
          ref="laneEl"
          class="lane"
          :class="{ drop: laneOver }"
          :style="{ minWidth: segments.length * STRIDE + 'px' }"
          @dragover="onLaneDragOver"
          @dragleave="laneOver = false"
          @drop="onLaneDrop"
        >
          <div v-for="sg in songs" :key="sg.key" class="songbar" :style="barStyle(sg)" :title="mediaMap[sg.music_id]?.title">
            <span class="h left" @pointerdown="startHandle(sg, 'left', $event)"></span>
            <span class="slabel">🎵 {{ mediaMap[sg.music_id]?.title || '음악' }} · {{ formatTime(perPhotoSec(sg)) }}/장</span>
            <button class="srm" @click="removeSong(sg)" title="노래 떼기(음악 셀로)">✕</button>
            <span class="h right" @pointerdown="startHandle(sg, 'right', $event)"></span>
          </div>
          <div v-if="!songs.length" class="laneempty">🎵 음악 줄 — 음악 셀을 사진 아래로 끌어다 놓으면 그 사진의 배경음악이 됩니다</div>
        </div>
      </div>
    </div>

    <!-- 항목 피커 -->
    <div v-if="picker" class="picker-ov" @click.self="picker = false">
      <div class="picker">
        <div class="ph-head">
          <b>항목 추가 (동영상·사진·음악)</b>
          <button class="x2" @click="picker = false">✕</button>
        </div>
        <div class="ph-cats">
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
</template>

<style scoped>
.tlnotice { font-size: 11px; color: var(--teal); margin: 0 0 6px; }
.tl { overflow-x: auto; padding-bottom: 4px; }
.track { display: inline-block; min-width: 100%; }
.cells { display: flex; gap: 12px; align-items: flex-start; }
.cell { flex: none; border-radius: 10px; padding: 4px; border: 1px solid transparent; cursor: grab; position: relative; }
.cell.dragging { opacity: 0.4; }
.cell.cur { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent); }
.cell.over::before { content: ''; position: absolute; left: -7px; top: 3px; bottom: 3px; width: 3px; border-radius: 2px; background: var(--teal); }
.cell .cth { height: 66px; border-radius: 7px; background: #1a2129; position: relative; display: grid; place-items: center; overflow: hidden; cursor: pointer; }
.cell.music .cth { background: linear-gradient(135deg, #3a4a86, #7c3f6b); }
.cell .cemoji { font-size: 22px; }
.cell .curbadge { position: absolute; left: 5px; top: 5px; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 9px; display: grid; place-items: center; }
.cell .crm { position: absolute; right: 4px; top: 4px; width: 20px; height: 20px; border-radius: 6px; border: none; background: rgba(0, 0, 0, 0.55); color: #fff; font-size: 11px; display: grid; place-items: center; opacity: 0; transition: opacity 0.15s, background 0.15s; z-index: 2; }
.cell:hover .crm { opacity: 1; }
.cell .crm:hover { background: #c0392b; }
.cell .csec { position: absolute; left: 4px; bottom: 4px; font-size: 9px; color: #fff; background: rgba(0, 0, 0, 0.72); border-radius: 4px; padding: 1px 4px; display: flex; align-items: center; gap: 1px; }
.cell .csec.auto { background: color-mix(in srgb, var(--teal) 75%, #000); font-weight: 700; }
.cell .csec .secin { width: 22px; background: transparent; border: none; border-bottom: 1px solid rgba(255,255,255,0.5); color: #fff; font-family: var(--font-mono); font-size: 10px; text-align: right; padding: 0; -moz-appearance: textfield; }
.cell .csec .secin::-webkit-outer-spin-button, .cell .csec .secin::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.cell .ct { font-size: 10.5px; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); max-width: 96px; }
.addcell { flex: none; height: 66px; border: 1px dashed var(--bd); border-radius: 10px; background: transparent; color: var(--muted); display: grid; place-items: center; align-content: center; gap: 2px; }
.addcell .plus { font-size: 20px; color: var(--teal); }
.addcell .al { font-size: 10px; }
.lane { position: relative; min-height: 42px; margin-top: 8px; border-top: 1px dashed var(--bd); padding-top: 8px; border-radius: 0 0 8px 8px; transition: background 0.15s; }
.lane.drop { background: color-mix(in srgb, var(--accent) 14%, transparent); outline: 2px dashed color-mix(in srgb, var(--accent) 60%, transparent); outline-offset: -2px; }
.laneempty { font-size: 10.5px; color: var(--faint); padding-top: 6px; }
.songbar { position: absolute; top: 8px; height: 26px; border-radius: 7px; background: color-mix(in srgb, var(--accent) 30%, #1a2129); border: 1px solid var(--accent); display: flex; align-items: center; gap: 4px; padding: 0 3px; overflow: hidden; }
.songbar .slabel { flex: 1; font-size: 9.5px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px; }
.songbar .h { width: 9px; align-self: stretch; cursor: ew-resize; flex: none; border-radius: 4px; background: var(--accent); }
.songbar .h:hover { background: #fff; }
.songbar .srm { border: none; background: rgba(0,0,0,0.4); color: #fff; font-size: 9px; width: 16px; height: 16px; border-radius: 4px; flex: none; }
.picker-ov { position: fixed; inset: 0; background: rgba(8,11,13,0.7); display: grid; place-items: center; z-index: 30; padding: 20px; }
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
.empty { color: var(--faint); font-size: 13px; padding: 20px; text-align: center; }
</style>
