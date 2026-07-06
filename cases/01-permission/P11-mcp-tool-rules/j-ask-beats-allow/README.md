# P11-j: `ask mcp__server__tool` は同居する広い allow に勝つ — MCP の確認ゲートが成立(ツールは残存)

## 目的

- ask 規則が MCP ツールでも allow に勝つこと(評価順 deny→ask→allow の真ん中)を実測する。
- 「特定の MCP ツールだけ人間確認」(外部書込の確認ゲート)の機構的裏づけ。

## 前提(設定)

```json
{ "permissions": { "allow": ["mcp__probe"], "ask": ["mcp__probe__net_get"] } }
```

## 実行内容

1. `mcp__probe__net_get` で https://example.com を取得(ask 対象。サーバ allow に含まれる)
2. `mcp__probe__read_path` で note.txt を読む(allow 側対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | net_get(ask 規則) | ask | ✅ | allow 同居でも ask 勝ち。ツールは**残存**(除去でない)・denials に記録 |
| 2 | read_path(allow のみ) | allow | ✅ | ask 対象外は事前承認のまま |

## なぜそうなるか

- 評価順は deny → **ask** → allow(P6-b)。同一ツールに ask と allow(サーバ形経由)が同居すると ask が
  先にマッチしてプロンプトになる。deny(f)と違いツールセットには残り、承認すれば実行できる。

## 運用時の留意事項

- **「Slack 返信は毎回確認」は `allow: ["mcp__slack"]` + `ask: ["mcp__slack__post_message"]` で書ける**
  (対話=承認プロンプト / headless=auto-deny で安全側)。除去型 deny と違い denials に試行が記録されるため、
  **監査可能な塞ぎ方**でもある。
- ask 規則は bypassPermissions でも残る(P6-d)が、**dontAsk では即 deny に化ける**(P6-e)。ロールの
  実行モードと組み合わせて挙動を確認してから使う。引数(チャンネル等)単位の条件は書けない
  (→ hook / canUseTool で構造化引数を検査)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/j-ask-beats-allow
python3 harness/run.py -m sdk P11-mcp-tool-rules/j-ask-beats-allow
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1=headless DENIED(auto-deny)・sdk ASK(canUseTool=mcp__probe__net_get 発火) / 2=ALLOWED) |

## 対応する知識

- グループ [P11 README](../README.md) / P6-b(ask>allow の組込版)/ P6-d/e(モードとの交差)/ S4-f(content-scoped ask の同系)

