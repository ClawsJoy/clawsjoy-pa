# #27 YouTube 下载失败 根因分析 + 修复方案

- 日期: 2026-08-19
- 方式: 只读排查 + 实测复现(无代理 vs 带代理对照)
- 结论: **沙箱环境变量白名单剥离了代理, yt-dlp 直连 YouTube 被网络策略拦截**

---

## 一、排查结果

### 1. yt-dlp 已安装 [OK]
- /home/<user>/miniconda3/bin/yt-dlp, 版本 2026.07.04
- pip 包存在(yt-dlp 2026.7.4)

### 2. 代理配置现状

| 位置 | 状态 |
|---|---|
| 宿主 shell 环境变量 | http_proxy/https_proxy/HTTP_PROXY/HTTPS_PROXY = http://127.0.0.1:7890 (clash 代理) 存在 |
| config/.env | HTTP_PROXY/HTTPS_PROXY 被注释(# 开头) |
| 网关进程 environ | 无任何代理变量 |
| 沙箱 _SANDBOX_ENV 白名单 | 不含代理变量 (shared_state.py:147-150) |

### 3. 网络连通性实测

| 场景 | 结果 |
|---|---|
| curl example.com (带代理) | 200 [OK] |
| curl youtube.com (带代理) | 200 [OK] |
| yt-dlp 元数据 (带代理 env) | 成功, 609KB JSON [OK] |
| yt-dlp 元数据 (无代理) | 失败: Connection reset by peer + Connection to www.youtube.com timed out [FAIL] |

---

## 二、根因链

1. V9 的 execute_command 工具执行子进程时使用 _SANDBOX_ENV(shared_state.py:147-150)
2. _SANDBOX_ENV 是白名单, 只透传 PATH/HOME/LANG/PYTHON 等, 刻意排除所有代理变量
3. 沙箱内跑 yt-dlp -> 无代理 -> 直连 YouTube -> 被网络策略拦截(Connection reset by peer)
4. yt-dlp 重试 3 次后放弃 -> V9 报 'example.com 可达但 Google/YouTube 被网络策略拦截'
5. 宿主 shell 测试正常是因为宿主环境有代理, 与沙箱环境不同

一句话: 不是工具缺失、不是沙箱 URL 白名单问题, 是沙箱 env 剥离代理导致 yt-dlp 无代理直连被拦。

---

## 三、修复方案(三选一, 按推荐度)

### 方案 A(推荐): _SANDBOX_ENV 白名单加代理变量

在 shared_state.py:147-150 的白名单集合中加入:
http_proxy, https_proxy, HTTP_PROXY, HTTPS_PROXY, no_proxy, NO_PROXY

- 影响: 所有沙箱子进程获得代理能力(下载/外网访问正常)
- 风险: 低 — 代理仅指向本机 127.0.0.1:7890, 不泄露凭据

### 方案 B: 网关启动时从 config/.env 读代理注入
- 取消 config/.env 注释 + 启动时加载进 os.environ, 再配合方案 A 透传
- 适合代理地址要配置化的场景

### 方案 C: yt-dlp 专用代理参数
- 在下载工具里显式 yt-dlp --proxy http://127.0.0.1:7890
- 只修 YouTube 下载, 其他网络工具不受益

建议: 方案 A + 方案 B 组合(白名单透传 + .env 配置代理地址), 一劳永逸。

---

## 四、修复影响面

| 项 | 影响 |
|---|---|
| 沙箱子进程 | 获得代理能力(yt-dlp/curl/pip 等外网访问正常) |
| 安全 | 代理指向本机 clash, 无凭据泄露; no_proxy 保留本地直连 |
| 测试 | 需验证沙箱内 yt-dlp 下载成功 |

## 五、验证方法(修复后)

沙箱 env 模拟(带代理) 应成功:
env -i PATH=... http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 yt-dlp -J URL (已实测成功)
