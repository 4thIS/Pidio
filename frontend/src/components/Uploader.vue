<script setup>
// D-6 업로드 — 파일 선택/드롭(라이브러리 영역에서 처리) → 청크 업로드 + 진행률.
// 드롭 감지는 Library 가 담당하고(전체화면 아님), 여기선 실제 업로드 + 진행 패널만.
import { ref, reactive } from 'vue'
import { uploadFile, mediaTypeOf } from '../upload.js'
import { ApiError } from '../api.js'

const emit = defineEmits(['uploaded'])

const jobs = reactive([]) // {name, percent, state:'up'|'done'|'err', msg}
const fileInput = ref(null)

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
  setTimeout(() => {
    for (let i = jobs.length - 1; i >= 0; i--) if (jobs[i].state === 'done') jobs.splice(i, 1)
  }, 4000)
}

defineExpose({ pick, startFiles: start })
</script>

<template>
  <div>
    <input ref="fileInput" type="file" multiple hidden @change="onPicked" />

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
