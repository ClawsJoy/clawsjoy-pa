@echo off
REM ============================================================
REM  Win-PA gateway launcher          (CW line / CodexWindows)
REM  Port is NOT hardcoded here: it is read from the single
REM  source of truth  config/system/system_unified.yaml
REM  via  core.lib.port_config.gateway_port()
REM  Rule L-239: re-check the port AT THE MOMENT of starting.
REM ============================================================
setlocal
cd /d D:\clawsjoy_v9

set GPORT=
for /f %%p in ('python -c "import sys;sys.path.insert(0,'.');from core.lib.port_config import gateway_port;print(gateway_port())"') do set GPORT=%%p
if "%GPORT%"=="" ( echo [FAIL] cannot read gateway port from source of truth & exit /b 3 )
echo [INFO] gateway port = %GPORT%  (source: config/system/system_unified.yaml)

echo [1/3] port check at this very moment ...
set BUSY=
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"TCP.*:%GPORT% .*LISTENING"') do set BUSY=%%p
if not "%BUSY%"=="" (
  echo [STOP] port %GPORT% is ALREADY listening ^(PID %BUSY%^) - not starting a second one.
  echo        first look at  paseo-pm\_端口归属登记_v1.md  and agree who owns it.
  exit /b 2
)

echo [2/3] starting gateway ^(boot takes ~30s; probes will fail before that^) ...
echo [3/3] log: logs\gateway_5102_console.log
python -X utf8 agent_gateway_enhanced.py >> "logs\gateway_5102_console.log" 2>&1
endlocal
