#!/usr/bin/env bash
# 用法：bash scripts/dsh_commit.sh "提交信息" <路径1> <路径2> ...
MSG="$1"; shift
if [ -z "$MSG" ] || [ $# -eq 0 ]; then
  echo "用法：bash scripts/dsh_commit.sh '提交信息' <路径...>"
  exit 1
fi

# 1. add
git add "$@"

# 2. 先验——列出将提交的全量
echo "=== 将提交的文件 ==="
git diff --cached --name-status

# 3. commit（钩子全过才成功）
git commit -m "$MSG"
