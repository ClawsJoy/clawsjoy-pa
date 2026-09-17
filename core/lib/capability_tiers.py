#!/usr/bin/env python3
"""
能力分级 - LLM自由发挥的安全边界
"""

# 安全等级定义
SAFE = "safe"           # LLM自由发挥，系统直接执行
CAUTION = "caution"     # LLM自由发挥，系统记录日志
CONFIRM = "confirm"     # LLM建议，系统要求用户确认
FORBIDDEN = "forbidden" # LLM禁止执行

# 每个action的安全等级
ACTION_TIERS = {
    # 读操作 - 安全
    "greeting": SAFE,
    "recall": SAFE,
    "chat": SAFE,
    
    # 分析 - 安全（只读数据）
    "analyze": SAFE,
    "code": SAFE,        # 生成代码是安全的，执行代码需要确认
    
    # 存储 - 需确认（写操作）
    "identity": CONFIRM,  # 修改用户画像需确认
    "memory": CONFIRM,    # 存储记忆需确认
    "task": CONFIRM,      # 创建任务需确认
    
    # 文件操作 - 需确认
    "file_read": SAFE,
    "file_write": CONFIRM,
    "file_delete": CONFIRM,
    
    # 执行 - 需确认
    "execute": CONFIRM,
    "code_execute": CONFIRM,
    
    # 禁止
    "system_modify": FORBIDDEN,
    "delete_all": FORBIDDEN,
}

def get_tier(action: str) -> str:
    """获取action的安全等级"""
    return ACTION_TIERS.get(action, CAUTION)  # 未知action默认谨慎

def needs_confirmation(action: str) -> bool:
    """是否需要用户确认"""
    return get_tier(action) in (CONFIRM, FORBIDDEN)

def is_safe(action: str) -> bool:
    """是否安全可自动执行"""
    return get_tier(action) == SAFE
