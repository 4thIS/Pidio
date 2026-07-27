<script setup>
// 현재 재생목록(라이브) — 공용 Timeline 에디터로 표시·편집. 편집은 라이브 큐에 즉시 반영.
// 음악 셀을 사진 아래로 끌면 배경음악이 됨(에디터와 동일). 헤더에서 비우기·새 플리로 저장.
import { ref, computed, watch, onMounted } from 'vue'
import { store } from '../store.js'
import { player as playerApi, playlists as plApi, media as mediaApi, folders as folderApi } from '../api.js'
import { formatTime } from '../format.js'
import Timeline from './Timeline.vue'

const emit = defineEmits(['saved'])

const blocks = ref([])
const source = ref(null)
const seedKey = ref(0)
const allMedia = ref([])
const pickerFolders = ref([])
const mediaMap = computed(() => Object.fromEntries(allMedia.value.map((m) => [m.content_id, m])))
const currentId = computed(() => store.player?.current_id || null)

onMounted(loadMedia)
async function loadMedia() {
  try { const d = await mediaApi.list('all'); allMedia.value = Array.isArray(d) ? d : [] } catch { allMedia.value = [] }
  try { pickerFolders.value = await folderApi.list() } catch { pickerFolders.value = [] }
}

async function reload() {
  try {
    const [q, qb] = await Promise.all([playerApi.queue(), playerApi.queueBlocks()])
    source.value = q.source_playlist || null
    blocks.value = qb.blocks || []
  } catch {
    source.value = null
    blocks.value = []
  }
  seedKey.value++
}
// 큐 구조(길이·출처)가 바뀌면 다시 시드. 진행 위치(current)는 시드 없이 하이라이트만.
watch(
  () => { const p = store.player; return p ? `${p.queue_len}|${p.source_label}` : 'none' },
  reload,
  { immediate: true },
)

// Timeline 편집 → 라이브 큐에 반영
function applyLive(newBlocks) {
  playerApi.setBlocks(newBlocks).catch(() => {})
}
function jumpTo(blockIndex) {
  playerApi.jump(blockIndex).catch(() => {})
}

function clearQueue() {
  if (!blocks.value.length) return
  if (!confirm('현재 재생목록을 비울까요? (재생이 멈추고 대기화면이 됩니다)')) return
  playerApi.action('stop').then(reload).catch(() => {})
}
function saveQueue() {
  if (!blocks.value.length) return
  const name = (prompt('새 플레이리스트 이름', source.value?.name ? source.value.name + ' 복사' : '재생목록') || '').trim()
  if (!name) return
  playerApi.saveQueue(name).then(() => { emit('saved'); flash(`"${name}"으로 저장했습니다.`) }).catch(() => flash('저장에 실패했습니다.'))
}

// 바깥에서 드롭(미디어 추가 / 플리 교체)
const dragOver = ref(false)
function onDragOver(e) {
  const t = [...(e.dataTransfer?.types || [])]
  if (t.includes('application/x-pidio-media') || t.includes('application/x-pidio-playlist')) {
    e.preventDefault(); dragOver.value = true
  }
}
function onDrop(e) {
  dragOver.value = false
  const media = e.dataTransfer.getData('application/x-pidio-media')
  const pl = e.dataTransfer.getData('application/x-pidio-playlist')
  if (media) {
    e.preventDefault()
    const { content_ids } = JSON.parse(media)
    // 추가만 요청 — 큐 갱신은 SSE(queue_len 변경)로 자동 재시드(중복 fetch 제거로 지연 감소)
    playerApi.queueAdd(content_ids).catch(() => {})
  } else if (pl) {
    e.preventDefault()
    const { id } = JSON.parse(pl)
    plApi.play(id).catch(() => {})
  }
}
function coverStyle(c) { return { backgroundImage: `url(/thumb/${c})`, backgroundSize: 'cover', backgroundColor: '#1a2129' } }

const notice = ref('')
let nt = null
function flash(msg) { notice.value = msg; clearTimeout(nt); nt = setTimeout(() => (notice.value = ''), 2600) }
</script>

<template>
  <section class="pq" :class="{ over: dragOver }" @dragover="onDragOver" @dragleave="dragOver = false" @drop="onDrop">
    <div class="pqhead">
      <span class="pqtitle">재생목록</span>
      <span v-if="notice" class="pqnotice">{{ notice }}</span>
      <span class="grow"></span>
      <button class="clearq" :disabled="!blocks.length" @click="clearQueue" title="재생목록 비우기">🗑 비우기</button>
      <button class="saveq" :disabled="!blocks.length" @click="saveQueue" title="현재 재생목록을 새 플레이리스트로 저장">💾 새 플리로 저장</button>
    </div>

    <div class="pqbody">
      <div v-if="source" class="plcard">
        <button class="plx" @click.stop="clearQueue" title="이 플레이리스트를 재생목록에서 비우기">✕</button>
        <div class="cover">
          <span v-for="(c, i) in (source.cover_content_ids || []).slice(0, 3)" :key="i" class="s" :class="'s' + i" :style="coverStyle(c)"></span>
        </div>
        <div class="nm">{{ source.name }}</div>
        <div class="mt"><span>{{ source.item_count }}개</span><span>{{ formatTime(source.total_sec) }}</span></div>
      </div>

      <Timeline
        :blocks="blocks"
        :media-map="mediaMap"
        :all-media="allMedia"
        :picker-folders="pickerFolders"
        :current-id="currentId"
        :enable-jump="true"
        :seed-key="seedKey"
        @change="applyLive"
        @activate="jumpTo"
      />
    </div>
  </section>
</template>

<style scoped>
.pq.over { outline: 2px dashed var(--accent); outline-offset: -4px; }
.pq { padding: 10px 16px 12px; background: #141a1f; border-bottom: 1px solid var(--bd); }
.pqhead { display: flex; align-items: center; gap: 9px; margin-bottom: 9px; }
.pqtitle { font-size: 12px; font-weight: 680; color: var(--muted); letter-spacing: -0.01em; }
.pqnotice { font-size: 11px; color: var(--teal); }
.grow { flex: 1; }
.clearq { font-size: 11px; font-weight: 600; padding: 6px 11px; border-radius: 8px; border: 1px solid var(--bd); background: var(--elev); color: var(--muted); }
.clearq:hover:not(:disabled) { color: #fff; background: #c0392b; border-color: #c0392b; }
.clearq:disabled { opacity: 0.4; }
.saveq { font-size: 11px; font-weight: 600; padding: 6px 11px; border-radius: 8px; border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent); background: color-mix(in srgb, var(--accent) 15%, transparent); color: var(--accent); }
.saveq:disabled { opacity: 0.4; }
.pqbody { display: flex; align-items: flex-start; gap: 12px; }
.plcard { width: 132px; flex: none; background: var(--sf); border: 1px solid var(--bd); border-radius: 10px; padding: 8px; position: relative; }
.plcard .plx { position: absolute; right: 5px; top: 5px; width: 20px; height: 20px; border-radius: 6px; border: none; background: rgba(0,0,0,0.5); color: #fff; font-size: 11px; display: grid; place-items: center; opacity: 0; transition: opacity 0.15s, background 0.15s; z-index: 3; }
.plcard:hover .plx { opacity: 1; }
.plcard .plx:hover { background: #c0392b; }
.plcard .cover { height: 62px; border-radius: 7px; position: relative; overflow: hidden; background: #0f1519; }
.plcard .s { position: absolute; width: 40px; height: 50px; border-radius: 5px; top: 6px; box-shadow: 0 3px 8px rgba(0,0,0,0.4); }
.plcard .s0 { left: 12px; transform: rotate(-9deg); }
.plcard .s1 { left: 38px; transform: rotate(3deg); }
.plcard .s2 { left: 62px; transform: rotate(12deg); }
.plcard .nm { font-size: 11.5px; font-weight: 640; margin-top: 7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.plcard .mt { font-size: 10px; color: var(--faint); margin-top: 2px; display: flex; justify-content: space-between; }
</style>
