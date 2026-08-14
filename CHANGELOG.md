# 变更记录

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
