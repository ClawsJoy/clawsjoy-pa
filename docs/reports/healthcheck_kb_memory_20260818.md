# 知识库 & 永久记忆系统健康检查报告

- 日期: 2026-08-18
- 方式: 只读检查(不改代码), 实测驱动(实例化/读写/完整性校验)
- 环境: 沙箱 ClawsJoy Gateway v6.0 (5003), data_root=data

---

## 一、VectorKnowledgeCenter 五个集合状态

| 集合 | 计数 | 描述 | 状态 |
|---|---|---|---|
| skills | 1 | 技能知识库 | 正常(含1条测试残留, 见 §五) |
| agents | 0 | Agent知识库 | 正常(空) |
| routes | 0 | 路由知识库 | 正常(空) |
| memories | 0 | 记忆知识库 | 正常(空) |
| documents | 0 | 文档知识库 | 正常(空) |

初始化确认: 5 集合全部创建成功(collections 表 5 条 knowledge_* 记录),
get_client() 修复后 collections 正常初始化(不再死代码)。

另存在 6 个非标准集合(其他模块使用): code_blocks(36)、agent_capabilities(23)、
skill_vectors(0)、conversation(0)、learning_patterns(0)、intent_vectors(0)。

---

## 二、永久记忆(memory_agent) 写入/读取链路

### 存储层
- 目录: data/permanent_memory/ (2 个 JSON 文件, 12K)
- 命名: md5(user_id_agent_name)[:16].json
- 文件1: 7cab9796f6886842.json -> agent=memory_agent_v4, key=名字, value=小明 (08-17 22:27)
- 文件2: eb2396aaed09f5f3.json -> agent=memory_agent_v4, key=名字, value=李华 (08-18 16:35)

### 写入链路 (实测通过)
BaseAgent.remember_forever() -> _save_permanent_memory() -> md5 文件落盘
- 额外入口: core/lib/gateway_helpers.save_memory()(经 MemoryAgentV4.remember_forever)
- 另: MemoryBank.remember() 与 BaseAgent 共享同一文件(双引用模式)

### 读取链路 (实测通过)
- BaseAgent.recall_forever(key) 直接读内存 dict
- BaseAgent._load_permanent_memory(): 精确 key 文件 + 同 name 历史文件 fallback(方案A)
- AgentCortex: MemoryBank.get_bank(uid) -> recall(field) 语义检索注入(confidence 0.6)
- MemoryBank 同义词映射: 名字/密码/地址/年龄/职业/语言/城市/爱好/食物 (9 组)

### 实测结果
- 实例化 memory_agent(health_check_uid) -> 加载 1 条永久记忆(李华) -> recall_forever 返回 '李华' OK
- MemoryBank remember/recall 读写 OK(临时目录验证)
- 生命周期: memory_agent_v4 唤醒/健康检查 healthy, 启动日志无错误

---

## 三、知识库数据完整性

| 检查项 | 结果 |
|---|---|
| vector_kb 目录 | 存在, 17M, 4 个 UUID 段目录(每段含 data_level0.bin/header.bin/length.bin/link_lists.bin) |
| chroma.sqlite3 | 16M, 存在 |
| SQLite integrity_check | **ok** |
| page_size/page_count | 4096 / 3900 |
| journal_mode | delete |
| foreign_keys | 0(ChromaDB 默认) |
| 文件 JSON 校验 | 2 个永久记忆文件均合法 |
| 嵌入计数 | code_blocks=36, agent_capabilities=23, knowledge_skills=1, 其余 0 |

结论: 数据库结构完整, 无损坏。知识库实际承载数据集中在 code_blocks/agent_capabilities
(代码索引与能力库), 五知识集合中仅 skills 有 1 条测试数据。

---

## 四、get_client 修复后 add_skill/search 路径验证

| 路径 | 结果 |
|---|---|
| get_client() | 存在且返回 ChromaDB Client |
| add_skill() | 返回 doc_id (930d4c7b888ee4ec) |
| search(knowledge_type='skills') | 命中 1 条, 内容完整(技能名称/分类/描述/关键词/用法) |
| add_agent() | 成功, agents 计数 +1 |
| get_stats() | {skills:1, agents:1, routes:0, memories:0, documents:0} |
| VectorBank 实例化 | OK(独立 embedding 方案, 不依赖 ChromaDB client) |
| 网关 Code preload | 0 次 'Code preload failed'(修复后) |

结论: #22 修复的 add_skill/search 等全部路径工作正常。

---

## 五、发现的问题与建议

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | skills 集合含 1 条测试残留 'test_skill_x'(08-18 16:32, #22 修复验证时写入) | 低(测试数据污染生产库) | 用 clear_collection('skills') 或手工删除该条 |
| 2 | data/projects/test_sess_22、test_sess_22b 临时目录残留(各 200K) | 低 | 清理 |
| 3 | 五知识集合中 agents/routes/memories/documents 均为空 | 信息 | 正常(知识库按需写入) |
| 4 | knowledge_memories 集合(0条)与 permanent_memory JSON 文件并存 | 信息 | 两套记忆体系: 向量记忆(未用) vs JSON 永久记忆(在用), 建议确认是否需统一 |
| 5 | 永久记忆仅 2 条且都是 key='名字'(小明/李华), 无时间衰减/去重 | 低 | 观察; 长期建议增加去重与 importance 分级清理 |

---

## 六、总体结论

- 知识库: 健康。ChromaDB 完整性 ok, 五集合就绪, get_client 修复后读写链路全部验证通过。
- 永久记忆: 健康。写入(md5 文件落盘)/读取(精确 key + fallback + MemoryBank 语义检索)链路实测通过。
- 网关: 运行期间 0 知识库/记忆相关错误, Code preload 正常。
- 遗留: 2 处测试残留数据(#22 验证产生)建议清理; 双记忆体系设计建议后续确认。
