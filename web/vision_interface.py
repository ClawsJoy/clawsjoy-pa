#!/usr/bin/env python3
"""Vision Agent - 文生图 + ComfyUI风格工作流"""

import base64
import io
import json

import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="ClawsJoy Vision - AI图像生成", page_icon="🎨", layout="wide"
)

# 初始化工作流
if "workflow" not in st.session_state:
    st.session_state.workflow = {
        "nodes": [
            {"id": 1, "type": "text_input", "name": "提示词", "value": ""},
            {"id": 2, "type": "negative_input", "name": "负面提示词", "value": ""},
            {"id": 3, "type": "model", "name": "模型", "value": "sd-xl"},
            {"id": 4, "type": "sampler", "name": "采样器", "value": "DPM++ 2M"},
            {"id": 5, "type": "output", "name": "输出", "value": ""},
        ],
        "connections": [[1, 3], [2, 3], [3, 4], [4, 5]],
    }

st.title("🎨 ClawsJoy Vision Studio")
st.caption("ComfyUI风格工作流 + 文生图")

# 工作流编辑器（左侧）
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔧 工作流编辑器")

    # 节点列表
    for node in st.session_state.workflow["nodes"]:
        with st.expander(f"{node['name']} (ID:{node['id']})"):
            if node["type"] == "text_input":
                node["value"] = st.text_area("提示词", node["value"], height=100)
            elif node["type"] == "negative_input":
                node["value"] = st.text_area("负面提示词", node["value"], height=80)
            elif node["type"] == "model":
                node["value"] = st.selectbox("模型", ["sd-xl", "sd-3", "dalle-3"])
            elif node["type"] == "sampler":
                node["value"] = st.selectbox("采样器", ["DPM++ 2M", "Euler a", "DDIM"])

    # 添加节点
    if st.button("➕ 添加节点"):
        new_id = max(n["id"] for n in st.session_state.workflow["nodes"]) + 1
        st.session_state.workflow["nodes"].append(
            {"id": new_id, "type": "text_input", "name": f"新节点{new_id}", "value": ""}
        )
        st.rerun()

# 生成区域（右侧）
with col2:
    st.subheader("🎨 生成")

    # 获取提示词
    prompt_node = next(
        (n for n in st.session_state.workflow["nodes"] if n["type"] == "text_input"),
        None,
    )
    negative_node = next(
        (
            n
            for n in st.session_state.workflow["nodes"]
            if n["type"] == "negative_input"
        ),
        None,
    )

    prompt = prompt_node["value"] if prompt_node else ""
    negative = negative_node["value"] if negative_node else ""

    # 生成按钮
    if st.button("🚀 生成图像", type="primary", use_container_width=True):
        if prompt:
            with st.spinner("生成中..."):
                try:
                    resp = requests.post(
                        "http://localhost:5002/api/v5/vision/generate",
                        json={"prompt": prompt, "negative_prompt": negative},
                    )
                    if resp.status_code == 200:
                        img_data = resp.json().get("image")
                        if img_data:
                            image = Image.open(io.BytesIO(base64.b64decode(img_data)))
                            st.image(image, caption=prompt, use_container_width=True)

                            # 下载按钮
                            buf = io.BytesIO()
                            image.save(buf, format="PNG")
                            st.download_button(
                                "📥 下载", buf.getvalue(), "generated.png"
                            )
                except Exception as e:
                    st.error(f"生成失败: {e}")
        else:
            st.warning("请输入提示词")

    # 参数调整
    st.subheader("⚙️ 参数")
    width = st.slider("宽度", 256, 1024, 512, 64)
    height = st.slider("高度", 256, 1024, 512, 64)
    steps = st.slider("步数", 1, 50, 20)
    cfg = st.slider("CFG", 1.0, 20.0, 7.5, 0.5)

# 底部 - 工作流保存
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("💾 保存工作流"):
        import json

        with open("workflow_save.json", "w") as f:
            json.dump(st.session_state.workflow, f)
        st.success("工作流已保存")
with col2:
    if st.button("📤 导出"):
        st.download_button(
            "下载", json.dumps(st.session_state.workflow), "workflow.json"
        )
