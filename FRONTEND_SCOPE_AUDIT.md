# Visualizer 前端范围审计

审计日期：2026-08-20

## 正式保留

- `structured_data/`：GPT 风格 JSON/CSV、公司级 manifest 与一次性 legacy migration manifest。
- `scripts/structured_data.py`：JSON/CSV schema-lite validator/parser。
- `scripts/build_visualizer_snapshot.py`：纯展示分组、排序与 HTML/page-data 构建。
- `app/page.tsx`、`app/company/[companyId]/page.tsx`：公司入口、指标表格和历史趋势。
- `public/snapshot-app.js`：浏览器图表交互，只读取输入值。
- `scripts/export_github_pages.py`：静态 Pages 构建和泄漏校验。

## 已退出前端

- 财报预报路由与 M1 日历输入。
- ResearchOS Excel/Registry 读取器。
- 前端自动同比/环比计算。
- Research Console、M4、管理层表态与研究 UI。
- legacy record/evidence/material ID 展示。

## 首次正式 GPT 输入上线

- 赛力斯 389 条 `verified` records 已无损合并；原 362 条记录继续存在。
- `/company/seres` 按财务、公司销量、问界车型销量分区。
- period frequency 在序列身份中独立保存，月度不与季度 / 半年 / 年度机械连线。
- 页面只显示输入中的 formula、同比与口径说明，不重新执行财经计算。

## 更高层约束残留

根仓库的 M1/M2/M3、正式材料、records/evidence、Data API 与 Formal Apply 仍受当前会话上级 `AGENTS.md` 保护；本次前端不再依赖它们，但不能在本任务中物理删除。
