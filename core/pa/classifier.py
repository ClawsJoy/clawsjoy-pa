# -*- coding: utf-8 -*-
"""数据分级器 classify(text) -> L1/L2/L3/L4（2026-09-11 块 0）

四级数据分级（老板拍板，硬红线不可改）：
  L1 公开（讲义/口播稿/宣传）                 -> 自动外发
  L2 脱敏（去掉报价/图纸/个人信息的产物）      -> 自动外发
  L3 原始（成本/报价/客户/图纸）              -> 老板在场授权一次
  L4 隐私（工资/合同/身份证/个人信息标识）     -> 绝对禁止出机器

L4 双保险（老板硬性要求 2026-09-11）：
  保险1  semantic_classify()        语义关键词判级
  保险2  has_personal_identifier()  正则匹配个人标识（手机号/身份证号/银行卡号/住址）
  原则：宁可误判 L4（多禁一次），不可漏判。L4 是法律红线，不是业务偏好。

判定逻辑（与老板任务书逐字一致）：
  if semantic_classify(text) == L4:   -> L4
  elif has_personal_identifier(text): -> L4（双保险）
  else:                               -> semantic_classify 结果

纯标准库（re），零外部依赖，可同时跑 Linux 后端与 Windows 客户端。
"""

from __future__ import annotations

import re
from typing import Dict, List

# ===== 保险2：个人标识正则（手机号 / 身份证号 / 银行卡号 / 住址）=====
# 手机号：11 位，1[3-9] 开头（大陆）；容忍 - 或空格分隔（138-0013-8000 / 138 0013 8000）
PHONE_RE = re.compile(r"(?<!\d)1[3-9](?:[ -]?\d){9}(?!\d)")

# 身份证号：18 位（17 数字 + 数字/X）与 15 位（旧证）
ID18_RE = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")
ID15_RE = re.compile(r"(?<!\d)\d{15}(?!\d)")

# 银行卡号：16-19 位（与 18 位身份证重叠无妨，两者皆 L4）
BANK_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")

# 住址：显式标签 + 结构化地址 + 路号结构
ADDR_LABEL_RE = re.compile(r"(?:家庭住址|联系地址|通讯地址|收货地址|居住地址|户籍地址|住址|地址)\s*[:：]?\s*\S{1,30}")
ADDR_STRUCT_RE = re.compile(
    r"[\u4e00-\u9fa5]{2,}(?:省|自治区|特别行政区)[\u4e00-\u9fa5]{1,}(?:市|地区|自治州|盟)[\u4e00-\u9fa5]{1,}(?:区|县|旗)"
)
ADDR_ROAD_RE = re.compile(r"[\u4e00-\u9fa5]{2,}(?:路|街|大道|巷|弄|胡同)[\u4e00-\u9fa5]{0,}\d+\s*号")
ADDR_UNIT_RE = re.compile(r"[\u4e00-\u9fa5]{1,}(?:小区|花园|公寓|大厦|号楼|栋|幢|单元|室)\s*\d{1,5}")


# ===== 保险1：语义关键词 =====
# L4 隐私（工资/合同/身份证 + 通用敏感标记）
L4_KEYWORDS = (
    "工资",
    "薪资",
    "薪酬",
    "薪水",
    "工资单",
    "工资表",
    "年终奖",
    "五险一金",
    "公积金",
    "合同",
    "劳动合同",
    "劳务合同",
    "雇佣合同",
    "保密协议",
    "身份证",
    "身份证号",
    "身份证号码",
    "银行卡",
    "银行卡号",
    "开户行",
    "密码",
    "密钥",
    "口令",
    "验证码",
    "password",
    "secret",
    "token",
    "apikey",
    "api_key",
    "api key",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".key",
    ".env",
)

# L3 原始（成本/报价/客户/图纸）
L3_KEYWORDS = (
    "成本",
    "成本价",
    "采购价",
    "进价",
    "报价",
    "报价单",
    "报价表",
    "单价",
    "总价",
    "成交价",
    "客户",
    "客户信息",
    "客户名单",
    "客户数据",
    "图纸",
    "设计图",
    "施工图",
    "cad图",
    "cad",
    "供应商",
    "采购",
    "利润",
    "毛利",
    "回款",
    "账期",
)

# L2 脱敏（显式脱敏标记 + 掩码占位符）
L2_KEYWORDS = (
    "脱敏",
    "已脱敏",
    "脱敏后",
    "脱敏版",
    "匿名化",
    "去标识化",
    "去标识",
    "打码",
    "掩码",
    "遮蔽",
    "马赛克",
    "redacted",
    "masked",
    "anonymized",
    "***",
    "×××",
    "✱✱✱",
    "xxx",
)

# L1 公开（讲义/口播稿/宣传）
L1_KEYWORDS = (
    "讲义",
    "课件",
    "口播稿",
    "口播",
    "宣传",
    "推广",
    "文案",
    "公众号",
    "公众号文案",
    "公开",
    "培训材料",
    "课程",
    "教程",
    "演讲稿",
    "直播稿",
    "短视频脚本",
    "通稿",
)


def _find_keywords(text: str, keywords) -> List[str]:
    """返回命中的关键词（保序、去重）。"""
    tl = text.lower()
    seen = []
    for kw in keywords:
        if kw in tl and kw not in seen:
            seen.append(kw)
    return seen


def find_personal_identifiers(text: str) -> List[str]:
    """保险2：正则匹配个人标识，返回命中的类别（供审计/理由展示）。"""
    text = str(text or "")
    hits: List[str] = []
    if PHONE_RE.search(text):
        hits.append("手机号")
    _id18 = ID18_RE.search(text)
    if _id18:
        hits.append("身份证号(18位)")
    elif ID15_RE.search(text):
        hits.append("身份证号(15位)")
    if BANK_RE.search(text) and not _id18:
        hits.append("银行卡号")
    if (
        ADDR_LABEL_RE.search(text)
        or ADDR_STRUCT_RE.search(text)
        or ADDR_ROAD_RE.search(text)
        or ADDR_UNIT_RE.search(text)
    ):
        hits.append("住址")
    return hits


def has_personal_identifier(text: str) -> bool:
    """保险2 布尔接口。"""
    return bool(find_personal_identifiers(text))


def semantic_classify(text: str) -> str:
    """保险1：语义关键词判级。返回 "L1"|"L2"|"L3"|"L4"。

    优先级（高->低）：L4（法律红线） -> L2（脱敏降级，先于 L3）
                    -> L3（原始）   -> L1（公开） -> 默认 L3（不确定保守）。
    """
    text = str(text or "")
    if _find_keywords(text, L4_KEYWORDS):
        return "L4"
    if _find_keywords(text, L2_KEYWORDS):
        return "L2"
    if _find_keywords(text, L3_KEYWORDS):
        return "L3"
    if _find_keywords(text, L1_KEYWORDS):
        return "L1"
    return "L3"


def classify(text: str) -> str:
    """数据分级主入口（双保险）。返回 "L1"|"L2"|"L3"|"L4"。"""
    text = str(text or "")
    sem = semantic_classify(text)
    if sem == "L4":
        return "L4"
    if has_personal_identifier(text):
        return "L4"  # 保险2：正则命中个人标识 -> 直接 L4
    return sem


def classify_with_reason(text: str) -> Dict:
    """分级 + 理由（供老板授权时看「为什么判这个级」）。"""
    text = str(text or "")
    sem = semantic_classify(text)
    if sem == "L4":
        return {
            "level": "L4",
            "insurance": "semantic",
            "reasons": ["敏感关键词: " + "、".join(_find_keywords(text, L4_KEYWORDS))],
        }
    pids = find_personal_identifiers(text)
    if pids:
        return {"level": "L4", "insurance": "regex", "reasons": ["个人信息标识: " + "、".join(pids)]}
    if sem == "L2":
        return {
            "level": "L2",
            "insurance": "semantic",
            "reasons": ["脱敏标记: " + "、".join(_find_keywords(text, L2_KEYWORDS))],
        }
    if sem == "L3":
        return {
            "level": "L3",
            "insurance": "semantic",
            "reasons": ["原始数据关键词: " + "、".join(_find_keywords(text, L3_KEYWORDS))],
        }
    if sem == "L1":
        return {
            "level": "L1",
            "insurance": "semantic",
            "reasons": ["公开内容关键词: " + "、".join(_find_keywords(text, L1_KEYWORDS))],
        }
    return {"level": "L3", "insurance": "semantic", "reasons": ["不确定，默认保守 L3"]}
