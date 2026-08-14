# Research Console Web Snapshot

Research Console v0.1.3 的独立、只读 Web Snapshot 源码。

本仓库只保存前端、导出器、Snapshot Contract 和测试，不保存运行时生成的正式研究 Snapshot。ResearchOS production 仍是唯一事实源和唯一写入方。

公开导出只接受当前 canonical output，且每个 output 都必须存在与 canonical、revision、accepted SHA 和 findings SHA 完整绑定的 active `publishable` 决定；授权缺失或失效时会 fail closed。

## 架构

```text
Local ResearchOS production
  → fail-closed snapshot export
  → derived / non-authoritative JSON
  → static GitHub Pages artifact
  → browser / mobile
```

Snapshot 不调用 AI 重新生成研究结论，不读取 Dry Run、staging 或 candidate 替代 canonical，也不能写回 ResearchOS。

## 本地目录要求

```text
ResearchOS/
  00_系统/ResearchConsole_v0.1/
  01_财报日历/
  04_公司数据库/
  05_研究结果/
  11_ResearchConsole_WebSnapshot/   ← 本仓库
```

## 本地验证

```bash
npm install
npm run snapshot:export
npm run snapshot:verify
npm run build
npm test
npm run lint
```

## 生成 GitHub Pages 静态包

```bash
npm run pages:export
npm run pages:verify
```

成品位于 `github-pages-dist/`，包含首页、Qualcomm、XPeng 和必要 CSS / JavaScript。公开成品不部署原始 `snapshot/research_snapshot.json`，也不依赖 Vinext/Next 服务端运行时。

## 分支与部署

- `master` 是唯一稳定分支，也是静态资源打包和部署来源。
- 每次迭代从 `master` 创建 `agent/vX.Y.Z-主题`。
- 测试和审计通过后，以 Pull Request 合并回 `master`。
- 新 Snapshot 只有显式导出并重新提交 Pages `master` 后才更新线上版本。

## 数据边界

- ResearchOS production 是唯一事实源和唯一写入方。
- Snapshot 生成不会修改 production。
- 本地修改不会自动改变线上站点。
- 未获得正式 `publishable` 决定的 canonical output 不会进入公开包。
- `snapshot/research_snapshot.json` 是可删除重建的运行时派生文件，不进入源码仓库。

完整合同见 `SNAPSHOT_CONTRACT.md`。

## 在线地址

<https://soberyimo.github.io/>
