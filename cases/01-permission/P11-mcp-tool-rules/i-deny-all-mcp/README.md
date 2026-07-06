# P11-i: `deny mcp__*`(bare glob)は deny 側では有効 — 全 MCP ツールを除去するキルスイッチ

## 目的

- deny/ask 側では bare glob `mcp__*` が**全 MCP ツール**にマッチすることを実測する(allow 側 e との非対称)。

## 前提(設定)

```json
{ "permissions": { "deny": ["mcp__*"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む(MCP が全滅している想定下)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path | deny | - | init tools に MCP ツールが 1 つも無い(全除去) |

## なぜそうなるか

- docs: 「deny と ask 規則はツール名位置の glob パターンを受け付ける。`mcp__*` は**全サーバの全 MCP
  ツール**にマッチ」。allow 側(e=無効)と対照的に、締める側は全域 glob が書ける。

## 運用時の留意事項

- **「MCP を一切使わせない」が 1 行で書ける**。deny はスコープ横断で常勝(P7-a)なので、user/managed
  スコープに置けば project 側の `.mcp.json` や allow では覆せない=組織のキルスイッチとして機能する。
- 全面禁止でなく選別なら: サーバ選定(刺すかどうか)→ h の形(サーバ allow + 危険ツール deny)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/i-deny-all-mcp
python3 harness/run.py -m sdk P11-mcp-tool-rules/i-deny-all-mcp
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(DENIED(除去型・init の MCP ツール空・sdk=DENIED_HARD)) |

## 対応する知識

- グループ [P11 README](../README.md)(e⇔i 非対称表)/ P7-a(deny のスコープ横断常勝)

