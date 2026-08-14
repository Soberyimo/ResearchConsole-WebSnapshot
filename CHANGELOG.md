# 变更记录

## [Unreleased]

- 后续迭代使用 `agent/vX.Y.Z-主题` 分支。
- 静态资源只从 `master` 打包和部署。

## [Web Snapshot v0.1] - 2026-08-14

### Added

- 从冻结的 Research Console v0.1.3 派生只读 Web Snapshot。
- 首页、公司页、8Q 趋势图、研究结论、管理层表态、研究缺口、来源与证据和数据覆盖。
- 桌面与手机响应式交互。
- Snapshot Contract、来源哈希、freshness 和 fail-closed 校验。

### Validation

- Snapshot 定向测试：4/4。
- ResearchOS production mutation：NO。

### Hosting

- 源码与派生数据分离。
- GitHub `master` 为未来静态打包唯一来源。

