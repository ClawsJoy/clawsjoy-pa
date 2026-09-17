#!/usr/bin/env python3
"""Streamlit 升级监控面板"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, "/home/flybo/clawsjoy_v5")

from core.agents.builtin.config_upgrader import ConfigUpgrader
from tools.real_log_collector import RealLogCollector

st.set_page_config(page_title="ClawsJoy 自我升级监控", layout="wide")

st.title("🤖 ClawsJoy 智能体自我升级系统")

# 初始化
collector = RealLogCollector()
upgrader = ConfigUpgrader()

# 侧边栏
with st.sidebar:
    st.header("📊 系统状态")
    st.metric("总升级次数", len(upgrader.history))
    st.metric("监控Agent数", 3)

    if upgrader.history:
        last = upgrader.history[-1]
        st.metric("最后升级", last["timestamp"][:16])

# 主面板
col1, col2, col3 = st.columns(3)

agents = ["chat_agent", "code_agent", "vision_agent"]
colors = ["🔵", "🟢", "🟠"]

for col, agent, color in zip([col1, col2, col3], agents, colors):
    with col:
        st.subheader(f"{color} {agent}")

        stats = collector.get_performance_stats(agent, hours=24)

        success_rate = stats["success_rate"]
        st.metric(
            "成功率",
            f"{success_rate:.1%}",
            delta=f"{success_rate - 0.7:.1%}" if success_rate else None,
        )

        st.metric("总交互", stats["total"])

        if stats["failure_types"]:
            st.write("**失败类型:**")
            for error, count in stats["failure_types"].items():
                st.caption(f"• {error}: {count}次")

        if st.button(f"立即升级 {agent}", key=agent):
            logs = collector.collect_agent_logs(agent, hours=24)
            result = upgrader.upgrade_agent(agent, logs, auto_apply=True)
            if result["upgraded"]:
                st.success(f"✅ 已升级！改进: {result['suggestions']}")
            else:
                st.info(f"ℹ️ {result.get('reason', '无需升级')}")

# 历史记录
st.subheader("📜 升级历史记录")
if upgrader.history:
    history_df = []
    for record in upgrader.history[-20:]:
        history_df.append(
            {
                "时间": record["timestamp"][:19],
                "Agent": record["agent"],
                "升级前成功率": f"{record['success_rate_before']:.1%}",
                "改进": record["suggestions"],
            }
        )
    st.dataframe(history_df)
else:
    st.info("暂无升级记录")

# 实时刷新
if st.button("🔄 刷新数据"):
    st.rerun()

if __name__ == "__main__":
    st.write("运行: streamlit run web/upgrade_dashboard.py")
