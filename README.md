# 云见财报数据平台 Web Snapshot

ResearchOS 的独立、派生、只读前端，只展示两类一级功能：

- 财报预报：公司、财报期、发布时间、发布状态、即将发布、已发布与来源；
- 公司 / 财报数据：历史财务与运营指标、同比环比、单位、币种、口径、程序计算及来源 lineage。

网页不展示研究结论、管理层表态分析、研究问题、风险、选题、图表建议或其他 M4 研究结果。

## 本地验证

```bash
npm run snapshot:export
npm run snapshot:verify
npm run build
npm test
npm run lint
npm run pages:export
npm run pages:verify
```

生成的 `snapshot/data_platform_snapshot.json` 是可删除重建的前端派生文件，不进入源码仓库，也不部署到公开站点。ResearchOS production 始终是唯一事实源和唯一写入方。

## 数据边界

- 导出、构建和浏览均为只读，不写回 ResearchOS。
- 不修改财报日历、财务历史数据库、正式材料、API 或 M1/M2/M3 流程。
- 精确发布时间只使用正式字段；只有日期时不推测具体时刻。
- 前端导出器直接只读财报日历、财务历史库、指标定义和材料索引，不依赖 M4 canonical、研究发现或管理层表态数据库。
