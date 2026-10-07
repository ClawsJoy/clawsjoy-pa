# Obsidian 第二大脑集成规范（2026-08-29）

参考: https://github.com/kepano/obsidian-skills (Agent Skills 规范, vault 文件结构/双链/标签约定)

## 一、vault 路径配置

| 环境 | 路径 |
|---|---|
| Windows | <vault>\\ClawsJoy |
| WSL | /mnt/d/vault/ClawsJoy |
| V9 配置 | config/v9/execution_policy.yaml → obsidian.vault_path |

当前 vault 状态: /mnt/d/vault/ClawsJoy/ClawsJoy (已初始化, .obsidian + 欢迎.md)
写权限: V9 网关(danger-full-access 环境)可写 /mnt/d (实测 WRITE OK); 普通 sandbox 只读

## 二、vault 结构（obsidian-skills 最佳实践 + ClawsJoy 需求）

```
ClawsJoy/
├── .obsidian/                    # Obsidian 配置(已有)
├── 欢迎.md                       # 入口(已有)
├── Templates/                    # 笔记模板
│   ├── task-review.md           # 任务复盘模板
│   └── avoid-pitfalls.md        # 踩坑沉淀模板
├── Reviews/                      # 任务复盘笔记
│   └── {date}-{task_id}.md
├── SOPs/                         # 标准操作流程(可复用经验)
│   ├── 番茄推广SOP.md
│   └── 抖音发布SOP.md
└── Pitfalls/                     # 避坑集合
    └── avoid_pitfalls.md        # 按标签聚合的坑清单
```

## 三、笔记模板（frontmatter + 双链, 遵循 obsidian-skills PROPERTIES 规范）

```markdown
---
type: task-review
tags: [番茄推广, 抖音发布]
created: 2026-08-27
task_id: xxx
---
# 任务复盘：xxx

## 做了什么
## 关键决策
## 踩坑
## 可复用经验
## 相关
- [[番茄推广SOP]]
- [[抖音发布SOP]]
```

## 四、obsidian-skills 核心约定（V9 遵循）

1. **Frontmatter**: title/tags/aliases/cssclasses + 自定义属性(type/task_id/created)
2. **双链**: vault 内笔记用 [[Note]] (Obsidian 自动跟踪重命名); 外部 URL 用 [text](url)
3. **标签**: 行内 #tag + 嵌套 #nested/tag; frontmatter tags 列表可搜索
4. **Callout**: > [!note]/[!warning] 等用于高亮; AI 写笔记用 callout 标注关键经验
5. **AI 读写方式**: 直接文件系统读写 .md(Obsidian 自动检测文件变化刷新)

## 五、自动写入时机（V9 集成）

| 时机 | 动作 | 目标 |
|---|---|---|
| 任务完成(reason=completed) | 写复盘笔记 | Reviews/{date}-{task_id}.md |
| 新坑发现(连续失败/越权) | 追加 avoid_pitfalls.md | Pitfalls/avoid_pitfalls.md |
| SOP 更新(可复用经验) | 同步/创建 SOP | SOPs/*.md |

## 六、知识检索（precision_inject 源）

vault 扫描 → 按任务语义检索相关笔记, 与 SAG/VectorBank 并列作为知识源。
实现: precision_inject.py 的 search_candidates 加 vault 源 —
扫描 Reviews/SOPs/Pitfalls/*.md → frontmatter tags + 标题 + 首段 → TF 关键词命中 → 候选
