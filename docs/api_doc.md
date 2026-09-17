# Video Studio API 文档

> 基础路径：`/api/video-studio`
> 所有路由定义在 `web/api/video_studio_api.py` 中。

---

## 目录

1. [POST /api/video-studio/import — 导入视频](#1-post-apivideo-studioimport--导入视频)
2. [GET /api/video-studio/timeline/\\<project_id\\> — 获取时间线](#2-get-apivideo-studiotimelineproject_id--获取时间线)
3. [PUT /api/video-studio/timeline/\\<project_id\\> — 更新时间线](#3-put-apivideo-studiotimelineproject_id--更新时间线)
4. [POST /api/video-studio/export — 导出视频](#4-post-apivideo-studioexport--导出视频)
5. [OS 事件](#5-os-事件)
6. [元认知](#6-元认知)
7. [精准投喂](#7-精准投喂)
8. [花名册](#8-花名册)

---

## 1. POST /api/video-studio/import — 导入视频

**功能说明：** 导入视频文件，支持两种方式：multipart 文件上传 或 JSON 元数据注册。上传后保存到 `data/videos/` 目录，并可自动关联到项目时间线。

### 请求参数

**方案 A：文件上传（multipart/form-data）**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 是 | — | 上传的视频文件 |
| `project_id` | string | 否 | `""` | 关联的项目 ID，非空且存在时自动添加到项目时间线 |
| `title` | string | 否 | 文件名 | 视频标题 |
| `duration` | string | 否 | `""` | 视频时长 |
| `tags` | string | 否 | `""` | 标签 |

**方案 B：JSON 元数据（application/json）**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `project_id` | string | 否 | `""` | 关联的项目 ID |
| `title` | string | 否 | `"untitled.mp4"` | 视频标题 |
| `duration` | string | 否 | `""` | 视频时长 |
| `tags` | string | 否 | `""` | 标签 |
| `file_path` | string | 否 | `""` | 视频文件路径 |

### 返回格式

**200 OK — 导入成功**

```json
{
  "ok": true,
  "video_id": "vid-2",
  "filename": "demo.mp4",
  "file_size": 1048576,
  "saved_path": "data/videos/vid-2_demo.mp4",
  "metadata": {
    "project_id": "proj-001",
    "title": "demo.mp4",
    "duration": "30.0",
    "tags": "demo,test"
  },
  "project_id": "proj-001"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 是否成功 |
| `video_id` | string | 生成的视频 ID，格式 `vid-{递增数字}` |
| `filename` | string | 上传的文件名 |
| `file_size` | number | 文件大小（字节） |
| `saved_path` | string | 文件在服务器上的存储路径 |
| `metadata` | object | 视频元数据 |
| `project_id` | string | 关联的项目 ID |

**400 Bad Request — 参数错误**

```json
{
  "ok": false,
  "error": "请求体为空或格式错误"
}
```

---

## 2. GET /api/video-studio/timeline/\\<project_id\\> — 获取时间线

**功能说明：** 查询指定项目的完整时间线数据（包含所有轨道和片段）。

### 请求参数

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `project_id` | path | string | 是 | 项目 ID |

### 返回格式

**200 OK — 获取成功**

```json
{
  "ok": true,
  "timeline": {
    "duration": 60.0,
    "tracks": [
      {
        "id": "t1",
        "type": "video",
        "clips": [
          {
            "id": "clip-1",
            "video_id": "vid-1",
            "file_path": "data/videos/vid-1_demo.mp4",
            "start": 0.0,
            "end": 15.0
          },
          {
            "id": "clip-2",
            "video_id": "vid-2",
            "file_path": "data/videos/vid-2_demo.mp4",
            "start": 0.0,
            "end": 10.0
          }
        ]
      },
      {
        "id": "t2",
        "type": "audio",
        "clips": []
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 是否成功 |
| `timeline.duration` | number | 时间线总时长（秒） |
| `timeline.tracks[].id` | string | 轨道 ID |
| `timeline.tracks[].type` | string | 轨道类型，`"video"` 或 `"audio"` |
| `timeline.tracks[].clips[].id` | string | 片段 ID |
| `timeline.tracks[].clips[].video_id` | string | 关联的视频 ID |
| `timeline.tracks[].clips[].file_path` | string | 视频文件路径 |
| `timeline.tracks[].clips[].start` | number | 片段开始时间（秒） |
| `timeline.tracks[].clips[].end` | number | 片段结束时间（秒） |

**404 Not Found — 项目不存在**

```json
{
  "ok": false,
  "error": "项目不存在"
}
```

---

## 3. PUT /api/video-studio/timeline/\\<project_id\\> — 更新时间线

**功能说明：** 全量替换指定项目的时间线数据。

### 请求参数

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `project_id` | path | string | 是 | 项目 ID |

**请求体（application/json）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timeline` | object | 是 | 完整的时间线数据（包含 duration 和 tracks） |

**请求示例**

```json
{
  "timeline": {
    "duration": 60.0,
    "tracks": [
      {
        "id": "t1",
        "type": "video",
        "clips": [
          {
            "id": "clip-1",
            "video_id": "vid-1",
            "file_path": "data/videos/vid-1_demo.mp4",
            "start": 0.0,
            "end": 15.0
          }
        ]
      }
    ]
  }
}
```

### 返回格式

**200 OK — 更新成功**

```json
{
  "ok": true,
  "timeline": {
    "duration": 60.0,
    "tracks": [...]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 是否成功 |
| `timeline` | object | 更新后的时间线数据 |

**404 Not Found — 项目不存在**

```json
{
  "ok": false,
  "error": "项目不存在"
}
```

---

## 4. POST /api/video-studio/export — 导出视频

**功能说明：** 根据项目时间线数据，调用 ffmpeg 渲染输出视频文件。支持 mp4 和 webm 格式。

### 请求参数

**请求体（application/json）**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `project_id` | string | **是** | — | 项目 ID |
| `format` | string | 否 | `"mp4"` | 输出格式，可选 `"mp4"` 或 `"webm"` |
| `resolution` | string | 否 | `"1920x1080"` | 分辨率，格式 `"宽x高"`，如 `"1280x720"` |
| `bitrate` | string | 否 | `"5M"` | 视频比特率，如 `"5M"`、`"10M"` |

**请求示例**

```json
{
  "project_id": "proj-001",
  "format": "mp4",
  "resolution": "1920x1080",
  "bitrate": "5M"
}
```

### 返回格式

**202 Accepted — 任务已提交**

```json
{
  "ok": true,
  "task_id": "task-1",
  "status": "pending",
  "message": "导出任务已提交"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | boolean | 是否成功 |
| `task_id` | string | 导出任务 ID |
| `status` | string | 任务状态，`"pending"` 等待处理中 |
| `message` | string | 提示信息 |

**400 Bad Request — 参数错误**

```json
{
  "ok": false,
  "error": "缺少必填参数: project_id"
}
```

---

## 5. OS 事件

### write_os_event

**功能说明：** 写入 OS 事件到 `events_default.jsonl` 文件，用于记录系统运行过程中的关键操作事件。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `event_type` | string | 是 | 事件类型分类 |
| `operation` | string | 是 | 操作名称 |
| `os_action` | string | 是 | 系统动作描述 |
| `reason` | string | 是 | 触发原因 |
| `command` | string | 否 | 执行的命令 |
| `detail` | string | 否 | 详细描述 |
| `session_id` | string | 否 | 会话 ID |
| `user_id` | string | 否 | 用户 ID |
| `server_id` | string | 否 | 服务器 ID |
| `task_id` | string | 否 | 任务 ID |
| `channel_id` | string | 否 | 频道 ID |
| `agent_name` | string | 否 | 代理名称 |

### read_recent_os_events

**功能说明：** 读取最近 N 行 OS 事件记录，支持按事件类型过滤。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `max_lines` | integer | 否 | `10` | 读取的最大行数 |
| `filter_types` | array[string] | 否 | `[]` | 事件类型过滤列表，仅返回匹配类型的事件 |

---

## 6. 元认知

### reflect

**功能说明：** GLM5.2 深度分析 OS 事件，产出 `system_hypothesis`，用于系统自我诊断与优化。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | string | 是 | 用户输入内容 |
| `response` | string | 是 | 系统响应内容 |
| `os_events` | array[object] | 是 | 待分析的 OS 事件列表 |

---

## 7. 精准投喂

### os_precision_feeds.yaml

**功能说明：** 配置驱动，按任务类型自动注入数据资产。系统根据指令关键词自动匹配规则，注入对应的上下文数据。

**规则：**

| 任务类型 | 触发关键词 | 注入资产 |
|----------|-----------|----------|
| `panorama` | 全景/概览/项目结构 | PROJECT_TREE + world_model_summary |
| `code_modify` | 修改/添加/重构代码 | world_model + dependency_graph |
| `troubleshoot` | 故障/调试/错误排查 | os_events + system_hypothesis |
| `billing_review` | 账单/计费/费用审核 | billing_summary |
| `plan_discussion` | 方案/计划/架构设计 | 按需组合注入 |
| `capability_audit` | 能力审计/功能盘点 | capability_manifest |

---

## 8. 花名册

### should_auto_correct

**功能说明：** 负面缓存机制，120 秒内同类拦截自动纠正，避免重复处理相同错误。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `session_id` | string | 是 | 会话 ID |
| `reason` | string | 是 | 拦截原因 |
| `ttl` | integer | 是 | 缓存生存时间（秒） |

### 模型探活

**功能说明：** 每小时检测花名册中 DeepSeek 模型可用性，不可用时自动标记 `model_deprecated`，确保系统始终使用可用模型。

**执行规则：**
- 检测频率：每小时一次
- 检测目标：花名册中所有 DeepSeek 模型端点
- 不可用处理：自动标记 `model_deprecated`，从可用模型列表中移除
