# Research Console Web Snapshot

云见财报 ResearchOS 的独立、只读 Web Snapshot 源码。

本仓库只保存前端、导出器、Snapshot Contract 和测试，不保存运行时生成的正式研究 Snapshot。ResearchOS production 仍是唯一事实源和唯一写入方。

## 架构

```text
Local ResearchOS production
  → fail-closed snapshot export
  → derived / non-authoritative JSON
  → static Web Snapshot
  → browser / mobile
```

Snapshot 不调用 AI 重新生成研究结论，不读取 Dry Run、staging 或 candidate 替代 canonical，也不能写回 ResearchOS。

## 本地目录要求

导出器按 ResearchOS 原项目结构运行：

```text
ResearchOS/
  00_系统/ResearchConsole_v0.1/
  01_财报日历/
  04_公司数据库/
  05_研究结果/
  11_ResearchConsole_WebSnapshot/   ← 本仓库
```

## 快速开始

```bash
npm install
npm run snapshot:export
npm run snapshot:verify
npm test
npm run build
```

本地开发：

```bash
npm run dev
```

## 分支与部署

- `master`：唯一稳定分支，也是静态资源打包和部署来源。
- 每次迭代：从 `master` 创建 `agent/vX.Y.Z-主题`。
- 通过测试和审计后，以 Pull Request 合并回 `master`。
- 迭代分支不得覆盖正式线上 Snapshot。
- 新 Snapshot 只有显式导出并从 `master` 重新部署后才更新线上版本。

## 数据边界

`snapshot/research_snapshot.json` 是派生运行时文件，不进入源码仓库。它必须：

- 由当前正式 production truth source 生成；
- 带有 source hash、generated_at 和 derived 标识；
- canonical pointer、hash、lineage 或 visibility 不明确时 fail closed；
- 可删除并重建，不能成为新的事实源。

完整合同见 `SNAPSHOT_CONTRACT.md`。

## 验证

```bash
npm run snapshot:verify
npm test
npm run build
```

测试至少验证首页、Qualcomm、XPeng、canonical-only、fail-closed 和静态交互。

## 迭代记录

每次更新同步维护 `CHANGELOG.md`，至少记录：目标、修改文件、测试结果、production mutation、protected semantic diff、部署 URL 和 blocker。

