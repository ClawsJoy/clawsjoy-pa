# ============================================================
# ClawsJoy 缃戝叧 鈥?鐢熶骇绾?Dockerfile锛堝闃舵鏋勫缓锛?# 涓€閿鍣ㄥ寲閮ㄧ讲锛歞ocker build -t clawsjoy-gateway . && docker run -p 8000:8000 clawsjoy-gateway
# ============================================================

# ---------- 闃舵 1: builder ----------
# 瀹夎鎵€鏈?Python 渚濊禆鍒?/install锛屼緵 runtime 闃舵澶嶇敤
FROM python:3.12-slim AS builder

WORKDIR /build

# 瀹夎缂栬瘧宸ュ叿锛堥儴鍒嗕緷璧栧彲鑳藉惈 C 鎵╁睍锛夛紝瑁呭畬鍗虫竻鐞嗭紝鎺у埗闀滃儚浣撶Н
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 鍏堝鍒?requirements.txt锛屽厖鍒嗗埄鐢?Docker 灞傜紦瀛?COPY requirements.txt .

# 灏嗘墍鏈変緷璧栧畨瑁呭埌鐙珛鍓嶇紑 /install
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- 闃舵 2: runtime ----------
FROM python:3.12-slim AS runtime

# 鐜鍙橀噺锛氭棩蹇楀嵆鏃惰緭鍑恒€佷笉鐢熸垚 __pycache__
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 浠?builder 澶嶅埗宸插畨瑁呯殑渚濊禆锛坰ite-packages / bin 鍚堝苟杩?/usr/local锛?COPY --from=builder /install /usr/local

# 澶嶅埗椤圭洰婧愮爜
COPY . .

# 鏆撮湶缃戝叧 HTTP 绔彛
EXPOSE 8000

# 鍚姩鍛戒护
CMD ["python3", "agent_gateway_enhanced.py"]
