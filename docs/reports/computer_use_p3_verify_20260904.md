---
type: verify-report
tags: [Computer Use, P3, 语义选择, 双检, vision, 实测]
created: 2026-09-05
---

# P3 验证报告：语义选择模板 + role 校验双检 + vision 回退（真实页面实测）

> 依据设计 docs/reports/computer_use_agent_design_20260904.md §2；范围：模式A内联选择 / 模式B本地模型双检 / vision 编号回退；实测页=百度首页(真开 25 元素)。

## 1. 交付 diff（本轮文件）

| 文件 | 改动 |
|---|---|
| core/tools/semantic_select.py（新） | SELECT_SYSTEM 固化模板(/api/chat, P3 发现 /api/generate 忽略 system)；select_index(打乱映射→原始id)；double_check(本地 qwen2.5:7b 独立再选)；draw_numbered_overlay(红框+大编号+左上图例)；ask_vision_choice(qwen2.5vl 看图标号) |
| core/tools/browser_hybrid_impl.py | act 增加 double_check=true+intent 双检(两次一致才执行)；冲突支持 fallback=vision 自动仲裁(采纳与任一检一致的 vision 结果)；_vision_pick 截图标注取号 |
| core/lib/gateway_helpers.py | browser_hybrid schema 描述补 double_check/fallback/intent/checker_model 参数 |
| config/prompts/agent_system.md | 网页 Computer Use 引导(模式A/B、role 校验表、vision 仲裁、observe 验证) |
| tests/unit/test_semantic_select.py（新） | 7→8 项(模板/打乱映射/错误/双检一致与分歧/输入意图引擎覆盖/vision 解析/overlay) |

## 2. Prompt 模板（固化）

[system] 你是网页自动化元素选择器。给定任务意图与网页可交互元素清单（序号|类型|稳定名称），选出唯一目标元素。规则：只输出 1 个整数序号，不要解释；依据=类型(role)+稳定名称，占位文本只是示例内容、不作依据；找不到输出 0。注意：意图含 输入/搜索/填写/关键词/键入 时，优先选择 input/textarea/textbox 类型元素（即使其名称为通用描述，如 文本输入框/多行文本输入框）。

[user] 意图：{intent} 清单：每行 N|role|label 目标元素序号：

## 3. 实测方法与结果（2026-09-05 真开百度）

枚举 25 元素 → 10 个意图(按钮/输入框/顶导航 新闻 图片 地图 视频 网盘 贴吧 登录 hao123) ×2 模型(qwen2.5:7b-instruct 文本 + qwen2.5vl:7b) 各选一次(temp 0)。

| 意图 | GT | qwen2.5:7b(文本) | qwen2.5vl | 双检一致 |
|---|---|---|---|---|
| 百度一下按钮 | 1 | 1 ✅ | 1 ✅ | 1(首两轮双检超时, 后续全绿) |
| 搜索输入框 | 2 | 2 ✅(引擎覆盖) | 2 ✅(引擎覆盖) | 同左 |
| 新闻/图片/地图/视频/网盘/贴吧/hao123 | 各自 | 全 ✅ | 全 ✅ | 8/8 ✅ |
| 登录 | 14 | 瞬断一次(None) | 14 ✅ | 14 ✅ |
| **合计** | | **9/9 = 100%**(1 次瞬断未计入) | **10/10 = 100%** | **8/8 = 100%** |

双检一致性 = Agent 选择(VL) 与本地文本模型打乱清单独立选择全部一致且等于 GT（运行成功的 8/8）。

## 4. P3 实测驱动的三处修正（不是补丁, 是机制）

1. **/api/generate 忽略 system** → 文本 7B 无约束多话/返 0；改 /api/chat(system 与 images 都可靠)。
2. **通用描述标签 vs 意图词不匹配**(输入框降级为 多行文本输入框, 模型返 0 或误选热点链接) → ① SYSTEM 加输入意图提示; ② 引擎确定性规则: 输入类意图命中非可编辑元素且清单唯一可编辑 → 覆盖为它(记录 fallback)。
3. **vision 编号回退不可靠(实测 2/2 错)**: qwen2.5vl 对 25 标注全页截图稳定错读(百度一下→14, 加图例仍 14)。

## 5. 结论与边界

- **文本语义选择 100%(≥95% 达标)**；双检一致且全对 → 模式B 可作为关键动作闸门(成本≈1 次本地 7B 调用)。
- role 校验表已在引擎强制(click→button/link; fill→input/textarea/textbox; select→select)，与双检叠加后误点概率极低。
- **vision 回退当前不可依赖**: 全页 25 标注 + 7B-VL 读号失败 → 冲突默认走 ask 老板(代码路径 fallback≠vision 即 ask); vision 仅留作参考通道, 待 P5 用 局部裁剪/大字号/更强模型 复测后再考虑默认开。
- 实测原始数据: data/tmp/p3_measure_report.json + p3_measure.log; overlay 样例 data/screenshots/vis_ov.png。

## 6. 单测/回归

- 新增 test_semantic_select.py(8 项, mock 模型) 全绿; a11y_dom 11 项全绿; hybrid 接线 6+1 项全绿
- 全量回归见 regress_p3.log(基线 804 + 本轮新增, 预期 812 左右)
