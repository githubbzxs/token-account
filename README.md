# Codex Token Usage Report

Small local tool that reads Codex CLI session logs and generates a visual HTML report.

## Requirements
- Python 3.8+

## Quick start
python src/codex_token_report.py
python src/codex_token_report.py --out report --open

Or just double-click `open-report.bat`.

Report features:
- Chinese/English toggle in the HTML report
- 时间分析模块（核心分析）：按时间维度展示会话分布与活跃趋势
- Estimated cost in USD using OpenAI API pricing (standard tier)
- Default range is all-time, with in-page date range filters (Last 7/30/90, or custom)
- One-click export/import in the report to merge data from multiple machines

## Date filters
python src/codex_token_report.py --days 30
python src/codex_token_report.py --since 2025-12-01 --until 2025-12-31

## Options
--codex-home PATH        Path to .codex directory
--sessions-root PATH     Path to sessions directory
--out PATH               Output directory (default: report)
--days N                 Limit to last N days (only if since/until not set)
--since YYYY-MM-DD       Start date
--until YYYY-MM-DD       End date
--pricing-file PATH      Override pricing json (optional)
--json                   Write data.json alongside report
--open                   Open report in default browser

Report output:
- report/index.html
- report/data.json (optional)

## Pricing
Default USD pricing is embedded from https://platform.openai.com/pricing (standard tier).
Use --pricing-file or edit pricing.json to override. You can also set aliases for
model names not listed in the official table.
