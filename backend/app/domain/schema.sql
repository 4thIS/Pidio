-- Pidio 데이터 스키마 (설계 01_설계.MD 4.2)
-- init_db 재실행 안전을 위해 IF NOT EXISTS 사용.

-- 모든 미디어의 부가정보 (파일 자체는 USB가 진실)
CREATE TABLE IF NOT EXISTS media (
  content_id        TEXT PRIMARY KEY,   -- size + 앞/뒤 1MB 해시
  media_type        TEXT NOT NULL,      -- 'video' | 'photo' | 'music'
  original_name     TEXT NOT NULL,      -- 최초 발견 시 파일명
  custom_title      TEXT,               -- 사용자 수정 제목 (없으면 파일명 표시)
  rel_path          TEXT,               -- 현재 USB 내 상대경로 (스캔 시 갱신)
  duration          REAL,               -- video/music 재생시간(초); photo는 NULL
  default_photo_sec REAL,               -- photo 기본 표시 시간(초), 기본 5
  thumb_rel         TEXT,               -- .pidio/thumbs/<content_id>.jpg (video/photo)
  available         INTEGER DEFAULT 1,  -- 현재 스캔에 존재? (USB 빼면 0)
  first_seen        TEXT,
  last_seen         TEXT
);

-- 플레이리스트 (블록들의 순서 있는 모음)
CREATE TABLE IF NOT EXISTS playlists (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  repeat_mode TEXT DEFAULT 'off',       -- 'off'(순차1회) | 'all' | 'one'  ※ 블록 단위
  shuffle     INTEGER DEFAULT 0,        -- 블록 순서 셔플
  created_at  TEXT,
  updated_at  TEXT
);

-- 플레이리스트 안의 "블록" = 재생 단위
--   kind='video'     : 동영상 1개(자체 소리, 음악 불가)
--   kind='slideshow' : 사진 슬라이드쇼 + 선택적 배경음악(=음악 라인)
CREATE TABLE IF NOT EXISTS playlist_blocks (
  id          INTEGER PRIMARY KEY,
  playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
  position    INTEGER,                  -- 블록 순서
  kind        TEXT NOT NULL,            -- 'video' | 'slideshow'
  video_id    TEXT REFERENCES media(content_id),  -- kind='video'일 때
  music_id    TEXT REFERENCES media(content_id)   -- kind='slideshow'의 배경음악(NULL=음악없음)
);

-- 슬라이드쇼 블록(음악 라인) 안의 사진들
CREATE TABLE IF NOT EXISTS block_photos (
  block_id     INTEGER REFERENCES playlist_blocks(id) ON DELETE CASCADE,
  position     INTEGER,                 -- 라인 내 사진 순서
  photo_id     TEXT REFERENCES media(content_id),
  duration_sec REAL,                    -- 이 사진 표시 시간(초). NULL이면 media.default_photo_sec
  PRIMARY KEY (block_id, position)
);

-- 예약(스케줄)
CREATE TABLE IF NOT EXISTS schedules (
  id          INTEGER PRIMARY KEY,
  playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
  sched_type  TEXT NOT NULL,            -- 'date_range' | 'weekly'
  start_dt    TEXT,                     -- date_range: 'YYYY-MM-DD HH:MM'
  end_dt      TEXT,
  weekdays    TEXT,                     -- weekly: 'mon,tue,wed,thu,fri'
  start_time  TEXT,                     -- weekly: 'HH:MM'
  end_time    TEXT,
  enabled     INTEGER DEFAULT 1
);

-- 전역 설정 (key-value)
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);

-- 폴더 = 사용자가 드래그로 담는 이름 있는 미디어 묶음(타입 혼합, 수동 관리)
CREATE TABLE IF NOT EXISTS folders (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  created_at TEXT
);

-- 폴더 소속(태그식: 한 미디어가 여러 폴더에 중복 소속 가능)
CREATE TABLE IF NOT EXISTS folder_items (
  folder_id  INTEGER REFERENCES folders(id) ON DELETE CASCADE,
  content_id TEXT REFERENCES media(content_id),
  added_at   TEXT,
  PRIMARY KEY (folder_id, content_id)
);
