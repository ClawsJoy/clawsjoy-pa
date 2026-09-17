# -*- coding: utf-8 -*-
"""配置 Schema 校验（AUDIT 4.2-4）

为 config/ 下的 OS 注册表 YAML（os_capabilities / os_precision_feeds /
os_event_injection_points）提供启动前结构校验，配置错误时快速定位失败原因。

用法:
    from core.lib.config_schema import validate_os_configs
    ok, errors = validate_os_configs()
    # ok=False 时 errors 为 [文件路径: 行级错误, ...]

不引入第三方依赖（纯 pyyaml + 内置类型检查），避免增加 requirements。
"""
import os
import sys
from pathlib import Path

import yaml

# ────────────────────────────────────────────────────────────────
# Schema 定义
# 每项: top_key 顶层键; items 列表元素校验规则
#   required: 必填字段
#   fields:   {field: {type: <类型>, enum: [可选值], required: bool}}
# ────────────────────────────────────────────────────────────────

_STATUS_ENUM = ["active", "pending_review", "deprecated", "rejected"]

OS_CONFIG_SCHEMAS = {
    "config/os_capabilities.yaml": {
        "top_key": "capabilities",
        "items": {
            "required": ["id", "type", "domain", "description", "status"],
            "fields": {
                "id": {"type": str, "required": True},
                "type": {"type": str, "required": True},
                "domain": {"type": str, "required": True},
                "description": {"type": str, "required": True},
                "since": {"type": str, "required": False},
                "status": {"type": str, "required": True, "enum": _STATUS_ENUM},
                "event_type": {"type": str, "required": False},
                "reason": {"type": str, "required": False},
                "constraints": {"type": list, "required": False},
            },
        },
    },
    "config/os_precision_feeds.yaml": {
        "top_key": "feeds",
        "items": {
            "required": ["id", "keywords", "inject", "status"],
            "fields": {
                "id": {"type": str, "required": True},
                "keywords": {"type": list, "required": True},
                "agent_positions": {"type": list, "required": False},
                "task_scoped": {"type": bool, "required": False},
                "inject": {"type": list, "required": True},
                "status": {"type": str, "required": True, "enum": _STATUS_ENUM},
            },
        },
    },
    "config/os_event_injection_points.yaml": {
        "top_key": "injection_points",
        "items": {
            "required": ["id", "file", "method", "trigger", "event", "status"],
            "fields": {
                "id": {"type": str, "required": True},
                "file": {"type": str, "required": True},
                "method": {"type": str, "required": True},
                "trigger": {"type": str, "required": True},
                "event": {"type": dict, "required": True},
                "status": {"type": str, "required": True, "enum": _STATUS_ENUM},
                "note": {"type": str, "required": False},
            },
        },
    },
}

# 额外语义校验：event 子结构
_EVENT_SUB_REQUIRED = ["event_type", "operation", "os_action", "reason"]


def _check_type(value, expected_type, field_name, index, errors):
    """类型检查（bool 是 int 子类，需单独处理）"""
    if expected_type is bool:
        if not isinstance(value, bool):
            errors.append(f"  第{index + 1}项字段 {field_name}: 期望 bool，实际 {type(value).__name__}")
    elif not isinstance(value, expected_type):
        errors.append(f"  第{index + 1}项字段 {field_name}: 期望 {expected_type.__name__}，实际 {type(value).__name__}")


def _validate_items(yaml_path, data, schema):
    """校验单个 YAML 的顶层列表，返回错误列表"""
    errors = []
    top_key = schema["top_key"]
    items = data.get(top_key) if isinstance(data, dict) else None
    if items is None:
        errors.append(f"[{yaml_path}] 缺少顶层键 {top_key}")
        return errors
    if not isinstance(items, list):
        errors.append(f"[{yaml_path}] 顶层键 {top_key} 应为列表，实际 {type(items).__name__}")
        return errors

    rule = schema["items"]
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"[{yaml_path}] 第{idx + 1}项应为 dict，实际 {type(item).__name__}")
            continue
        # 必填字段
        for field in rule["required"]:
            if field not in item or item[field] is None:
                errors.append(f"[{yaml_path}] 第{idx + 1}项缺少必填字段: {field}")
        # 字段类型 / 枚举
        for field, spec in rule["fields"].items():
            if field not in item:
                continue
            value = item[field]
            if value is None:
                continue
            expected_type = spec.get("type")
            if expected_type is not None:
                _check_type(value, expected_type, field, idx, errors)
            enum = spec.get("enum")
            if enum and value not in enum:
                errors.append(f"[{yaml_path}] 第{idx + 1}项字段 {field}: 值 '{value}' 不在允许范围 {enum}")
        # event 子结构（os_event_injection_points）
        event = item.get("event")
        if isinstance(event, dict):
            for sub in _EVENT_SUB_REQUIRED:
                if sub not in event or event[sub] is None:
                    errors.append(f"[{yaml_path}] 第{idx + 1}项 event 缺少子字段: {sub}")
    return errors


def validate_os_configs(base_dir="config"):
    """校验 config/ 下所有 OS 注册表 YAML

    Returns:
        (bool, list[str]): (是否全部通过, 错误列表；通过时为空列表)
    """
    errors = []
    base = Path(base_dir)
    for rel_path, schema in OS_CONFIG_SCHEMAS.items():
        full_path = base / rel_path
        if not full_path.exists():
            errors.append(f"[{rel_path}] 文件不存在")
            continue
        try:
            with open(full_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            errors.append(f"[{rel_path}] YAML 解析失败: {e}")
            continue
        errors.extend(_validate_items(rel_path, data, schema))
    return (len(errors) == 0, errors)


def validate_os_configs_cli():
    """命令行入口：校验失败返回退出码 1"""
    ok, errors = validate_os_configs()
    if ok:
        print("[CONFIG_SCHEMA] ✅ 全部 OS 配置通过 Schema 校验")
        return 0
    print("[CONFIG_SCHEMA] ❌ OS 配置 Schema 校验失败：")
    for err in errors:
        print(f"  {err}")
    return 1


if __name__ == "__main__":
    sys.exit(validate_os_configs_cli())
