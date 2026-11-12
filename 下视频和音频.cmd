@echo off
REM Mode: download video AND audio, keep both. This is the default.
REM Double-click this file, or drag a list txt onto it.
setlocal
set "GETLEC_DROPVIDEO="
set "GETLEC_NOAUDIO="
call "%~dp0getlec.cmd" %*
exit /b %ERRORLEVEL%
