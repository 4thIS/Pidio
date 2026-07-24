<script setup>
// 재생 큐 패널 — 재생바 아래 가로. 왼쪽: 재생중 플리 정보(+구분선), 오른쪽: 큐 동영상 목록.
// 즉석선택(플리 아님) 재생이면 플리 정보 없이 목록만.
import { ref, watch } from 'vue'
import { store } from '../store.js'
import { player as playerApi, playlists as plApi } from '../api.js'
import { formatTime } from '../format.js'

const items = ref([])
const source = ref(null)

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

// 큐 길이·현재 인덱스·출처가 바뀌면 다시 로드
watch(
  () => {
    const p = store.player
    return p ? `${p.queue_len}|${p.current_index}|${p.source_label}` : 'none'
  },
  load,
  { immediate: true },
)

function jump(i) {
  playerApi.jump(i).catch(() => {})
}

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
    const { content_id } = JSON.parse(media)
    playerApi.queueAdd([content_id]).then(load).catch(() => {})
  } else if (pl) {
    e.preventDefault()
    const { id } = JSON.parse(pl)
    plApi.play(id).catch(() => {}) // 플리 드롭 → 그 재생목록으로 교체
  }
}
function coverStyle(c) {
  return { backgroundImage: `url(/thumb/${c})`, backgroundSize: 'cover', backgroundColor: '#1a2129' }
}
</script>

<template>
  <section class="pq" :class="{ over: dragOver }" @dragover="onDragOver" @dragleave="dragOver = false" @drop="onDrop">
    <template v-if="source">
      <div class="plcard">
        <div class="cover">
          <span
            v-for="(c, i) in (source.cover_content_ids || []).slice(0, 3)"
            :key="i" class="s" :class="'s' + i" :style="coverStyle(c)"
          ></span>
        </div>
        <div class="nm">{{ source.name }}</div>
        <div class="mt">
          <span>{{ source.item_count }}개</span>
          <span>{{ formatTime(source.total_sec) }}</span>
        </div>
      </div>
      <div class="divider"></div>
    </template>

    <div v-if="!items.length" class="hint">여기에 동영상/플레이리스트를 드래그해 재생목록에 추가</div>
    <div v-else class="vids">
      <button
        v-for="(it, i) in items" :key="i" class="vid" :class="{ cur: it.current }"
        @click="jump(i)" :title="it.title"
      >
        <div class="th" :style="it.thumb_url ? coverStyle(it.content_id) : {}">
          <span v-if="!it.thumb_url">🎬</span>
          <span v-if="it.current" class="badge">▶</span>
        </div>
        <div class="t">{{ it.title }}</div>
      </button>
    </div>
  </section>
</template>

<style scoped>
.pq.over { outline: 2px dashed var(--accent); outline-offset: -4px; }
.pq .hint { color: var(--faint); font-size: 12px; padding: 6px 2px; }
.pq {
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 12px 16px;
  background: #141a1f;
  border-bottom: 1px solid var(--bd);
  overflow-x: auto;
}
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
  cursor: pointer;
  text-align: left;
}
.vid.cur { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent); }
.vid .th {
  height: 60px;
  border-radius: 6px;
  background: #1a2129;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  font-size: 18px;
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
