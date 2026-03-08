# Codex Token Usage Service

将原本一次性生成静态 HTML 的脚本改为常驻服务：
- 服务端使用 FastAPI + SQLite 持久化数据
- 客户端通过 `sync` / `sync-loop` 持续推送本机 Codex 会话增量
- HTML 报告页继续保留，直接由服务提供，并定时从 API 拉取最新数据

## 依赖
- Python 3.11+
- `pip install -r requirements.txt`

## 快速开始

### 1）启动服务
```bash
python3 src/codex_token_report.py serve --host 0.0.0.0 --port 8000 --db-file data/token-account.db
```

Windows 下也可以直接双击 `open-report.bat`，它会在后台拉起本地服务并自动打开浏览器。

启动后可访问：
- 报告页：`http://127.0.0.1:8000/`
- 报表接口：`http://127.0.0.1:8000/api/report`
- 来源列表：`http://127.0.0.1:8000/api/sources`
- 健康检查：`http://127.0.0.1:8000/api/health`

### 2）执行一次同步
```bash
python3 src/codex_token_report.py sync --service-url http://127.0.0.1:8000
```

### 3）后台持续同步
```bash
python3 src/codex_token_report.py sync-loop --service-url http://127.0.0.1:8000 --interval 60
```

## 命令说明

### `serve`
启动常驻服务。

常用参数：
- `--host`：监听地址，默认 `127.0.0.1`
- `--port`：监听端口，默认 `8000`
- `--db-file`：SQLite 文件路径，默认 `data/token-account.db`
- `--pricing-file`：覆盖定价文件

### `sync`
扫描本机 `.codex/sessions` 目录，将规范化 token 增量事件推送到服务。

常用参数：
- `--service-url`：服务地址，默认 `http://127.0.0.1:8000`
- `--codex-home`：指定 `.codex` 根目录
- `--sessions-root`：直接指定 `sessions` 目录
- `--state-file`：本地同步状态文件
- `--source-id`：来源设备 ID
- `--hostname`：来源设备主机名
- `--batch-size`：单批上传事件数，默认 `1000`
- `--timeout`：HTTP 超时秒数，默认 `30`

### `sync-loop`
定时执行同步，适合配合 `systemd`、计划任务或守护进程使用。

额外参数：
- `--interval`：同步间隔秒数，默认 `60`

## 数据模型说明
- 服务端按事件入库，并通过 `event_id` 幂等去重
- 多台设备默认合并成一份总报告
- 服务端仍保留来源设备信息，用于展示最近同步状态
- 报告页默认每 30 秒轮询一次 `/api/report`

## 与旧版行为的变化
- 不再以 `report/index.html` 为主交付物
- 页面内手动导入/导出合并能力已移除为“服务同步”模式
- HTML 报告页仍保留，但它现在是服务的一部分，而不是静态文件输出

## 公网部署提醒
当前实现按你的要求 **不加鉴权**。
这意味着任何能访问服务地址的人，都可以：
- 查看你的使用报告
- 读取来源设备状态
- 调用同步接口写入数据

如果要上公网，至少建议通过反向代理、访问控制或后续补 token 鉴权来收口。

## Docker Compose
仓库内包含 `Dockerfile` 与 `docker-compose.yml`，默认服务命令为：
```bash
python src/codex_token_report.py serve --host 0.0.0.0 --port 8000 --db-file /data/token-account.db
```

启动：
```bash
docker compose up -d --build
```

默认将本地 `./data` 挂载到容器 `/data`，用于持久化 SQLite 数据。
