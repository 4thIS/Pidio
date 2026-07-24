#!/usr/bin/env bash
# 음악 채널 mpv: 오디오 전용 + IPC 소켓. idle 상주.
set -e
SOCK="${PIDIO_MPV_MUSIC_SOCK:-/tmp/pidio/mpv-music.sock}"
mkdir -p "$(dirname "$SOCK")"
rm -f "$SOCK"
exec mpv --idle=yes --no-video --keep-open=no \
  --input-ipc-server="$SOCK"
