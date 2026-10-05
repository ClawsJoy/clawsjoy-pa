# -*- coding: utf-8 -*-
"""口径卡（2026-09-10，t1）：PPT 里 10 项「待核实」的定状态与 preflight 联动。

三态:
  confirmed   有官方依据 → 正文可写数字
  unverified  公开查不到确切值 → 正文删数字、只留定性（本卡绝大多数, 诚实标注）
  pending     待老板线下确认 → 进备注栏, 不进对客户可见页

与内容合规联动:
  audit.content_compliance 拦「待核实/口径」等标注文字出现在正文（fail）。
  本卡是第二层: 拦【未定实的数字本身】—— 标注被删了, 未定实数字又冒进正文, 也会 warn。
  即: 定实 → 数字可写; 未定 → 数字必须删/移备注。
"""
import json
import re

CALIBER = [
    {
        "id": "#1",
        "topic": "政策级别（市级）",
        "status": "confirmed",
        "pattern": r"",
        "note": "已检索到官方文件名：宁波市人民政府办公厅《支持人工智能OPC创新创业发展的若干措施》= 市级政策（另有「甬创9条」）。『市级』可写。",
    },
    {
        "id": "#1b",
        "topic": "区级说法（未证实）",
        "status": "unverified",
        "pattern": r"区级",
        "note": "政策级别实为市级；若正文出现『区级』属未证实/错误说法，拦。",
    },
    {
        "id": "#2",
        "topic": "10% 投资奖励",
        "status": "confirmed",
        "pattern": r"10\s*%|投资.*奖励|奖励.*投资",
        "note": "【已验真·原文】对股权投资机构投资符合条件的初创期OPC、投资期限满2年的，按实际投资额的10%给予奖励。注意主语是『股权投资机构』不是OPC本身。",
    },
    {
        "id": "#3",
        "topic": "算力补贴（最高800万/30%比例）",
        "status": "confirmed",
        "pattern": r"算力|800\s*万|补贴",
        "note": "【已验真·原文】按不超过算力/语料/模型(算法)合同执行金额的30%、最高800万元补助，其中非自主算力按不高于10%补助。PPT 原写『算力补贴800万』不准确。",
    },
    {
        "id": "#4",
        "topic": "OPC 专属贷（建行·待核实）",
        "status": "unverified",
        "pattern": r"300\s*万|专属贷",
        "note": "【老板补充+多轮复核】建行AIOPC专属信贷属实: 最高300万信用贷款, 授信评价纳入『AI算力投入/知识产权价值/投资机构投资/获得订单』四维。但『销售/投资/算力/订单4种定贷模式』这一分类表述 + 『算力定贷最高50万』未获官方证实。来源=高新区OPC联盟签约媒体(中国高新), 属社区合作框架下金融方案, 非政府文件 → 存疑, 待建行确认。",
    },
    {
        "id": "#5",
        "topic": "创业保（最高6万）",
        "status": "confirmed",
        "pattern": r"6\s*万|创业保|创业保险",
        "note": "【已验真·原文】创业失败可获最高2万创业基础补助+最高4万带动就业补助=合计最高6万(分项)。",
    },
    {
        "id": "#6",
        "topic": "8大行业 48 场景",
        "status": "confirmed",
        "pattern": r"8\s*大|48\s*(个|项)?\s*场景|场景清单",
        "note": "【修正·多源】出自宁波『人工智能+制造』行动方案(非甬创9条)：聚焦绿色石化、新能源汽车等 8 大重点行业、打造 48 个标杆应用场景。来源=经信局/人民网/央广网。我此前单查甬创9条才误判查无。",
    },
    {
        "id": "#7",
        "topic": "揭榜挂帅场景清单（首批106个）",
        "status": "confirmed",
        "pattern": r"揭榜挂帅|100\s*\+",
        "note": "【修正·多源】人民网报道：政府/国企/龙头向OPC开放场景，2026年内将开放【超百项】揭榜挂帅场景清单。是『前瞻性表述』(将开放)非已落地数量，来源为人民网(官方媒体)。@DS Chat 复核: 经信局《宁波市『人工智能+制造』应用场景机会清单(第一批)》= 首批106个场景(已发布实数字), PPT 建议改用「首批106个场景(经信局)」更准。",
    },
    {
        "id": "#8",
        "topic": "1300亿基金项目（市级·非OPC专项）",
        "status": "confirmed",
        "pattern": r"1300\s*亿|基金群|跟投",
        "note": "【老板澄清+官方源确认】2024年11月宁波『创投日』: 总规模超1300亿元重大基金项目正式发布(含340亿AIC股权投资基金集群落地)。来源=宁波市政府官网/地方金融管理局(宁波日报)。但这是【市级基金布局】, 非OPC专项, 更非『OPC可跟投』 → PPT 表述须改为『市级基金布局, OPC对接需向基金管理方确认』。",
    },
    {
        "id": "#9",
        "topic": "工位号/一址多照",
        "status": "confirmed",
        "pattern": r"工位号|一址多照|同址批量",
        "note": "【已验真·原文】支持OPC社区运营管理单位通过「工位号」登记、一址多照等方式提供共享办公空间。第九条(十七)。",
    },
    {"id": "#10", "topic": "老板侧基线数据", "status": "pending", "pattern": r"", "note": "老板自己的经营基线数据，待收集/线下确认"},
]

VISIBLE_FIELDS = (
    "title",
    "subtitle",
    "body",
    "items",
    "rows",
    "headers",
    "number",
    "label",
    "description",
    "leftLabel",
    "leftBody",
    "rightLabel",
    "rightBody",
    "leftHead",
    "rightHead",
    "quote",
    "author",
    "role",
    "mainText",
    "subText",
    "contacts",
    "heroTitle",
    "tag",
    "footer",
    "steps",
)


def _store_cards():
    """真源：外置 store（`data/v9/pa/caliber.json`）优先；无 store ⇒ 回落源码内种子 CALIBER。
    返回 (cards, source)。store **存在但损坏 ⇒ 抛出**（fail-loud，⛔ 不静默回种子）。
    """
    import os
    from pathlib import Path

    p = Path(os.getenv("PA_DATA_DIR", "data/v9/pa")) / "caliber.json"
    if not p.is_file():
        return list(CALIBER), "seed"
    from core.pa.caliber_store import CaliberStore

    st = CaliberStore(str(p.parent))
    return st.cards(), "store"


def effective_cards():
    return _store_cards()[0]


def source():
    return _store_cards()[1]


def _patterns():
    return [(c["id"], c["topic"], c["status"], c["pattern"], c["note"]) for c in effective_cards()]


def check(pages):
    """口径卡联动：未定实(unverified/pending)的数字出现在正文 → warn。

    返回 [(page, item_id, topic, status, matched_text)]。只 warn 不 fail。
    """
    hits = []
    for i, p in enumerate(pages, 1):
        data = p.get("data") or {}
        parts = []
        for fld in VISIBLE_FIELDS:
            v = data.get(fld)
            if v is not None:
                parts.append(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
        blob = " ".join(parts)
        for cid, topic, status, pat, _note in _patterns():
            if not pat or status == "confirmed":
                continue
            if re.search(pat, blob):
                hits.append(("P%02d" % i, cid, topic, status, pat))
    return hits


def summary():
    return [{"id": c["id"], "topic": c["topic"], "status": c["status"], "note": c["note"], "owner": c.get("owner"), "updated": c.get("updated"),
                "supersedes": c.get("supersedes"), "change_count": c.get("change_count", 0)} for c in effective_cards()]


def counts():
    s = {"confirmed": 0, "unverified": 0, "pending": 0}
    for c in effective_cards():
        s[c["status"]] = s.get(c["status"], 0) + 1
    return s
