@echo off
REM ============================================================
REM  Win-PA gateway launcher  (thin shell)   (CW line / CodexWindows)
REM  STAR 收口 (pm_1369 Sec-2 裁): this file MUST NOT start the
REM  gateway itself -- it only forwards to the SINGLE entry:
REM      scripts\win_pa\pa_nowindow.py start
REM  Why: two entries have DIFFERENT gates (here: port only;
REM  pa_nowindow: full preflight) => drift = false green.
REM  Also honours scripts\win_pa\boot_resume.py:6 'no second launcher'.
REM  Port still comes from the single source of truth
REM  config/system/system_unified.yaml via core.lib.port_config.
REM ============================================================
setlocal
cd /d D:\clawsjoy_v9
python -X utf8 scripts\win_pa\pa_nowindow.py start
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%
