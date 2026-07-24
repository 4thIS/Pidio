#!/usr/bin/env bash
# systemd 유닛 설치·활성화·기동 (Pi에서 실행).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
sudo cp "$DIR"/pidio-mpv-video.service "$DIR"/pidio-mpv-music.service "$DIR"/pidio-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pidio-mpv-video pidio-mpv-music pidio-web
sudo systemctl restart pidio-mpv-video pidio-mpv-music
sleep 3
sudo systemctl restart pidio-web
echo "=== 설치 완료 ==="
systemctl --no-pager --property=ActiveState,SubState show pidio-mpv-video pidio-mpv-music pidio-web
