# V9 工作区 Agent 的 DeepSeek ProxyError 排查报告（修订版）

**日期**: 2026-08-24（第 2 版，根因实证修正）
**现象**: HTTPSConnectionPool(host='api.deepseek.com') → ProxyError('Unable to connect to proxy') → 127.0.0.1:7890 Connection refused

---

## 一、调用链（完整链路）

```
config/.env: HTTP_PROXY=http://127.0.0.1:7890   ← #27 为沙箱 yt-dlp/下载启用代理
  └─ agent_gateway_enhanced.py L115: load_dotenv(_env_path, override=True)
       └─ 运行时注入 os.environ[HTTP_PROXY] = http://127.0.0.1:7890   ★ 根因注入点
            └─ requests 默认 trust_env=True → 每次调用继承进程代理
                 ├─ DeepSeekAdapter (V9 Agent 主推理)
                 ├─ LLMClient / code_indexer / sandbox_ops FIM / os_monitor 探测
                 └─ /v9/user/balance 余额检查（裸 requests.get）
                      └─ 本机 7890 (Clash) 未监听 → Connection refused → ProxyError
```

**同链路全部 DeepSeek 出口**（逐一核对并加固）:

| 调用点 | 文件:行 | 用途 | 加固 |
|---|---|---|---|
| DeepSeekAdapter | core/lib/v8/adapters/deepseek_adapter.py | V9 Agent 主推理 | _DS_SESSION.trust_env=False |
| LLMClient | core/lib/llm_client.py L104-105 | 通用 LLM 客户端 | self._session.trust_env=False（原本已有）|
| 关键词生成 | core/lib/code_indexer.py L403 | 代码索引批处理 | proxies=None |
| FIM 补全 | core/gateway/sandbox_ops.py L602 | 代码补全 | proxies=None |
| 模型探测 | core/gateway/os_monitor.py L42 | 模型可用性探活 | proxies=None |
| 余额检查 ×2 | agent_gateway_enhanced.py L1818/L1926 | /v9 余额展示 | proxies=None |

---

## 二、根因（已实证，含对照实验）

**三层叠加**:

1. **注入源**: config/.env 中 HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:7890（#27 为沙箱 yt-dlp/下载访问外网而启用）。
2. **注入路径**: 网关启动时 load_dotenv(_env_path, override=True)（agent_gateway_enhanced.py L115）把代理**运行时注入** os.environ。
   ⚠️ 注意: /proc/<pid>/environ 只是 execve 启动快照，**看不到** load_dotenv 的运行时注入——早期“环境干净”的判断因此有盲区。
3. **继承放大**: requests 默认 trust_env=True，每次调用读 os.environ 代理 → 裸 requests 全部被引导到 7890 → 本机 Clash 未开 → Connection refused。

**实证**（在 load_dotenv 注入后）:
- 裸 requests.get → **ProxyError 复现**（与 live 网关 /v9/user/balance 实时返回完全一致）
- 加固后 DeepSeekAdapter → **success=True**（200）
- 加固后 proxies=None → **200**
- live 网关 curl /v9/user/balance **当前仍在报 ProxyError**（非陈旧错误；未修复代码时每次启动都会注入代理）

---

## 三、修复（已完成并验证）

**设计原则**: .env 保留代理（#27 沙箱 yt-dlp 需要），DeepSeek 等国内直连 API 在**代码层绕过**代理——两者不冲突。

| 文件 | 修复 |
|---|---|
| core/lib/v8/adapters/deepseek_adapter.py | 模块级 _DS_SESSION = requests.Session(); trust_env=False，全部请求走该 session |
| core/lib/code_indexer.py L403 | proxies={'http': None, 'https': None} |
| core/gateway/sandbox_ops.py L602 | 同上 |
| core/gateway/os_monitor.py L42 | 同上 |
| agent_gateway_enhanced.py L1818/L1926 | 两处余额检查 proxies=None |
| config/.env | **恢复** HTTP_PROXY/HTTPS_PROXY=7890（之前被误清空，破坏 #27）|

**验证结果**:
- 对照实验: 注入代理下 裸 requests 复现 ProxyError / adapter success=True / proxies=None 200 ✅
- py_compile 全部通过 ✅
- test_adapter_timeout + test_max_total_tools: **8 passed** ✅
- test_proxy_sandbox_fix: **4 passed**（.env 恢复后）✅

---

## 四、待同步到线上（必须，否则 live 仍报错）

需手动同步 sandbox → /home/<user>/clawsjoy_v5 并**重启网关**:
- agent_gateway_enhanced.py（L1818/L1926 加固 + 此前 max_bridge_rounds 16 改动）
- core/lib/v8/adapters/deepseek_adapter.py
- core/lib/code_indexer.py
- core/gateway/sandbox_ops.py
- core/gateway/os_monitor.py
- config/.env（若 live 端被清空过则恢复代理行）

**验证方法（重启后）**: curl http://127.0.0.1:5002/v9/user/balance 应返回余额 JSON 而非 ProxyError。

> 备注: live 端 config/.env 目前仍是 HTTP_PROXY=7890（正确，#27 需求），无需改动；重启加载新代码后 DeepSeek 调用即绕过代理。
