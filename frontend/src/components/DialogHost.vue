<script setup>
// 인앱 다이얼로그 호스트 — App 최상단에 한 번 마운트. dialog.js 상태를 렌더.
import { watch, nextTick, ref } from 'vue'
import { dialogState, resolveDialog } from '../dialog.js'

const inputEl = ref(null)

watch(() => dialogState.open, async (o) => {
  if (o && dialogState.mode === 'prompt') {
    await nextTick()
    inputEl.value?.focus()
    inputEl.value?.select()
  }
})

function onConfirm() {
  if (dialogState.mode === 'prompt') resolveDialog(dialogState.value)
  else resolveDialog(true)
}
function onCancel() {
  resolveDialog(dialogState.mode === 'prompt' ? null : dialogState.mode === 'choice' ? null : false)
}
function onChoice(c) {
  resolveDialog(c.value)
}
</script>

<template>
  <Transition name="dlg">
    <div v-if="dialogState.open" class="dlg-ov" @click.self="onCancel" @keydown.esc="onCancel">
      <div class="dlg">
        <div class="dt">{{ dialogState.title }}</div>
        <div v-if="dialogState.message" class="dm">{{ dialogState.message }}</div>

        <input
          v-if="dialogState.mode === 'prompt'"
          ref="inputEl"
          v-model="dialogState.value"
          class="din"
          :placeholder="dialogState.placeholder"
          @keyup.enter="onConfirm"
          @keyup.esc="onCancel"
        />

        <div v-if="dialogState.mode === 'choice'" class="dbtns col">
          <button class="db" @click="onCancel">{{ dialogState.cancelText }}</button>
          <button
            v-for="c in dialogState.choices"
            :key="c.value"
            class="db"
            :class="{ danger: c.danger, primary: !c.danger }"
            @click="onChoice(c)"
          >
            {{ c.label }}
          </button>
        </div>
        <div v-else class="dbtns">
          <button class="db" @click="onCancel">{{ dialogState.cancelText }}</button>
          <button class="db primary" @click="onConfirm">{{ dialogState.confirmText }}</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.dlg-enter-active, .dlg-leave-active { transition: opacity 0.15s ease; }
.dlg-enter-active .dlg, .dlg-leave-active .dlg { transition: transform 0.18s cubic-bezier(0.2, 0.8, 0.2, 1); }
.dlg-enter-from, .dlg-leave-to { opacity: 0; }
.dlg-enter-from .dlg, .dlg-leave-to .dlg { transform: translateY(12px) scale(0.96); }
.dlg-ov {
  position: fixed;
  inset: 0;
  background: rgba(6, 9, 11, 0.6);
  backdrop-filter: blur(2px);
  display: grid;
  place-items: center;
  z-index: 60;
  padding: 20px;
}
.dlg {
  width: 340px;
  max-width: 100%;
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
}
.dt { font-size: 15px; font-weight: 700; color: var(--text); }
.dm { font-size: 12.5px; color: var(--muted); margin-top: 8px; line-height: 1.55; }
.din {
  width: 100%;
  margin-top: 14px;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 9px;
  padding: 10px 12px;
  color: var(--text);
  font-size: 13.5px;
}
.din:focus { outline: none; border-color: var(--accent); }
.dbtns { display: flex; gap: 8px; margin-top: 18px; justify-content: flex-end; }
.dbtns.col { flex-direction: column; }
.db {
  font-size: 12.5px;
  font-weight: 600;
  padding: 9px 15px;
  border-radius: 9px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
}
.dbtns.col .db { padding: 11px 14px; text-align: center; }
.db.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.db.danger { background: var(--danger); border-color: var(--danger); color: #fff; }
</style>
