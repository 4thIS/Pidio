<script setup>
// 재생 큐 패널 — 헤더(새 플리로 저장) + 왼쪽 재생중 플리 정보 + 오른쪽 큐 목록(썸네일).
// 항목: X로 큐에서 삭제, 드래그로 순서변경, 사진은 표시시간 편집.
import { ref, watch } from 'vue'
import { store } from '../store.js'
import { player as playerApi, playlists as plApi } from '../api.js'
import { formatTime } from '../format.js'

const emit = defineEmits(['edit'])

const items = ref([])
const source = ref(null)
const added = ref([]) // 플리 재생 중 즉석 추가한 파일들(썸네일 겹침 표시용)
const notice = ref('')

async function load() {
  try {
    const d = await playerApi.queue()
    items.value = Array.isArray(d.items) ? d.items : []
    source.value = d.source_playlist || null
  } catch {
    items.value = []
    source.value = null
  }
}

watch(
  () => {
    const p = store.player
    return p ? `${p.queue_len}|${p.current_index}|${p.source_label}` : 'none'
  },
  load,
  { immediate: true },
)
watch(() => source.value?.id ?? null, () => { added.value = [] })

function jump(i) {
  playerApi.jump(i).catch(() => {})
}

let nt = null
function flash(msg) {
  notice.value = msg
  clearTimeout(nt)
  nt = setTimeout(() => (notice.value = ''), 2600)
}

// ---- 편집 · 새 플리로 저장(#1) → 타임라인 에디터 열기 ----
function openEditor() {
  if (!items.value.length) return
  emit('edit')
}

// ---- 항목 삭제(#3) ----
function removeItem(i, e) {
  e?.stopPropagation()
  playerApi.queueRemove(i).then(load).catch(() => {})
}

// ---- 사진 표시시간(#4) ----
function onSecChange(i, e) {
  const s = Number(e.target.value)
  if (s > 0) playerApi.setPhotoSec(i, s).then(load).catch(() => {})
}

// ---- 바깥에서 드롭(미디어 추가 / 플리 교체) ----
const dragOver = ref(false)
function onDragOver(e) {
  const t = [...(e.dataTransfer?.types || [])]
  if (t.includes('application/x-pidio-media') || t.includes('application/x-pidio-playlist')) {
    e.preventDefault()
    dragOver.value = true
  }
}
function onDrop(e) {
  dragOver.value = false
  const media = e.dataTransfer.getData('application/x-pidio-media')
  const pl = e.dataTransfer.getData('application/x-pidio-playlist')
  if (media) {
    e.preventDefault()
    const { content_ids } = JSON.parse(media)
    playerApi.queueAdd(content_ids).then(() => {
      load()
      if (source.value) content_ids.forEach((c) => { if (!added.value.includes(c)) added.value.push(c) })
    }).catch(() => {})
  } else if (pl) {
    e.preventDefault()
    const { id } = JSON.parse(pl)
    plApi.play(id).catch(() => {}) // 플리 드롭 → 그 재생목록으로 교체
  }
}

// ---- 큐 내부 순서 변경 ----
const dragIndex = ref(null)
const overIndex = ref(null)
function isQueueDrag(e) {
  return [...(e.dataTransfer?.types || [])].includes('application/x-pidio-queue')
}
function onVidDragStart(i, e) {
  dragIndex.value = i
  e.dataTransfer.setData('application/x-pidio-queue', String(i))
  e.dataTransfer.effectAllowed = 'move'
}
function onVidDragOver(i, e) {
  if (!isQueueDrag(e)) return
  e.preventDefault()
  e.stopPropagation()
  overIndex.value = i
}
function onVidDrop(i, e) {
  if (!isQueueDrag(e)) return
  e.preventDefault()
  e.stopPropagation()
  const from = dragIndex.value
  dragIndex.value = null
  overIndex.value = null
  if (from === null || from === i) return
  playerApi.reorder(from, i).then(load).catch(() => {})
}
function onVidDragEnd() {
  dragIndex.value = null
  overIndex.value = null
}

function coverStyle(c) {
  return { backgroundImage: `url(/thumb/${c})`, backgroundSize: 'cover', backgroundColor: '#1a2129' }
}
</script>

<template>
  <section class="pq" :class="{ over: dragOver }" @dragover="onDragOver" @dragleave="dragOver = false" @drop="onDrop">
    <div class="pqhead">
      <span class="pqtitle">재생목록</span>
      <span v-if="notice" class="pqnotice">{{ notice }}</span>
      <span class="grow"></span>
      <button class="saveq" :disabled="!items.length" @click="openEditor" title="현재 재생목록을 편집하고 새 플레이리스트로 저장">
        🎬 편집 · 새 플리로 저장
      </button>
    </div>

    <div class="pqbody">
      <template v-if="source">
        <div class="plcard">
          <div class="cover">
            <span
              v-for="(c, i) in (source.cover_content_ids || []).slice(0, 3)"
              :key="i" class="s" :class="'s' + i" :style="coverStyle(c)"
            ></span>
            <div v-if="added.length" class="added" :title="`추가된 ${added.length}개`">
              <span v-for="c in added.slice(0, 3)" :key="c" class="am" :style="coverStyle(c)"></span>
              <span v-if="added.length > 3" class="amore">+{{ added.length - 3 }}</span>
            </div>
          </div>
          <div class="nm">{{ source.name }}</div>
          <div class="mt">
            <span>{{ source.item_count }}개<template v-if="added.length"> +{{ added.length }}</template></span>
            <span>{{ formatTime(source.total_sec) }}</span>
          </div>
        </div>
        <div class="divider"></div>
      </template>

      <div v-if="!items.length" class="hint">여기에 동영상/플레이리스트를 드래그해 재생목록에 추가</div>
      <div v-else class="vids">
        <div
          v-for="(it, i) in items" :key="i" class="vid"
          :class="{
            cur: it.current,
            dragging: dragIndex === i,
            'ins-before': overIndex === i && dragIndex !== null && dragIndex > i,
            'ins-after': overIndex === i && dragIndex !== null && dragIndex < i,
          }"
          :title="it.title"
          draggable="true"
          @dragstart="onVidDragStart(i, $event)"
          @dragover="onVidDragOver(i, $event)"
          @drop="onVidDrop(i, $event)"
          @dragend="onVidDragEnd"
        >
          <div class="th" :style="it.thumb_url ? coverStyle(it.content_id) : {}" @click="jump(i)">
            <span v-if="!it.thumb_url">🎬</span>
            <span v-if="it.current" class="badge">▶</span>
            <button class="rmx" @click.stop="removeItem(i, $event)" title="재생목록에서 삭제">✕</button>
            <span v-if="it.media_type === 'photo'" class="secbox" @click.stop>
              <input class="secin" type="number" min="1" step="1" :value="it.photo_sec ?? 5" @change="onSecChange(i, $event)" @click.stop />초
            </span>
          </div>
          <div class="t">{{ it.title }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.pq.over { outline: 2px dashed var(--accent); outline-offset: -4px; }
.pq {
  padding: 10px 16px 12px;
  background: #141a1f;
  border-bottom: 1px solid var(--bd);
}
.pqhead {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 9px;
}
.pqtitle { font-size: 12px; font-weight: 680; color: var(--muted); letter-spacing: -0.01em; }
.pqnotice { font-size: 11px; color: var(--teal); }
.grow { flex: 1; }
.saveq {
  font-size: 11px;
  font-weight: 600;
  padding: 6px 11px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent);
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
}
.saveq:disabled { opacity: 0.4; }
.pqbody {
  display: flex;
  align-items: stretch;
  gap: 12px;
  overflow-x: auto;
}
.hint { color: var(--faint); font-size: 12px; padding: 6px 2px; }
.plcard {
  width: 132px;
  flex: none;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 10px;
  padding: 8px;
}
.plcard .cover {
  height: 62px;
  border-radius: 7px;
  position: relative;
  overflow: hidden;
  background: #0f1519;
}
.plcard .s {
  position: absolute;
  width: 40px;
  height: 50px;
  border-radius: 5px;
  top: 6px;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.4);
}
.plcard .s0 { left: 12px; transform: rotate(-9deg); }
.plcard .s1 { left: 38px; transform: rotate(3deg); }
.plcard .s2 { left: 62px; transform: rotate(12deg); }
.plcard .added {
  position: absolute;
  right: 4px;
  bottom: 4px;
  display: flex;
  align-items: center;
  z-index: 2;
}
.plcard .added .am {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  border: 1.5px solid #141a1f;
  background-size: cover;
  background-position: center;
  margin-left: -8px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.5);
}
.plcard .added .am:first-child { margin-left: 0; }
.plcard .added .amore {
  margin-left: 3px;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  background: rgba(0, 0, 0, 0.72);
  border-radius: 4px;
  padding: 1px 4px;
}
.plcard .nm { font-size: 11.5px; font-weight: 640; margin-top: 7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.plcard .mt { font-size: 10px; color: var(--faint); margin-top: 2px; display: flex; justify-content: space-between; }
.divider { width: 1px; background: var(--bd); flex: none; margin: 2px 0; }
.vids { display: flex; gap: 9px; align-items: stretch; }
.vid {
  width: 108px;
  flex: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 9px;
  padding: 4px;
  cursor: grab;
  text-align: left;
  position: relative;
}
.vid.cur { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent); }
.vid.dragging { opacity: 0.4; }
/* 세로 삽입선(| 느낌): 드래그 방향에 맞춰 대상 카드의 왼쪽(앞)/오른쪽(뒤)에 표시 */
.vid.ins-before::before,
.vid.ins-after::after {
  content: '';
  position: absolute;
  top: 3px;
  bottom: 3px;
  width: 3px;
  border-radius: 2px;
  background: var(--teal);
  box-shadow: 0 0 6px color-mix(in srgb, var(--teal) 70%, transparent);
}
.vid.ins-before::before { left: -6px; }
.vid.ins-after::after { right: -6px; }
.vid .th {
  height: 60px;
  border-radius: 6px;
  background: #1a2129;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  font-size: 18px;
  cursor: pointer;
}
.vid .th .badge {
  position: absolute;
  right: 5px;
  bottom: 5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  display: grid;
  place-items: center;
}
.vid .th .rmx {
  position: absolute;
  right: 4px;
  top: 4px;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: none;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 11px;
  display: grid;
  place-items: center;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
  z-index: 2;
}
.vid:hover .th .rmx { opacity: 1; }
.vid .th .rmx:hover { background: #c0392b; }
.vid .th .secbox {
  position: absolute;
  left: 4px;
  bottom: 4px;
  display: flex;
  align-items: center;
  gap: 1px;
  font-size: 9px;
  color: #fff;
  background: rgba(0, 0, 0, 0.72);
  border-radius: 4px;
  padding: 1px 4px;
  z-index: 2;
}
.vid .th .secin {
  width: 24px;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
  color: #fff;
  font-family: var(--font-mono);
  font-size: 10px;
  text-align: right;
  padding: 0;
  -moz-appearance: textfield;
}
.vid .th .secin::-webkit-outer-spin-button,
.vid .th .secin::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.vid .t {
  font-size: 11px;
  margin-top: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
}
.vid.cur .t { color: var(--accent); font-weight: 640; }
</style>
