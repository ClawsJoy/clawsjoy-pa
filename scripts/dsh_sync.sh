#!/usr/bin/env bash
# 用法：bash scripts/dsh_sync.sh [--apply]
#   默认 **dry-run**（只打印将要做什么，不改任何文件）；加 --apply 才真同步。
#   方向：dev 正本 → live。**只增不删**（不带 --delete，见 .git-automation.md 五、例外）。
#
# 体检项 110 修：同步脚本的「默认源路径 + --delete」组合是一键清空目标树的脚枪——
#   本脚本三条防线：①默认源指向**真 dev 检出**（不再是空目录 $HOME/clawsjoy_dev）
#   ②**体量自检**：源文件数 < 目标文件数的 10% ⇒ 拒绝（exit 1）
#   ③默认 dry-run，且**永不 --delete**
set -u

DEFAULT_SANDBOX="/home/flybo/clawsjoy_v5/data/projects/web_1783219071801/session_1783388196051/clawsjoy_dev"
SANDBOX="${SANDBOX:-$DEFAULT_SANDBOX}"
LIVE="${LIVE:-$HOME/clawsjoy_v5}"

APPLY=0
for _a in "$@"; do
  case "$_a" in
    --apply) APPLY=1 ;;
    -n|--dry-run) APPLY=0 ;;
    "") ;;
    *) echo "未知参数：$_a（用法：bash scripts/dsh_sync.sh [--apply]）"; exit 2 ;;
  esac
done

echo "=== 0. 前置自检（体检项 110）==="
if [ ! -d "$SANDBOX" ]; then echo "❌ 源目录不存在：$SANDBOX"; exit 1; fi
if [ ! -d "$LIVE" ]; then echo "❌ 目标目录不存在：$LIVE"; exit 1; fi
if [ "$(cd "$SANDBOX" && pwd)" = "$(cd "$LIVE" && pwd)" ]; then echo "❌ 源与目标是同一个目录：$SANDBOX"; exit 1; fi

SRC_N=$(find "$SANDBOX" -type f -not -path '*/.git/*' 2>/dev/null | wc -l)
DST_N=$(find "$LIVE" -type f -not -path '*/.git/*' -not -path '*/data/*' -not -path '*/logs/*' -not -path '*/archive/*' 2>/dev/null | wc -l)
echo "  源（dev 正本）：$SANDBOX"
echo "    文件数 = $SRC_N"
echo "  目标（live）：$LIVE"
echo "    文件数 = $DST_N（已排除 .git/ data/ logs/ archive/）"
if [ "$DST_N" -gt 0 ] && [ $((SRC_N * 10)) -lt "$DST_N" ]; then
  echo "源文件数异常，疑似路径错，已拒绝同步（源 $SRC_N < 目标 $DST_N 的 10%）"
  exit 1
fi

echo "=== 1. 改前 sha256（体检项 106）==="
find "$LIVE" -type f -name '*.py' -exec sha256sum {} \; > /tmp/live_before_sync.txt
echo "  记录数: $(wc -l < /tmp/live_before_sync.txt)"

echo "=== 2. rsync（只增不删）==="
RSYNC_OPTS=(-av --exclude='.git' --exclude='data/' --exclude='logs/' --exclude='archive/')
if [ "$APPLY" -eq 1 ]; then
  echo "  模式：真同步（--apply）"
else
  RSYNC_OPTS+=(-n)
  echo "  模式：DRY-RUN（不改文件；确认无误后加 --apply 真同步）"
fi
rsync "${RSYNC_OPTS[@]}" "$SANDBOX/" "$LIVE/"

echo "=== 3. 复测（体检项 106）==="
if [ -e "$LIVE/web/api" ]; then echo "  web/api OK"; else echo "  web/api MISSING"; fi
curl -s --max-time 5 http://127.0.0.1:5002/health | head -1
echo "  （收口提醒：复测时刻 + 本脚本“只增不删”，删除类同步请走单独指令）"
