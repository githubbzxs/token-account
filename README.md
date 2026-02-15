# Codex Token Usage Report

本地工具：读取 Codex CLI 会话日志并生成可视化 HTML 报告。

## 依赖
- Python 3.8+

## 快速开始
python src/codex_token_report.py
python src/codex_token_report.py --out report --open

或直接双击 `open-report.bat`。

## 报告功能
- 报告页面中英双语切换
- 时间分布分析（按小时聚合）
- 输入/输出时长估算（输入 240 tok/min，输出 120 tok/min）
- 基于 OpenAI API 定价的美元成本估算（标准档）
- 默认展示全量范围，支持页面内日期筛选（近 7/30/90 天与自定义）
- 一键导出/导入，支持多机器数据合并

## 日期筛选
python src/codex_token_report.py --days 30
python src/codex_token_report.py --since 2025-12-01 --until 2025-12-31

## 参数
--codex-home PATH        .codex 目录路径
--sessions-root PATH     sessions 目录路径
--out PATH               输出目录（默认：report）
--days N                 最近 N 天（仅在未设置 since/until 时生效）
--since YYYY-MM-DD       起始日期
--until YYYY-MM-DD       结束日期
--pricing-file PATH      覆盖定价文件（可选）
--json                   同时写出 data.json
--open                   用默认浏览器打开报告

## 输出文件
- report/index.html
- report/data.json（可选）

## 定价
默认内置定价来源：https://platform.openai.com/pricing （standard tier）。
可通过 `--pricing-file` 或编辑 `pricing.json` 覆盖，也可为未列出的模型配置别名。
