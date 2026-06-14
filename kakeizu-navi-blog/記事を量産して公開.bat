@echo off
chcp 932 >nul
cd /d "%~dp0"

rem --- Python ---
set "PY=C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PY%" ( where py >nul 2>nul && set "PY=py" || set "PY=python" )

rem --- 認証情報を環境変数から取り込み（値は画面に出ません） ---
for /f "delims=" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Livedoor API','Machine')"') do set "LIVEDOOR_APIKEY=%%a"
for /f "delims=" %%a in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Gemini_API_KEY','Machine')"') do set "Gemini_API_KEY=%%a"
if not defined LIVEDOOR_ID set "LIVEDOOR_ID=infinity_peace24"
if not defined LIVEDOOR_BLOG set "LIVEDOOR_BLOG=infinity_peace24"
set "PYTHONUTF8=1"

echo ====================================================
echo   Auto-generate articles and PUBLISH to livedoor
echo   (blog: infinity_peace24)
echo ====================================================
echo.
set /p N="How many NEW articles to generate and publish? (e.g. 5): "

echo.
echo ---- 1) generating %N% article(s) with Gemini ----
"%PY%" generate_articles.py --auto %N%
if errorlevel 1 ( echo [stop] generation failed. & pause & exit /b )

echo.
echo ---- 2) publishing new article(s) to livedoor ----
"%PY%" post_to_livedoor.py --publish

echo.
echo ====================================================
echo   Done.  ->  https://blog.livedoor.jp/infinity_peace24/
echo ====================================================
pause
