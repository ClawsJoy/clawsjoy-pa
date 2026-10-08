# -*- coding: utf-8 -*-
"""1949 · 「要」件编目入 SAG 之齿 —— `scripts/dev/编目_要件入SAG.py` 之纯逻辑。

正控：① 题切段 ／ 段号连号 ② 摘要取规线（须／⛔） ③ 席／号／到刻之结构化
      ④ 「格 ＋ 件名」定域 ⑤ 边（动态超边）载 类／格／席／号／到刻 ∧ 封顶 12。
反控：① 域外之同名件（`codex/…判据…`）⛔ 归　② 临件（`_回_` ／ `_派件_`）⛔ 采
      ③ 存底（`.before_` ／ `.sha256`）⛔ 采　④ 取不到 ⇒ 空（**⛔ 猜**）
      ⑤ 器**只读源**（源码 ⛔ 含改 ／ 删 ／ 挪之通用调用）
      ⑥ **⛔ 模块级引桥**（惰引 ⇒ 计划期 ⛔ 触 DB）
      ⑦ 注销唯 `--prune-stale` 一路（SQL DELETE 恰一处 ∧ 须显式点名 ∧ ⛔ 默认开）。

⚠ 本件 ⛔ 触 DB · ⛔ 触网 · ⛔ 读 vault（唯纯逻辑 ＋ 源码之结构断言）。
"""
import importlib.util
import io
import os
import re

import pytest

_MOD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts", "dev", "编目_要件入SAG.py",
)


def _load():
    spec = importlib.util.spec_from_file_location("sag_catalog_1949", _MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def M():
    assert os.path.exists(_MOD), "器不在盘: %s" % _MOD
    return _load()


def test_器在盘且只读源(M):
    src = io.open(_MOD, encoding="utf-8").read()
    # ⚠ 逐词拆写（⛔ 令本件自带该串 ⇒ 免「自指之假红」）
    for bad in ("shut" "il", "rm" "tree", "os.re" "move", "os.un" "link",
                "os.ren" "ame", "os.rep" "lace", "trunc" "ate"):
        assert bad not in src, "器须只读源，⛔ 含 %s" % bad
    assert not re.search(r"open\([^)]*['\"][wa+]b?['\"]", src), "⛔ 写模式开件"


def test_惰引_计划期不触库(M):
    src = io.open(_MOD, encoding="utf-8").read()
    assert not re.search(r"^from core\.", src, re.M | re.U), "⛔ 模块级引桥（须惰引）"


def test_注销唯prune_stale一路(M):
    """⭐ 承 pm_1951 §二.1（裁⒝）：注销之 SQL **归桥** ⇒ 本器 ⛔ 直写 ＋ 唯走 `unregister_stale`。

    ⚠ 断言之字面须**拆写**（`"DELETE" + " FROM"`）—— 合写即自破（本齿扫本器之源码）。
    """
    src = io.open(_MOD, encoding="utf-8").read()
    assert src.count("DELETE" + " FROM") == 0, "⛔ 本器不得直写注销之 SQL（一处定形归桥）"
    assert "unregister_stale" in src, "注销须走桥之 `unregister_stale`"
    assert "prune_stale=args.prune_stale" in src, "注销须由 `--prune-stale` 达"
    assert "prune_stale=False" in src, "注销 ⛔ 默认开"


def test_正控_注销归桥(M):
    """⛔ 本器自撰连接（psycopg2）—— 注销唯经桥 ⇒ 本器 ⛔ 建连。"""
    src = io.open(_MOD, encoding="utf-8").read()
    assert "psycopg2" not in src, "注销已归桥 ⇒ 本器 ⛔ 直连库"


def test_正控_段切与段号(M):
    s = M.segments("# 一 甲\n甲之正文\n\n## 二 乙\n乙之正文\n")
    assert len(s) == 2
    assert s[0]["head"] == "一 甲" and s[1]["head"] == "二 乙"
    assert [x["i"] for x in s] == [0, 1]


def test_反控_空件与超长与封顶(M):
    assert M.segments("") == []
    assert M.segments("   \n\n  ") == []
    long = M.segments("# T\n" + "甲乙" * 400, max_chars=300)
    assert long and all(len(x["text"]) <= 300 for x in long), "超长必切"
    assert len(M.segments("# T\n" + "甲乙" * 5000, max_chars=100, max_seg=7)) == 7


def test_正控_摘要载题与规线(M):
    d = M.digest("净机升号", "须先提交载荷。\n闲话一行。\n⛔ 静默装。")
    assert d.startswith("《净机升号》")
    assert "须先提交载荷。" in d and "⛔ 静默装。" in d


def test_正控_摘要封顶(M):
    assert len(M.digest("H", "甲" * 3000, max_sig=120)) == 120


def test_正控_件摘要载类与印(M):
    segs = M.segments("# 一\n正文\n")
    assert M.doc_digest("判据", "a.md", "abc", 3, segs).startswith("【判据】")


def test_正控_结构化_席(M):
    assert M.fields("paseo-pm/x.md", "---\nfrom: 技术总监\n---\n")[0] == "技术总监"
    assert M.fields("paseo-pm/说明_技术总监_出图链.md", "无头")[0] == "技术总监"


def test_反控_结构化_取不到即空(M):
    assert M.fields("paseo-pm/PA-宏图之判_v1.md", "无头")[0] == "", "⛔ 猜席"
    assert M.fields("paseo-pm/_PM时间线_v1.md", "无头")[0] == ""


def test_正控_结构化_号与到刻(M):
    assert M.fields("paseo-pm/_令_TD_1946.md", "")[1] == "1946"
    assert M.fields("paseo-pm/_续接_PM_20261008.md", "")[2] == "2026-10-08"
    assert M.fields("x.md", "date: 2026-10-08\n")[2] == "2026-10-08"


def test_正控_定域(M):
    r = M.build_rules(with_tools=True)
    assert M.match_category("vault", "paseo-pm/PA-插件面之判_v1.md", r) == "蓝图"
    assert M.match_category("vault", "paseo-pm/_判据_留存与删除_v1.md", r) == "判据"
    assert M.match_category("_pm", "_经验库_v1.md", r) == "经验"
    assert M.match_category("vault", "内容工坊/07_SOP/SOP_章节审核.md", r) == "工具"
    assert M.match_category("vault", "codex/_经验库.md", r) == "经验"


def test_反控_域外同名与他格不归(M):
    r = M.build_rules(with_tools=True)
    assert M.match_category("vault", "codex/2026-09-24-…判据…_v7.md", r) is None
    assert M.match_category("vault", "内容工坊/08_工具/待落清单_技术总监.md", r) is None
    assert M.match_category("vault", "内容工坊/PA-宏图之判_v1.md", r) is None
    assert M.match_category("vault", "内容工坊/07_SOP/SOP_章节审核.md",
                           M.build_rules(False)) is None


def test_反控_临件与存底不采(M):
    assert M.is_noise_name("_回_CW_1212_认翻判与答判据.md") is True
    assert M.is_noise_name("_派件_秘书_登记经验库入册.md") is True
    assert M.is_noise_name("投递台账.csv.before_abc") is True
    assert M.is_noise_name("00_索引.md.sha256") is True
    assert M.is_noise_name("_判据_留存与删除_v1.md") is False
    assert M.is_noise_name("_续接_PM_20261008.md") is False


def test_正控_清单唯件名可归(M):
    r = M.build_rules(with_tools=True)
    assert M.match_basename("D:" + chr(92) + "x" + chr(92) + "PA-宏图之判_v1.md", r) == "蓝图"


def test_反控_目录剪枝(M):
    assert M.prune_dir("_冷区") is True and M.prune_dir("_老板") is True
    assert M.prune_dir(".obsidian") is True
    assert M.prune_dir("_规范") is False and M.prune_dir("paseo-pm") is False


def test_正控_边载五格且封顶(M):
    e = M.edges_of("判据", "vault", "题", "项目经理", "1946", "2026-10-08")
    for want in ("类=判据", "格=vault", "题=题", "席=项目经理", "号=1946", "到刻=2026-10-08"):
        assert want in e
    assert len(M.edges_of("类", "格", "题", "席", "号", "刻",
                          extra=["件=x"] * 20)) == 12


def test_自证全过(M):
    assert M._self_test(io.StringIO()) == 0