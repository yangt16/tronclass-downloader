@echo off
REM Mode: video only. No audio extraction, keeps the mp4 as-is.
setlocal
set "GETLEC_DROPVIDEO="
set "GETLEC_NOAUDIO=1"
call "%~dp0getlec.cmd" %*
exit /b %ERRORLEVEL%
