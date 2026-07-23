<script setup>
// 앱 셸: 시작 시 세션 확인 → 로그인 화면 또는 메인.
// 메인 진입 시 SSE(/events) 구독. (전체 목록 등 본체는 D-3~ 에서.)
import { onMounted, watch } from 'vue'
import { store, connectEvents, disconnectEvents } from './store.js'
import { auth } from './api.js'
import Login from './components/Login.vue'
import NowPlaying from './components/NowPlaying.vue'

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
      <button class="out" @click="logout">로그아웃</button>
    </div>

    <NowPlaying />

    <div class="rest">
      <p>플레이리스트 · 전체 목록(넷플릭스 호버)은 다음 단계 <b>D-3~</b>에서 만들어요.</p>
    </div>
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
.rest {
  flex: 1;
  display: grid;
  place-content: center;
  text-align: center;
  color: var(--muted);
  font-size: 13.5px;
  padding: 24px;
}
.rest b { color: var(--text); }
</style>
