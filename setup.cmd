@echo off
REM ===========================================================
REM  setup.cmd - one-time setup for a fresh copy of this folder.
REM
REM  What it does:
REM    1. finds a working Python
REM    2. downloads ffmpeg (ffmpeg.exe + ffprobe.exe) into bin\
REM    3. creates the lists\ folder
REM    4. checks that ffmpeg actually runs
REM
REM  Safe to run again: an existing ffmpeg is left alone.
REM
REM  HARD RULES FOR THIS FILE (see README):
REM    1. ASCII only. cmd.exe decodes .cmd as GBK, so UTF-8 CJK
REM       bytes in comments break parsing.
REM    2. No angle brackets in comments.
REM    3. CRLF line endings.
REM ===========================================================
setlocal
chcp 65001 >nul
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ============================================================
echo  course-notes setup
echo  root: %ROOT%
echo ============================================================
echo.

REM ---------- 1. find python (each candidate must actually run) ----------
set "PYEXE="
if exist "%ROOT%\python\python.exe" call :trypy "%ROOT%\python\python.exe"
if defined PYEXE goto havepy
for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYEXE call :trypy "%%P"
if defined PYEXE goto havepy
for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined PYEXE call :trypy "%%P"
if defined PYEXE goto havepy
echo [setup] ERROR: Python not found.
echo         Install Python 3.8+ from python.org, or unzip a portable
echo         python into %ROOT%\python\
echo.
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 9009
:havepy
echo [setup] python: %PYEXE%
echo.

REM ---------- 2. ffmpeg ----------
REM any arguments are forwarded to fetch_ffmpeg.py, e.g.
REM   setup.cmd --check         only check
REM   setup.cmd --force         re-download
REM   setup.cmd --dest D:\x     install somewhere else
echo [setup] step 1/3: ffmpeg
"%PYEXE%" "%ROOT%\tools\fetch_ffmpeg.py" %*
if errorlevel 1 goto fffail
echo.

REM ---------- 3. lists folder ----------
echo [setup] step 2/3: lists folder
if not exist "%ROOT%\lists" mkdir "%ROOT%\lists"
if not exist "%ROOT%\lists" goto nomkdir
echo   ok: %ROOT%\lists
echo.

REM ---------- 4. final check ----------
echo [setup] step 3/3: final check
if not exist "%ROOT%\bin\ffmpeg.exe" goto fffail
if not exist "%ROOT%\bin\ffprobe.exe" goto fffail
echo   ffmpeg    ok
echo   ffprobe   ok
echo.
echo ============================================================
echo  setup done.
echo.
echo  next:
echo    1. put a course list into lists\ (see docs for how)
echo    2. double-click one of the three .cmd entries in this
echo       folder: both / audio only / video only
echo ============================================================
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 0

:fffail
echo.
echo [setup] ERROR: ffmpeg is not ready.
echo         Download a Windows build of ffmpeg manually and put
echo         ffmpeg.exe and ffprobe.exe into %ROOT%\bin\
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 1

:nomkdir
echo [setup] ERROR: cannot create %ROOT%\lists
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 1

REM -----------------------------------------------------------
REM  subroutines at the very end: the main flow must not fall
REM  through into them.
REM -----------------------------------------------------------
:trypy
"%~1" -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYEXE=%~1"
exit /b 0
