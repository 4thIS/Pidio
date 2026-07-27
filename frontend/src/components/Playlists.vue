<script setup>
// D-4 플레이리스트 카드 목록 (가로 스크롤). 클릭 → 상세, ▶ → 재생.
import { ref, computed, onMounted } from 'vue'
import { playlists as plApi, ApiError } from '../api.js'
import { MOCK_PLAYLISTS, mediaById } from '../mock.js'
import { thumbGradient } from '../mediaView.js'
import { scheduleSummary } from '../schedule.js'
import { formatTime } from '../format.js'

const emit = defineEmits(['open'])

const items = ref([])
const usingMock = ref(false)
const notice = ref('')

onMounted(load)
async function load() {
  try {
    const d = await plApi.list()
    items.value = Array.isArray(d) ? d : []
    usingMock.value = false
  } catch {
    items.value = MOCK_PLAYLISTS
    usingMock.value = true
  }
}

function coverStyle(id) {
  return {
    backgroundImage: `url(/thumb/${id})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundColor: '#1a2129',
  }
}

async function play(pl) {
  try {
    await plApi.play(pl.id)
    notify(`"${pl.name}" 재생을 요청했습니다.`)
  } catch {
    notify('재생 요청을 처리하지 못했습니다.')
  }
}
async function create() {
  try {
    const r = await plApi.create('새 목록')
    if (r && r.id) emit('open', { id: r.id, justCreated: true }) // 빈 채로 닫으면 자동 삭제
  } catch {
    notify('새 목록을 만들지 못했습니다.')
  }
}

async function remove(pl) {
  if (!confirm(`"${pl.name}" 목록을 삭제할까요?`)) return
  try {
    await plApi.remove(pl.id)
    items.value = items.value.filter((x) => x.id !== pl.id)
    notify(`"${pl.name}" 삭제됨.`)
  } catch {
    notify('삭제하지 못했습니다.')
  }
}

const editingId = ref(null)
const draft = ref('')
function startEdit(pl) {
  editingId.value = pl.id
  draft.value = pl.name
}
async function commitEdit(pl) {
  const t = draft.value.trim()
  editingId.value = null
  if (!t || t === pl.name) return
  try {
    const full = await plApi.get(pl.id)
    await plApi.save(pl.id, {
      name: t,
      repeat_mode: full.repeat_mode,
      shuffle: full.shuffle,
      blocks: full.blocks || [],
    })
    pl.name = t
    notify('이름을 변경했습니다.')
  } catch {
    notify('이름 변경 실패.')
  }
}

const dragOverId = ref(null) // 미디어 추가 하이라이트
const dragId = ref(null)     // 재정렬 중인 플리 id
const overId = ref(null)     // 재정렬 드롭 대상 id
const dragFromIdx = computed(() => items.value.findIndex((x) => x.id === dragId.value))

function onCardDragStart(e, pl) {
  e.dataTransfer.setData('application/x-pidio-playlist', JSON.stringify({ id: pl.id }))
  e.dataTransfer.effectAllowed = 'copyMove'
  dragId.value = pl.id
}
function onCardDragEnd() {
  dragId.value = null
  overId.value = null
}
function onCardDragOver(e, pl) {
  const t = [...(e.dataTransfer?.types || [])]
  if (t.includes('application/x-pidio-media')) {
    e.preventDefault()
    dragOverId.value = pl.id
  } else if (t.includes('application/x-pidio-playlist')) {
    e.preventDefault()
    overId.value = pl.id
  }
}
function onCardDrop(e, pl) {
  dragOverId.value = null
  overId.value = null
  const media = e.dataTransfer.getData('application/x-pidio-media')
  const pld = e.dataTransfer.getData('application/x-pidio-playlist')
  if (media) {
    e.preventDefault()
    const { content_ids } = JSON.parse(media)
    plApi.add(pl.id, content_ids)
      .then(() => { pl.item_count = (pl.item_count || 0) + content_ids.length; notify(`"${pl.name}"에 ${content_ids.length}개 추가됨.`) })
      .catch(() => notify('추가하지 못했습니다.'))
  } else if (pld) {
    e.preventDefault()
    const { id } = JSON.parse(pld)
    if (id === pl.id) return
    const from = items.value.findIndex((x) => x.id === id)
    const to = items.value.findIndex((x) => x.id === pl.id)
    if (from < 0 || to < 0) return
    const arr = [...items.value]
    const [moved] = arr.splice(from, 1)
    arr.splice(to, 0, moved)
    items.value = arr
    plApi.reorder(arr.map((x) => x.id)).catch(() => load())
  }
}

let nt = null
function notify(msg) {
  notice.value = msg
  clearTimeout(nt)
  nt = setTimeout(() => (notice.value = ''), 2600)
}
</script>

<template>
  <section class="pls-sec">
    <div class="head">
      <h3>플레이리스트</h3>
      <span class="src">가로 스크롤 →</span>
      <span v-if="notice" class="notice">{{ notice }}</span>
    </div>

    <div class="pls">
      <div v-for="(pl, pi) in items" :key="pl.id" class="pl"
           :class="{
             dragover: dragOverId === pl.id,
             'ins-before': overId === pl.id && dragFromIdx > pi,
             'ins-after': overId === pl.id && dragFromIdx < pi,
           }"
           @click="emit('open', pl.id)"
           draggable="true" @dragstart="onCardDragStart($event, pl)" @dragend="onCardDragEnd"
           @dragover="onCardDragOver($event, pl)" @dragleave="dragOverId = null; overId = null" @drop="onCardDrop($event, pl)">
        <div class="cover">
          <span v-for="(c, i) in (pl.cover_content_ids || pl.cover || []).slice(0, 3)" :key="i" class="s" :class="'s' + i" :style="coverStyle(c)"></span>
          <button class="del" @click.stop="remove(pl)" aria-label="삭제" title="목록 삭제">🗑</button>
          <button class="play" @click.stop="play(pl)" aria-label="재생">▶</button>
        </div>
        <input
          v-if="editingId === pl.id"
          v-model="draft"
          class="nmedit"
          @click.stop
          @keyup.enter="commitEdit(pl)"
          @blur="commitEdit(pl)"
          @keyup.esc="editingId = null"
        />
        <div v-else class="nm">
          <span class="txt">{{ pl.name }}</span>
          <button class="pen" @click.stop="startEdit(pl)" aria-label="이름 수정">✎</button>
        </div>
        <div class="mt">
          <span>{{ pl.item_count }}개</span>
          <span>{{ formatTime(pl.total_sec) }}</span>
        </div>
        <div v-if="pl.schedule" class="sched" :title="scheduleSummary(pl.schedule)">
          🕒 {{ scheduleSummary(pl.schedule) }}
        </div>
      </div>

      <button class="pl add" @click="create">
        <div><div class="plus">＋</div>새 목록</div>
      </button>
    </div>
  </section>
</template>

<style scoped>
.pls-sec { padding: 16px 16px 0; }
.head {
  display: flex;
  align-items: baseline;
  gap: 9px;
  margin: 2px 2px 12px;
}
.head h3 { font-size: 13px; font-weight: 680; margin: 0; letter-spacing: -0.01em; }
.head .src { font-size: 11px; color: var(--faint); font-family: var(--font-mono); }
.head .notice { font-size: 11px; color: var(--teal); margin-left: auto; }
.pls {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 6px;
}
.pl {
  width: 150px;
  flex: none;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 11px;
  padding: 9px;
  cursor: pointer;
  transition: border-color 0.15s;
  position: relative;
}
.pl:hover { border-color: var(--muted); }
.pl.dragover { border-color: var(--accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 40%, transparent); }
/* 재정렬 삽입선(| 느낌): 드래그 방향에 맞춰 왼쪽(앞)/오른쪽(뒤) */
.pl.ins-before::before,
.pl.ins-after::after {
  content: '';
  position: absolute;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 2px;
  background: var(--teal);
  box-shadow: 0 0 6px color-mix(in srgb, var(--teal) 70%, transparent);
  z-index: 3;
}
.pl.ins-before::before { left: -7px; }
.pl.ins-after::after { right: -7px; }
.cover {
  height: 82px;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  background: #0f1519;
}
.cover .s {
  position: absolute;
  width: 52px;
  height: 64px;
  border-radius: 6px;
  top: 9px;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.4);
}
.cover .s0 { left: 16px; transform: rotate(-9deg); }
.cover .s1 { left: 46px; transform: rotate(3deg); }
.cover .s2 { left: 74px; transform: rotate(12deg); }
.cover .play {
  position: absolute;
  right: 7px;
  bottom: 7px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  display: grid;
  place-items: center;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 2;
}
.pl:hover .cover .play { opacity: 1; }
.cover .del {
  position: absolute;
  right: 6px;
  top: 6px;
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
  z-index: 2;
}
.pl:hover .cover .del { opacity: 1; }
.cover .del:hover { background: #c0392b; }
.nm {
  font-size: 12.5px;
  font-weight: 640;
  margin-top: 9px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.nm .txt { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nm .pen { opacity: 0; border: none; background: transparent; color: var(--muted); font-size: 11px; padding: 0 2px; flex: none; transition: opacity 0.15s; }
.pl:hover .nm .pen { opacity: 1; }
.nmedit { width: 100%; margin-top: 9px; background: var(--bg); border: 1px solid var(--teal); border-radius: 6px; color: var(--text); font-size: 12px; padding: 3px 6px; box-sizing: border-box; }
.mt {
  font-size: 11px;
  color: var(--faint);
  margin-top: 2px;
  display: flex;
  justify-content: space-between;
  font-variant-numeric: tabular-nums;
}
.sched {
  margin-top: 5px;
  font-size: 10px;
  color: var(--teal);
  background: color-mix(in srgb, var(--teal) 12%, transparent);
  border-radius: 5px;
  padding: 2px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pl.add {
  display: grid;
  place-items: center;
  color: var(--muted);
  border-style: dashed;
  min-height: 132px;
  font-size: 12px;
  background: transparent;
}
.pl.add > div { text-align: center; }
.pl.add .plus { font-size: 22px; }
</style>
