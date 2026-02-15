# Facts
- **[2026-02-15] 测试部署偏好**：默认不在测试 VPS 执行部署与回归，只有用户当次明确要求才执行。
  - Why：当前阶段优先本地快速迭代与反馈速度。
  - Impact：交付说明需明确“本次未做 VPS 验证”。
  - Verify：回复中列出本地验证命令与结果。

# Decisions
- **[2026-02-15] 数据分析增强方向**：从单点指标升级为对比型分析，覆盖效率、峰值集中度、活跃覆盖率、近 7 天趋势和波动性。
  - Why：原分析维度不足，缺少结构化深度判断。
  - Impact：`src/codex_token_report.py` 分析面板与 `applyRangeInternal` 计算逻辑。
- **[2026-02-15] 移除分析模块**：按用户最新要求，前端报告彻底去掉“数据分析”模块及其计算逻辑。
  - Why：用户明确要求不保留任何分析模块。
  - Impact：`src/codex_token_report.py` 模板、样式、i18n 与 `applyRangeInternal`。

# Commands
- `python -m py_compile src/codex_token_report.py`
- `python src/codex_token_report.py --sessions-root dummy_sessions --out report-test`

# Status / Next
- 当前：分析面板已增强并支持范围内实时计算。
- 下一步：如用户仍觉得不够深入，可增加自动结论与建议层。

# Known Issues
- `dummy_sessions/test.jsonl` 是本地未跟踪测试数据文件，默认不纳入提交。
