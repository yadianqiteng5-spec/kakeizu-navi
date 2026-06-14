@echo off
chcp 932 >nul
echo ====================================================
echo  Set Livedoor credentials as ENVIRONMENT VARIABLES
echo  (blog handle already set: infinity_peace24)
echo ====================================================
echo.
set /p ID="1) livedoor ID            : "
set /p KEY="2) API key (AtomPub pass) : "
setx LIVEDOOR_ID "%ID%" >nul
setx LIVEDOOR_APIKEY "%KEY%" >nul
setx LIVEDOOR_BLOG "infinity_peace24" >nul
echo.
echo  Saved (persisted) to your user environment:
echo    LIVEDOOR_ID     = %ID%
echo    LIVEDOOR_APIKEY = (hidden)
echo    LIVEDOOR_BLOG   = infinity_peace24
echo.
echo  IMPORTANT: CLOSE this window, then run STEP 1 in a NEW window.
pause
