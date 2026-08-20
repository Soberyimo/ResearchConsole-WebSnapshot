# 云见财报 Visualizer

只读展示 GPT 提供的结构化财报数据。正式输入位于：

- `structured_data/financial_records.json`
- `structured_data/financial_records.csv`
- `structured_data/company_manifests/*.json`（公司级展示边界与推荐 slug）

JSON 与 CSV 表达同一批记录；Visualizer 只解析、校验、排序和格式化，不搜索来源、不补数、不判断财年、不执行财经计算。

## 本地验证

```bash
npm run structured:verify
npm run snapshot:build
npm run snapshot:verify
npm run build
npm test
npm run lint
npm run pages:export
npm run pages:verify
```

`snapshot/visualizer_snapshot.json`、`dist/` 和 `github-pages-dist/` 均为可删除重建的派生文件。公开 Pages 成品不携带原始 JSON/CSV。

## 输入边界

- 必填：公司、财报期、指标、值、单位、口径、来源身份、来源、来源位置、状态。
- 支持 `company_disclosed`、`program_calculated`、`management_forward_looking`、`external_research`、`gpt_estimate`、`user_material`。
- `program_calculated` 必须由输入提供公式；Visualizer 不重算。
- `yoy`、`yoy_pp`、`qoq` 只有在输入明确提供时显示。
- `missing` 状态允许空值；其他状态的值必须为数字。
- legacy `record_id`、`evidence_id`、`material_id` 等治理 ID 不进入展示输入。
- 相同 company / period / metric / scope / dimension / basis / unit 的展示 key 不得重复。

## 赛力斯正式输入

赛力斯使用固定路由 `/company/seres`，389 条记录全部来自 GPT / 用户审核输入。页面将财务、上市公司产销快报和乘联会车型销量分区展示；年度、半年、季度、月度按频率独立成序列。最新财务期间只从财务 records 判断。
