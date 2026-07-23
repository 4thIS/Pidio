<script setup>
// D-1 로그인 화면
import { ref } from 'vue'
import { auth, ApiError } from '../api.js'
import { store } from '../store.js'

const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  if (loading.value) return
  error.value = ''
  if (!password.value) {
    error.value = '비밀번호를 입력해 주세요.'
    return
  }
  loading.value = true
  try {
    await auth.login(password.value)
    store.authed = true // 성공 → 메인 화면으로
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      error.value = '비밀번호가 올바르지 않습니다.'
    } else if (e instanceof ApiError && e.status === 429) {
      error.value = '시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.'
    } else {
      error.value = '로그인 중 문제가 발생했습니다. 서버 상태를 확인해 주세요.'
    }
    password.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <form class="card" @submit.prevent="submit">
      <div class="brand"><span class="dot"></span> Pidio</div>
      <div class="sub">🔒 관리자 로그인</div>

      <label class="field" :class="{ err: error }">
        <span class="key">🔑</span>
        <input
          v-model="password"
          type="password"
          placeholder="비밀번호"
          autocomplete="current-password"
          :disabled="loading"
          autofocus
        />
      </label>

      <p v-if="error" class="msg">{{ error }}</p>

      <button class="go" type="submit" :disabled="loading">
        {{ loading ? '확인 중…' : '로그인' }}
      </button>

      <p class="note">처음 접속이면 여기 입력한 비밀번호로 설정됩니다.</p>
    </form>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: radial-gradient(120% 90% at 50% 0%, #1d2831, #10161a);
}
.card {
  width: 320px;
  max-width: 100%;
  text-align: center;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 22px;
  font-weight: 730;
  letter-spacing: -0.02em;
}
.dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 22%, transparent);
}
.sub {
  color: var(--muted);
  font-size: 13px;
  margin: 9px 0 22px;
}
.field {
  display: flex;
  align-items: center;
  gap: 9px;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 11px;
  padding: 12px 14px;
  transition: border-color 0.15s;
}
.field:focus-within {
  border-color: var(--teal);
}
.field.err {
  border-color: var(--danger);
}
.field .key {
  font-size: 15px;
}
.field input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 14px;
  letter-spacing: 1px;
}
.msg {
  color: var(--danger);
  font-size: 12.5px;
  margin: 11px 0 0;
}
.go {
  width: 100%;
  margin-top: 12px;
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 13px;
  border-radius: 11px;
  font-size: 14px;
  font-weight: 640;
  transition: opacity 0.15s;
}
.go:disabled {
  opacity: 0.6;
  cursor: default;
}
.note {
  font-size: 11.5px;
  color: var(--faint);
  margin: 14px 0 0;
}
</style>
