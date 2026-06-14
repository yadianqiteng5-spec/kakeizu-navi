@echo off
chcp 932 >nul
cd /d "%~dp0"

rem ==== 無人自動実行（タスクスケジューラから呼ばれる） ====
rem 1回ぶん: 記事を3本生成し、新規ぶんを公開。総数70本で自動停止。

set "PY=C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PY%" ( where py >nul 2>nul && set "PY=py" || set "PY=python" )

for /f "delims=" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Livedoor API','Machine')"') do set "LIVEDOOR_APIKEY=%%a"
for /f "delims=" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Gemini_API_KEY','Machine')"') do set "Gemini_API_KEY=%%a"
if not defined LIVEDOOR_ID set "LIVEDOOR_ID=infinity_peace24"
if not defined LIVEDOOR_BLOG set "LIVEDOOR_BLOG=infinity_peace24"
set "PYTHONUTF8=1"

echo.>> auto_log.txt
echo ===================== %date% %time% =====================>> auto_log.txt
"%PY%" generate_articles.py --auto 3 --max-total 70 >> auto_log.txt 2>&1
"%PY%" post_to_livedoor.py --publish >> auto_log.txt 2>&1
