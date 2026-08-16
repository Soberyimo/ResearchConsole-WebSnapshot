# 前端瘦身机械审计

审计日期：2026-08-16

## KEEP_DATA_PLATFORM

- `app/page.tsx`：公司入口与数据概览。
- `app/earnings/page.tsx`：财报预报、即将发布、已发布、时间、状态和来源。
- `app/company/[companyId]/page.tsx`：财务与运营趋势、历史表格、同比环比、单位、币种、程序计算和数据覆盖；不再提供单独的“来源与口径”页面。
- `public/snapshot-app.js`：财务趋势图交互。
- `public/snapshot-styles.css`、`public/snapshot-polish.css`、`app/globals.css`：共享布局与数据展示样式。

## REMOVE_RESEARCH

- 首页最近研究更新、研究数量、研究身份和“查看研究”入口。
- 公司页研究结论、管理层表态、研究缺口 Tab 与 Panel。
- 一句话判断、关键发现、风险、反向解释、研究问题、选题与图表建议。
- `research_output_id`、`finding_id`、`statement_id`、M4 canonical/publication 状态等研究型界面字段。
- 原有仅验证研究模块存在的前端测试断言。

## SHARED_OR_UNCERTAIN

- `00_系统/ResearchConsole_v0.1/static/`：属于旧本地 Console 的共享静态资产，工作区已有用户改动，本轮不覆盖。
- `public/snapshot-styles.css` 与 `public/snapshot-polish.css` 中未被数据页面调用的旧选择器暂时保留，避免为样式清理扩大重构范围；生成后的 HTML、导航和路由不再引用研究模块。
- `scripts/export_snapshot.py` 仅在前端构建时只读正式表格，未修改 API、数据库或后端。

## BACKEND_CLEANUP_REQUIRED

- `01_财报日历/财报日历.xlsx` 的 `财报日历` 工作表缺少吉利汽车 `2026H1` 事件。前端暂由 `frontend_data/earnings_calendar_supplements.json` 根据吉利汽车 2026-07-10《DATE OF BOARD MEETING》官方公告补充 `2026-08-17`，未写入或修改正式日历。M1 后续应按标准流程补录，补录后前端会以正式日历为优先并自动忽略同公司同财报期的补充事件。
- M4、管理层表态和历史研究数据的物理清理由后端任务另行决定，不影响本轮前端瘦身，也未在本轮删除。

## BUILD_GATES

- 财报预报覆盖：每家已有公司数据的关注公司必须有一条日期未过期的“下一次财报事件”，或在 `frontend_data/calendar_coverage_reviews.json` 中有一条最长 7 天、带来源和到期日的 `needs_m1_review` 记录；否则快照生成和校验失败。
- 事件时效：未发布事件的日期早于当前日期时，快照生成和校验失败，必须更新为已发布、补充实际时间或重新核查。
- 前端补充让位：正式日历存在相同 `company_id + 财报期` 时，前端补充自动忽略，避免重复事件。
- 趋势指标唯一性：每家公司页面的 `series_id` 和最终显示名称必须唯一；同一基础指标存在多个序列时，名称必须同时显示期间类型和口径，仍重名时追加实际覆盖期间。
- 输入防陈旧：正式 Excel/Registry 或两个 `frontend_data` 规则文件发生变化后，旧快照校验失败，必须重新导出后才能发布。
