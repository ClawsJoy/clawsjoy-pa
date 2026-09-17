#!/usr/bin/env python3
"""
系统能力申明 → 正则规则映射
每个Agent的能力对应一组正则匹配规则
"""

ABILITY_REGEX = {
    # ========== greeting：问候/身份询问 ==========
    "greeting": {
        "agent": "chat_agent",
        "description": "问候和身份询问",
        "patterns": [
            r"^你好", r"^嗨", r"^hi", r"^hello",
            r".*你是谁.*",
            r"介绍一下", r"介绍下", r"你是.",
        ],
        "extract": "none",
    },

    # ========== memory_agent：记忆存储 ==========
    "memory": {
        "agent": "memory_agent",
        "description": "存储键值记忆",
        "patterns": [
            r"帮我记.*", r"帮我存.*", r"记住.*",
        ],
        "extract": "key_value",  # 从输入中提取key和value
    },
    
    # ========== identity：用户身份 ==========
    "identity": {
        "agent": "memory_agent", 
        "description": "记录用户身份信息",
        "patterns": [
            r"我叫[^什么].*", r"我是[^谁].*", r"叫我[^什么].*", r"我的名字[^是].*",
        ],
        "extract": "name",
    },
    
    # ========== recall：记忆查询 ==========
    "recall": {
        "agent": "memory_agent",
        "description": "查询记忆",
        "patterns": [
            r".*叫什么.*", r".*是什么.*", r"回忆.*", r"查询.*", r".*来着.*",
            r"^记得.*", r"^还记得.*",
        ],
        "extract": "query",
    },
    
    # ========== code_agent：代码生成 ==========
    "code": {
        "agent": "code_agent",
        "description": "生成/调试代码",
        "patterns": [
            r"写.*代码", r"写.*函数", r"写.*算法", r"写.*排序",
            r"编程.*", r"生成.*代码", r"修复.*bug", r"修.*bug",
        ],
        "extract": "description",
    },
    
    # ========== translate_agent：翻译 ==========
    "translate": {
        "agent": "translate_agent",
        "description": "多语言翻译",
        "patterns": [
            r"翻译.*", r".*翻译成.*", r"translate.*",
        ],
        "extract": "text",
    },
    
    # ========== calculator_agent：计算 ==========
    "calculate": {
        "agent": "calculator_agent",
        "description": "数学计算",
        "patterns": [
            r"^[\d\s\+\-\*\/\(\)\.\^]+$",  # 纯数学表达式
            r"计算.*", r".*等于.*",
        ],
        "extract": "expression",
    },
    
    # ========== writer_agent：写作 ==========
    "write": {
        "agent": "writer_agent",
        "description": "创作内容",
        "patterns": [
            r"写.*小说", r"写.*故事", r"写.*文章", r"创作.*",
            r"继续写", r"写.*诗", r"写.*剧本",
        ],
        "extract": "topic",
    },
    
    # ========== analysis_agent：分析 ==========
    "analyze": {
        "agent": "analysis_agent",
        "description": "数据分析",
        "patterns": [
            r"分析.*", r"统计.*", r".*趋势.*", r".*报告.*",
        ],
        "extract": "data",
    },
    
    # ========== file_agent：文件操作 ==========
    "file": {
        "agent": "file_agent",
        "description": "文件管理",
        "patterns": [
            r"读取.*文件", r"写入.*文件", r"列出.*目录", r"删除.*文件",
            r"打开.*文件", r"保存.*文件",
        ],
        "extract": "path",
    },
    
    # ========== butler_agent：管家 ==========
    "task": {
        "agent": "butler_agent",
        "description": "日程管理",
        "patterns": [
            r"待办.*", r"提醒.*", r"安排.*", r"日程.*",
            r"明天.*", r"下周.*", r"截止.*",
        ],
        "extract": "task_info",
    },
    # ========== youtube_agent：YouTube ==========
    "youtube": {
        "agent": "youtube_agent",
        "description": "YouTube 视频搜索/下载/分析",
        "patterns": [
            r"youtube\.com", r"youtu\.be",
            r"油管",
            r"下载.*视频", r"分析频道", r"频道分析",
            r"生成标题", r"起标题",
            r"seo.*优化|优化.*seo", r"搜索优化",
        ],
        "extract": "query",
    },
}

# 匹配优先级（越靠前越优先）
PRIORITY = ["greeting", "identity", "recall", "memory", "youtube", "translate", "calculate",
            "code", "write", "analyze", "file", "task"]

# 默认兜底
DEFAULT_ACTION = "chat"
DEFAULT_AGENT = "chat_agent"
