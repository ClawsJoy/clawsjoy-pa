# -*- coding: utf-8 -*-
import os
from pathlib import Path

from core.pa import notes as N


def test_create_get_list_update_delete(tmp_path):
    n = N.create("本周复盘", "这周记了 A 和 B。", ["周报", "PA"], data_dir=str(tmp_path))
    assert n["id"]
    p = Path(n["path"])
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "title:" in text

    got = N.get(n["id"], data_dir=str(tmp_path))
    assert got["title"] == "本周复盘"
    assert "这周记了" in got["body"]

    rows = N.list_notes("", data_dir=str(tmp_path))
    assert len(rows) == 1
    assert rows[0]["title"] == "本周复盘"

    upd = N.update(n["id"], title="本周复盘v2", body="改了", tags=["周报"], data_dir=str(tmp_path))
    assert upd["title"] == "本周复盘v2"
    assert N.get(n["id"], data_dir=str(tmp_path))["body"] == "改了"

    N.delete(n["id"], data_dir=str(tmp_path))
    assert N.list_notes("", data_dir=str(tmp_path)) == []
    assert not p.exists()


def test_search_chinese_and_tag(tmp_path):
    N.create("会议纪要", "客户说下周三看方案。", ["客户", "会议"], data_dir=str(tmp_path))
    N.create("购物清单", "牛奶、鸡蛋。", ["生活"], data_dir=str(tmp_path))
    a = N.list_notes("客户", data_dir=str(tmp_path))
    assert [x["title"] for x in a] == ["会议纪要"]
    b = N.list_notes("生活", data_dir=str(tmp_path))
    assert [x["title"] for x in b] == ["购物清单"]


def test_import_dir_and_reindex(tmp_path):
    src = tmp_path / "vault"
    (src / "子目录").mkdir(parents=True)
    (src / "a.md").write_text("---\ntitle: \"A\"\ntags: [\"x\"]\n---\n\nA body\n", encoding="utf-8")
    (src / "子目录" / "b.md").write_text("# B\n\nB body\n", encoding="utf-8")
    r = N.import_dir(str(src), data_dir=str(tmp_path / "data"))
    assert r["imported"] == 2
    assert len(N.list_notes("", data_dir=str(tmp_path / "data"))) == 2
    # 同目录再导：跳过已导
    r2 = N.import_dir(str(src), data_dir=str(tmp_path / "data"))
    assert r2["imported"] == 0 and r2["skipped"] == 2

    # 索引删掉再重建
    db = tmp_path / "data" / "workspace" / "index.sqlite"
    assert db.exists()
    os.remove(db)
    rr = N.reindex(data_dir=str(tmp_path / "data"))
    assert rr["indexed"] == 2
    assert len(N.list_notes("", data_dir=str(tmp_path / "data"))) == 2


def test_note_id_rejects_traversal(tmp_path):
    try:
        N.get("../etc/passwd", data_dir=str(tmp_path))
        assert False
    except N.NoteError:
        pass
