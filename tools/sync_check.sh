#!/usr/bin/env bash
# ============================================================
# ClawsJoy 发布流程：线上同步 + 重启核对清单
# 用法: bash tools/sync_check.sh [--restart-check]
#   - 对比 sandbox(会话工作区) 与 live(/home/<user>/clawsjoy_v5) 的关键文件 md5
#   - 输出待同步文件清单 + 重启提示
#   - 系统文件双写检查（live 正本 → sandbox 镜像）
#   - 可选 --restart-check: 检查 gateway 进程是否在跑
# ============================================================
set -u

LIVE_ROOT="/home/<user>/clawsjoy_v5"
# 会话工作区（sandbox）：
# 1) 优先用环境变量 SANDBOX_ROOT（在 live 目录运行时必须显式指定）
# 2) 否则从脚本位置推导（脚本在沙箱 tools/ 下时正确）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "${SANDBOX_ROOT:-}" ]; then
  SANDBOX_ROOT="$SANDBOX_ROOT"
else
  SANDBOX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
# 防呆：脚本在 live 目录运行（sandbox==live）时，提示正确用法
if [ "$SANDBOX_ROOT" = "$LIVE_ROOT" ]; then
  echo "⚠️  sandbox 与 live 路径相同！脚本可能被复制到了 live 目录。"
  echo "   正确用法（在沙箱会话工作区运行）："
  echo "     bash tools/sync_check.sh"
  echo "   或在 live 目录运行时显式指定沙箱路径："
  echo "     SANDBOX_ROOT=/home/<user>/clawsjoy_v5/data/projects/web_1783219071801/session_1783388196051/clawsjoy_dev bash tools/sync_check.sh"
  echo ""
fi

echo "=========================================="
echo " ClawsJoy 同步核对"
echo " sandbox: $SANDBOX_ROOT"
echo " live:    $LIVE_ROOT"
echo "=========================================="

# 关键文件清单（同步核对对象，sandbox → live）
FILES=(
  "agent_gateway_enhanced.py"
  "core/gateway/security.py"
  "core/gateway/audit.py"
  "core/gateway/goal_state.py"
  "core/gateway/tool_router.py"
  "core/gateway/execute_agent_task.py"
  "core/gateway/message_assembler.py"
  "core/gateway/shared_state.py"
  "core/gateway/sandbox_ops.py"
  "core/gateway/sandbox_util.py"
  "core/gateway/sandbox_git.py"
  "core/gateway/sandbox_write.py"
  "core/lib/task_vars.py"
  "core/lib/precision_feed.py"
  "core/lib/sag_audit_bridge.py"
  "core/tools/file_tools.py"
  "core/tools/query_index.py"
  "core/tools/read_file.py"
  "core/gateway/registry.py"
  "core/gateway/chat_stream.py"
  "core/gateway/state_persist.py"
  "core/gateway/archive.py"
  "core/gateway/sag_feedback.py"
  "core/gateway/context_validator.py"
  "core/gateway/quota_manager.py"
  "core/context/context_manager.py"
  "core/lib/dependency_graph.json"
  "tools/backfill_dependency_graph.py"
  "tests/integration/test_arch_guards.py"
  "tests/integration/test_http_audit.py"
  "tests/integration/test_filter_reliability.py"
  "web/dashboard/workbench.html"
  "config/prompts/agent_system.md"
)

# ============================================================
# 系统文件双写清单（正本在 live，需镜像到沙箱）
# 说明书/配置类系统文件改在 live 正本，必须双写到沙箱镜像，
# 否则 Agent 在沙箱里读到的是旧版本。
# 镜像方向：live（正本）→ sandbox（镜像）
# ============================================================
SYS_FILES=(
  "config/prompts/agent_manual.md"
  "config/prompts/agent_system.md"
)

NEED_SYNC=0
SYNC_LIST=()
for f in "${FILES[@]}"; do
  s="$SANDBOX_ROOT/$f"
  l="$LIVE_ROOT/$f"
  if [ ! -f "$s" ]; then
    echo "  [SKIP] sandbox 无文件: $f"
    continue
  fi
  if [ ! -f "$l" ]; then
    echo "  [NEW]  live 缺失(需新建): $f"
    NEED_SYNC=1
    SYNC_LIST+=("$f")
    continue
  fi
  md5_s=$(md5sum "$s" | awk '{print $1}')
  md5_l=$(md5sum "$l" | awk '{print $1}')
  if [ "$md5_s" = "$md5_l" ]; then
    echo "  [OK]   $f"
  else
    echo "  [DIFF] $f"
    NEED_SYNC=1
    SYNC_LIST+=("$f")
  fi
done

echo ""
echo "=========================================="
if [ "$NEED_SYNC" -eq 1 ]; then
  echo "  有 ${#SYNC_LIST[@]} 个文件需同步到 live（sandbox → live）:"
  for f in "${SYNC_LIST[@]}"; do
    echo "    cp $SANDBOX_ROOT/$f $LIVE_ROOT/$f"
  done
  echo ""
  echo " 一键同步命令:"
  echo -n "    for f in "
  printf '%q ' "${SYNC_LIST[@]}"
  echo "; do cp \"$SANDBOX_ROOT/\$f\" \"$LIVE_ROOT/\$f\"; done"
else
  echo "  全部关键文件已同步（md5 一致）"
fi
echo "=========================================="

# ============================================================
# 删除流程检查: git 已删 .py 文件的残留 import 引用
# (API/模块删除须同步删引用, 防 test_e2e 式死测试: WisdomWrapper 删除
#  未同步删测试 -> 0 tests collected)
# ============================================================
DEL_CHECK_HIT=0
echo ""
echo "--- 删除流程检查（git 最近删除 .py 的残留引用）---"
while read -r DELFILE; do
  [ -z "$DELFILE" ] && continue
  # 完整模块路径匹配(只匹配同模块, 避免 basename 跨目录误报):
  # clawsjoy_v10/engine/adapters/x.py -> clawsjoy_v10.engine.adapters.x
  MODULE=$(echo "$DELFILE" | sed 's|\.py$||; s|/|.|g')
  # 排除跨项目路径(v10 删除不应匹配 core 同名模块引用)
  case "$MODULE" in
    clawsjoy_v10.*|clawsjoy_dev.*) continue ;;
  esac
  # grep 全仓 import/from 引用(完整模块路径, 排除 .git/node_modules/__pycache__)
  REFS=$(grep -rn --include='*.py' -E "from[[:space:]]+${MODULE}[[:space:]]+import|import[[:space:]]+${MODULE}([[:space:]]|$)" . 2>/dev/null \
    | grep -v -E '\.git/|node_modules|__pycache__|\.venv/|sync_check\.sh' \
    | grep -v -E '^[^:]+:[0-9]+:[[:space:]]*#' | head -5)
  if [ -n "$REFS" ]; then
    DEL_CHECK_HIT=1
    echo "  [DELETE-CHECK] 已删除 ${DELFILE} 仍有残留引用:"
    echo "$REFS" | sed 's/^/    /'
  fi
done < <(git log --diff-filter=D --name-only -20 --format="" -- '*.py' 2>/dev/null | grep -E '\.py$' | sort -u)
if [ "$DEL_CHECK_HIT" -eq 0 ]; then
  echo "  [DELETE-CHECK] 无残留引用 ✓"
fi

# ============================================================
# 系统文件双写检查（live 正本 → sandbox 镜像）
# ============================================================
MIRROR_NEED=0
MIRROR_LIST=()
echo ""
echo "--- 系统文件双写检查（live 正本 → sandbox 镜像）---"
for f in "${SYS_FILES[@]}"; do
  l="$LIVE_ROOT/$f"
  s="$SANDBOX_ROOT/$f"
  if [ ! -f "$l" ]; then
    echo "  [SKIP] live 正本不存在: $f"
    continue
  fi
  if [ ! -f "$s" ]; then
    echo "  [MIRROR-NEW] 沙箱镜像缺失: $f"
    MIRROR_NEED=1
    MIRROR_LIST+=("$f")
    continue
  fi
  md5_l=$(md5sum "$l" | awk '{print $1}')
  md5_s=$(md5sum "$s" | awk '{print $1}')
  if [ "$md5_l" = "$md5_s" ]; then
    echo "  [OK]   $f（镜像一致）"
  else
    echo "  [MIRROR-DIFF] $f（正本与镜像不同，需双写）"
    MIRROR_NEED=1
    MIRROR_LIST+=("$f")
  fi
done
if [ "$MIRROR_NEED" -eq 1 ]; then
  echo ""
  echo "  有 ${#MIRROR_LIST[@]} 个系统文件需双写到沙箱镜像（live → sandbox）:"
  for f in "${MIRROR_LIST[@]}"; do
    echo "    cp $LIVE_ROOT/$f $SANDBOX_ROOT/$f"
  done
  echo ""
  echo " 一键双写命令:"
  echo -n "    for f in "
  printf '%q ' "${MIRROR_LIST[@]}"
  echo "; do cp \"$LIVE_ROOT/\$f\" \"$SANDBOX_ROOT/\$f\"; done"
else
  echo "  系统文件镜像全部一致"
fi
echo "=========================================="

# ============================================================
# 第三类：运行态数据一致性检查
# 1) user_messages 归档：真双写（live 正本 + 沙箱镜像，实时双向）
# 2) .agent_state.json：单一运行态（网关以 live 为 cwd 写沙箱内这份）
# ============================================================
RUNTIME_NEED=0
RUNTIME_LIST=()
echo ""
echo "--- 运行态数据一致性检查 ---"
echo "  [user_messages 双写] live 正本 vs 沙箱镜像:"
UM_MIRROR_NEED=0
for l in "$LIVE_ROOT"/data/v8/user_messages/*.jsonl; do
  [ -f "$l" ] || continue
  _sid=$(basename "$l" .jsonl)
  s="$SANDBOX_ROOT/data/v8/user_messages/$_sid.jsonl"
  if [ ! -f "$s" ]; then
    echo "    [MIRROR-NEW] $_sid: 沙箱镜像缺失"
    UM_MIRROR_NEED=1
    continue
  fi
  _lc=$(wc -l < "$l" | tr -d " ")
  _sc=$(wc -l < "$s" | tr -d " ")
  if [ "$_lc" = "$_sc" ]; then
    echo "    [OK] $_sid ($_lc 行一致)"
  else
    echo "    [DIFF] $_sid: live=$_lc 行 vs 镜像=$_sc 行"
    UM_MIRROR_NEED=1
    RUNTIME_NEED=1
    RUNTIME_LIST+=("data/v8/user_messages/$_sid.jsonl")
  fi
done
if [ "$UM_MIRROR_NEED" -eq 0 ]; then
  echo "    全部 user_messages 镜像一致"
fi

# 2) .agent_state.json 存在性（单一运行态）
AG_STATE="$SANDBOX_ROOT/.agent_state.json"
echo "  [.agent_state.json] 运行态文件:"
if [ -f "$AG_STATE" ]; then
  echo "    [OK] 存在 ($(wc -c < "$AG_STATE" | tr -d " ") 字节)"
else
  echo "    [MISSING] $AG_STATE"
  RUNTIME_NEED=1
  RUNTIME_LIST+=(".agent_state.json")
fi

if [ "$RUNTIME_NEED" -eq 1 ]; then
  echo ""
  echo "  运行态数据存在差异（${#RUNTIME_LIST[@]} 项）:"
  for f in "${RUNTIME_LIST[@]}"; do
    echo "    检查: $f"
  done
  echo "  提示: user_messages 由启动回填自动补齐(H9)；agent_state 为网关运行时生成"
else
  echo "  运行态数据检查通过"
fi
echo "=========================================="

# 重启检查
if [ "${1:-}" = "--restart-check" ]; then
  echo ""
  echo "--- Gateway 进程检查 ---"
  PGID=$(pgrep -f "python agent_gateway_enhanced.py" | head -1)
  if [ -n "$PGID" ]; then
    echo "  Gateway 运行中 (PID=$PGID)"
    if curl -s -m 3 http://127.0.0.1:5002/ >/dev/null 2>&1; then
      echo "  端口 5002 响应正常"
    else
      echo "  端口 5002 无响应（可能仍在启动或崩溃）"
    fi
  else
    echo "  Gateway 未运行！启动命令:"
    echo "    cd $LIVE_ROOT && nohup python agent_gateway_enhanced.py > /tmp/clawsjoy_gateway.log 2>&1 &"
  fi
fi

echo ""
echo " 发布流程: 同步 → 重启 → curl http://127.0.0.1:5002/ 验证 → 浏览器测试"