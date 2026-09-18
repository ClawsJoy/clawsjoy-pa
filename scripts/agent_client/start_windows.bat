@echo off
chcp 65001 >nul
setlocal
echo ================================================
echo  ClawsJoy V9 本地浏览器客户端 - Windows 启动
echo ================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 默认 WS 地址(网关 5005 端口); 可用 AGENT_CLIENT_WS 环境变量覆盖
if not defined AGENT_CLIENT_WS set AGENT_CLIENT_WS=ws://127.0.0.1:5005
if not defined AGENT_CLIENT_USER set AGENT_CLIENT_USER=web_windows

echo WS     : %AGENT_CLIENT_WS%
echo USER   : %AGENT_CLIENT_USER%
echo.

REM 可选: --platform 指定启动后打开的登录平台(如 xiaohongshu/bilibili)
set PLATFORM=
if not "%1"=="" set PLATFORM=--platform %1

echo 启动中(Windows Chrome 模式, 弹出 Chrome 窗口)...
echo.

REM --chrome: 用系统 Chrome; 默认用专用实例目录(不接管日常 profile)
REM --profile: 显式接管一个已存在的 Chrome 用户数据目录(会复用其登录态; 启动日志打印实际路径)
REM 示例: start_windows.bat bilibili
REM       或显式接管: python agent_client.py --chrome --profile "<某个已存在的 Chrome 用户数据目录>"
python agent_client.py --ws "%AGENT_CLIENT_WS%" --user-id "%AGENT_CLIENT_USER%" --chrome %PLATFORM%

if errorlevel 1 (
    echo.
    echo [X] 启动失败, 请检查:
    echo     1) 已运行 install_windows.bat
    echo     2) 网关已启动(端口 5005 可访问)
    echo     3) Chrome 已安装
    echo.
    pause
)