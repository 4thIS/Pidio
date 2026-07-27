<script setup>
// D-3 미디어 카드 — 체크박스 선택 · 제목 인라인 수정 · 호버(디바운스 200ms) 시 확대+미리보기.
import { ref, computed, onBeforeUnmount } from 'vue'
import HoverPreview from './HoverPreview.vue'
import { typeEmoji, typeLabel, thumbGradient } from '../mediaView.js'
import { formatTime } from '../format.js'

const props = defineProps({
  item: Object,
  selected: Boolean,
  deleteIcon: { type: String, default: '🗑' },
  deleteTitle: { type: String, default: '삭제' },
})
const emit = defineEmits(['toggle', 'save-title', 'add-queue', 'delete'])

// ---- 호버 미리보기 (200ms 디바운스) ----
const expanded = ref(false)
let timer = null
function enter() {
  timer = setTimeout(() => (expanded.value = true), 200)
}
function leave() {
  clearTimeout(timer)
  expanded.value = false
}
onBeforeUnmount(() => clearTimeout(timer))

// ---- 제목 인라인 수정 ----
const editing = ref(false)
const draft = ref('')
function startEdit() {
  draft.value = props.item.title
  editing.value = true
}
function commit() {
  if (!editing.value) return
  editing.value = false
  const t = draft.value.trim()
  if (t && t !== props.item.title) emit('save-title', props.item.content_id, t)
}

const thumbFailed = ref(false)
const thumbSrc = computed(() =>
  props.item.thumb_url && !thumbFailed.value ? props.item.thumb_url : null,
)

function onDragStart(e) {
  e.dataTransfer.setData('application/x-pidio-media', JSON.stringify({ content_id: props.item.content_id, media_type: props.item.media_type }))
  e.dataTransfer.effectAllowed = 'copy'
}

const durText = computed(() =>
  props.item.media_type === 'photo' ? '' : formatTime(props.item.duration),
)
</script>

<template>
  <div
    class="card"
    :class="{ sel: selected, expanded, dim: item.available === false }"
    @mouseenter="enter"
    @mouseleave="leave"
    draggable="true"
    @dragstart="onDragStart"
  >
    <div class="thumb" :style="{ background: thumbGradient(item) }">
      <button
        class="chk"
        :class="{ on: selected }"
        @click.stop="emit('toggle', item.content_id)"
        :aria-label="selected ? '선택 해제' : '선택'"
      >
        <span v-if="selected">✓</span>
      </button>

      <div class="acts">
        <button class="act" @click.stop="emit('add-queue', item.content_id)" title="재생목록에 추가">＋</button>
        <button class="act del" @click.stop="emit('delete', item.content_id)" :title="deleteTitle">{{ deleteIcon }}</button>
      </div>

      <HoverPreview v-if="expanded" :item="item" />
      <template v-else>
        <img v-if="thumbSrc" class="thumbimg" :src="thumbSrc" alt="" draggable="false" @error="thumbFailed = true" />
        <span v-else class="emoji">{{ typeEmoji(item.media_type) }}</span>
        <span v-if="durText" class="dur">{{ durText }}</span>
      </template>
    </div>

    <div class="info">
      <input
        v-if="editing"
        v-model="draft"
        class="edit"
        draggable="false"
        @keyup.enter="commit"
        @blur="commit"
        @keyup.esc="editing = false"
        @click.stop
      />
      <div v-else class="nm" @dblclick="startEdit" :title="item.title">
        <span class="txt">{{ item.title }}</span>
        <button class="pen" @click.stop="startEdit" aria-label="제목 수정">✎</button>
      </div>
      <div class="ty">
        {{ typeEmoji(item.media_type) }} {{ typeLabel(item.media_type) }}
        <span v-if="item.available === false" class="na">· 없음</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--sf);
  border: 1px solid var(--bd);
  border-radius: 10px;
  overflow: hidden;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.15s;
  will-change: transform;
}
.card.sel { border-color: var(--accent); }
.card.dim { opacity: 0.45; }
.card.expanded {
  transform: scale(1.14);
  z-index: 3;
  border-color: var(--teal);
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.55);
}
@media (prefers-reduced-motion: reduce) {
  .card { transition: none; }
  .card.expanded { transform: none; }
}
.thumb {
  position: relative;
  height: 78px;
  display: grid;
  place-items: center;
}
.thumbimg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.emoji { font-size: 22px; }
.chk {
  position: absolute;
  top: 7px;
  left: 7px;
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid rgba(255, 255, 255, 0.6);
  background: rgba(0, 0, 0, 0.35);
  color: #fff;
  font-size: 11px;
  display: grid;
  place-items: center;
  padding: 0;
  z-index: 2;
}
.chk.on {
  background: var(--accent);
  border-color: var(--accent);
}
.acts {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  gap: 5px;
  opacity: 0;
  z-index: 3;
  transition: opacity 0.15s;
}
.card:hover .acts { opacity: 1; }
.act {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: none;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 12px;
  display: grid;
  place-items: center;
  padding: 0;
}
.act:hover { background: rgba(0, 0, 0, 0.85); }
.act.del:hover { background: #c0392b; }
.dur {
  position: absolute;
  bottom: 6px;
  right: 6px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 1px 5px;
  border-radius: 4px;
}
.info { padding: 7px 8px; }
.nm {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 560;
}
.nm .txt {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pen {
  opacity: 0;
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  padding: 0 2px;
  flex: none;
  transition: opacity 0.15s;
}
.card:hover .pen { opacity: 1; }
.edit {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--teal);
  border-radius: 6px;
  color: var(--text);
  font-size: 11.5px;
  padding: 4px 6px;
}
.ty {
  font-size: 10px;
  color: var(--faint);
  margin-top: 3px;
}
.ty .na { color: var(--warn); }
</style>
