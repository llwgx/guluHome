# guluHome

接收中国移动 OneNet 平台 HTTP 推送数据，写入 PostgreSQL，并提供传感器数据看板。

## 环境要求

- Docker 与 Docker Compose

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填写 OneNet 推送 Token（须与 OneNet 控制台 HTTP 推送实例中配置的一致）：

```env
ONENET_TOKEN=your_onenet_token_here
ONENET_SKIP_VERIFY=false
APP_PORT=8000
```

> `DATABASE_URL` 在 Docker 部署下已由 `docker-compose.yml` 注入，一般无需修改。

### 2. 启动服务

```bash
docker compose up -d --build
```

首次启动会构建应用镜像并拉起 PostgreSQL 与应用容器。数据库就绪后应用会自动建表。

### 3. 验证运行

```bash
curl http://localhost:8000/health
```

返回 `{"status":"healthy"}` 表示服务正常。

### 4. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:8000/ | 传感器数据看板 |
| http://localhost:8000/onenet/push | OneNet HTTP 推送回调（GET 校验 / POST 接收数据） |
| http://localhost:8000/api/latest | 最新传感器读数 API |
| http://localhost:8000/health | 健康检查 |

若修改了 `.env` 中的 `APP_PORT`，请将上述 URL 中的端口替换为对应值。

## OneNet 配置

在 OneNet 控制台创建 HTTP 推送实例时：

1. 推送 URL 填写：`http://<你的服务器公网 IP 或域名>:8000/onenet/push`
2. Token 与 `.env` 中的 `ONENET_TOKEN` 保持一致
3. 本地调试可将 `ONENET_SKIP_VERIFY=true` 跳过签名校验（**生产环境请设为 false**）

## 常用命令

```bash
# 查看日志
docker compose logs -f app

# 停止服务
docker compose down

# 停止并删除数据库卷（会清空历史数据）
docker compose down -v
```

## 项目结构

```
app/
├── main.py           # FastAPI 入口
├── routes/           # 推送接口与看板 API
├── services/         # 传感器数据处理
└── static/           # 前端看板页面
docker-compose.yml    # PostgreSQL + 应用
Dockerfile
requirements.txt
.env.example          # 环境变量模板（复制为 .env 后使用）
```
