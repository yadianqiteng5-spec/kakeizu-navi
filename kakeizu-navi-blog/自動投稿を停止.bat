@echo off
chcp 932 >nul
echo Stopping the auto-post scheduled task...
schtasks /Delete /TN "KakeizuNavi-AutoPost" /F
echo.
echo Done. Auto-posting has been stopped.
echo (To restart, run the registration step again.)
pause
