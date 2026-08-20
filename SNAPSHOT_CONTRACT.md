# Visualizer Snapshot Contract v1

- Source：`structured_data/*.json|csv`。
- Snapshot：`snapshot/visualizer_snapshot.json`，仅供构建与渲染。
- Parser 允许 JSON/CSV parse、schema-lite validation、sorting、filtering 与 display formatting。
- 公司级 `structured_data/company_manifests/*.json` 只提供推荐 slug、分区名称和输入口径说明。
- Parser 禁止自动同比/环比、单位换算、财年判断、重述处理、缺失值补全或外部搜索。
- Snapshot 必须标记 `authoritative=false`、`production_mutation=false`。
- 浏览器页面不得暴露 legacy record/evidence/material ID 或 ResearchOS runtime 状态。
- 原始结构化输入与 Snapshot 均不得复制到公开 Pages 成品。
- 不同 period frequency 必须独立成序列；不得把月度、季度、半年和年度机械连线。
- 公司卡片的最新财务期必须仅由财务 records 决定，不能用销量或外部研究的最大 period 替代。

生成与验证：

```bash
npm run structured:verify
npm run snapshot:build
npm run snapshot:verify
npm run build
npm test
```
