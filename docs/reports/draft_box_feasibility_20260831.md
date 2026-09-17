
# Obsidian 草稿箱系统（插件化）可行性分析

> 日期: 2026-08-31 · 关联: v9_architecture_governance_v2.md (R5 browser_local 成本修复)
> 状态: 可行性研究完成, 结论=可行, 建议按方案实施

---

## 一、结论先行

**方案可行, 且是当前架构下的正确演进方向。** 核心前提已全部具备:

| 前提 | 现状 | 证据 |
|---|---|---|
| 网关侧写 vault | ✅ 已具备 | write_task_review/append_pitfall/update_sop 均直接写 vault(Reviews/SOPs/Pitfalls 文件存在) |
| 写 vault 免审批 | ✅ 已确认 | ApprovalGuard._WRITE_TOOLS=(write_file), obsidian_knowledge 不经沙箱审批直接写 |
| frontmatter 读写 | ✅ 已具备 | update_sop 已读写 frontmatter(updated 字段); read_knowledge_file 已解析 tags |
| 媒体复制 | ✅ 可行 | 沙箱 data/videos(bilibili_kaoyan_ai.mp4 4.7MB)可复制到 vault assets/ |
| 插件架构 | ✅ 有基类 | core/os/plugin.py V9Plugin (apply/dispose), 新插件注册进 registry 即可 |
| 工具扩展 | ✅ 有入口 | obsidian_knowledge 已有 action 枚举, 加 write_draft/mark_published/list_drafts 即可 |
| vault 全量检索 | ✅ R4 已修复 | _scan_vault 递归扫全部 .md, 草稿箱/ 目录自动纳入检索 |
| 上下文隔离 | ✅ R5 已修复 | 任务级隔离已上线, 新方案不依赖 browser_local 反复操作 → 成本大幅下降 |

---

## 二、关键可行性验证

### 2.1 vault 写入能力(已验证)
- precision_inject 网关侧直接写 vault, 不经沙箱/不经审批 — write_task_review 产出的 Reviews/*.md 已存在
- 草稿箱 = vault 下一个新目录, 复用同一写入路径, 零新基础设施

### 2.2 媒体文件处理(已验证)
- 沙箱 data/videos/bilibili_kaoyan_ai.mp4 (4.7MB) 存在 — 复制到 vault 草稿箱/B站/assets/ 用 shutil.copy
- 图片(<10MB)同理。Obsidian 原生支持 ![[文件名]] 嵌入与本地预览
- 注意: 视频复制会增加 vault 体积(4.7MB/条), 建议大文件用相对路径引用而非复制(见风险)

### 2.3 frontmatter 标准(已验证可行)
- platform/title/status/created/published/post_url/cover/summary/tags 均为标准 YAML, Obsidian 原生解析
- mark_published 更新 frontmatter = 读文件 → 正则/YAML 改 status/published/post_url → 写回 + shutil.move 到已发布/

### 2.4 插件化接入(已验证有基类)
- core/os/plugin.py V9Plugin(apply/dispose) 是现成基类
- 方案建议 core/plugins/draft_box/ 独立目录 — 需确认注册机制(见实施建议)

---

## 三、方案价值(相对现状)

| 维度 | 现状(browser_local 后台草稿) | 新方案(Obsidian 草稿箱) |
|---|---|---|
| 成本 | 11 次 browser_local = 527K tokens | Agent 只写本地文件, 成本≈一次 write_draft 调用 |
| 可靠性 | 平台 DOM 复杂(公众号/B站)反复失败 | 本地文件写入, 零平台依赖 |
| 用户可见性 | 草稿在平台后台, 难以审核 | Obsidian 原生查看内容+素材预览 |
| 反爬 | 反复操作触发平台反爬 | 不碰平台后台, 零反爬风险 |
| 发布确认 | Agent 操作易误发 | 用户手动发布, 天然审批 |
| 平台规范 | 散在 SOP 文件 | 草稿箱/平台规范/ 集中维护, Agent 调研后更新 |

---

## 四、风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 视频大文件复制膨胀 vault | vault 体积增长 | 视频用相对路径(../assets/video.mp4)或 symlink, 不复制; 图片仍复制 |
| 用户可能不回传链接 → mark_published 不触发 | 状态滞留 draft | write_draft 时给用户明确提示; 回传链接是轻量操作(复制 URL) |
| 旧草稿迁移量大(zhihu/xhs/wechat/bilibili) | 一次性工作量 | 按迁移清单分批; 可先建目录+模板, 再迁移 |
| 平台规范可能过时 | 用户看到的规范不准 | 规范文件加 updated 日期; Agent 定期(任务触发)调研刷新 |
| 插件注册机制未验证 | 接入成本 | 实施第一步先验证 V9Plugin 注册(现有 playwright_browser 等是否走此路径) |
| 草稿内容质量(Agent 生成的标题/摘要) | 用户仍需改 | 草稿箱定位=半成品, 用户审核修改后发布, 符合预期 |

---

## 五、实施建议(按方案十的顺序, 略调整)

1. **建目录 + 模板**: 草稿箱/{平台}/ + assets/ + 平台规范/ 5 个 md (基础, 无代码)
2. **base.py + 5 平台插件**: 先实现 write_draft + list_drafts(核心), mark_published 次之
3. **obsidian_knowledge 扩展 action**: 复用现有 tool_router 分发, 加 write_draft/mark_published/list_drafts 三个 action
4. **旧草稿迁移**: 按清单移动文件(zhihu/xhs/wechat/bilibili)
5. **SOP 更新**: 各平台发布 SOP 改为 产出→写草稿箱→用户审核→回传链接→mark_published
6. **端到端验证**: Agent 写一篇测试草稿(公众号) → 用户 Obsidian 审核 → 手动发布 → 回传 → 状态更新

> 建议验证 V9Plugin 注册机制后再定插件目录位置(core/plugins/ vs core/gateway/plugins/), 避免空转。
