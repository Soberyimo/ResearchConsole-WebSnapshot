# 变更记录

## [Seres production launch] - 2026-08-20

- 合并 389 条 GPT / 用户已审核赛力斯记录，静态数据总量增至 751 条、7 家公司。
- 新增正式路由 `/company/seres`，最新财务期间为输入中的 `2026Q1`。
- 赛力斯页拆分财务、上市公司产销快报和乘联会问界车型销量三个数据区。
- 年度、半年、季度、月度序列独立展示；Visualizer 不执行差分、同比、毛利率或跨口径补差。
- 保留 A 股财务口径、2024 质保成本重分类及两类销量不可混算说明。

## [Visualizer static-input cutover] - 2026-08-20

- 新增 GPT 风格 JSON/CSV 输入、schema-lite validator 和 deterministic Visualizer snapshot。
- 迁移 362 条历史财务记录；12 条 program-calculated 记录公式复核通过。
- 首页与公司页切换到静态结构化数据；同比/环比仅显示输入值。
- 移除财报预报路由、M1/M2/M3 Excel 导出器及相关前端测试/规则文件。
- GitHub Pages 改为只发布 Visualizer HTML，不发布原始结构化数据。

## [Data Platform Slimdown] - 2026-08-16

### Changed

- 一级功能收缩为“财报预报”和“公司 / 财报数据”。
- 公司页只保留财务趋势、历史表格、同比环比、口径、来源与数据覆盖。
- 新增只读财报预报路由，展示即将发布、已发布、时间、状态和来源。

### Removed

- 研究结论、管理层表态、研究缺口、研究身份与研究发布状态的前端展示。

### Data Safety

- ResearchOS production mutation：NO。
- 后端、API、数据库、M1/M2/M3 与 Briefing OS：未修改。

## [Public GitHub Pages Snapshot] - 2026-08-14

### Added

- 正式 publication decision Gate 校验。
- GitHub Pages 的框架无关静态导出器。
- 静态包完整性、visibility 与运行时泄漏检查。

### Changed

- Snapshot access intent 调整为 `public_github_pages`。
- 已正式授权的 Qualcomm 与 XPeng 显示为“公开研究 / publishable”。
- 页面身份调整为“公开快照 · 只读”。

### Validation

- Snapshot tests：4/4。
- Build：PASS。
- GitHub Pages artifact verify：PASS。
- 1440×1000 与 390×844 真浏览器检查：PASS。

## [Private Preview Snapshot] - 2026-08-14

### Added

- 从冻结的 Research Console v0.1.3 派生只读 Web Snapshot。
- 首页、公司页、8Q 趋势图、研究结论、管理层表态、研究缺口、来源与证据和数据覆盖。
- 桌面与手机响应式交互。
- Snapshot Contract、来源哈希、freshness 和 fail-closed 校验。

### Validation

- Snapshot 定向测试：4/4。
- ResearchOS production mutation：NO。
