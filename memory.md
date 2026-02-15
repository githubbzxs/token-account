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
- **[2026-02-15] 主题切换动效恢复**：为主题切换增加显式 `theme-switching` 动画层，并补上主题按钮 `is-bronze` 状态过渡；保留 `prefers-reduced-motion` 下的无动画退化。
  - Why：用户反馈“两种主题切换的动效”缺失，变量替换在渐变场景下观感接近瞬切。
  - Impact：`src/codex_token_report.py` 的 `html.theme-ready` 过渡范围、`themeSwap` 关键帧、`playThemeSwitchMotion`、`applyTheme` 与 `.theme-dot-toggle.is-bronze`。
  - Verify：本地 `report-test/index.html` 与香港测试 VPS `/root/token-account/report-vps/index.html` 均可检索到 `theme-switching`、`@keyframes themeSwap`、`playThemeSwitchMotion`。
- **[2026-02-15] 主图视觉改为面积图风格**：将主图由“线条主导”调整为“面积主导”，弱化线宽并提升填充层层次（平滑 0.46、线宽 1.4、面积分层停靠点 0.38/0.62）。
  - Why：用户要求“图表改为面积图”。
  - Impact：`src/codex_token_report.py` 的 `lineChart` 系列样式参数（`smooth`、`lineStyle`、`areaStyle`）。
  - Verify：本地 `report-test/index.html` 与香港测试 VPS `/root/token-account/report-vps/index.html` 均可检索到 `smooth: 0.46`、`width: 1.4`、`offset: 0.38/0.62`。
- **[2026-02-15] 动态文本动效统一为纯透明过渡**：将动态文本动画统一为 `opacity-only`，时长 `360ms`，移除位移动效与强制重排触发，覆盖指标数值、范围标签、日历标题、导入状态与 i18n 动态文案。
  - Why：用户反馈“动画太生硬”，并明确选择“仅透明过渡 + 全站动态文本统一 + 360ms”。
  - Impact：`src/codex_token_report.py` 的 `.metric-value-anim`、`.i18n-switch-anim`、`@keyframes textFadeOnly`、`triggerSwapAnimation`、`setAnimatedText`、`applyI18n`、`updateRangeDateButton`、`renderCalendarDays`、`setupImportExport`。
  - Verify：本地 `report-test/index.html` 与香港测试 VPS `/root/token-account/report-vps/index.html` 均可检索到 `animation: textFadeOnly 360ms` 与 `setAnimatedText(...)`。
- **[2026-02-15] 数字动效统一为单段轻量动画**：`setDisplayText` 覆盖点统一改为“轻微位移淡入”，移除原“淡出+淡入”双阶段与定时器链路，并将范围文本纳入同一动效入口。
  - Why：用户要求“统一数字变化动效，并稍微简单一点”。
  - Impact：`src/codex_token_report.py` 的 `.metric-value-anim`、`@keyframes metricFade`、`animateMetricValue`、`applyRangeInternal`。
  - Verify：首次加载、切换范围、自动刷新时，指标与范围文本均为同款轻量淡入；开启减少动态效果后不播放动画。
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
- **[2026-02-15] 报表可读性修复**：恢复胶囊切换动效，指标统一 `K/M/B` 大写缩写，X 轴改为智能简化显示，并平滑底部背景过渡。
  - Why：用户反馈胶囊切换缺少动画、数值与 X 轴信息过密、页面底部存在明显分界线。
  - Impact：`src/codex_token_report.py` 的 `prefers-reduced-motion` 覆盖策略、数值格式函数、X 轴标签格式化和 `body` 背景渐变。
  - Verify：切换快捷范围时滑块有过渡；图表与卡片均显示 `K/M/B`；短区间显示 `HH:mm`、长区间显示 `MM-DD`；底部无明显断层。
- **[2026-02-15] 快捷范围改为缩写并统一控件宽度**：时间切换胶囊改为 `1D/2D/1W/1M/3M/ALL`，并与左侧日期选择器保持同宽。
  - Why：用户希望范围切换更紧凑，且左右控件视觉对齐。
  - Impact：`src/codex_token_report.py` 的 i18n 快捷范围文案、范围控件 CSS 栅格与宽度变量、模板默认按钮文本。
  - Verify：生成 `report-test/index.html` 后，快捷按钮显示缩写，`range-date-trigger` 与 `quick-range-segmented` 宽度一致。
- **[2026-02-15] 范围控件高度与动效修正**：左右控件改为同高度（上下齐平），快捷范围点击先触发滑块视觉切换再执行筛选，恢复动效体感。
  - Why：用户反馈“等宽”需求实际为上下视觉一致，且滑块动效不明显。
  - Impact：`src/codex_token_report.py` 的范围控件高度样式、`setQuickRangeActive` 与 `setupRangeControls` 点击流程。
  - Verify：`report-test/index.html` 中两侧控件共享 `--range-selector-height`，点击快捷范围时滑块先移动再更新数据。
- **[2026-02-15] 范围控件中度收紧并修复滑块过渡覆盖**：范围控件高度降为 `40px`，外框间距同步收紧；移除 `theme-ready` 对滑块过渡的覆盖并改为更慢更丝滑的缓动。
  - Why：用户反馈控件“太粗”且快捷范围胶囊“没有动效”。
  - Impact：`src/codex_token_report.py` 样式模板中的范围控件尺寸参数与 `.range-segmented-slider` 过渡策略。
  - Verify：本地生成 `report-test/index.html` 后包含 `--range-selector-height: 40px` 与 `transform 0.66s`；大陆测试 VPS 的 `report/index.html` 同步更新并可检索到相同参数。
- **[2026-02-15] 范围控件精细对齐修复**：将控件高度进一步收紧到 `36px`，提升文字占比，并把快捷滑块定位改为 `offsetLeft/offsetWidth` 同坐标系。
  - Why：用户反馈存在 `1D` 选中态未对齐、范围条偏厚、日期文本面积占比偏低。
  - Impact：`src/codex_token_report.py` 的 `.range-controls`、`.range-date-trigger`、`#range-date-label`、`.range-segmented-slider`、`.range-segmented button` 与 `updateQuickRangeSlider()`。
  - Verify：本地 `report-test/index.html` 与香港测试 VPS `/root/token-account/report-vps/index.html` 均可检索到 `--range-selector-height: 36px`、`left: 0`、`offsetLeft`、`offsetWidth`。

# Commands
- `python -m py_compile src/codex_token_report.py`
- `python src/codex_token_report.py --sessions-root dummy_sessions --out report-test`
- `python3 -m py_compile src/codex_token_report.py`（香港测试 VPS）
- `python3 src/codex_token_report.py --out report-vps`（香港测试 VPS）

# Status / Next
- 当前：动态文本动效已统一为 `opacity-only 360ms`，并在本地与香港测试 VPS 重新生成报告验证通过。
- 下一步：如需继续微调，可基于真实使用频率把时长从 `360ms` 下调到 `280ms`（仅参数调整，无需改逻辑）。

# Known Issues
- `dummy_sessions/test.jsonl` 是本地未跟踪测试数据文件，默认不纳入提交。
- 香港测试 VPS 环境无 `python`/`rg` 命令别名，需使用 `python3` 与 `grep`。
