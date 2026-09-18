# agent_client — V9 本地浏览器客户端（Python + Playwright）

真实 Chrome（headed）+ 持久登录态，替代已废弃的扩展 CDP 方案。V9 Agent 调 \`browser_local\` 时由本客户端执行。

## 安装（一次性）

\`\`\`bash
pip install playwright websockets
playwright install chromium
\`\`\`

## 使用

\`\`\`bash
# 首次: 启动客户端并打开小红书登录页, 在浏览器窗口扫码一次
python agent_client.py --user-id <你的V9用户ID> --platform xiaohongshu

# 之后: 直接启动即复用登录态
python agent_client.py --user-id <你的V9用户ID>
\`\`\`

- \`--ws\` 默认 \`ws://127.0.0.1:5006\`（V9 WS 端口, 可配置）
- \`--headless\` 无头模式（测试用; 真机登录/过风控需 headed）
- 登录态存 \`~/.clawsjoy/profiles/\`（persistent context, 自动复用）

## 协议

复用 V9 桥接协议: \`hello{user_id}\` → \`exec{cmd_id,action,params}\` → \`result{cmd_id,ok,data}\`
新增: \`login_status{platform,logged_in}\` / \`verify_required{platform,url}\`（风控暂停通知）

## 动作

navigate / extract / screenshot / scroll / click / fill / search / publish（playwright 原生实现）

## 测试

\`\`\`bash
python scripts/agent_client/tests/test_roundtrip.py   # WS 往返 + 动作 + 卡片提取(fixture 模拟小红书 DOM)
\`\`\`

## 平台适配

编辑 \`config/platforms.yaml\`（覆盖/新增平台: 登录URL/搜索URL/卡片选择器/登录Cookie标识）。内置: 小红书/抖音/B站/知乎/微博/YouTube。

## 登录态 / 风控

- 启动时上报各平台登录态: \`login_status{platform, logged_in}\`(cookie 启发式)
- 未登录平台执行 search/publish/click/fill → 返回 \`login_required\`(Agent 提示用户扫码) + 上报 login_status False
- 风控检测: 页面含验证关键字/URL 命中(安全限制/IP风险/验证码/滑动验证/captcha…) → 返回 \`verify_required\` + 发 \`verify_required\` 消息
- 用户直接在 headed 窗口过验证(扫码/滑块), 之后 Agent 重试即可继续

## 第 4/5 步测试

\`\`\`bash
python scripts/agent_client/tests/test_step45.py   # 未登录门槛 + 风控上报 + click/fill/publish
\`\`\`
## Windows 客户端（真实 Chrome；默认专用实例，可选显式接管）

### 特点

- 用 **系统安装的 Chrome**（playwright `channel=chrome`），**默认用专用实例目录**（`~/.clawsjoy/profiles/default`）；扫码登录一次即由该目录保存登录态
- 一键脚本：`install_windows.bat` 装依赖、`start_windows.bat` 启动
- 可选 `--profile` **显式接管**一个已存在的 Chrome 用户数据目录（会复用其登录态；启动日志打印实际路径）

### 安装

```bat
双击 install_windows.bat   （或命令行执行）
:: 检查 Python 3.10+ / pip -> 装 playwright+websockets+pyyaml -> 验证 Chrome 可被驱动
```

### 启动

```bat
双击 start_windows.bat                :: 默认连 ws://127.0.0.1:5006, user=web_windows
start_windows.bat bilibili            :: 启动后自动打开 B站登录页(可选平台参数)
```

### 直接命令（等价）

```bat
REM 用系统 Chrome + 默认 profile（~/.clawsjoy/profiles/default 由本客户端自建）
python agent_client.py --chrome --user-id web_windows --ws ws://127.0.0.1:5006

REM 显式接管一个已存在的 Chrome 用户数据目录（不拼 /default；日志会打印实际路径）
python agent_client.py --chrome --profile "<某个已存在的 Chrome 用户数据目录>"

REM 带平台: 启动后打开登录页
python agent_client.py --chrome --user-id web_windows --platform bilibili
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `--chrome` | 用系统安装的 Chrome（channel=chrome）。Linux 上会报 Chromium distribution chrome is not found（预期，仅 Windows 用） |
| `--profile` | **显式接管**一个已存在的 Chrome 用户数据目录。传了则直接复用该目录登录态（启动日志会打印实际路径）；留空用 `--profile-root/default` 专用实例目录 |

### 注意

- 使用 `--profile` 指向日常 Chrome 目录时，**先关闭正在运行的 Chrome**（否则 profile 锁冲突）
- 首次用默认 profile 时在弹出窗口扫码登录一次，之后自动复用
- WS 端口 5006 是 V9 网关的 browser_local 服务端；确保网关已启动
