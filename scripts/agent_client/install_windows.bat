@echo off
chcp 65001 >nul
setlocal
echo ================================================
echo  ClawsJoy V9 本地浏览器客户端 - Windows 安装
echo ================================================
echo.

REM 定位脚本目录(支持从任意 cwd 运行)
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/4] 检查 Python ...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [X] 未找到 python, 请先安装 Python 3.10+ 并加入 PATH
    echo       下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
python -c "import sys; v=sys.version_info; assert v>=(3,10), '需要 Python 3.10+'; print('  [OK] Python', sys.version.split()[0])" 2>nul
if errorlevel 1 (
    echo   [X] Python 版本过低, 需要 3.10+
    pause
    exit /b 1
)

echo [2/4] 检查 pip ...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [X] pip 不可用, 请修复 Python 安装
    pause
    exit /b 1
)
echo   [OK] pip 可用

echo [3/4] 安装/检查依赖 (playwright / websockets / pyyaml) ...
python -m pip install -q --upgrade playwright websockets pyyaml
if errorlevel 1 (
    echo   [X] 依赖安装失败, 请检查网络
    pause
    exit /b 1
)
echo   [OK] 依赖已就绪

echo [4/4] 检查 playwright 浏览器(Windows 用系统 Chrome, 无需下载 chromium) ...
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(channel='chrome'); b.close(); p.stop(); print('  [OK] 系统 Chrome 可被 playwright 驱动')" 2>nul
if errorlevel 1 (
    echo   [.] 未检测到系统 Chrome(channel=chrome), 尝试安装 playwright chromium ...
    python -m playwright install chromium
    if errorlevel 1 (
        echo   [X] 浏览器安装失败
        pause
        exit /b 1
    )
    echo   [OK] playwright chromium 已安装
) else (
    echo   [OK] 系统 Chrome 可用(推荐: 可复用日常登录态)
)

echo.
echo ================================================
echo  安装完成! 用 start_windows.bat 启动客户端
echo ================================================
pause