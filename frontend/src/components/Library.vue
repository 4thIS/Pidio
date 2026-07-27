<script setup>
// D-3 전체 목록 — 타입 탭 · 폴더(수동 그룹) · 체크박스 다중선택 · 넷플릭스 호버 미리보기.
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import MediaCard from './MediaCard.vue'
import { media as mediaApi, player as playerApi, folders as folderApi } from '../api.js'
import { MOCK_MEDIA } from '../mock.js'

const emit = defineEmits(['media-deleted', 'upload-files'])

const TYPE_TABS = [
  { k: 'all', label: '전체' },
  { k: 'video', label: '🎬 동영상' },
  { k: 'photo', label: '🖼 사진' },
  { k: 'music', label: '🎵 음악' },
]
const tab = ref('all') // 'all'|'video'|'photo'|'music'|'folder:<id>'
const items = ref([])
const foldersList = ref([]) // [{id,name,item_count}]
const folderIds = ref([]) // 현재 폴더 탭의 content_id 목록
const dragFolderId = ref(null) // 드래그 오버 중인 폴더 탭
const usingMock = ref(false)
const loading = ref(true)
const selected = reactive(new Set())

const activeFolder = computed(() =>
  tab.value.startsWith('folder:') ? Number(tab.value.slice(7)) : null,
)
const activeFolderObj = computed(() =>
  foldersList.value.find((f) => f.id === activeFolder.value) || null,
)

onMounted(async () => {
  await Promise.all([load(), loadFolders()])
})

// 화면 어디든(카드가 아닌 빈 공간·다른 영역) 클릭하면 선택 해제(#7)
function onDocClick(e) {
  if (selected.size && !e.target.closest('.card')) selected.clear()
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

async function load() {
  loading.value = true
  try {
    const data = await mediaApi.list('all')
    items.value = Array.isArray(data) ? data : []
    usingMock.value = false
  } catch {
    items.value = MOCK_MEDIA
    usingMock.value = true
  } finally {
    loading.value = false
  }
}
async function loadFolders() {
  try {
    foldersList.value = await folderApi.list()
  } catch {
    foldersList.value = []
  }
}

async function selectTab(k) {
  tab.value = k
  selected.clear()
  if (k.startsWith('folder:')) {
    try {
      const f = await folderApi.get(Number(k.slice(7)))
      folderIds.value = f.content_ids
    } catch {
      folderIds.value = []
    }
  }
}

// 정렬 토글: 추가순↑ → 추가순↓ → 이름순↑ → 이름순↓
const SORTS = ['added_asc', 'added_desc', 'name_asc', 'name_desc']
const sortLabels = {
  added_asc: '↑ 추가순',
  added_desc: '↓ 추가순',
  name_asc: '↑ 이름순',
  name_desc: '↓ 이름순',
}
const sortMode = ref('added_asc')
function cycleSort() {
  sortMode.value = SORTS[(SORTS.indexOf(sortMode.value) + 1) % SORTS.length]
}

const filtered = computed(() => {
  let base
  if (activeFolder.value !== null) {
    const set = new Set(folderIds.value)
    base = items.value.filter((m) => set.has(m.content_id))
  } else {
    base = tab.value === 'all' ? items.value : items.value.filter((m) => m.media_type === tab.value)
  }
  const arr = [...base]
  const name = (m) => m.title || ''
  const added = (m) => m.first_seen || ''
  if (sortMode.value === 'name_asc') arr.sort((a, b) => name(a).localeCompare(name(b)))
  else if (sortMode.value === 'name_desc') arr.sort((a, b) => name(b).localeCompare(name(a)))
  else if (sortMode.value === 'added_desc') arr.sort((a, b) => added(b).localeCompare(added(a)))
  else arr.sort((a, b) => added(a).localeCompare(added(b))) // added_asc(오래된→최근)
  return arr
})

function toggle(id) {
  selected.has(id) ? selected.delete(id) : selected.add(id)
}
function clearSel() {
  selected.clear()
}
// 다중선택 드래그용: 배열을 prop으로 넘기면 선택 변경 시 전체 카드가 리렌더됨.
// 안정적인 함수(참조 불변)로 넘겨 드래그 시작 순간에만 읽게 해 리렌더를 막는다.
const getSelected = () => [...selected]

// 사진 표시시간 저장(#4)
async function setPhotoSec(id, sec) {
  const it = items.value.find((m) => m.content_id === id)
  try {
    await mediaApi.setPhotoSec(id, sec)
    if (it) it.photo_sec = sec
  } catch {
    if (it) it.photo_sec = sec
    if (!usingMock.value) notify('시간 저장에 실패했습니다.')
  }
}

// ---- 업로드 드롭존(라이브러리 영역 한정, #6) ----
const uploadOver = ref(false)
let upDepth = 0
function hasFiles(e) {
  return [...(e.dataTransfer?.types || [])].includes('Files')
}
function onLibDragEnter(e) {
  if (!hasFiles(e)) return
  upDepth++
  uploadOver.value = true
}
function onLibDragOver(e) {
  if (hasFiles(e)) e.preventDefault()
}
function onLibDragLeave() {
  upDepth = Math.max(0, upDepth - 1)
  if (upDepth === 0) uploadOver.value = false
}
function onLibDrop(e) {
  if (!hasFiles(e)) return
  e.preventDefault()
  upDepth = 0
  uploadOver.value = false
  const files = [...(e.dataTransfer?.files || [])]
  if (files.length) emit('upload-files', files)
}

async function saveTitle(id, title) {
  const it = items.value.find((m) => m.content_id === id)
  try {
    await mediaApi.patchTitle(id, title)
    if (it) it.title = title
  } catch {
    if (it) it.title = title
    if (!usingMock.value) notify('제목 저장에 실패했습니다.')
  }
}

async function addToQueue(id) {
  try {
    await playerApi.queueAdd([id])
    notify('재생목록에 추가했습니다.')
  } catch {
    notify('추가하지 못했습니다.')
  }
}

// 카드 🗑 — 폴더 탭에선 폴더에서 제거(파일 유지), 타입 탭에선 실제 파일 삭제
async function deleteMedia(id) {
  if (activeFolder.value !== null) {
    const f = activeFolderObj.value
    if (!confirm(`"${f?.name}" 폴더에서 이 파일을 뺄까요? (파일 자체는 유지)`)) return
    try {
      await folderApi.removeItem(activeFolder.value, id)
      folderIds.value = folderIds.value.filter((c) => c !== id)
      await loadFolders()
      notify('폴더에서 제거했습니다.')
    } catch {
      notify('제거하지 못했습니다.')
    }
    return
  }
  if (!confirm('이 파일을 삭제할까요? (USB에서 제거됩니다)')) return
  try {
    await mediaApi.remove(id)
    items.value = items.value.filter((m) => m.content_id !== id)
    selected.delete(id)
    await loadFolders() // 폴더 카운트 갱신
    emit('media-deleted', id)
    notify('삭제했습니다.')
  } catch {
    notify('삭제하지 못했습니다.')
  }
}

// ---- 폴더 생성 ----
async function createFolder() {
  const name = (prompt('새 폴더 이름', '새 폴더') || '').trim()
  if (!name) return
  try {
    const r = await folderApi.create(name)
    await loadFolders()
    if (r?.id) await selectTab('folder:' + r.id)
  } catch {
    notify('폴더를 만들지 못했습니다.')
  }
}

// ---- 폴더 탭: 미디어 드롭(추가) + 폴더 드롭(순서변경) 겸용 ----
function onFolderTabDragStart(e, idx) {
  e.dataTransfer.setData('application/x-pidio-folder', String(idx))
  e.dataTransfer.effectAllowed = 'move'
}
function onFolderDragOver(e, f) {
  const t = [...(e.dataTransfer?.types || [])]
  if (t.includes('application/x-pidio-media') || t.includes('application/x-pidio-folder')) {
    e.preventDefault()
    dragFolderId.value = f.id
  }
}
function onFolderDrop(e, f) {
  dragFolderId.value = null
  const media = e.dataTransfer.getData('application/x-pidio-media')
  const fold = e.dataTransfer.getData('application/x-pidio-folder')
  if (media) {
    e.preventDefault()
    const { content_ids } = JSON.parse(media)
    folderApi
      .addItems(f.id, content_ids)
      .then(async () => {
        await loadFolders()
        if (activeFolder.value === f.id) await selectTab('folder:' + f.id)
        notify(`"${f.name}"에 ${content_ids.length}개 추가됨.`)
      })
      .catch(() => notify('추가하지 못했습니다.'))
  } else if (fold !== '') {
    e.preventDefault()
    const from = Number(fold)
    const to = foldersList.value.findIndex((x) => x.id === f.id)
    if (from === to || from < 0 || to < 0) return
    const arr = [...foldersList.value]
    const [moved] = arr.splice(from, 1)
    arr.splice(to, 0, moved)
    foldersList.value = arr
    folderApi.reorder(arr.map((x) => x.id)).catch(() => loadFolders())
  }
}

// ---- 폴더 삭제(폴더만 / 파일까지) ----
const folderToDelete = ref(null)
function askDeleteFolder(f) {
  folderToDelete.value = f
}
async function doDeleteFolder(withMedia) {
  const f = folderToDelete.value
  folderToDelete.value = null
  if (!f) return
  try {
    await folderApi.remove(f.id, withMedia)
    if (withMedia) {
      await load()
      emit('media-deleted')
    }
    await loadFolders()
    if (activeFolder.value === f.id) tab.value = 'all'
    notify(withMedia ? '폴더와 파일을 삭제했습니다.' : '폴더를 삭제했습니다.')
  } catch {
    notify('폴더 삭제에 실패했습니다.')
  }
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
  <section
    class="lib"
    @click.self="clearSel"
    @dragenter="onLibDragEnter"
    @dragover="onLibDragOver"
    @dragleave="onLibDragLeave"
    @drop="onLibDrop"
  >
    <div class="head">
      <h3>전체 목록</h3>
      <span class="src">USB 라이브러리</span>
      <span v-if="selected.size" class="selcnt">{{ selected.size }}개 선택됨</span>
      <span v-if="usingMock" class="mock">샘플 데이터 · 서버 미연결</span>
      <button class="sortbtn" @click="cycleSort" title="정렬 순서 바꾸기">{{ sortLabels[sortMode] }}</button>
    </div>

    <div class="tabs">
      <button
        v-for="t in TYPE_TABS"
        :key="t.k"
        class="tab"
        :class="{ on: tab === t.k }"
        @click="selectTab(t.k)"
      >
        {{ t.label }}
      </button>

      <span class="tabdiv"></span>

      <button
        v-for="(f, fi) in foldersList"
        :key="'f' + f.id"
        class="tab folder"
        :class="{ on: activeFolder === f.id, drop: dragFolderId === f.id }"
        draggable="true"
        @dragstart="onFolderTabDragStart($event, fi)"
        @click="selectTab('folder:' + f.id)"
        @dragover="onFolderDragOver($event, f)"
        @dragleave="dragFolderId = null"
        @drop="onFolderDrop($event, f)"
      >
        📁 {{ f.name }} <span class="fc">{{ f.item_count }}</span>
        <span class="fx" @click.stop="askDeleteFolder(f)" title="폴더 삭제">✕</span>
      </button>

      <button class="tab addf" @click="createFolder" title="새 폴더 만들기">＋ 폴더</button>
    </div>

    <p v-if="activeFolder !== null" class="fhint">
      전체·동영상·사진·음악 탭에서 파일을 이 폴더 탭 위로 드래그하면 담깁니다.
    </p>

    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="loading" class="empty">불러오는 중…</div>
    <div v-else-if="!filtered.length" class="empty" @click="clearSel">
      {{ activeFolder !== null ? '이 폴더는 비어 있습니다. 파일을 드래그해 담아보세요.' : '이 유형의 미디어가 없습니다.' }}
    </div>
    <div v-else class="grid" @click.self="clearSel">
      <MediaCard
        v-for="m in filtered"
        :key="m.content_id"
        :item="m"
        :selected="selected.has(m.content_id)"
        :get-selected="getSelected"
        :delete-icon="activeFolder !== null ? '⊘' : '🗑'"
        :delete-title="activeFolder !== null ? '폴더에서 빼기' : '삭제'"
        @toggle="toggle"
        @save-title="saveTitle"
        @add-queue="addToQueue"
        @delete="deleteMedia"
        @set-photo-sec="setPhotoSec"
      />
    </div>

    <!-- 업로드 드롭 오버레이(라이브러리 영역 한정) -->
    <div v-if="uploadOver" class="up-ov">
      <div class="up-in">📥 여기에 놓으면 업로드 (동영상·사진·음악)</div>
    </div>

    <!-- 폴더 삭제 다이얼로그 -->
    <div v-if="folderToDelete" class="fd-ov" @click.self="folderToDelete = null">
      <div class="fd">
        <div class="fd-t">"{{ folderToDelete.name }}" 폴더를 삭제할까요?</div>
        <div class="fd-s">폴더만 삭제하면 안의 파일은 전체 목록에 그대로 남습니다.</div>
        <div class="fd-btns">
          <button class="fd-b ghost" @click="folderToDelete = null">취소</button>
          <button class="fd-b" @click="doDeleteFolder(false)">폴더만 삭제</button>
          <button class="fd-b danger" @click="doDeleteFolder(true)">파일까지 삭제</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lib { padding: 16px; position: relative; }
.up-ov {
  position: absolute;
  inset: 8px;
  border: 2.5px dashed color-mix(in srgb, var(--accent) 75%, #fff);
  border-radius: 14px;
  background: color-mix(in srgb, var(--accent) 16%, rgba(10, 13, 15, 0.72));
  display: grid;
  place-items: center;
  z-index: 15;
  pointer-events: none;
}
.up-in { font-size: 14px; font-weight: 700; color: #fff; }
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
.head .selcnt {
  font-size: 11.5px;
  color: var(--muted);
}
.head .sortbtn {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: 20px;
  border: 1px solid var(--bd);
  background: var(--sf);
  color: var(--muted);
}
.head .sortbtn:hover { color: var(--text); border-color: var(--muted); }
.tabs {
  display: flex;
  gap: 5px;
  margin-bottom: 10px;
  flex-wrap: wrap;
  align-items: center;
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
.tabdiv {
  width: 1px;
  align-self: stretch;
  background: var(--bd);
  margin: 2px 3px;
}
.tab.addf {
  border-style: dashed;
  color: var(--teal);
  border-color: color-mix(in srgb, var(--teal) 45%, transparent);
  background: transparent;
}
.tab.folder {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.tab.folder .fc {
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  opacity: 0.75;
}
.tab.folder .fx {
  font-size: 10px;
  opacity: 0;
  margin-left: 1px;
  border-radius: 4px;
  padding: 0 3px;
  transition: opacity 0.15s, background 0.15s;
}
.tab.folder:hover .fx { opacity: 0.7; }
.tab.folder .fx:hover { opacity: 1; background: rgba(192, 57, 43, 0.85); color: #fff; }
.tab.folder.drop {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 40%, transparent);
  color: var(--text);
}
.fhint {
  font-size: 11px;
  color: var(--faint);
  font-style: italic;
  margin: 0 0 10px;
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

/* 폴더 삭제 다이얼로그 */
.fd-ov {
  position: fixed;
  inset: 0;
  background: rgba(8, 11, 13, 0.72);
  display: grid;
  place-items: center;
  z-index: 30;
  padding: 20px;
}
.fd {
  width: 360px;
  max-width: 100%;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 13px;
  padding: 18px;
}
.fd-t { font-size: 14px; font-weight: 680; }
.fd-s { font-size: 11.5px; color: var(--muted); margin-top: 7px; line-height: 1.5; }
.fd-btns { display: flex; gap: 8px; margin-top: 16px; justify-content: flex-end; flex-wrap: wrap; }
.fd-b {
  font-size: 12px;
  font-weight: 600;
  padding: 8px 13px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.fd-b.ghost { color: var(--muted); background: transparent; }
.fd-b.danger { background: #c0392b; border-color: #c0392b; color: #fff; }
</style>
