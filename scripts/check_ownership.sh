#!/usr/bin/env bash
# DSH 提交时，禁止越界到老板目录
OWNER="${OWNER:-UNKNOWN}"
[ "$OWNER" = "UNKNOWN" ] && exit 0
[ "$OWNER" != "DSH" ] && exit 0

for f in "$@"; do
  case "$f" in
    # DSH 自己的目录——放行
    archive/*|tests/*|web/static/js/*)
      ;;
    # DSH 自己的自动化配置——放行
    .git-automation.md|scripts/check_ownership.sh|scripts/dsh_commit.sh|scripts/dsh_sync.sh)
      ;;
    # 老板目录——拦
    agents/*|core/*|engine/*|skills/*|tools/*|.git*)
      echo "❌ DSH 不能提交：$f（属老板目录）"
      exit 1
      ;;
    # 其余——放行（如根目录散文件）
    *)
      ;;
  esac
done
exit 0
