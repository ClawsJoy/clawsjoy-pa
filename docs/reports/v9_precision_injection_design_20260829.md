# V9 过滤网能力评估 + 上下文精准注入组合方案（2026-08-29）

---

## 一、现有过滤网能力清单

| 机制 | 位置 | 类型 | 现状 | 精准注入可用性 |
|---|---|---|---|---|
| TOOLS_FILTER | agent_gateway L2811 | 安全过滤(mode白名单) | 按模式隐藏不可用工具 | 保留(安全), 不扩展 |
| domain_whitelist | browser_local L166 | 安全过滤(域名白名单) | 浏览器域名白名单 | 保留(安全), 不扩展 |
| 递归检测/守卫 | guards/registry.py | 安全过滤(防循环) | 同工具/同路径计数+暂停 | 保留(安全), 不扩展 |
| EscapeGuard/ApprovalGuard | guards/registry.py | 安全过滤(越权/审批) | 路径/命令/写审批 | 保留(安全), 不扩展 |
| known_issues | memory.py | 注入(20条) | 失败经验, 纯时间序取前5 | **可扩展**: 缺相关性评分 |
| known_patterns | memory.py | 注入(20条) | 有效模式, 纯时间序取前5 | **可扩展**: 缺相关性评分 |
| 跨会话记忆【跨会话记忆】 | agent_gateway L3028 | 注入 | get_memory_context 时间序 | **扩展点** |
| platform_insights | metacognitive_agent | 注入 | 平台洞察(未接入主流程) | 可复用 |
| _finalize_messages | message_assembler L357 | 规范化 | 配对修复+tool_calls规范化 | 保留(出口守卫) |
| _compress_messages | message_assembler L207 | 上下文管理 | 压缩旧消息 | 保留(总量控制) |
| 沙箱边界提示 | agent_gateway L3036 | 注入(静态) | 固定提示 | 保留 |
| SAG 全文检索 | code_entity_extractor L702 | 语义检索(关键词) | query_fulltext_by_keywords + search_with_hyperedges | **可复用**: relevance 命中率 |
| VectorBank | core/vector/* | 语义检索(向量) | vector_store(search) + vector_memory(TF余弦) | **可复用**: search(query, limit) |
| 报告产出 | data/reports/ | 知识源(任务产出) | write_file 落盘, _scan_session_files 可见 | 新知识源 |

## 二、评估结论

### 纯安全过滤（保留, 不用于注入）
- TOOLS_FILTER / domain_whitelist / 递归守卫 / EscapeGuard / ApprovalGuard — 5 项

### 已有注入能力（可扩展为精准注入）
- known_issues + known_patterns: 已是注入, 但**纯时间序取前5, 无相关性** → 加相关性评分即精准
- SAG 全文检索: 已有 relevance(关键词命中率), 可作候选检索器
- VectorBank: vector_memory 有 TF 词频余弦相似度(不依赖外部模型, 已可用); vector_store 有 sentence-transformers(当前 torch 不兼容, 降级 TF)

### 缺相关性评分/语义检索的部分
- memory.py get_memory_context: 时间序 → 缺任务相关性
- 无任务语义提取(当前任务 embedding) → 需新增
- 无过滤层(评分+去重+优先级+衰减) → 需新增
- 无压缩(摘要≤100字/条) → 需新增

## 三、组合方案设计

### 架构: 知识源 → 注入过滤层 → 注入

```
知识源层                          注入过滤层(新增: core/gateway/precision_inject.py)         注入层
├ Obsidian vault        ─┐       ┌ 1.任务语义提取(当前user_msg+最近消息 → 关键词/embedding)
├ SAG(代码图谱)         ─┼─候选─→├ 2.检索(多源并行: memory/SAG/Vector/报告)
├ VectorBank(语义)      ─┤       ├ 3.过滤(相关性评分+去重+优先级+时间衰减)
└ 报告/SOP(data/reports)─┘       └ 4.压缩(摘要≤100字/条, 注入top 3-5条)
                                                        ↓
                                          messages += 【精准上下文】...
```

### 数据流
1. **任务语义提取**: 取最近 user 消息 → 中文分词(TF 复用 vector_memory._tokenize) → 关键词集 + 可选 embedding
2. **多源检索**:
   - memory: known_issues/known_patterns 全文 → TF 相似度排序
   - SAG: query_fulltext_by_keywords(关键词) → relevance
   - Vector: vector_memory.search(查询文本) → cosine
   - 报告: data/reports/*.md 文件名+首段 → 关键词命中
3. **过滤**: 各源结果合并 → 去重(内容相似>0.8 保留最新) → 加权(任务词命中×2 + 时间衰减) → 取 top 5
4. **压缩**: 每条截断/摘要 ≤100 字 → 拼【精准上下文】system 消息注入

### 接口设计（新增 precision_inject.py）
```python
def extract_task_semantics(messages) -> dict:      # {keywords: [...], text: "..."}
def search_candidates(sem, user_id, session_id, sandbox_base) -> list[dict]:  # 多源候选
def filter_and_rank(candidates, sem, now) -> list[dict]:  # 评分+去重+衰减, 返回 top N
def summarize(item, max_chars=100) -> str:          # 压缩
def build_injection(candidates) -> str:             # 拼【精准上下文】文本
def get_precision_context(messages, user_id, session_id, sandbox_base) -> str:  # 入口
```

### 注入点（agent_gateway L3028 附近, 与【跨会话记忆】并列）
```python
try:
    from core.gateway.precision_inject import get_precision_context as _pctx
    _pctx_txt = _pctx(messages, user_id, session_id, _get_sandbox_base(user_id, session_id))
    if _pctx_txt and not any(str(m.get('content','')).startswith('【精准上下文】') for m in messages):
        messages.append({"role": "system", "content": _pctx_txt})
except Exception:
    pass
```

## 四、增量实现量

| 组件 | 状态 | 增量 |
|---|---|---|
| 任务语义提取 | 新做 | 中: 复用 vector_memory._tokenize(已有) + 关键词提取 |
| 检索-memory | 扩展 | 小: memory.py 加 search(keywords) 替代纯时间序 |
| 检索-SAG | 复用 | 0: 已有 query_fulltext_by_keywords |
| 检索-Vector | 复用 | 0: vector_memory.search 已有(TF, 无需外部模型) |
| 检索-报告 | 新做 | 小: 扫 data/reports/*.md 文件名+首段关键词命中 |
| 过滤(评分/去重/衰减) | 新做 | 中: precision_inject.py 核心逻辑 |
| 压缩(≤100字) | 新做 | 小: 截断/摘要函数 |
| 注入点 | 新做 | 小: agent_gateway L3028 并列接入 |
| Obsidian vault | 可选(未装) | 中: 目录扫描+markdown解析(双链/标签→关键词); 仅当用户需要时安装 |
| 测试 | 新做 | 中: test_precision_inject.py 单元测试 |

## 五、冲突风险评估

| 关系 | 风险 | 缓解 |
|---|---|---|
| Obsidian ↔ SAG | 低: 一个人类知识(双链), 一个代码图谱(结构), 语义不同源 | 各自独立候选, 注入层合并去重 |
| Obsidian ↔ Vector | 中: 若 Obsidian 也入向量库, 双份语义 | 二选一: Obsidian 走关键词(双链/标签), 不重复入向量; 或统一入 Vector 由源字段区分 |
| SAG ↔ Vector | 低: SAG 是关键词精确, Vector 是语义模糊, 互补 | 合并时按源加权, 关键词命中优先 |
| 注入 ↔ 压缩 | 中: 注入多 + 压缩少 → 上下文膨胀; 注入少 + 压缩多 → 有用信息丢失 | 总量预算: 精准上下文 ≤ 500 tokens, 与 _calc_token_budget 联动 |
| 注入 ↔ 现有记忆 | 中: 【跨会话记忆】(时间序) 与 【精准上下文】(相关) 可能重复 | 精准注入优先, 跨会话记忆降为兜底(时间序), 去重逻辑覆盖 |
| 向量模型依赖 | 中: sentence-transformers 当前 torch 不兼容 | 默认 TF 降级(已可用), 模型可用时自动升级; 不阻塞 |

## 六、建议实施顺序
1. precision_inject.py 核心(提取+检索+过滤+压缩) — 复用 memory/SAG/Vector 已有能力
2. 接入 agent_gateway L3028 注入点
3. test_precision_inject.py 单元测试(纯函数, 不依赖外部服务)
4. Obsidian vault(可选, 用户确认后) — 目录扫描 + 双链/标签 → 关键词候选
5. 端到端验证: 跑几个任务, 检查注入条目的相关性
