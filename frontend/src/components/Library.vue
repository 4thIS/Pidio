<script setup>
// D-3 전체 목록 — 타입 탭 · 체크박스 다중선택 · 넷플릭스 호버 미리보기.
import { ref, reactive, computed, onMounted } from 'vue'
import MediaCard from './MediaCard.vue'
import { media as mediaApi, play as playApi, ApiError } from '../api.js'
import { MOCK_MEDIA } from '../mock.js'

const TABS = [
  { k: 'all', label: '전체' },
  { k: 'video', label: '🎬 동영상' },
  { k: 'photo', label: '🖼 사진' },
  { k: 'music', label: '🎵 음악' },
]
const tab = ref('all')
const items = ref([])
const usingMock = ref(false)
const loading = ref(true)
const selected = reactive(new Set())

onMounted(load)
async function load() {
  loading.value = true
  try {
    const data = await mediaApi.list('all')
    items.value = Array.isArray(data) ? data : []
    usingMock.value = false
  } catch {
    items.value = MOCK_MEDIA // 서버 미연결 시 샘플로 폴백
    usingMock.value = true
  } finally {
    loading.value = false
  }
}

const filtered = computed(() =>
  tab.value === 'all' ? items.value : items.value.filter((m) => m.media_type === tab.value),
)

function toggle(id) {
  selected.has(id) ? selected.delete(id) : selected.add(id)
}
function clearSel() {
  selected.clear()
}

async function saveTitle(id, title) {
  const it = items.value.find((m) => m.content_id === id)
  try {
    await mediaApi.patchTitle(id, title)
    if (it) it.title = title
  } catch {
    if (it) it.title = title // 낙관적 갱신(샘플/오프라인)
    if (!usingMock.value) notify('제목 저장에 실패했습니다.')
  }
}

async function playSelection() {
  try {
    await playApi.selection([...selected], {})
    notify(`${selected.size}개 재생을 요청했습니다.`)
  } catch {
    notify('재생 요청을 처리하지 못했습니다.')
  }
}
function todo(what) {
  // 큐 추가·목록 저장은 아직 미구현 기능(엔드포인트 없음).
  notify(`${what} 기능은 준비 중입니다.`)
}

const notice = ref('')
let nt = null
function notify(msg) {
  notice.value = msg
  clearTimeout(nt)
  nt = setTimeout(() => (notice.value = ''), 2800)
}
</script>

<template>
  <section class="lib">
    <div class="head">
      <h3>전체 목록</h3>
      <span class="src">USB 라이브러리</span>
      <span v-if="usingMock" class="mock">샘플 데이터 · 서버 미연결</span>
    </div>

    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.k"
        class="tab"
        :class="{ on: tab === t.k }"
        @click="tab = t.k"
      >
        {{ t.label }}
      </button>
    </div>

    <div v-if="selected.size" class="selbar">
      <span class="cnt">{{ selected.size }}개 선택됨</span>
      <button class="sbtn" @click="playSelection">▶ 선택 재생</button>
      <button class="sbtn" @click="todo('큐에 추가')">＋ 큐에 추가</button>
      <button class="sbtn" @click="todo('목록으로 저장')">💾 목록으로 저장</button>
      <button class="sbtn ghost" @click="clearSel">선택 해제</button>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="loading" class="empty">불러오는 중…</div>
    <div v-else-if="!filtered.length" class="empty">이 유형의 미디어가 없습니다.</div>
    <div v-else class="grid">
      <MediaCard
        v-for="m in filtered"
        :key="m.content_id"
        :item="m"
        :selected="selected.has(m.content_id)"
        @toggle="toggle"
        @save-title="saveTitle"
      />
    </div>
  </section>
</template>

<style scoped>
.lib { padding: 16px; }
.head {
  display: flex;
  align-items: baseline;
  gap: 9px;
  margin: 2px 2px 12px;
  flex-wrap: wrap;
}
.head h3 {
  font-size: 13px;
  font-weight: 680;
  margin: 0;
  letter-spacing: -0.01em;
}
.head .src {
  font-size: 11px;
  color: var(--faint);
  font-family: var(--font-mono);
}
.head .mock {
  font-size: 10.5px;
  color: var(--warn);
  font-family: var(--font-mono);
  border: 1px solid color-mix(in srgb, var(--warn) 40%, transparent);
  background: color-mix(in srgb, var(--warn) 12%, transparent);
  padding: 1px 7px;
  border-radius: 20px;
}
.tabs {
  display: flex;
  gap: 5px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tab {
  font-size: 12px;
  padding: 6px 13px;
  border-radius: 20px;
  border: 1px solid var(--bd);
  color: var(--muted);
  background: var(--sf);
}
.tab.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 600;
}
.selbar {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 11px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--muted);
}
.selbar .cnt { color: var(--text); font-weight: 600; }
.sbtn {
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 7px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.sbtn.ghost { color: var(--muted); background: transparent; }
.notice {
  font-size: 11.5px;
  color: var(--warn);
  margin: 0 0 11px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 11px;
}
.empty {
  color: var(--faint);
  font-size: 13px;
  padding: 24px 4px;
  text-align: center;
}
</style>
