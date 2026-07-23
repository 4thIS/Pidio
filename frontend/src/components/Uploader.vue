<script setup>
// D-6 업로드 — 화면 아무 곳에 드롭 → 청크 업로드 + 진행률.
// 백엔드 /api/upload/* 는 Task 7.2 로 완성되어 실제 업로드가 동작한다.
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { uploadFile, mediaTypeOf } from '../upload.js'
import { ApiError } from '../api.js'

const emit = defineEmits(['uploaded'])

const dragging = ref(false)
const jobs = reactive([]) // {name, percent, state:'up'|'done'|'err', msg}
let depth = 0 // dragenter/leave 중첩 카운트
const fileInput = ref(null)

function onDragEnter(e) {
  if (!hasFiles(e)) return
  depth++
  dragging.value = true
}
function onDragOver(e) {
  if (hasFiles(e)) e.preventDefault() // drop 허용
}
function onDragLeave() {
  depth = Math.max(0, depth - 1)
  if (depth === 0) dragging.value = false
}
function onDrop(e) {
  e.preventDefault()
  depth = 0
  dragging.value = false
  const files = [...(e.dataTransfer?.files || [])]
  if (files.length) start(files)
}
function hasFiles(e) {
  return [...(e.dataTransfer?.types || [])].includes('Files')
}

function pick() {
  fileInput.value?.click()
}
function onPicked(e) {
  const files = [...(e.target.files || [])]
  if (files.length) start(files)
  e.target.value = '' // 같은 파일 다시 선택 가능하게
}

async function start(files) {
  for (const f of files) {
    const job = reactive({ name: f.name, percent: 0, state: 'up', msg: '' })
    jobs.unshift(job)

    if (!mediaTypeOf(f.name)) {
      job.state = 'err'
      job.msg = '지원하지 않는 형식'
      continue
    }
    try {
      await uploadFile(f, (p) => (job.percent = p))
      job.percent = 100
      job.state = 'done'
      emit('uploaded')
    } catch (err) {
      job.state = 'err'
      job.msg =
        err instanceof ApiError && err.status === 409
          ? 'USB가 연결되어 있지 않습니다'
          : err instanceof ApiError && err.status === 401
            ? '로그인이 필요합니다'
            : '업로드 실패'
    }
  }
  // 완료된 항목은 잠시 후 정리
  setTimeout(() => {
    for (let i = jobs.length - 1; i >= 0; i--) if (jobs[i].state === 'done') jobs.splice(i, 1)
  }, 4000)
}

onMounted(() => {
  window.addEventListener('dragenter', onDragEnter)
  window.addEventListener('dragover', onDragOver)
  window.addEventListener('dragleave', onDragLeave)
  window.addEventListener('drop', onDrop)
})
onBeforeUnmount(() => {
  window.removeEventListener('dragenter', onDragEnter)
  window.removeEventListener('dragover', onDragOver)
  window.removeEventListener('dragleave', onDragLeave)
  window.removeEventListener('drop', onDrop)
})

defineExpose({ pick })
</script>

<template>
  <div>
    <input ref="fileInput" type="file" multiple hidden @change="onPicked" />

    <!-- 드롭 오버레이 -->
    <div v-if="dragging" class="drop-ov">
      <div class="drop-in">
        <div class="big">📥</div>
        <div class="t">여기에 파일을 놓으세요</div>
        <div class="s">동영상 · 사진 · 음악 · 여러 개 한꺼번에 OK</div>
      </div>
    </div>

    <!-- 진행률 패널 -->
    <div v-if="jobs.length" class="uplist">
      <div class="ut">업로드 {{ jobs.filter((j) => j.state === 'up').length }}개 진행 중</div>
      <div v-for="(j, i) in jobs" :key="i" class="uprow" :class="j.state">
        <div class="nm">
          <span class="fn">{{ j.name }}</span>
          <span class="st">
            {{ j.state === 'done' ? '완료 ✓' : j.state === 'err' ? j.msg : j.percent + '%' }}
          </span>
        </div>
        <div class="bar"><i :style="{ width: j.percent + '%' }"></i></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drop-ov {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--accent) 20%, rgba(10, 13, 15, 0.82));
  backdrop-filter: blur(2px);
  display: grid;
  place-items: center;
  z-index: 50;
  pointer-events: none;
}
.drop-in {
  border: 2.5px dashed color-mix(in srgb, var(--accent) 70%, #fff);
  border-radius: 16px;
  padding: 34px 54px;
  text-align: center;
}
.drop-in .big { font-size: 40px; }
.drop-in .t { font-size: 16px; font-weight: 700; margin-top: 10px; }
.drop-in .s { font-size: 12px; color: #e9c2cd; margin-top: 4px; }

.uplist {
  position: fixed;
  right: 16px;
  bottom: 16px;
  width: 270px;
  max-height: 50vh;
  overflow-y: auto;
  background: var(--elev);
  border: 1px solid var(--bd);
  border-radius: 11px;
  padding: 11px;
  z-index: 40;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
}
.ut { font-size: 11px; color: var(--muted); margin-bottom: 9px; font-weight: 600; }
.uprow { font-size: 11.5px; margin-bottom: 9px; }
.uprow .nm { display: flex; justify-content: space-between; gap: 8px; }
.uprow .fn { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.uprow .st { font-family: var(--font-mono); color: var(--teal); flex: none; }
.uprow.done .st { color: #57b57c; }
.uprow.err .st { color: var(--danger); }
.uprow .bar {
  height: 5px;
  border-radius: 3px;
  background: #2b353d;
  margin-top: 5px;
  overflow: hidden;
}
.uprow .bar i { display: block; height: 100%; background: var(--teal); border-radius: 3px; transition: width 0.2s; }
.uprow.done .bar i { background: #57b57c; }
.uprow.err .bar i { background: var(--danger); }
</style>
