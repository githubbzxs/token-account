# Codex Token Usage Report

本项目用于读取 Codex CLI 会话日志并生成可视化报告。当前架构为：
- Python 负责聚合日志并写出 `data.json`
- React 前端负责渲染交互页面（范围切换、动画图表、导入导出等）

## 依赖
- Python 3.8+
- Node.js 18+

## 前端初始化（首次）
```bash
cd web
npm install
npm run build
```

## 生成报告
```bash
python src/codex_token_report.py --out report
python src/codex_token_report.py --out report --open
```

说明：
- 默认会从 `web/dist` 复制前端构建产物到 `report/`
- 同时写入 `report/data.json`
- 若 `web/dist` 不存在，命令会报错并提示先构建前端
- `--open` 会优先通过本地 `http://127.0.0.1:8765` 打开，避免 `file://` 直开导致白屏

## 常用参数
- `--codex-home PATH`：`.codex` 目录路径
- `--sessions-root PATH`：`sessions` 目录路径
- `--out PATH`：输出目录（默认 `report`）
- `--frontend-dist PATH`：前端构建目录（默认 `web/dist`）
- `--days N`：最近 N 天（仅在未设置 `--since/--until` 时生效）
- `--since YYYY-MM-DD`：起始日期
- `--until YYYY-MM-DD`：结束日期
- `--pricing-file PATH`：覆盖定价文件（可选）
- `--open`：生成后用默认浏览器打开报告

## 输出文件
- `report/index.html`
- `report/data.json`

## 本地开发前端
```bash
cd web
npm run dev
```

开发环境中前端会请求同目录 `data.json`。如需联调，可先执行一次 Python 生成命令，或手动放置测试数据文件。
