@echo off
REM Pidio dev server (sample media, no USB needed)
cd /d "%~dp0"
set PIDIO_MEDIA_ROOT=sample_media
set PIDIO_DB=dev.db
echo.
echo === Pidio dev server: sample_media + dev.db ===
echo   Frontend: http://localhost:5173   Backend only: http://localhost:8000
echo   Stop: Ctrl+C
echo.
uv run uvicorn app.web.main:app --port 8000
