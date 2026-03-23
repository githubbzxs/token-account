# token-account

[English README](./README.md)

`token-account` 是一个面向 Codex 会话的常驻 token 统计服务。

它把原本一次性生成静态 HTML 的脚本改造成一个基于 FastAPI 和 SQLite 的轻量服务，支持多台设备持续上报增量事件，同时继续保留旧版报表页面作为实时仪表盘。

## 功能

- 以常驻 HTTP 服务方式提供 token 使用统计
- 从本地 Codex 会话日志增量采集事件
- 基于 `event_id` 做幂等去重
- 将多台设备的使用量合并为一份报告
- 同时提供仪表盘 API 与旧版 HTML 报表页
- 在本地保存同步状态，减少重复上传

## 技术栈

- API：`FastAPI`、`Pydantic`、`Uvicorn`
- 存储：`SQLite`、`sqlite3`
- 同步端：`urllib.request`、本地 JSON 状态文件
- 报表界面：服务端渲染 HTML、旧版报表渲染器
- 运行与部署：`Python 3.11+`、`Docker`、`Docker Compose`

## 目录结构

```text
src/token_account/
  cli.py                  serve / sync / sync-loop 命令入口
  service.py              FastAPI 路由与服务装配
  syncer.py               增量同步客户端
  storage.py              SQLite 结构与入库逻辑
  reporting.py            报表聚合与接口数据组装
  legacy_report.py        旧版 HTML 报表渲染器
src/codex_token_report.py 轻量启动入口
Dockerfile                容器镜像定义
docker-compose.yml        Compose 服务配置
pricing.json              可选定价覆盖文件
```

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动服务

```bash
python3 src/codex_token_report.py serve --host 0.0.0.0 --port 8000 --db-file data/token-account.db
```

3. 执行一次本机同步

```bash
python3 src/codex_token_report.py sync --service-url http://127.0.0.1:8000
```

4. 持续后台同步

```bash
python3 src/codex_token_report.py sync-loop --service-url http://127.0.0.1:8000 --interval 60
```

服务启动后默认可访问：

- 报告页：`http://127.0.0.1:8000/`
- 仪表盘接口：`http://127.0.0.1:8000/api/dashboard`
- 报表接口：`http://127.0.0.1:8000/api/report`
- 来源列表：`http://127.0.0.1:8000/api/sources`
- 健康检查：`http://127.0.0.1:8000/api/health`

Windows 下也可以直接双击 `open-report.bat`，它会在后台拉起本地服务并自动打开浏览器。

## 命令说明

### `serve`

启动 FastAPI 服务。

常用参数：

- `--host`：监听地址，默认 `127.0.0.1`
- `--port`：监听端口，默认 `8000`
- `--db-file`：SQLite 文件路径，默认 `data/token-account.db`
- `--pricing-file`：可选定价覆盖文件

### `sync`

扫描本机 `.codex/sessions` 数据，并将规范化后的 token 事件推送到服务端。

常用参数：

- `--service-url`：服务地址，默认 `http://127.0.0.1:8000`
- `--codex-home`：自定义 `.codex` 根目录
- `--sessions-root`：直接指定 `sessions` 目录
- `--state-file`：本地同步状态文件
- `--source-id`：来源设备标识
- `--hostname`：来源主机名
- `--batch-size`：单批上传数量，默认 `1000`
- `--timeout`：HTTP 超时秒数，默认 `30`

### `sync-loop`

循环执行 `sync`，适合守护进程、计划任务或 `systemd` 使用。

额外参数：

- `--interval`：同步间隔秒数，默认 `60`

## 数据模型

- 事件逐条落库，并通过 `event_id` 做幂等去重
- 设备元信息保存在 `sources` 表中
- 每次同步运行都会记录到 `sync_runs`，便于排查与展示状态
- HTML 报表页会定时从服务端拉取最新数据

## Docker Compose

仓库内已包含 `Dockerfile` 与 `docker-compose.yml`。

默认容器启动命令为：

```bash
python src/codex_token_report.py serve --host 0.0.0.0 --port 8000 --db-file /data/token-account.db
```

启动方式：

```bash
docker compose up -d --build
```

默认将本地 `./data` 挂载到容器 `/data`，用于持久化 SQLite 数据。

## 安全提醒

当前服务默认不做鉴权。

如果直接暴露到公网，任何可以访问该地址的人都能读取报表数据、查看来源设备状态，并向同步接口写入数据。正式对外使用前，至少建议接入反向代理、访问控制或补充认证层。
