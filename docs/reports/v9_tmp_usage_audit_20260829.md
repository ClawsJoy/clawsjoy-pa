---

# V9 Agent /tmp 沙箱外路径检查报告（2026-08-29）

## 现象
- Agent 频繁尝试 /tmp（沙箱外），被拦截后浪费工具调用

## 检查结果

### 1. 工具默认临时路径
- playwright_browser 截图: 已强制落沙箱 data/screenshots/（L32-38, 无 /tmp）
- write_file 长内容通道: NamedTemporaryFile 瞬时(写完立即 unlink, 不落盘)
- query_index SAG 写: mkstemp 在目标父目录(沙箱内)
- video_analyzer: 系统 mkdtemp(进程内, 立即清理)
- **结论: 无工具默认写 /tmp**（瞬时 tempfile 不落盘）

### 2. 沙箱内专用临时目录
- **之前不存在** clawsjoy_dev/data/tmp/
- write_file L195 已自动创建父目录 → 写 data/tmp/xxx 自动建 data/tmp/（无需预建）

### 3. 系统提示
- 已有【沙箱边界】"禁止使用 /tmp、/home、/etc 等系统路径"（agent_gateway L3036-3040）
- **增强**: 明确告知 data/tmp/ 做临时文件 + data/reports/ 做报告

### 4. 拦截引导
- bridge_loop(主任务): 已有引导 L3500"请换沙箱内或项目根路径"
- **execute_agent_task(async/子任务): 之前只回 reason 无引导 → 已修复**, 与 bridge_loop 一致

## 证据（8 条真实 /tmp 越权）
- 7 条 read_file: /tmp/beidou_index.js ×2、/tmp ×4、绝对路径
- 1 条 execute_command: `> /tmp/pytest_run.log` 重定向
- 分布: 5 个不同 session（user-mt*、ext-integration、web_*）
- read_file 读 /tmp 居多 → Agent 想读临时/缓存文件, 但不知道往哪放

## 修复（已实施）
1. execute_agent_task L1388 forbidden 分支: 拦截后加替代路径引导
   "请改用沙箱内相对路径(data/tmp/ 临时文件、data/reports/ 报告)"
2. agent_gateway L3036 系统提示: 明确 data/tmp/ + data/reports/ 用法
3. data/tmp/ 无需预建: write_file L195 自动创建父目录

## 验证
- 全量回归(进行中, 预计 652+)
- 已同步 live 2 文件 + 提交
