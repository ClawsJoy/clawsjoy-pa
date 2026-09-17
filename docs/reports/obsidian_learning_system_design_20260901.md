
# Obsidian 多模态学习系统设计

> 日期: 2026-09-01 · 状态: 已确认调研, 待实施

---

## 一、技术调研结论

| 能力 | 现状 | 结论 |
|---|---|---|
| GPU | 无(NVML 被阻) | 转录走 CPU(faster-whisper int8) |
| faster-whisper | 1.2.1 已装, base 模型 CPU 加载 1.7s | ✅ 中文转录可行 |
| openai-whisper | 已装 | 备用 |
| ffmpeg | 已装 | ✅ 音频/视频解码 |
| PyPDF2 | 3.0.1 已装 | ✅ PDF 文本提取 |
| pydub/librosa | 已装 | 音频预处理(可选) |
| OCR(VLM/Tesseract) | 未装 | 后续阶段(图片先存原文件+占位) |

## 二、目录结构

vault/
├── 收件箱/           # 用户拖入文件, Agent 监控
├── 学习笔记/
│   ├── 视频/
│   ├── 音频/
│   ├── 图片/
│   └── PDF/
└── assets/           # 媒体文件统一存放(嵌入用)

## 三、处理管线(process_media 动作)

obsidian_knowledge 新增 process_media(file_path, media_type):

1. 视频/音频 → faster-whisper 转录(中文 int8) → LLM 总结要点 → 写笔记 + 原文件复制 assets/
2. PDF → PyPDF2 提取文本(限长) → LLM 总结 → 写笔记 + 原文件复制 assets/
3. 图片 → 复制原文件 + 占位描述(OCR 后续)

## 四、笔记格式

---
type: learning
source: video | audio | image | pdf
original: "![[原文件]]"
transcript: true | false
summary: 要点总结
tags: [学习, 视频]
created: 2026-09-01
---
## 要点
...
## 原文转录(可折叠)
...

## 五、whisper 接入方案

- 模型: faster-whisper base(CPU int8, 中文够用; 精度不足可升 small/medium)
- 语言: 自动检测, 中文优先; 模型缓存 ~/.cache/huggingface
- 降级: 模型加载失败 → 返回错误 + 提示; 后续可接 OpenAI whisper API
- 长音频: 分段转录(whisper 自动分段); 超长(>30min)限时/截断

## 六、触发方式

1. 手动: 用户告诉 Agent 「处理收件箱里的 xxx」 → Agent 调 process_media
2. 自动(后续): Agent 任务开始扫描 收件箱/ 新文件; 或文件系统 watch

## 七、实施顺序

1. vault 目录结构(收件箱/学习笔记{4类}/assets)
2. process_media 管线(whisper + PyPDF2 + 写笔记 + 媒体复制)
3. obsidian_knowledge 扩展 process_media action + schema
4. E2E: 放测试音频 → Agent 处理 → 笔记 + 原文件嵌入
