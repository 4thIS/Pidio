<script setup>
// D-4 라인(블록) 편집기.
// - kind='video' : 동영상 독립행
// - kind='slideshow' : 음악 라인(배경음악+사진) / music_id=null 이면 무음 라인
// 사진은 vuedraggable(group 'photos')로 라인 안 순서변경 + 다른 라인으로 이동 가능.
import draggable from 'vuedraggable'
import { thumbGradient } from '../mediaView.js'

const props = defineProps({ block: Object, mediaMap: Object })
const emit = defineEmits(['pick-music', 'add-photo', 'remove'])

const title = (id) => props.mediaMap[id]?.title || id || '(없음)'
const grad = (id, type) => thumbGradient({ content_id: id || 'x', media_type: type })
function removePhoto(i) {
  props.block.photos.splice(i, 1)
}
function clearMusic() {
  props.block.music_id = null
}
</script>

<template>
  <!-- 동영상 독립행 -->
  <div v-if="block.kind === 'video'" class="lane video">
    <div class="lh">
      <span class="badge2">🎬 동영상</span>
      <span class="lt">{{ title(block.video_id) }}</span>
      <div class="grow"></div>
      <button class="x" @click="emit('remove', block)" aria-label="행 삭제">✕</button>
    </div>
    <div class="body">
      <div class="clip">
        <div class="big" :style="{ background: grad(block.video_id, 'video') }">🎬</div>
        <div class="cl-t">{{ title(block.video_id) }}</div>
      </div>
    </div>
  </div>

  <!-- 슬라이드쇼 라인(음악/무음) -->
  <div v-else class="lane" :class="block.music_id ? 'music' : 'silent'">
    <div class="lh">
      <span class="badge2">{{ block.music_id ? '🎵 음악 라인' : '🔇 음악 없음' }}</span>
      <button class="music-sel" @click="emit('pick-music', block)">
        <template v-if="block.music_id">배경음악: {{ title(block.music_id) }}</template>
        <template v-else>＋ 배경음악 선택</template>
      </button>
      <button v-if="block.music_id" class="mini" @click="clearMusic" aria-label="음악 제거">음악 없음으로</button>
      <span class="cnt">· 사진 {{ block.photos.length }}장</span>
      <div class="grow"></div>
      <button class="x" @click="emit('remove', block)" aria-label="라인 삭제">✕</button>
    </div>

    <div class="body">
      <draggable
        v-model="block.photos"
        :group="{ name: 'photos' }"
        item-key="_key"
        class="photos"
        :animation="150"
      >
        <template #item="{ element, index }">
          <div class="ph">
            <div class="pic" :style="{ background: grad(element.photo_id, 'photo') }" :title="title(element.photo_id)">
              <span class="drag">⠿</span>
              <button class="rm" @click="removePhoto(index)" aria-label="사진 제거">✕</button>
            </div>
            <div class="sec">
              <input v-model.number="element.duration_sec" type="number" min="1" max="60" /><span>초</span>
            </div>
          </div>
        </template>
        <template #footer>
          <button class="add-ph" @click="emit('add-photo', block)">＋ 사진</button>
        </template>
      </draggable>
    </div>
  </div>
</template>

<style scoped>
.lane {
  border: 1px solid var(--bd);
  border-radius: 11px;
  background: var(--sf);
  overflow: hidden;
}
.lh {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  font-size: 12px;
  border-bottom: 1px solid var(--bd);
  background: #1d262c;
  flex-wrap: wrap;
}
.badge2 {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 6px;
  flex: none;
}
.video .badge2 { background: color-mix(in srgb, #5a86c4 22%, transparent); color: #9cc0ee; }
.music .badge2 { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
.silent .badge2 { background: #2c373f; color: var(--muted); }
.lt { font-weight: 600; }
.grow { flex: 1; }
.x {
  border: none;
  background: transparent;
  color: var(--faint);
  font-size: 13px;
  padding: 2px 6px;
}
.x:hover { color: var(--danger); }
.music-sel {
  font-size: 11.5px;
  border: 1px solid var(--bd);
  background: var(--elev);
  color: var(--text);
  border-radius: 7px;
  padding: 4px 9px;
}
.mini {
  font-size: 10.5px;
  border: none;
  background: transparent;
  color: var(--muted);
  text-decoration: underline;
}
.cnt { font-size: 11px; color: var(--faint); }
.body { padding: 11px 12px; }
.clip { display: flex; align-items: center; gap: 10px; }
.clip .big {
  width: 96px;
  height: 54px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  font-size: 20px;
  flex: none;
}
.clip .cl-t { font-size: 12px; font-weight: 600; }
.photos {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  flex-wrap: wrap;
  min-height: 60px;
}
.ph { width: 64px; text-align: center; }
.pic {
  height: 48px;
  border-radius: 6px;
  position: relative;
  cursor: grab;
}
.pic .drag { position: absolute; top: 3px; left: 4px; font-size: 9px; color: rgba(255, 255, 255, 0.7); }
.pic .rm {
  position: absolute;
  top: 2px;
  right: 2px;
  border: none;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 9px;
  border-radius: 4px;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.pic:hover .rm { opacity: 1; }
.sec {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  margin-top: 3px;
}
.sec input {
  width: 34px;
  background: var(--bg);
  border: 1px solid var(--bd);
  border-radius: 5px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 10px;
  text-align: center;
  padding: 2px 0;
}
.sec span { font-size: 9.5px; color: var(--faint); }
.add-ph {
  height: 48px;
  border: 1px dashed var(--bd);
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  padding: 0 12px;
}
</style>
