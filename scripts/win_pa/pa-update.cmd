@echo off
setlocal EnableExtensions
for /f "tokens=2 delims=:" %%C in ('chcp') do set "_CJPA_CP=%%C"
chcp 65001 >nul
rem ============================================================
rem  pa-update.cmd -- apply the PAYLOAD-layer update BY HAND.
rem
rem  Why this file exists (pm_1684 Sec-3):
rem    * the in-app button is not wired yet (that lands in payload 9.0.4),
rem      and the Electron shell entry needs the NEW installer: this is the
rem      "by hand" road that works RIGHT NOW with whatever is installed.
rem    * it is also the fallback when the shell itself will not start.
rem
rem  It only CALLS the shipped tool (ONE place, no second copy of the shape):
rem      <root>\runtime\python.exe -X utf8 -B <root>\scripts\win_pa\pa_update.py
rem          --root <root> --go --json
rem  <root> is the PAYLOAD ROOT.  The tool stops the service, checks EVERY
rem  file by sha256, backs up, replaces, restarts -- and every human word
rem  comes from python (WriteConsoleW => code-page independent).
rem
rem  Root is found in TWO shapes (pm_1684 Sec-3.2):
rem    [A] %LOCALAPPDATA%\Programs\ClawsJoyPA\resources\payload  (Electron shell)
rem    [B] %LOCALAPPDATA%\ClawsJoyPA                             (older pack)
rem  Override with:  set PA_ROOT=<the payload root>
rem
rem  THIS FILE MUST STAY 100% ASCII (pm_1578 s2.2).  cmd.exe decodes .cmd
rem  BYTES with the CONSOLE code page; a BOM-less UTF-8 file on a GBK(936)
rem  console mis-pairs CJK bytes and SWALLOWS 2 bytes on an invalid trail
rem  byte => it eats CR / ^ / quotes => lines splice and CJK bytes get run
rem  as commands.  ALL human words therefore come from the bundled python.
rem ============================================================
set "ROOT="
if not "%PA_ROOT%"=="" if exist "%PA_ROOT%\scripts\win_pa\pa_update.py" set "ROOT=%PA_ROOT%"
if "%ROOT%"=="" if exist "%LOCALAPPDATA%\Programs\ClawsJoyPA\resources\payload\scripts\win_pa\pa_update.py" set "ROOT=%LOCALAPPDATA%\Programs\ClawsJoyPA\resources\payload"
if "%ROOT%"=="" if exist "%LOCALAPPDATA%\ClawsJoyPA\scripts\win_pa\pa_update.py" set "ROOT=%LOCALAPPDATA%\ClawsJoyPA"
if "%ROOT%"=="" set "RC=3" & goto :noroot
set "PY=%ROOT%\runtime\python.exe"
set "UPD=%ROOT%\scripts\win_pa\pa_update.py"
set "LOGDIR=%LOCALAPPDATA%\ClawsJoyPA"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "LOG=%LOGDIR%\pa-update.log"
if not exist "%PY%" set "RC=3" & goto :nopy

rem --- clock: two DIRECT python one-liners (ASCII only; no %TIME% parsing
rem     => no locale trap; no for /f quoting trap either) ---
set "STAMP=%TEMP%\cjpa_pa_update_t0.txt"
"%PY%" -X utf8 -B -c "import sys,time;open(sys.argv[1],'w').write(str(int(time.time())))" "%STAMP%"

echo ============================================================
echo   ClawsJoy PA  --  payload update (by hand)
echo   root : %ROOT%
echo   log  : %LOG%
echo   the tool prints its own words below; usually well under 2 minutes
echo ============================================================
echo.
"%PY%" -X utf8 -B "%UPD%" --root "%ROOT%" --go --json > "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
type "%LOG%"
echo.

"%PY%" -X utf8 -B -c "import sys,time;print('[PA] elapsed ' + str(int(time.time()) - int(open(sys.argv[1]).read())) + ' s')" "%STAMP%"
echo [PA] exit=%RC%
if "%RC%"=="0" echo [PA] done  --  if it said "already latest", nothing was changed.
if not "%RC%"=="0" echo [PA] [FAIL] NOT updated  --  read the lines above; the whole log is kept at:
if not "%RC%"=="0" echo        %LOG%
echo.
goto :done

:noroot
echo ============================================================
echo   ClawsJoy PA  --  payload update (by hand)
echo ============================================================
echo [FAIL] no installed payload found.  looked at:
echo          %LOCALAPPDATA%\Programs\ClawsJoyPA\resources\payload
echo          %LOCALAPPDATA%\ClawsJoyPA
echo.
echo   if ClawsJoy PA is installed somewhere else, point us at it first:
echo          set PA_ROOT=D:\path\to\payload
echo          pa-update.cmd
echo.
goto :done

:nopy
echo [FAIL] found %ROOT%
echo        but there is no bundled python at %PY%
echo        the install looks incomplete -- reinstall from the setup exe.
echo.
goto :done

:done
pause
if not "%_CJPA_CP%"=="" chcp %_CJPA_CP% >nul 2>&1
endlocal & exit /b %RC%