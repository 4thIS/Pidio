#!/usr/bin/env bash
# 화면 채널 mpv: KMS/DRM 전체화면 출력 + IPC 소켓. idle 상주(파일 없으면 대기).
set -e
SOCK="${PIDIO_MPV_VIDEO_SOCK:-/tmp/pidio/mpv-video.sock}"
mkdir -p "$(dirname "$SOCK")"
rm -f "$SOCK"
exec mpv --idle=yes --force-window=yes --fs \
  --vo=gpu --gpu-context=drm \
  --image-display-duration=inf --keep-open=no \
  --no-osc --no-input-default-bindings \
  --input-ipc-server="$SOCK"
