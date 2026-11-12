@echo off
REM Mode: audio only. Extracts m4a, then deletes the mp4 to save space.
REM About 1/7 of the disk usage of video+audio.
setlocal
set "GETLEC_DROPVIDEO=1"
set "GETLEC_NOAUDIO="
call "%~dp0getlec.cmd" %*
exit /b %ERRORLEVEL%
