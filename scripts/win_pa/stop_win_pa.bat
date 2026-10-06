@echo off
REM ============================================================
REM  Win-PA gateway stopper           (CW line / CodexWindows)
REM  Kills EXACTLY the PID that holds the configured port.
REM  By convention (see the paseo-pm port-ownership ledger v1, rule 1):
REM    the FIRST starter keeps the port; log every start/stop.
REM ============================================================
setlocal
REM  Path is taken from THIS file' location (%~dp0..\..) => runs from any folder.
cd /d "%~dp0..\.."

set GPORT=
for /f %%p in ('python -c "import sys;sys.path.insert(0,'.');from core.lib.port_config import gateway_port;print(gateway_port())"') do set GPORT=%%p
if "%GPORT%"=="" ( echo [FAIL] cannot read gateway port & exit /b 3 )

set PID=
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"TCP.*:%GPORT% .*LISTENING"') do set PID=%%p
if "%PID%"=="" ( echo [--] nothing listening on %GPORT%, nothing to stop & exit /b 0 )

echo [INFO] stopping PID %PID% on port %GPORT%
taskkill /PID %PID% /F
echo [DONE] remember to log this stop in the paseo-pm port-ownership ledger.
endlocal
