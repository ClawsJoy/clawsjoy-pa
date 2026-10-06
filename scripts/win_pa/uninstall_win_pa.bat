@echo off
REM ============================================================
REM  Win-PA uninstaller (thin shell)   (TD line / CodexWindows)
REM  Removes ONLY the two registered scheduled tasks:
REM      \ClawsJoy_PA_Boot  \ClawsJoy_PA_Start_Once
REM  Dry-run by default; pass --go to actually delete.
REM  Never touches data\ logs\ web\ core\ (any product file).
REM  Rationale: pm_1382 Sec-2 item-1 (three-gaps #1).
REM ============================================================
setlocal
REM  Path is taken from THIS file' location (%~dp0..\..) => runs from any folder.
cd /d "%~dp0..\.."
python -X utf8 scripts\win_pa\uninstall_win_pa.py %*
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%
