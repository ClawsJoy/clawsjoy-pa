#!/usr/bin/env python3
"""增强版 ClawsJoy 自我升级监控面板"""

import sys
from datetime import datetime, timedelta
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

sys.path.insert(0, "/home/flybo/clawsjoy_v5")

from core.agents.builtin.config_upgrader import ConfigUpgrader
from tools.real_log_collector import RealLogCollector

# 页面配置
st.set_page_config(
    page_title="ClawsJoy 智能体监控",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 初始化
collector = RealLogCollector()
upgrader = ConfigUpgrader()

# 所有Agent列表
ALL_AGENTS = [
    "analysis_agent",
    "chat_agent",
    "code_agent",
    "collaboration_agent",
    "decision_agent",
    "dialect_agent",
    "director_agent",
    "executor_agent",
    "memory_agent",
    "orchestrator",
    "translate_agent",
    "video_agent",
    "video_indexer_agent",
    "vision_agent",
    "writer_agent",
    "youtube_agent",
]

# 侧边栏
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=80)
    st.title("🤖 ClawsJoy")
    st.markdown("---")

    # 系统状态
    st.subheader("📊 系统状态")
    total_upgrades = len(upgrader.history)
    col1, col2 = st.columns(2)
    col1.metric("总升级次数", total_upgrades)
    col2.metric(
        "监控Agent",
        len([a for a in ALL_AGENTS if Path(f"agents/{a}/config.yaml").exists()]),
    )

    st.markdown("---")

    # 快速操作
    st.subheader("⚡ 快速操作")
    if st.button("🔄 刷新数据", use_container_width=True):
        st.rerun()

    if st.button("🚀 立即升级所有Agent", use_container_width=True):
        with st.spinner("升级中..."):
            for agent in ALL_AGENTS[:5]:  # 只升级前5个避免超时
                logs = collector.collect_agent_logs(agent, hours=24)
                if len(logs) > 10:
                    upgrader.upgrade_agent(agent, logs, auto_apply=True)
        st.success("升级完成！")
        st.rerun()

    st.markdown("---")
    st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 主页面
st.title("🤖 ClawsJoy 智能体自我升级系统")

# Tab 布局
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 性能监控", "📈 升级历史", "⚙️ 配置管理", "🔧 手动升级"]
)

# Tab 1: 性能监控
with tab1:
    st.subheader("Agent 性能概览")

    # 收集数据
    performance_data = []
    for agent in ALL_AGENTS:
        stats = collector.get_performance_stats(agent, hours=24)
        if stats["total"] > 0:
            config_file = Path(f"agents/{agent}/config.yaml")
            temp = "N/A"
            if config_file.exists():
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                    temp = (
                        config.get("agent", {}).get("llm", {}).get("temperature", "N/A")
                    )

            performance_data.append(
                {
                    "Agent": agent,
                    "成功率": f"{stats['success_rate']:.1%}",
                    "成功率数值": stats["success_rate"],
                    "交互次数": stats["total"],
                    "成功次数": stats["successes"],
                    "失败次数": stats["failures"],
                    "温度": temp,
                }
            )

    if performance_data:
        df = pd.DataFrame(performance_data)

        # 指标卡片
        col1, col2, col3, col4 = st.columns(4)
        avg_rate = df["成功率数值"].mean()
        total_interactions = df["交互次数"].sum()
        high_perf = len([r for r in performance_data if r["成功率数值"] >= 0.8])

        col1.metric("平均成功率", f"{avg_rate:.1%}")
        col2.metric("总交互次数", total_interactions)
        col3.metric("优秀Agent(≥80%)", high_perf)
        col4.metric(
            "需优化(<70%)", len([r for r in performance_data if r["成功率数值"] < 0.7])
        )

        st.markdown("---")

        # 成功率图表
        fig = go.Figure(
            data=[
                go.Bar(
                    x=[d["Agent"] for d in performance_data],
                    y=[d["成功率数值"] for d in performance_data],
                    text=[d["成功率"] for d in performance_data],
                    textposition="auto",
                    marker_color=[d["成功率数值"] for d in performance_data],
                    marker_colorscale="RdYlGn",
                    marker_showscale=True,
                )
            ]
        )
        fig.update_layout(
            title="Agent 成功率对比",
            xaxis_title="Agent",
            yaxis_title="成功率",
            yaxis_tickformat=".0%",
            height=500,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 数据表格
        st.subheader("详细数据")
        st.dataframe(df.drop("成功率数值", axis=1), use_container_width=True)
    else:
        st.info("暂无性能数据，等待Agent交互...")

# Tab 2: 升级历史
with tab2:
    st.subheader("升级历史记录")

    if upgrader.history:
        history_df = pd.DataFrame(upgrader.history[::-1])  # 倒序显示最新的在前面
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"]).dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        history_df["改进详情"] = history_df["suggestions"].apply(lambda x: str(x))

        cols_to_show = [
            "timestamp",
            "agent",
            "success_rate_before",
            "改进详情",
            "applied",
        ]
        history_df = history_df[[c for c in cols_to_show if c in history_df.columns]]

        st.dataframe(history_df, use_container_width=True)

        # 统计图表
        st.subheader("升级统计")
        col1, col2 = st.columns(2)

        with col1:
            # 各Agent升级次数
            upgrade_counts = history_df["agent"].value_counts()
            fig2 = go.Figure(
                data=[go.Bar(x=upgrade_counts.index, y=upgrade_counts.values)]
            )
            fig2.update_layout(
                title="各Agent升级次数", xaxis_title="Agent", yaxis_title="次数"
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            # 升级时间趋势
            history_df["date"] = pd.to_datetime(history_df["timestamp"])
            daily_counts = history_df.groupby(history_df["date"].dt.date).size()
            fig3 = go.Figure(
                data=[
                    go.Scatter(
                        x=daily_counts.index,
                        y=daily_counts.values,
                        mode="lines+markers",
                    )
                ]
            )
            fig3.update_layout(
                title="升级趋势", xaxis_title="日期", yaxis_title="升级次数"
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("暂无升级记录")

# Tab 3: 配置管理
with tab3:
    st.subheader("Agent 配置管理")

    # 选择Agent
    selected_agent = st.selectbox("选择Agent", ALL_AGENTS)

    config_file = Path(f"agents/{selected_agent}/config.yaml")
    if config_file.exists():
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        col1, col2 = st.columns(2)

        with col1:
            st.write("📝 当前配置")
            st.json(config)

        with col2:
            st.write("🔧 修改配置")

            new_temp = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=float(
                    config.get("agent", {}).get("llm", {}).get("temperature", 0.7)
                ),
                step=0.1,
            )

            new_tokens = st.number_input(
                "Max Tokens",
                min_value=256,
                max_value=8192,
                value=int(
                    config.get("agent", {}).get("llm", {}).get("max_tokens", 1024)
                ),
                step=256,
            )

            if st.button("💾 保存配置"):
                if "agent" not in config:
                    config["agent"] = {}
                if "llm" not in config["agent"]:
                    config["agent"]["llm"] = {}

                config["agent"]["llm"]["temperature"] = new_temp
                config["agent"]["llm"]["max_tokens"] = new_tokens

                with open(config_file, "w") as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

                st.success("配置已保存！")
                st.rerun()
    else:
        st.error(f"配置文件不存在: {config_file}")

# Tab 4: 手动升级
with tab4:
    st.subheader("手动升级 Agent")

    col1, col2 = st.columns(2)

    with col1:
        upgrade_agent = st.selectbox(
            "选择要升级的Agent", ALL_AGENTS, key="upgrade_select"
        )

        if st.button("🔧 分析并升级", type="primary"):
            with st.spinner(f"正在分析 {upgrade_agent}..."):
                logs = collector.collect_agent_logs(upgrade_agent, hours=24)
                if len(logs) > 10:
                    result = upgrader.upgrade_agent(
                        upgrade_agent, logs, auto_apply=True
                    )
                    if result.get("upgraded"):
                        st.success(f"✅ {upgrade_agent} 已升级！")
                        st.json(result.get("suggestions", {}))
                    else:
                        st.info(f"ℹ️ {result.get('reason', '无需升级')}")
                else:
                    st.warning(f"日志不足 ({len(logs)}条)，需要至少10条")

    with col2:
        st.write("📊 当前性能")
        stats = collector.get_performance_stats(upgrade_agent, hours=24)
        if stats["total"] > 0:
            st.metric("成功率", f"{stats['success_rate']:.1%}")
            st.metric("交互次数", stats["total"])
            if stats.get("failure_types"):
                st.write("失败类型:")
                for error, count in stats["failure_types"].items():
                    st.caption(f"• {error}: {count}次")
        else:
            st.info("暂无数据")

# 自动刷新提示
st.sidebar.markdown("---")
st.sidebar.info("💡 提示: 页面每30秒自动刷新数据")
time.sleep(30)
st.rerun()
