<script setup>
// D-3 넷플릭스식 호버 미리보기 내용물.
// 동영상: 그 자리에서 무음 자동재생 / 사진: 확대 이미지 / 음악: 정보.
// /stream·/thumb 는 실제 업로드 미디어에 동작(샘플 데이터면 로드 실패 → 그라디언트만 보임).
import { formatTime } from '../format.js'

defineProps({ item: Object })
</script>

<template>
  <div class="prev">
    <video
      v-if="item.media_type === 'video'"
      class="media"
      draggable="false"
      :src="`/stream/${item.content_id}`"
      :poster="`/thumb/${item.content_id}`"
      muted
      autoplay
      loop
      playsinline
      preload="metadata"
    ></video>

    <!-- 사진: 무거운 원본(/stream) 대신 이미 캐시된 썸네일(/thumb) 사용 → 즉시 표시 -->
    <img
      v-else-if="item.media_type === 'photo'"
      class="media"
      draggable="false"
      :src="`/thumb/${item.content_id}`"
      alt=""
    />

    <div v-else class="music">
      <div class="mic">🎵</div>
      <div class="mt">{{ item.title }}</div>
      <div class="ms">{{ formatTime(item.duration) }}</div>
    </div>

    <div class="tag">● 미리보기</div>
  </div>
</template>

<style scoped>
.prev {
  position: absolute;
  inset: 0;
}
.media {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.music {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 4px;
  text-align: center;
  padding: 8px;
}
.music .mic { font-size: 26px; }
.music .mt {
  font-size: 11px;
  font-weight: 600;
  max-width: 92%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.music .ms {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
}
.tag {
  position: absolute;
  top: 7px;
  right: 7px;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: var(--teal);
  background: rgba(0, 0, 0, 0.5);
  padding: 2px 6px;
  border-radius: 5px;
}
</style>
