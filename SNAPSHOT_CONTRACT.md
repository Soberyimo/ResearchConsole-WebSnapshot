# Research Console Web Snapshot Contract v0.1

本目录是 Research Console v0.1.3 的独立、派生、只读 Web Snapshot。

- 唯一输入是 ResearchOS production truth source；读取与验证复用冻结的 Console v0.1.3。
- canonical pointer、accepted output、immutable snapshot、finding lineage、正式材料 SHA 与 visibility 任一校验失败时，导出失败。
- 不读取 staging、Dry Run 或 candidate；不调用 AI；不生成新的研究判断、finding 或 missing_data。
- Snapshot 标记为 `derived=true`、`authoritative=false`、`production_mutation=false`。
- Snapshot 不提供 API、表单、上传、编辑、评论或任何写回 ResearchOS 的连接。
- 线上内容只在显式重新导出、构建和部署后变化；本地文件变化不会自动影响已部署版本。
- `internal_only` 内容只能部署到经过 Sites 验证的 owner-only Private Preview。若无法验证该访问模式，必须停止部署。

生成：

```bash
npm run snapshot:export
```

验证：

```bash
npm run snapshot:verify
npm run build
npm test
```
