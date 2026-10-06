@echo off
setlocal EnableExtensions
rem ============================================================
rem  ClawsJoyPA-Setup.exe（iexpress 自解压）之 AppLaunched 入口（承 pm_1577 §二.3 ／ §三.3）
rem
rem  位次：iexpress 把本件 ＋ payload.zip 解到 %TEMP%\IXP*.TMP ⇒ 以本目录为 CWD 跑本件。
rem        ⭐ 故本件：ⓐ tar 解 payload.zip 入装根  ⓑ 以**自带之 runtime** 跑 installer_post.py
rem        ⛔ 本件 ⛔ 起服 ／ ⛔ 装依赖（依已在 runtime 内 ⇒ 免网之要）
rem
rem  装根 ＝ %LOCALAPPDATA%\ClawsJoyPA（**用户级** ⇒ ⛔ UAC）
rem   ⚠ 可覆：set CJPA_DEST=<径>
rem ============================================================
set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "DEST=%LOCALAPPDATA%\ClawsJoyPA"
if not "%CJPA_DEST%"=="" set "DEST=%CJPA_DEST%"

echo ============================================================
echo   ClawsJoy PA 安装
echo   自带 Python 运行时 ｜ 免网 ｜ 免管理员
echo   装到：%DEST%
echo ============================================================
echo.

if not exist "%SRC%\payload.zip" (
  echo [FAIL] 找不到 payload.zip —— 安装包不完整
  pause
  exit /b 2
)
if not exist "%DEST%" mkdir "%DEST%" >nul 2>&1

echo [1/3] 解包（程序 ＋ 自带运行时）…… 约需 1-3 分钟
tar -xf "%SRC%\payload.zip" -C "%DEST%"
if errorlevel 1 (
  echo       tar 不可用或失败 —— 改走 PowerShell
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%SRC%\payload.zip' -DestinationPath '%DEST%' -Force"
  if errorlevel 1 (
    echo [FAIL] 解包失败 —— 磁盘空间是否够（约需 1 GB）
    pause
    exit /b 2
  )
)

echo [2/3] 立目录 ／ 建快捷 ／ 注册卸载项 ……
"%DEST%\runtime\python.exe" -X utf8 "%DEST%\scripts\win_pa\installer_post.py" --go --dest "%DEST%"
set "RC=%ERRORLEVEL%"

echo.
echo [3/3] 结果 rc=%RC%
if not "%RC%"=="0" echo [WARN] 有未成之项 —— 见上之数行
echo.
echo 已装。开始菜单 ^> ClawsJoy PA ^> 「启动 ClawsJoy PA」即可起服（首启约 30 秒）。
echo 卸载：开始菜单 ^> ClawsJoy PA ^> 「卸载 ClawsJoy PA」（你的 data\ 会保留）。
echo.
pause
endlocal & exit /b %RC%