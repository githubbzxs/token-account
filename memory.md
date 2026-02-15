# Facts
- **[2026-02-15] 测试部署偏好**：默认不在测试 VPS 执行部署与回归，只有用户当次明确要求才执行。
  - Why：当前阶段优先本地快速迭代与反馈速度。
  - Impact：交付说明需明确“本次未做 VPS 验证”。
  - Verify：回复中列出本地验证命令与结果。
- **[2026-02-15] 测试部署规则覆盖更新**：按最新 AGENTS 规则，代码改动后默认需要在测试 VPS 重新部署并回归，此条覆盖旧“默认不部署”约定。
  - Why：项目协作规范已明确“改完代码后必须在测试 VPS 上重新部署”。
  - Impact：后续交付需包含测试 VPS 部署与验证结果。
  - Verify：部署后记录命令与结果。

# Decisions
- **[2026-02-15] 数据分析增强方向**：从单点指标升级为对比型分析，覆盖效率、峰值集中度、活跃覆盖率、近 7 天趋势和波动性。
  - Why：原分析维度不足，缺少结构化深度判断。
  - Impact：`src/codex_token_report.py` 分析面板与 `applyRangeInternal` 计算逻辑。
- **[2026-02-15] 移除分析模块**：按用户最新要求，前端报告彻底去掉“数据分析”模块及其计算逻辑。
  - Why：用户明确要求不保留任何分析模块。
  - Impact：`src/codex_token_report.py` 模板、样式、i18n 与 `applyRangeInternal`。
- **[2026-02-15] 恢复时间分析模块**：分析模块恢复为“时间相关分析”，采用会话窗口法，默认会话切分 15 分钟，并按筛选区间汇总；该决策覆盖“移除分析模块”的旧约定。
  - Why：需求已变更为加回时间相关分析，并统一统计口径。
  - Impact：分析模块定位、会话切分口径与区间汇总规则。
  - Verify：在筛选时间区间内，分析结果按 15 分钟会话窗口汇总展示。

# Commands
- `python -m py_compile src/codex_token_report.py`
- `python src/codex_token_report.py --sessions-root dummy_sessions --out report-test`

# Status / Next
- 当前：需求已切换为恢复时间分析模块，文档与记忆已同步。
- 下一步：等待实现代理完成代码并在测试 VPS 部署回归。

# Known Issues
- `dummy_sessions/test.jsonl` 是本地未跟踪测试数据文件，默认不纳入提交。
