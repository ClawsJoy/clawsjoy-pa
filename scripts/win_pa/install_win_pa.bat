@echo off
REM ============================================================
REM  Win-PA one-click installer (thin shell)  (TD line / CodexWindows)
REM  Ensures the product dirs exist (data\ data\tmp data\v9\pa logs).
REM  Dry-run by default; pass --go to actually create directories.
REM  --register-tasks (opt-in) additionally registers the two
REM  scheduled tasks  \ClawsJoy_PA_Boot  \ClawsJoy_PA_Start_Once.
REM  Never writes any file under data\ ; never deletes anything;
REM  never starts the gateway.
REM  Rationale: pm_1384 Sec-3 item-4 (M1 remaining work #4).
REM ============================================================
setlocal
REM  Path is taken from THIS file' location (%~dp0..\..) => runs from any folder.
cd /d "%~dp0..\.."
python -X utf8 scripts\win_pa\install_win_pa.py %*
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%
