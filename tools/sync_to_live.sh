#!/usr/bin/env bash
# ============================================================
# 纪律（2026-09-13，真 sync 验收时抓到门自身两个缺陷后立）：
#   1) 「绕过门可以，绕过留痕不行」
#   2) 「gate 的 bypass 只能 bypass 判定，不能 bypass 留痕」
# 具体含义：SKIP_SYNC_GATE=1 只跳过**判定**（门1），
#   不得跳过**留痕**（门2 同步点记录 / 积累记录）。
#   本脚本的门2 因此放在门块外面，且必须无条件执行。
# 改本脚本前请先读这三行 —— 纪律写在文档里但脚本不写 = 下次改脚本的人看不到。
# ============================================================
# 一键同步 + 重启（改正方案#2 + #4）
set -u
LIVE="/home/<user>/clawsjoy_v5"
SANDBOX="/home/<user>/clawsjoy_v5/data/projects/web_1783219071801/session_1783388196051/clawsjoy_dev"

echo "=== 0. 前置门（度量归属，2026-09-13）==="
GATE_FAIL=0
if [ "${SKIP_SYNC_GATE:-0}" != "1" ]; then
  # 批76: 白名单补 .json。原先收 yaml/yml 却漏 json，而 config/ 下两者并列（实测 322 yaml / 19 json）
  #       —— 同一层配置两种命运；filter_net.json / dependency_graph.json 等都能改变行为却不被拦。
  #       **刻意不加 .md**：交付文档每天都在改，拦它会误伤（见批70 门1 缺口清单）。
  #       批71 曾改过此处但**未生效**（批76 查证时发现仍是旧正则）→ 本次改完**用脚本本身**验证。
  DIRTY=$(git -C "$SANDBOX" status --porcelain 2>/dev/null | awk '{print $2}' | grep -E "\.(py|js|html|sh|yaml|yml|json)$" | grep -v "^tests/" | head -20)
  if [ -n "$DIRTY" ]; then
    echo "  [门1-拒绝] 存在未提交的代码改动（先 commit；或用 SKIP_SYNC_GATE=1 强制）："
    echo "$DIRTY" | sed "s/^/      /"
    GATE_FAIL=1
  else
    echo "  [门1-通过] 无未提交代码改动"
  fi
  if [ "$GATE_FAIL" = "1" ]; then echo "=== 前置门未通过，已停止同步（未做任何推送）==="; exit 1; fi
else
  echo "  [跳过] SKIP_SYNC_GATE=1"
fi
echo ""
echo "=== 1. 代码 diff 扫描(自动) ==="
DIFF_COUNT=0
DIFF_LIST=""
while IFS= read -r f; do
  case "$f" in
    *.py|*.yaml|*.yml|*.html|*.sh|*.bat|*.json|*.md) ;;
    *) continue ;;
  esac
  # 2026-09-13 修：原实现在**绝对路径**上匹配 */data/* —— 而沙箱本身就在
  # /home/<user>/clawsjoy_v5/data/projects/... 下，于是**每个文件都被跳过**，DIFF_COUNT 恒为 0
  # （声称扫描、实际没扫 = 流程假绿）。改为先算相对路径再过滤。
  relf=$(echo "$f" | sed "s#^$SANDBOX/##")
  case "$relf" in
    data/*|logs/*|.venv/*|*/__pycache__/*|*/node_modules/*|web/images/*|web/mobile/*|.git/*|goals/*|memory/*|archive/*|*/archive/*|.pytest_cache/*|.ruff_cache/*) continue ;;
  esac
  if [ -f "$LIVE/$relf" ]; then
    a=$(md5sum "$f" | cut -d' ' -f1); b=$(md5sum "$LIVE/$relf" | cut -d' ' -f1)
    if [ "$a" != "$b" ]; then echo "  [DIFF] $relf"; DIFF_COUNT=$((DIFF_COUNT+1)); DIFF_LIST="$DIFF_LIST $relf"; fi
  else
    echo "  [NEW]  $relf"; DIFF_COUNT=$((DIFF_COUNT+1))
  fi
done < <(find "$SANDBOX" -type f 2>/dev/null)
echo "  共 $DIFF_COUNT 个文件有差异/新增"

# ===== 门2（同步点记录）—— 2026-09-13 修两处位置缺陷 =====
# 缺陷1: 原先写在门块内 → SKIP_SYNC_GATE=1 时连记录也跳过（绕过门可以，绕过留痕不行）
# 缺陷2: 原先在差异扫描之前 → diff_count 恒为 0
# 修法: 移到门块**外面** + 扫描**之后**，无条件执行。
# 纪律: **gate 的 bypass 只能 bypass 判定，不能 bypass 留痕。**
mkdir -p "$LIVE/data/sync_state"
_HEAD_SHA=$(git -C "$SANDBOX" rev-parse HEAD 2>/dev/null)
# --- last_sync.jsonl 定位：**仅供人工排查，无自动消费者**（2026-09-13 批59 处置=选项a）---
# 批57 取证：本文件全仓**零读者**（文件名命中仅本写入行自身）→ 属「断头留痕」，不是归属锚点。
# 归属请看同一次 sync 写的 live_accumulation.jsonl —— 它有真消费者：tools/release_point.sh 按 source_task 出发布清单。
# 处置理由：答不出「下次算上次同步点」这条链的**具体用途**（rsync 本就全树比对，无需增量起点；归属已由积累记录承担）→ 按纪律不默认选 (b)，降级为纯日志。
# 落点遵循「纪律要在第一现场」：写在本文件的写入处，而非只写文档。
printf '{"at":"%s","sandbox_head":"%s","diff_count":%s}
'   "$(date +%Y-%m-%dT%H:%M:%S)" "$_HEAD_SHA" "$DIFF_COUNT"   >> "$LIVE/data/sync_state/last_sync.jsonl" 2>/dev/null || true
echo "  [门2-记录] sandbox_head=$_HEAD_SHA diff_count=$DIFF_COUNT"

# 2026-09-13 正本积累记录：每次同步追加一行（不 commit 正本；写 $LIVE/data/ 被 rsync 排除）
if [ "$DIFF_COUNT" -gt 0 ]; then
  mkdir -p "$LIVE/data/sync_state"
  _HEAD=$(git -C "$SANDBOX" rev-parse HEAD 2>/dev/null)
  _FILES=$(printf '%s' "$DIFF_LIST" | tr ' ' '|' | head -c 400)
  printf '{"at":"%s","by":"%s","sandbox_head":"%s","diff_count":%s,"diff_files":"%s","source_task":"%s"}
'     "$(date +%Y-%m-%dT%H:%M:%S)" "${SYNC_BY:-unknown}" "$_HEAD" "$DIFF_COUNT" "$_FILES" "${SYNC_TASK:-}"     >> "$LIVE/data/sync_state/live_accumulation.jsonl" 2>/dev/null || true
  echo "  [积累记录] 已追加一行 → data/sync_state/live_accumulation.jsonl"
fi

echo ""
echo "=== 2. rsync sandbox -> live (不带 --delete) ==="
rsync -a \
  --exclude='.git/' --exclude='.env' --exclude='data/' --exclude='logs/' \
  --exclude='goals/' --exclude='memory/' --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='node_modules/' --exclude='web/images/' --exclude='web/mobile/' \
  --exclude='.venv/' --exclude='.agent_state.json' --exclude='.progress_checkpoint.json' \
  --exclude='.snippet_save_state.txt' --exclude='*.log' --exclude='.pytest_cache/' \
  --exclude='.ruff_cache/' \
  "$SANDBOX/" "$LIVE/"
echo "rsync exit: $?"

echo ""
echo "=== 3. 从 live 重启 ==="
bash "$LIVE/tools/restart_gateway.sh"
