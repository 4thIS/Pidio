<script setup>
// 앱 셸: 시작 시 세션 확인 → 로그인 화면 또는 메인.
// 메인 진입 시 SSE(/events) 구독. 업로드는 화면 어디서나 드롭 가능.
import { onMounted, ref, watch } from 'vue'
import { store, connectEvents, disconnectEvents } from './store.js'
import { auth } from './api.js'
import Login from './components/Login.vue'
import NowPlaying from './components/NowPlaying.vue'
import PlayQueue from './components/PlayQueue.vue'
import Playlists from './components/Playlists.vue'
import Library from './components/Library.vue'
import PlaylistDetail from './components/PlaylistDetail.vue'
import Uploader from './components/Uploader.vue'
import Settings from './components/Settings.vue'

// 간단 뷰 전환: 메인 위에 플레이리스트 상세(모달) ↔ 설정 (라우터 없이)
const detailId = ref(null)
const detailJustCreated = ref(false)
const showSettings = ref(false)

function openDetail(payload) {
  // payload: 숫자 id(카드 클릭) 또는 {id, justCreated}(새 목록 생성)
  if (payload !== null && typeof payload === 'object') {
    detailId.value = payload.id
    detailJustCreated.value = !!payload.justCreated
  } else {
    detailId.value = payload
    detailJustCreated.value = false
  }
}
function closeDetail() {
  detailId.value = null
  detailJustCreated.value = false
}
const uploader = ref(null)
const libKey = ref(0) // 업로드 완료 시 목록 새로고침
const plKey = ref(0)  // 미디어 삭제 시 플레이리스트 목록 새로고침

onMounted(async () => {
  try {
    await auth.me() // 유효 세션이면 200
    store.authed = true
  } catch {
    store.authed = false // 401 등 → 로그인 필요
  } finally {
    store.ready = true
  }
})

// 로그인 상태에 따라 SSE 연결/해제
watch(
  () => store.authed,
  (v) => (v ? connectEvents() : disconnectEvents()),
  { immediate: true },
)

async function logout() {
  try {
    await auth.logout()
  } finally {
    store.authed = false
  }
}
</script>

<template>
  <div v-if="!store.ready" class="boot">불러오는 중…</div>

  <Login v-else-if="!store.authed" />

  <main v-else class="shell">
    <div class="topbar">
      <div class="logo"><span class="dot"></span> Pidio</div>
      <div class="grow"></div>
      <button class="up" @click="uploader?.pick()">⬆ 업로드</button>
      <button class="ico" :class="{ on: showSettings }" @click="showSettings = !showSettings" aria-label="설정">⚙</button>
      <button class="out" @click="logout">로그아웃</button>
    </div>

    <NowPlaying />
    <PlayQueue />

    <Settings v-if="showSettings" @close="showSettings = false" />

    <div v-else class="rest">
      <Playlists :key="plKey" @open="openDetail" />
      <Library :key="libKey" @media-deleted="plKey++" />
    </div>

    <!-- 플리 상세: 원래 화면 위에 박스로 열림 -->
    <Transition name="modal">
      <PlaylistDetail
        v-if="detailId !== null"
        :id="detailId"
        :just-created="detailJustCreated"
        @close="closeDetail"
        @changed="plKey++"
      />
    </Transition>

    <Uploader ref="uploader" @uploaded="libKey++" />
  </main>
</template>

<style scoped>
.boot {
  min-height: 100vh;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 14px;
}
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--bd);
  background: #151c21;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 730;
  font-size: 15px;
  letter-spacing: -0.01em;
}
.dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent);
}
.grow { flex: 1; }
.out {
  font-size: 12px;
  font-weight: 600;
  padding: 7px 13px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.up {
  font-size: 12px;
  font-weight: 600;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
}
.ico {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
  display: grid;
  place-items: center;
  font-size: 15px;
}
.ico.on { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 50%, transparent); }
.rest {
  flex: 1;
}
.rest .soon {
  color: var(--faint);
  font-size: 12px;
  text-align: center;
  padding: 12px 16px 0;
  margin: 0;
}
.rest b { color: var(--muted); }
</style>
