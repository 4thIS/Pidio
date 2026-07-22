# HTTP API 계약 (v1)

인증: 모든 `/api` 는 세션 쿠키 필요(로그인 제외). 401 시 프론트가 로그인 화면.

## 인증
```
POST /api/login {password}            -> 200 set-cookie / 401
POST /api/logout                      -> 200
```

## 미디어
```
GET   /api/media?type=video|photo|music|all   -> [{content_id,media_type,title,duration,thumb_url,available}]
PATCH /api/media/{content_id} {custom_title}  -> 200
POST  /api/upload (multipart, chunked; 아래 업로드 프로토콜)   -> {content_id}
GET   /stream/{content_id}            -> Range 지원 원본 스트림(호버 미리보기/재생)
GET   /thumb/{content_id}             -> jpeg
```

## 플레이리스트
```
GET    /api/playlists                 -> [{id,name,item_count,total_sec,cover_thumb_urls[],repeat_mode,shuffle,schedule?}]
POST   /api/playlists {name}          -> {id}
GET    /api/playlists/{id}            -> {id,name,repeat_mode,shuffle,blocks:[...], schedule?}
PUT    /api/playlists/{id}            -> 200 (blocks 전체 저장: video/slideshow 구조)
DELETE /api/playlists/{id}            -> 200
POST   /api/playlists/{id}/play       -> 200 (수동 모드로 이 플리 재생)
```

## 예약
```
PUT    /api/playlists/{id}/schedule {sched_type,...}  -> 200 / 409(같은타입 겹침)
DELETE /api/playlists/{id}/schedule                   -> 200
```

## 재생 제어
```
POST /api/play/selection {content_ids:[...], repeat, shuffle}  -> 200
POST /api/player/{action}   action∈ next|prev|pause|resume|stop|resume_auto
POST /api/player/jump {index}
POST /api/player/repeat {mode}
POST /api/player/shuffle {on}
POST /api/player/queue/reorder {from,to}
POST /api/player/queue/remove {index}
```

## 설정
```
GET/PUT /api/settings {default_playlist_id, photo_default_sec, ...}
POST    /api/settings/password {old,new}
POST    /api/settings/standby (multipart image)
```

## 실시간
```
GET /events (SSE)  -> data: PlayerState JSON (상태 변화 시 push)
```
