# ============================================================
# ClawsJoy 网关 — 生产级 Dockerfile（多阶段构建）
# 一键容器化部署：docker build -t clawsjoy-gateway . && docker run -p 8000:8000 clawsjoy-gateway
# ============================================================

# ---------- 阶段 1: builder ----------
# 安装所有 Python 依赖到 /install，供 runtime 阶段复用
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装编译工具（部分依赖可能含 C 扩展），装完即清理，控制镜像体积
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt，充分利用 Docker 层缓存
COPY requirements.txt .

# 将所有依赖安装到独立前缀 /install
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- 阶段 2: runtime ----------
FROM python:3.12-slim AS runtime

# 环境变量：日志即时输出、不生成 __pycache__
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 从 builder 复制已安装的依赖（site-packages / bin 合并进 /usr/local）
COPY --from=builder /install /usr/local

# 复制项目源码
COPY . .

# 暴露网关 HTTP 端口
EXPOSE 8000

# 启动命令
CMD ["python3", "agent_gateway_enhanced.py"]
