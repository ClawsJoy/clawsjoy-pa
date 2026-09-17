# Harness 间接指挥 V9 Agent 完成知乎发布设置 — 失败根因排查报告

> 日期: 2026-08-24 | 方式: Harness 不直接操作浏览器, 通过 live 网关(/v9/agent/chat)指挥 V9 Agent 用 browser_local 真机执行
> 环境: live 网关 5002 + WS 5005; Python 客户端(scripts/agent_client, --cookies-file 注入知乎登录态); 已登录编辑器 zhuanlan.zhihu.com/write

## 执行记录
| 轮次 | 结果 | 发现 |
|---|---|---|
| R1 | 12 步, 10 成功 + 2 click 失败「平台 xiaohongshu 未登录」 | 根因#1: 客户端 platform 默认 xiaohongshu, 无 platform 参数的 click/fill 被路由到 xiaohongshu 页面 → 登录门槛拦截 |
| R2 | 10 步, 8 成功 + 2 click 超时 input[placeholder=话题] | 根因#2: 话题输入真实 DOM 无「话题」placeholder(裸 input); 根因#3: 桥接硬编码 8 轮, 多步任务不够 |
| R3 | (暂停) zhuanlan.zhihu.com 对沙箱 IP 限流 ERR_CONNECTION_RESET | 环境限制, 待限流解除后真机继续 |

## 失败根因清单
1. 平台路由错误(已修): agent_client.execute 里 platform 默认 xiaohongshu,
   无 platform 的 click/fill/extract 被路由到默认 xiaohongshu 页 → 「平台 xiaohongshu 未登录」。
   → 修复: 按当前页面 URL 推断平台(infer_platform), navigate/search 按目标 URL 推断; 已在 R2 验证生效。
2. 话题输入 selector 错误(已缓解): 知乎话题输入是发布设置面板里的裸 input(placeholder 不含「话题」),
   input[placeholder*=话题] 必然超时。→ 客户端加 label 邻近兜底(点「添加话题」label → 找附近可编辑元素)。
3. 桥接 8 轮硬上限(已修): agent_gateway for _bridge_round in range(8) 硬编码, 多步浏览器任务耗尽。
   → 配置化 execution_budget.max_bridge_rounds(默认 16)。

## 每环节最终可用方案(待真机校准)
| 环节 | 方案 |
|---|---|
| 进入编辑器 | navigate https://zhuanlan.zhihu.com/write(客户端带登录态) |
| 发布设置调研 | extract include_hidden=true(隐藏/下拉/选项元素属性+文本) |
| 话题 | 打开发布设置面板 → extract include_hidden 定位话题输入(裸 input, 邻近「添加话题」label) → click → fill → 等下拉 → 点第一个匹配 |
| 声明 | 面板内 checkbox, 按 label 定位(「声明」/「原创」) → click |
| 封面 | file input accept='.jpeg, .jpg, .png'(窄集) 区分正文插图(webp/avif); 上传走 publish 的 cover 参数(需审批) |
| 投稿 | 调研发布设置面板内「投稿到专栏」控件(记录 selector) |
| 发布 | 【禁止】— submit 置空 / 审批流拦截 |

## 需要增强的 browser_local 能力
1. ✅ platform 推断(按 URL)—— 已完成
2. ✅ 话题 label 邻近兜底 —— 已完成
3. ✅ 桥接轮次配置化 —— 已完成(沙箱, 需同步 live + 重启)
4. ⏳ 发布设置面板的「打开面板」交互: 建议 publish 前先 click 发布设置按钮(可在任务指令中引导, 或客户端 publish 内置)

## 环境注意
- 沙箱 IP 对 zhuanlan.zhihu.com 登录态访问会限流(连续探测后 ERR_CONNECTION_RESET); 真机(用户网络)无此问题。
- 客户端 --cookies-file 注入登录态(新增能力); 真机用 --platform xiaohongshu 扫码登录同样有效。
