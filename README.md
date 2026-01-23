# Sitemap Monitor - 站点地图监控工具

一个用于监控网站 Sitemap 变化的工具，当发现新增 URL 时通过飞书机器人发送通知。

## 功能特点

- 自动监控多个站点的 Sitemap
- 检测新增 URL 并记录到数据库
- 通过飞书机器人发送新 URL 通知
- 提供 Web 管理界面
- 支持 Docker 部署
- 定时自动检查（每小时一次）

## 快速开始

### Docker 部署（推荐）

#### 1. 前置条件

- Docker 和 Docker Compose 已安装
- MySQL 数据库已准备好
- 创建 Docker 网络（如果不存在）

```bash
# 创建外部网络（如果你的 MySQL 容器在其他网络中）
docker network create db_network
```

#### 2. 配置

编辑 `config.yaml` 文件，配置你的站点和飞书通知：

```yaml
sites:
  - name: "MySite"
    sitemap_urls:
      - "https://example.com/sitemap.xml"
    active: true

feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook"
  secret: "your-secret"

database:
  type: mysql
  host: "your_mysql_host"
  port: 3306
  user: "your_user"
  password: "your_password"
  name: "sitemapmonitor"
```

编辑 `docker-compose.yml`，修改环境变量：

```yaml
environment:
  - DB_TYPE=mysql
  - DB_HOST=your_mysql_host    # MySQL 容器名或 IP
  - DB_PORT=3306
  - DB_USER=your_user
  - DB_PASSWORD=your_password
  - DB_NAME=sitemapmonitor
```

#### 3. 创建数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE sitemapmonitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 4. 启动服务

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 5. 访问 Web 界面

打开浏览器访问：`http://localhost:8000`

### 本地开发运行

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库并运行一次检查
python main.py

# 或以守护模式运行（持续监控）
python main.py --daemon

# 启动 Web 服务
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 使用指南

### Web 管理界面

访问 `http://localhost:8000` 可以：

1. **查看统计数据** - 总站点数、总 URL 数、24 小时新增
2. **管理站点** - 添加、删除监控站点
3. **手动触发检查** - 点击 "Run Check Now" 立即执行检查
4. **管理分类** - 为站点添加分类标签

### CLI 命令行工具

```bash
# 列出所有站点
python manager.py list-sites

# 添加新站点
python manager.py add-site "SiteName" "https://example.com/sitemap.xml" --category "Games"

# 添加分类
python manager.py add-category "Games"

# 查看统计
python manager.py stats
```

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/stats` | GET | 获取统计数据 |
| `/api/sites` | GET | 获取所有站点 |
| `/api/sites` | POST | 添加新站点 |
| `/api/sites/{id}` | DELETE | 删除站点 |
| `/api/categories` | GET | 获取所有分类 |
| `/api/categories` | POST | 添加新分类 |
| `/api/run-now` | POST | 立即触发检查 |
| `/api/init` | GET | 初始化默认分类 |

## 目录结构

```
sitemap-monitor-tangyian/
├── config.yaml          # 配置文件
├── main.py              # 主监控逻辑
├── server.py            # Web API 服务
├── manager.py           # CLI 管理工具
├── database.py          # 数据库连接
├── models.py            # 数据模型
├── templates/
│   └── index.html       # Web 界面
├── Dockerfile           # Docker 构建文件
├── docker-compose.yml   # Docker Compose 配置
├── requirements.txt     # Python 依赖
├── data/                # 数据目录（自动创建）
└── latest/              # 最新数据 JSON 文件
```

## 配置说明

### config.yaml 完整配置

```yaml
# 监控站点列表
sites:
  - name: "SiteName"           # 站点名称
    sitemap_urls:
      - "https://example.com/sitemap.xml"
    active: true               # 是否启用

# 飞书通知配置
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  secret: "your-secret"        # 签名密钥（可选）

# 存储配置
storage:
  retention_days: 7            # 数据保留天数
  data_dir: "./data"           # 数据目录

# 数据库配置
database:
  type: mysql                  # mysql 或 sqlite
  host: "localhost"
  port: 3306
  user: "root"
  password: "password"
  name: "sitemapmonitor"
```

### 环境变量

Docker 环境下支持通过环境变量覆盖数据库配置：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DB_TYPE` | 数据库类型 | mysql |
| `DB_HOST` | 数据库主机 | localhost |
| `DB_PORT` | 数据库端口 | 3306 |
| `DB_USER` | 数据库用户 | root |
| `DB_PASSWORD` | 数据库密码 | - |
| `DB_NAME` | 数据库名 | sitemapmonitor |
| `TZ` | 时区 | Asia/Shanghai |

## 故障排除

### 常见问题

1. **无法连接数据库**
   - 检查 MySQL 容器是否运行
   - 确认网络配置正确（容器在同一网络中）
   - 验证数据库用户权限

2. **飞书通知发送失败**
   - 检查 webhook_url 是否正确
   - 验证 secret 签名密钥

3. **容器启动失败**
   ```bash
   # 查看详细日志
   docker-compose logs sitemap-monitor
   ```

### 查看日志

```bash
# Docker 日志
docker-compose logs -f

# 实时查看
docker logs -f sitemap_monitor
```

## License

MIT
