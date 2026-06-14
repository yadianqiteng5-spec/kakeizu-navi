@echo off
chcp 932 >nul
echo ====================================================
echo  Save livedoor API key (AtomPub password)
echo  ID and BLOG are already set. Only the key is needed.
echo ====================================================
echo.
set /p KEY="Paste your 10-char API key, then Enter: "
setx LIVEDOOR_APIKEY "%KEY%" >nul
echo.
echo  Saved to LIVEDOOR_APIKEY (the value is not shown).
echo  -> Close this window, then run 手順1 in a NEW window.
echo.
pause
