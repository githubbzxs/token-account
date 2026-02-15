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
- **[2026-02-15] 时间分析改为分布口径**：按用户反馈移除会话时长占比逻辑，改为“输入/输出时长估算 + 小时分布分析”。
  - Why：用户认为旧估算不可信，要求改为估算输入/输出并聚焦时间分布。
  - Impact：`src/codex_token_report.py` 时间面板文案与 `renderTimeAnalysis` 计算逻辑。
  - Verify：页面展示输入/输出估算时长、输入/输出高峰时段、工作时段/夜间占比、Top3 集中度与活跃小时覆盖率。
- **[2026-02-15] 再次移除时间分析模块**：按用户最新指令，报告页去掉“时间相关分析”面板及其前端计算逻辑。
  - Why：用户明确要求“去掉时间分析”。
  - Impact：`src/codex_token_report.py` 的 i18n、样式、模板与 `applyRangeInternal` 流程；`README.md` 功能说明。
  - Verify：报告页不再出现时间分析卡片，筛选区间更新时无时间分析相关渲染调用。
- **[2026-02-15] 范围筛选交互重构**：改为自定义深色日历弹层，移除浏览器原生日期面板，默认全局英文。
  - Why：用户要求日历与页面 UI 风格统一，并统一英文界面。
  - Impact：`src/codex_token_report.py` 的范围输入控件、日历样式与语言初始化逻辑。
  - Verify：范围输入点击后打开自定义日历；页面默认英文文案；不再出现原生白底日期控件。
- **[2026-02-15] 图表缩放体验调整**：移除底部 dataZoom 滑块，滚轮缩放始终以鼠标位置为中心，无 Ctrl 依赖。
  - Why：用户要求去除底部缩放条，并简化缩放为“指哪放哪”。
  - Impact：`src/codex_token_report.py` 的 `lineChart` 事件处理与 `dataZoom` 配置。
  - Verify：图表下方不再出现缩放条；滚轮缩放围绕当前鼠标位置居中。
- **[2026-02-15] Apple 风格 UI 重构**：按用户给定设计方向重做报告页视觉（深灰玻璃、Bento 卡片、大圆角、Inter + Geist Mono）。
  - Why：用户要求“按照 Gemini 思路修改 UI”，并提升原生 App 观感。
  - Impact：`src/codex_token_report.py` 模板 CSS 色板/字体/卡片样式与范围控件结构。
  - Verify：页面出现深灰玻璃质感卡片、分段控件高亮滑块风格、数字主视觉改为等宽字体。
- **[2026-02-15] 日期筛选改为单胶囊范围选择**：由双输入框改为单日期胶囊按钮 + 双月范围日历面板。
  - Why：用户明确要求“不要把起始和结束分开两个框”。
  - Impact：`src/codex_token_report.py` 的范围输入 DOM、日历状态机与范围应用流程。
  - Verify：点击日期胶囊弹出双月日历，先选开始后选结束，选完自动应用并更新区间文本。
- **[2026-02-15] 图表提示文案下线**：移除页面中 “Scroll to zoom around the pointer; the hovered position stays centered” 显示文案。
  - Why：用户要求去掉该字样。
  - Impact：`src/codex_token_report.py` 图表面板模板与 i18n 的 `zoom_hint` 展示语义。
  - Verify：生成的 `index.html` 页面中不再渲染该提示文本。

# Commands
- `python -m py_compile src/codex_token_report.py`
- `python src/codex_token_report.py --sessions-root dummy_sessions --out report-test`

# Status / Next
- 当前：页面已完成 Apple 风格重构；区间筛选为单胶囊 + 双月范围日历；图表为股票风格 scrubbing 与首尾轴标签。
- 下一步：若需继续贴近 iOS，可补充 segmented 滑块动画与图表浮窗内容的业务字段扩展。

# Known Issues
- `dummy_sessions/test.jsonl` 是本地未跟踪测试数据文件，默认不纳入提交。
