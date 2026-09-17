#!/usr/bin/env bash
# 发布点流程（2026-09-13）：读积累记录 → 列「本次发了什么」→ commit → tag → 记录 → 归档
# 用法：bash tools/release_point.sh v9.1.0            # 预演（只列清单，不改）
#       bash tools/release_point.sh v9.1.0 --apply    # 真发布
set -u
# ===== 编号连续性检查（体检项 34 工具化 / 体检项 2 给它定读方，2026-09-13 批68）=====
# 为什么接这里而不是 sync 前置门：门1 刚因陈旧 HEAD 误拦过，不再加门（批66 约束）。
# 发布点是对外产出的最后一关，缺号在这里拦住，代价最小。
_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$_REPO/tools/check_ledger_numbering.py" ]; then
  if ! (cd "$_REPO" && python3 tools/check_ledger_numbering.py); then
    echo "  [编号检查-拒绝] 编号不连续 → 停止生成发布清单（体检项 34）"
    exit 1
  fi
  echo "  [编号检查-通过]"
fi
LIVE="/home/flybo/clawsjoy_v5"
ACC="$LIVE/data/sync_state/live_accumulation.jsonl"
REL="$LIVE/data/sync_state/release_points.jsonl"
TAG="${1:-}"
APPLY="${2:-}"
[ -z "$TAG" ] && { echo "用法: $0 <tag> [--apply]"; exit 2; }

LAST=$( [ -f "$REL" ] && tail -1 "$REL" | python3 -c "import sys,json;print(json.loads(sys.stdin.read() or chr(123)+chr(125)).get(chr(39)+chr(39),chr(39)))" 2>/dev/null || echo "" )
LAST_AT=$( [ -f "$REL" ] && tail -1 "$REL" | python3 -c "import sys,json;d=json.loads(sys.stdin.read());print(d.get(chr(97)+chr(116),chr(39)))" 2>/dev/null || echo "" )

echo "=== 发布清单（自上次发布点 $LAST_AT 起） ==="
python3 - "$ACC" "$LAST_AT" <<'PYEOF'
import json, sys
acc, since = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
rows = []
try:
    for ln in open(acc, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        try: rows.append(json.loads(ln))
        except Exception: continue
except FileNotFoundError:
    print("  (暂无积累记录 —— 还没有从修复后的同步脚本跑过)")
if since:
    rows = [r for r in rows if r.get("at", "") > since]
groups = {}
for r in rows:
    groups.setdefault(r.get("source_task") or "(未标注任务)", []).append(r)
print("  记录数 %d / 任务组 %d" % (len(rows), len(groups)))
for task, rs in groups.items():
    files = set()
    for r in rs:
        for f in (r.get("diff_files") or "").split("|"):
            if f.strip(): files.add(f.strip())
    print("  ● %s" % task)
    print("      记录 %d 条 / 文件 %d 个 / 最新 sandbox_head=%s" % (len(rs), len(files), rs[-1].get("sandbox_head", "")[:8]))
PYEOF


# 第 5 步：归档「本次发布清单」→ 收件箱/发布_<tag>_<日期>.md（人可读）
OUT_DIR="$LIVE/../收件箱"
[ -d "/mnt/d/Obsidian/ClawsJoy/ClawsJoy/收件箱" ] && OUT_DIR="/mnt/d/Obsidian/ClawsJoy/ClawsJoy/收件箱"
if [ "$APPLY" = "--apply" ]; then OUT_MD="$OUT_DIR/发布_${TAG}_$(date +%Y%m%d).md"; else OUT_MD="/tmp/发布_${TAG}_preview.md"; fi
python3 - "$ACC" "$LAST_AT" "$TAG" "$OUT_MD" <<'PYEOF2'
import json, sys, datetime
acc, since, tag, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
rows = []
try:
    for ln in open(acc, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        try: rows.append(json.loads(ln))
        except Exception: continue
except FileNotFoundError:
    pass
if since:
    rows = [r for r in rows if r.get("at", "") > since]
groups = {}
for r in rows:
    groups.setdefault(r.get("source_task") or "(未标注任务)", []).append(r)
L = ["# 发布 %s（%s）" % (tag, datetime.date.today().isoformat()), "",
     "> 本清单由 tools/release_point.sh 从 data/sync_state/live_accumulation.jsonl 生成。",
     "> 分组依据 = source_task（每批同步时登记的任务书标题）。", ""]
if not rows:
    L.append("（本次发布区间内暂无积累记录）")
else:
    L.append("共 **%d 条同步记录 / %d 个任务组**。" % (len(rows), len(groups)))
    L.append("")
    for task, rs in groups.items():
        files = set()
        heads = set()
        for r in rs:
            heads.add((r.get("sandbox_head") or "")[:8])
            for f in (r.get("diff_files") or "").split("|"):
                if f.strip(): files.add(f.strip())
        L.append("## %s" % task)
        L.append("")
        L.append("- 同步记录：%d 条｜sandbox_head: %s" % (len(rs), ", ".join(sorted(heads))))
        L.append("- 涉及文件：%d 个" % len(files))
        L.append("")
        for f in sorted(files):
            L.append("  - `%s`" % f)
        L.append("")
try:
    open(out, "w", encoding="utf-8").write(chr(10).join(L))
    print("  归档清单 → %s" % out)
except Exception as e:
    print("  归档失败: %s" % e)
PYEOF2
if [ "$APPLY" != "--apply" ]; then
  echo ""; echo "（预演模式：未做任何改动。加 --apply 才 commit + tag）"
  exit 0
fi

echo ""; echo "=== 真发布 ==="
git -C "$LIVE" add -A
git -C "$LIVE" commit -m "release($TAG): 发布点（清单见 data/sync_state/release_points.jsonl）" | tail -2
git -C "$LIVE" tag "$TAG" && echo "  tag: $TAG"
mkdir -p "$LIVE/data/sync_state"
printf '{"at":"%s","tag":"%s","sha":"%s"}\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$TAG" "$(git -C "$LIVE" rev-parse HEAD)" >> "$REL"
echo "  记录: $REL"
