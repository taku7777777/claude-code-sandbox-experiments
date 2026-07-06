# P11-a: 規則なしの MCP ツールは既定 ask(headless では auto-deny)

## 目的

- MCP ツールの**既定の許諾**を確定する(以降のサブケース b〜j の参照点)。
- 「MCP を刺しただけで動く/動かない」の切り分け: 規則ゼロでは動かない(fail-closed)ことの実測。

## 前提(設定)

```json
{ "permissions": {} }
```

- MCP fixture: `probe` サーバ(read_path / net_get の 2 ツール。[../mcp-probe-server.mjs](../mcp-probe-server.mjs))。

## 実行内容

1. `mcp__probe__read_path` でケース内の note.txt を読む

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | mcp__probe__read_path(規則なし) | ask | ✅ | 既定 ask(denials 記録・SDK canUseTool 発火) |

## なぜそうなるか

- **MCP ツールは read-only 組込ツールの無条件承認集合(P4-i)に入らない**。規則が無ければモードの既定
  (default=ask)に落ちる。組込の書込系ツール(P1-a)と同じ扱い。

## 運用時の留意事項

- headless/CI で MCP を使うには allow 規則(b/c/d の効く形)が必須。「刺しただけ」では auto-deny で全滅する。
- 逆に言えば、**MCP を刺しても規則を書かなければ勝手には動かない**(安全側の既定)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/a-baseline-ask
python3 harness/run.py -m sdk P11-mcp-tool-rules/a-baseline-ask
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(headless=DENIED(auto-deny) / sdk=ASK(canUseTool 発火)) |

## 対応する知識

- グループ [P11 README](../README.md) / P1-a(組込 Write の既定 ask=同型)/ S1-h(MCP の sandbox 迂回)

