#!/usr/bin/env bash
# 화면 채널 mpv: 연결된 모니터가 있으면 KMS/DRM 전체화면(해상도 자동),
# 없으면(개발/헤드리스) --vo=null 로 디코드만 → 재생·진행바·소리는 동작.
# idle 상주(파일 없으면 대기) + IPC 소켓.
set -e
SOCK="${PIDIO_MPV_VIDEO_SOCK:-/tmp/pidio/mpv-video.sock}"
mkdir -p "$(dirname "$SOCK")"
rm -f "$SOCK"

# 연결된 DRM 디스플레이(HDMI 등)가 하나라도 있는지 확인.
DISPLAY_CONNECTED=no
for s in /sys/class/drm/card*-*/status; do
  [ -f "$s" ] || continue
  if [ "$(cat "$s" 2>/dev/null)" = "connected" ]; then
    DISPLAY_CONNECTED=yes
    break
  fi
done

COMMON=(--idle=yes --image-display-duration=inf --keep-open=no \
        --no-osc --no-input-default-bindings --input-ipc-server="$SOCK")

if [ "$DISPLAY_CONNECTED" = "yes" ]; then
  # 실제 모니터: 연결된 디스플레이의 기본 해상도로 자동 전체화면(다른 모니터도 자동 대응).
  echo "start-mpv-video: DRM display connected -> gpu/drm fullscreen"
  exec mpv "${COMMON[@]}" --force-window=yes --fs --vo=gpu --gpu-context=drm
else
  # 모니터 없음(헤드리스): 화면 출력 없이 디코드만. 재생/진행바/음성 동작.
  echo "start-mpv-video: no DRM display -> --vo=null (headless)"
  exec mpv "${COMMON[@]}" --vo=null
fi
