# ClawsJoy Platform

> AI 驱动的开发者协作平台 — 连接老板与开发者，合约驱动声誉，实时协作。

## 项目简介

ClawsJoy Platform 是一个去中心化的开发者协作平台。老板可以发布开发任务、评分开发者；开发者可以接单、积累链上声誉。平台基于 **Go + Next.js** 构建，声誉数据存储在 **Polygon 区块链** 上，消息传递使用 **NATS**，实现实时协作。

## 技术栈

| 层 | 技术 | 用途 |
|--------|------|-------------|
| **前端** | Next.js + TypeScript + Tailwind CSS | Web UI |
| **后端** | Go (Gin/Chi) | REST API + WS |
| **区块链** | Solidity + Hardhat + Polygon | 合约开发与部署 |
| **数据库** | PostgreSQL 16 | 业务数据持久化 |
| **缓存** | Redis 7 | 会话 / 缓存 / 队列 |
| **消息队列** | NATS | 微服务间实时通信 |
| **容器** | Docker / Docker Compose | 基础设施编排 |

## 目录结构

```
clawsjoy-platform/
├── backend/                 # Go 后端
│   ├── main.go              # 入口
│   ├── go.mod / go.sum      # 依赖管理
│   ├── api/                 # HTTP API 处理器
│   ├── services/            # 业务逻辑
│   └── models/              # 数据模型
├── frontend/                # Next.js 前端
│   ├── pages/               # 页面路由
│   ├── components/          # UI 组件
│   └── styles/              # 样式
├── contracts/               # Solidity 智能合约
│   ├── contracts/           # 合约源码（.sol）
│   ├── test/                # 合约测试
│   └── hardhat.config.ts    # Hardhat 配置
├── docker-compose.yml       # 基础设施（PG / Redis / NATS）
└── README.md                # 本文件
```

## 启动方式

### 前置依赖

- Docker & Docker Compose
- Go 1.21+
- Node.js 20+
- pnpm

### 1. 启动基础设施

```bash
docker compose up -d
```

启动后：
- PostgreSQL → `localhost:5432`
- Redis → `localhost:6379`
- NATS → `localhost:4222`

### 2. 启动后端

```bash
cd backend
go mod tidy
go run main.go
```

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 4. 编译 & 部署合约（可选）

```bash
cd contracts
npx hardhat compile
npx hardhat test
npx hardhat run scripts/deploy.ts --network localhost
```

## 环境变量

创建 `backend/.env`：

```env
DATABASE_URL=postgres://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev?sslmode=disable
REDIS_URL=redis://localhost:6379/0
NATS_URL=nats://localhost:4222
```

## 智能合约

| 合约 | 说明 | 网络 |
|--------|------|------|
| Reputation.sol | 开发者声誉评分（老板评分 → 链上信誉） | Polygon Mumbai → Mainnet |

## 许可证

MIT
