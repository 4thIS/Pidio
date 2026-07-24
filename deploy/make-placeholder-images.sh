#!/usr/bin/env bash
# 대기화면/음악화면 임시 이미지 생성(ffmpeg). 나중에 실제 디자인으로 교체.
set -e
OUT="${1:-$HOME/pidio-assets}"
mkdir -p "$OUT"
ffmpeg -y -f lavfi -i color=c=black:s=1920x1080 -frames:v 1 "$OUT/standby.png"
ffmpeg -y -f lavfi -i "color=c=0x0f1020:s=1920x1080" -frames:v 1 "$OUT/music.png"
echo "생성됨: $OUT/standby.png, $OUT/music.png"
echo "→ 실행 시: export PIDIO_STANDBY_IMAGE=$OUT/standby.png PIDIO_MUSIC_IMAGE=$OUT/music.png"
