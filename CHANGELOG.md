# Changelog

## 2026-08 — 工程化自检整改（data/plans/engineering_audit.md 剩余项）

### P0-2：四层注入调用链收敛 — loop_context_manager.py 状态标注（完成）
- 现状确认：clawsjoy_v10/engine/context/loop_context_manager.py 与 core/lib/v8/loop_context_manager.py 内容完全一致（md5 相同），为四层上下文编排注入的完整实现，但属于死代码
- 实际调用点仅 2 处，均未走四层注入主链路：
  - agent_gateway_enhanced.py L6067-6068 仅调用 core/lib/v8 副本的 _inject_tool_declarations()（工具声明段注入）
  - clawsjoy_v10/run.py L37 仅 import V10 副本（# noqa: E402,F401，模块加载副作用）
- 双轨并存：主流程 agent_gateway_enhanced.py 散落独立的 recap（steps_summary）与 precision（os_precision_feeds.yaml）实现，与四层注入互不调用
- 架构决策：暂不改主流程调用链（改动太大），在两个 loop_context_manager.py 副本头部加状态声明注释，防止后续误用；修改注入逻辑优先改主流程已生效实现
- 验证通过：两副本 md5 一致（b12bf03fa8f3fd46d7daa6a490d1971e），注释插入幂等可重复执行


### P0-2/3/4：垃圾文件与嵌套目录清理（完成）
- 清理 core/bin 0 字节垃圾文件：Accept:、GET、Host:、User-Agent:、nul（共 5 个）
- 清理 tests 测试残留：test_xiaoxiao.mp3、test_chinese.mp3、conftest.py.bak
- 删除 web/web 递归嵌套目录：40 层无效符号链接链（指向 /mnt/d/clawsjoy/web 的 Windows 挂载路径，沙箱/仓库内均不存在），消除 371.59MB 幽灵引用
- 验证通过：删除后无残留，web/ 顶层正常

### P0-5：.env.example 脱敏模板（完成）
- 新增 .env.example：29 个配置键（JWT/端口/资讯 API/AI 模型），真实密钥全部替换为占位符
- 验证通过：真实密钥（sk-913c...、9f6b233c...）零泄漏

### P1-6：pyproject.toml（完成）
- 新增 pyproject.toml：project 元数据 + black（line-length=120）/isort/ruff（E/F/W/I/UP 规则集，排除 tools/archive/old/models/data）/mypy 配置
- 内置 pytest 配置（与 pytest.ini 对齐，testpaths=tests）
- 验证通过：TOML 解析 + 工具配置键齐全

### P1-8：CI 扩展（完成）
- ci.yml 从单 job 单测试扩展为三 job：lint（ruff + black 检查）/ test（pytest 全量 tests/，忽略 tests/tests 历史残留）/ build（Docker 镜像构建，依赖 lint+test）
- 验证通过：YAML 解析 OK，三个 job 步骤完整

### P1-9：端口统一（确认完成）
- 网关主入口 app.run 使用 unified_config.get("services.gateway.port", 5002)，与 .env GATEWAY_PORT=5002、core/lib/config_loader.py 环境变量读取一致
- 端口配置已三处统一（.env → config_loader → unified_config），无需再改

## 2026-08 — 审计整改（AUDIT_REPORT 4.1 立即执行项 + 4.3 开源治理）

### 开源治理文档补齐（4.3-2，完成）
- 新增 LICENSE（MIT，与 AUDIT 报告"开源免费（MIT License）"及 README 声明一致）
- 新增 CONTRIBUTING.md：开发环境、代码规范、Conventional Commits 提交规范、PR 流程、测试要求、问题报告模板
- 新增 SECURITY.md：支持版本声明、漏洞私下报告流程（7 个工作日响应）、部署安全建议（.env 脱敏 / 反向代理 / 沙箱隔离）
- 新增 CODE_OF_CONDUCT.md：Contributor Covenant 2.1 行为准则 + 社区影响分级执法指南
- README 许可证章节更新为明确引用 LICENSE 文件，并链接 CONTRIBUTING / SECURITY / CODE_OF_CONDUCT
- 验证通过：四文件存在性 + 内容完整性断言（MIT 声明 / PR 流程 / 漏洞报告 / Covenant 条款）

### 前置检测防误判：计划文本不再触发"文件已包含功能"（完成）
- 修复 agent_gateway_enhanced.py 两处前置检测：当最后一条 user 消息为计划文本（执行计划/修改计划/任务计划/实施计划/开发路线/步骤列表/实施步骤 开头或前 40 字含标记）时，关键词置空，不再误判"文件已包含任务要求的功能"直接 return，避免跳过实际修改
- 主路径 L2382 与 v9 同步路径 L5459 均加防护；正常用户需求消息不受影响
- 验证通过：py_compile + 4 场景断言（计划文本全过滤 / 正常需求保留）

### world_model code_edges 图化（#149 剩余，完成）
- agent_gateway_enhanced.py 新增 `_build_code_edges(modules)`：由 world_model.modules 线性 dict 推导图边（contains 文件→类/函数、imports 文件→依赖模块），与 DB code_edges 表同构
- `_update_world_model` 每次写入后重建 `world_model["code_edges"]`，实现 world_model 从线性 dict 到图结构升级

- 同步生成 .agent_state.json 持久化 code_edges（251 条边：183 imports + 68 contains，覆盖 54 个源文件）
- 验证通过：py_compile + 图边结构断言
- 归档一次性脚本到 tools/archive/（_fix_code_edges.py、_fix_code_edges_state.py）

### 依赖清单合并（4.1-1，完成）
- requirements.txt 统一为唯一运行依赖清单：17 个包（Web 服务 / 数据处理 / 认证缓存 / 可选 AI 依赖四组分类，含版本约束与注释）
- requirements-dev.txt 保留为开发测试依赖（pytest / 代码质量 / 安全扫描 / 性能测试），生产-开发分离属标准实践
- 校验 requirements.txt 与旧快照零缺失、零新增；Dockerfile（COPY requirements.txt + pip install -r）与 README 引用已对齐
- 归档冗余 requirements.txt.bak、.gitignore.bak 到 tools/archive/，根目录 .bak 残留清零

### 根目录清理（4.1-2，完成）
- 根目录一次性脚本（_fix_*.py / _patch_*.py / _edit_*.py / _extract_*.py）全部清零，均归档至 tools/archive/
- old/ 历史包袱目录（旧测试 5 个 + agent_test_artifacts 一次性脚本 7 个，无代码引用）整体归档至 tools/archive/old/
- 清理残留：空嵌套 clawsjoy_dev/ 目录、test_file.txt 测试残留；根目录 .bak 清零
- 根目录现仅保留运行/源码/文档/配置四类文件，与 AUDIT 3.2 历史包袱清理目标一致

### .gitignore 统一
- 覆盖 .env、*.bak、logs/、data/、__pycache__/、*.pyc、events_*.jsonl，防止敏感数据入库

### 网关瘦身（完成）
- 已拆分注册 Blueprint：video_studio_bp（web/api/video_studio_api.py）/ system_bp / skill_bp / agent_bp（core/routes/）/ web_bp（web/routes.py）
- 修复悬空导入：删除 `from routes.director_canvas_routes import canvas_bp`（routes/ 目录与 director_canvas_routes.py 均不存在，导致网关启动 ModuleNotFoundError 崩溃）及对应注册，启动导入链恢复完整

### cortex.py 折叠行修复（完成）
- 修复 core/agents/cortex.py L392 折叠损坏行（_fix_cortex_confidence.py 修复脚本残留的死代码导致 SyntaxError，网关无法启动）
- 删除损坏行、保留 v8 岗位专线注释，py_compile + 模块导入 + _infer_action 意图推断三重验证通过
- 网关 agent_gateway_enhanced.py 导入链完整，17 个核心模块语法检查全部通过

## 本轮 — Agent 工作区深度改造

### 核心成果
- **Agent@Agent 讨论引擎**：Agent 间可发起讨论、交换意见并收敛结论
- **长线七态状态机**：任务生命周期七态流转，支撑长线任务编排
- **上下文管理四层协同**：系统/工作区/任务/会话四层上下文协同管理
- **SAG 基础建设**：知识图谱（SAG）基础能力落地，语义检索 + 关联上下文
- **上下文温度监控 + 疲劳度管理**：监控上下文热度，自动管理疲劳度，防止上下文退化
- **文件系统外部记忆**：文件系统作为外部记忆载体，跨会话持久化
- **Verifier 验证模块**：修改后自动验证闭环，防止回归
- **注意力漂移检测 DriftDetector**：实时监测 Agent 注意力漂移，异常时自动纠偏，防止任务脱轨
- **OS 错误引导修复**：项目树注入改 system 角色 + 排除系统注入消息，消除 OS 层错误引导
- **工具配额超限降级引导**：read_file / list_dir 等配额超限时降级引导，替代生硬拒绝
- **@ 讨论按钮**：工作台一键 @ 发起讨论，衔接讨论引擎
- **_suggest_action 扩展**：建议动作能力扩展，覆盖更多交互场景

### 工具路径修复（完成）
- 修复 agent_gateway_enhanced.py 工具执行路径双重拼接：execute_command / search_files 含 `clawsjoy_dev/` 前缀时不再错误叠加 cwd
- 新增统一 `_resolve_path` 路径解析：read_file / write_file / list_dir / search_files / execute_command 五工具共用，自动补全 `clawsjoy_dev/` 前缀
- 验证通过：_verify_exec_path2.py（ASSERT OK）、_verify_search_path.py（VERIFY PASS）+ py_compile
- 归档 11 个一次性修复/验证脚本到 tools/archive/（_fix_exec_path*.py、_fix_search_path*.py、_verify_*.py、agent_gateway_enhanced.py.p0_backup）

### SAG 检索修复（完成）
- 修复 code_entity_extractor.py 检索两个问题：中文 query 匹配 + 返回路径格式
- 新增 `_chinese_query_terms`：中文 query 拆分为整句 + 中文段 + 二元组，提升 ILIKE 召回率；英文 query 保持原样
- 新增 `_format_path_for_agent`：实体返回路径统一输出 `clawsjoy_dev/xxx` 格式（与网关 `_resolve_path` 同逻辑，兼容绝对路径/双重前缀/裸相对路径）
- `search_with_hyperedges` 支持中文关键词匹配
- 验证通过：_verify_sag_fix.py 全部断言通过 + py_compile（code_entity_extractor.py / agent_gateway_enhanced.py）
- 归档 2 个一次性修复/验证脚本到 tools/archive/（_fix_sag_query.py、_verify_sag_fix.py）

### 数据层
- OS 事件采集：10 个注入点 → events_default.jsonl
- 递梯子链路：采集→读取→GLM5.2 分析→system_hypothesis 入库 SAG
- 精准投喂配置驱动：按任务类型自动注入数据资产

### 分析层
- GLM5.2 深度分析接入 reflect()
- 编排 Agent 自动消费 SAG 历史 hypothesis

### 配置
- os_precision_feeds.yaml：6 条投喂规则
- os_capabilities.yaml：20 条能力注册
- os_event_injection_points.yaml：10 个注入点

### 数字资产自动文件化（#145，完成）
- 新增 `_archive_asset`：将计划/报告/决策三类数字资产写入 `data/plans/{session_id}/`，plan/decision 存 JSON（含 steps、status、executable 元数据），report 存 Markdown（含会话摘要），并同步入库 SAG（store_step_summary）
- 触发点一：`_execute_agent_task` 的 `_save_state("done")` 时，按任务类型自动归档（planning → plan，其余 → report）
- 触发点二：`v9_agent_chat` 返回前检测最后一条 assistant 消息，含执行计划/步骤列表 → plan，含决策标记 → decision，含报告/结论标记 → report
- 新增 `_is_plan_message` 结构检测：≥2 个编号步骤 + 修改目标/路径 + ≥2 个动作步骤才判定为计划，避免误归档
- 端到端验证通过：plan/report/decision 三类资产文件结构校验 + SAG 入库成功，测试数据已清理
