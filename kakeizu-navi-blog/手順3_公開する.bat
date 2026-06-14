@echo off
chcp 932 >nul
cd /d "%~dp0"
set "PY="
if exist "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe" set "PY=C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not defined PY (where py >nul 2>nul && set "PY=py")
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (echo [ERROR] Python not found. & pause & exit /b)
echo ====================================================
echo  PUBLISH all articles  (this makes them PUBLIC)
echo ====================================================
set /p OK="Publish now? type y and Enter: "
if /i not "%OK%"=="y" (echo canceled. & pause & exit /b)
"%PY%" post_to_livedoor.py --publish
echo.
echo ----------------------------------------------------
echo  Done.
echo ----------------------------------------------------
pause
