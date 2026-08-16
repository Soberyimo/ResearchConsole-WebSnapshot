# 财报数据平台 Web Snapshot Contract v0.1

本目录是 ResearchOS 的独立、派生、只读 Web Snapshot。

- 浏览器数据仅包含财报日历、公司财务序列、财务来源 lineage 和数据覆盖。
- 浏览器数据不得包含研究结论、管理层表态分析、研究缺口或研究结果身份。
- Snapshot 标记为 `derived=true`、`authoritative=false`、`production_mutation=false`。
- Snapshot 不提供 API、表单、上传、编辑、评论或任何写回 ResearchOS 的连接。
- 正式财报日历和财务历史数据库是只读来源；导出失败时不得使用猜测值补齐。
- `snapshot/data_platform_snapshot.json` 不得部署到公开成品。

生成与验证：

```bash
npm run snapshot:export
npm run snapshot:verify
npm run build
npm test
```
