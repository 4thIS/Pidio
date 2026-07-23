@echo off
REM Pidio frontend dev server (Vite)
cd /d "%~dp0"
echo.
echo === Pidio frontend dev server ===
echo   Open: http://localhost:5173   (also run backend run-dev.cmd)
echo   Stop: Ctrl+C
echo.
npm run dev
