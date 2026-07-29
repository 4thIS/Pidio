<script setup>
// D-6 설정 (설계 §7.7) — 기본 재생목록 · 대기화면 이미지 · 사진 기본 표시시간 · 공용 비번 변경.
import { ref, onMounted } from 'vue'
import { settings as setApi, playlists as plApi, ApiError } from '../api.js'
import { MOCK_PLAYLISTS } from '../mock.js'

const emit = defineEmits(['close'])

const form = ref({ default_playlist_id: null, photo_default_sec: 5 })
const pls = ref([])
const usingMock = ref(false)
const loading = ref(true)
const notice = ref('')

// 비번 변경
const pw = ref({ old: '', new1: '', new2: '' })
const pwError = ref('')

// 테마(다크/라이트)
const theme = ref(localStorage.getItem('pidio-theme') || 'dark')
function setTheme(t) {
  theme.value = t
  localStorage.setItem('pidio-theme', t)
  document.documentElement.dataset.theme = t
}

onMounted(async () => {
  try {
    const s = await setApi.get()
    form.value = {
      default_playlist_id: s.default_playlist_id ?? null,
      photo_default_sec: s.photo_default_sec ?? 5,
    }
  } catch {
    usingMock.value = true
  }
  try {
    const d = await plApi.list()
    pls.value = Array.isArray(d) && d.length ? d : MOCK_PLAYLISTS
  } catch {
    pls.value = MOCK_PLAYLISTS
  }
  loading.value = false
})

function step(delta) {
  const v = Number(form.value.photo_default_sec) + delta
  form.value.photo_default_sec = Math.min(60, Math.max(1, v))
}

async function save() {
  try {
    await setApi.save({
      default_playlist_id: form.value.default_playlist_id,
      photo_default_sec: Number(form.value.photo_default_sec),
    })
    notify('설정을 저장했습니다.')
  } catch {
    notify('저장됨(서버 미연결 · 화면만 반영).')
  }
}

async function changePassword() {
  pwError.value = ''
  if (!pw.value.old || !pw.value.new1) {
    pwError.value = '현재 비밀번호와 새 비밀번호를 입력해 주세요.'
    return
  }
  if (pw.value.new1 !== pw.value.new2) {
    pwError.value = '새 비밀번호가 서로 다릅니다.'
    return
  }
  try {
    await setApi.changePassword(pw.value.old, pw.value.new1)
    pw.value = { old: '', new1: '', new2: '' }
    notify('비밀번호를 변경했습니다.')
  } catch (e) {
    pwError.value =
      e instanceof ApiError && e.status === 401
        ? '현재 비밀번호가 올바르지 않습니다.'
        : '비밀번호 변경을 처리하지 못했습니다.'
  }
}

let nt = null
function notify(m) {
  notice.value = m
  clearTimeout(nt)
  nt = setTimeout(() => (notice.value = ''), 2800)
}
</script>

<template>
  <div class="set-ov" @click.self="emit('close')">
    <div class="sheet">
      <div class="bar">
        <span class="ttl">⚙ 설정</span>
        <div class="grow"></div>
        <span v-if="notice" class="notice">{{ notice }}</span>
        <button class="save" @click="save">저장</button>
        <button class="x" @click="emit('close')" aria-label="닫기">✕</button>
      </div>

      <p v-if="usingMock" class="mock">샘플 값 · 서버 미연결</p>
      <div v-if="loading" class="empty">불러오는 중…</div>

      <div v-else class="set">
        <div class="srow">
          <div class="l">
            <div class="t">테마</div>
            <div class="d">다크(핑크 포인트) · 라이트(화이트+블루)</div>
          </div>
          <div class="themetoggle">
            <button :class="{ on: theme === 'dark' }" @click="setTheme('dark')">🌙 다크</button>
            <button :class="{ on: theme === 'light' }" @click="setTheme('light')">☀ 라이트</button>
          </div>
        </div>

        <div class="srow">
        <div class="l">
          <div class="t">기본 재생목록</div>
          <div class="d">예약이 없을 때 · 부팅 시 자동 재생</div>
        </div>
        <select v-model="form.default_playlist_id" class="ctl">
          <option :value="null">(없음 · 대기화면)</option>
          <option v-for="p in pls" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>

      <div class="srow">
        <div class="l">
          <div class="t">대기화면 이미지</div>
          <div class="d">아무것도 재생 안 할 때 TV에 표시</div>
        </div>
        <button class="ctl acc" @click="notify('대기화면 이미지 업로드는 준비 중입니다.')">
          🖼 이미지 변경
        </button>
      </div>

      <div class="srow">
        <div class="l">
          <div class="t">사진 기본 표시시간</div>
          <div class="d">슬라이드쇼에서 사진 한 장당 초</div>
        </div>
        <div class="ctl stepper">
          <button @click="step(-1)" aria-label="감소">－</button>
          <b>{{ form.photo_default_sec }}초</b>
          <button @click="step(1)" aria-label="증가">＋</button>
        </div>
      </div>

      <div class="srow col">
        <div class="l">
          <div class="t">공용 비밀번호 변경</div>
          <div class="d">관리자 로그인 비번</div>
        </div>
        <div class="pw">
          <input v-model="pw.old" type="password" placeholder="현재 비밀번호" />
          <input v-model="pw.new1" type="password" placeholder="새 비밀번호" />
          <input v-model="pw.new2" type="password" placeholder="새 비밀번호 확인" />
          <button class="ctl acc" @click="changePassword">🔑 변경</button>
        </div>
      </div>
        <p v-if="pwError" class="err">{{ pwError }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-active .sheet, .modal-leave-active .sheet { transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .sheet, .modal-leave-to .sheet { transform: translateY(14px) scale(0.97); }
.set-ov { position: fixed; inset: 0; background: rgba(6, 9, 11, 0.66); backdrop-filter: blur(2px); display: grid; place-items: center; z-index: 25; padding: 24px; }
.sheet { width: 720px; max-width: 100%; max-height: 88vh; overflow-y: auto; background: var(--bg); border: 1px solid var(--bd); border-radius: 16px; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55); }
.x { border: none; background: var(--elev); color: var(--muted); font-size: 13px; width: 30px; height: 30px; border-radius: 8px; }
.themetoggle { display: flex; gap: 6px; padding: 4px; background: transparent; border: none; }
.themetoggle button { border: 1px solid var(--bd); background: var(--elev); color: var(--muted); border-radius: 7px; padding: 6px 12px; font-size: 12px; font-weight: 600; }
.themetoggle button.on { background: var(--accent); border-color: var(--accent); color: #fff; }
.bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-bottom: 1px solid var(--bd);
  background: var(--topbar);
  border-radius: 16px 16px 0 0;
  position: sticky;
  top: 0;
  z-index: 2;
}
.back {
  font-size: 12px;
  font-weight: 600;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.ttl { font-size: 14px; font-weight: 680; }
.grow { flex: 1; }
.notice { font-size: 11.5px; color: var(--teal); }
.save {
  font-size: 12px;
  font-weight: 640;
  padding: 8px 15px;
  border-radius: 8px;
  border: none;
  background: var(--accent);
  color: #fff;
}
.mock { margin: 10px 16px 0; font-size: 10.5px; color: var(--warn); font-family: var(--font-mono); }
.empty { color: var(--faint); font-size: 13px; padding: 24px; text-align: center; }
.set { padding: 16px; display: flex; flex-direction: column; gap: 12px; max-width: 720px; }
.srow {
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 10px;
  padding: 13px 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}
.srow.col { flex-direction: column; align-items: stretch; }
.srow .l .t { font-size: 13px; font-weight: 600; }
.srow .l .d { font-size: 11px; color: var(--faint); margin-top: 2px; }
.ctl {
  font-size: 12px;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 8px 12px;
}
.ctl.acc { color: var(--accent); }
.stepper { display: flex; align-items: center; gap: 11px; font-family: var(--font-mono); }
.stepper button { border: none; background: transparent; color: var(--muted); font-size: 14px; padding: 0 4px; }
.stepper b { font-size: 13px; min-width: 42px; text-align: center; }
.pw { display: flex; gap: 8px; flex-wrap: wrap; }
.pw input {
  flex: 1;
  min-width: 130px;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 8px;
  padding: 9px 11px;
  color: var(--text);
  font-size: 12.5px;
}
.err { color: var(--danger); font-size: 12px; margin: 0 16px; }
</style>
