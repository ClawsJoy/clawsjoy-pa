@echo off
setlocal EnableExtensions
for /f "tokens=2 delims=:" %%C in ('chcp') do set "_CJPA_CP=%%C"
chcp 65001 >nul
rem ============================================================
rem  ClawsJoyPA-Setup.exe (iexpress self-extract) -- AppLaunched entry
rem
rem  iexpress unpacks this file + payload.zip into %TEMP%\IXP*.TMP and runs
rem  this file with CWD = that folder, so:
rem    [1] tar -xf payload.zip into DEST
rem    [2] run installer_post.py with the BUNDLED runtime (never the system
rem        python; never start the service; never install deps -- they are
rem        already inside runtime\, which is what makes install offline)
rem
rem  DEST = %LOCALAPPDATA%\ClawsJoyPA (user level => no UAC).
rem  Override with:  set CJPA_DEST=<path>
rem
rem  THIS FILE MUST STAY 100% ASCII (pm_1578 s2.2).  Why: cmd.exe decodes
rem  .cmd BYTES with the CONSOLE code page.  A BOM-less UTF-8 file on a
rem  GBK(936) console mis-pairs CJK bytes with DBCS units, and Windows
rem  DBCS decoding swallows 2 bytes on an invalid trail byte => it eats
rem  CR / ^ / quotes => lines splice and CJK bytes get run as commands
rem  (first-hand control: 'm' is not recognized ... / syntax is incorrect).
rem  Human-facing words come from the bundled Python instead.
rem ============================================================
set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "DEST=%LOCALAPPDATA%\ClawsJoyPA"
if not "%CJPA_DEST%"=="" set "DEST=%CJPA_DEST%"

echo ============================================================
echo   ClawsJoy PA setup
echo   bundled Python runtime  ^|  offline  ^|  no administrator
echo   DEST: %DEST%
echo ============================================================
echo.

if not exist "%SRC%\payload.zip" (
  echo [FAIL] payload.zip not found -- the setup package is incomplete
  pause
  exit /b 2
)
if not exist "%DEST%" mkdir "%DEST%" >nul 2>&1

echo [1/3] unpacking program + bundled runtime ... about 1-3 minutes
tar -xf "%SRC%\payload.zip" -C "%DEST%"
if errorlevel 1 (
  echo       tar unavailable or failed -- falling back to PowerShell
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%SRC%\payload.zip' -DestinationPath '%DEST%' -Force"
  if errorlevel 1 (
    echo [FAIL] unpack failed -- is there enough free space? about 1 GB needed
    pause
    exit /b 2
  )
)

echo [2/3] creating folders / shortcuts / uninstall entry ...
"%DEST%\runtime\python.exe" -X utf8 "%DEST%\scripts\win_pa\installer_post.py" --go --dest "%DEST%"
set "RC=%ERRORLEVEL%"

echo.
echo [3/3] result rc=%RC%
if not "%RC%"=="0" echo [WARN] some steps did not succeed -- see the lines above
echo.
echo Done. Start it from the Start Menu under ClawsJoy PA.
echo Uninstall from the Start Menu too -- your data folder is kept.
echo.
pause
endlocal & exit /b %RC%
