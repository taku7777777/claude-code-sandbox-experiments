# P11-g: サーバ deny の内側にツール allow で穴は開けられない(deny 常勝・P2-e の MCP 版)

## 目的

- 「広 deny + 狭 allow」の向きが MCP でも**彫れない**ことを実測する(彫れる向きは h だけ、の否定側対照)。

## 前提(設定)

```json
{ "permissions": { "deny": ["mcp__probe"], "allow": ["mcp__probe__read_path"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む(allow を書いてある)
2. `mcp__probe__net_get` で https://example.com を取得

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path(allow 併記) | deny | - | allow は無効・サーバごと除去(init の MCP ツールが空) |
| 2 | net_get | deny | - | サーバ deny が全ツールを除去 |

## なぜそうなるか

- 評価順 deny→ask→allow は**ネストを見ない**。サーバ形 deny にマッチした時点で、内側のツール形 allow は
  評価されない。P2-e(deny Bash(*) + allow Bash(echo:*) → echo も拒否)と同型。

## 運用時の留意事項

- 「基本禁止・一部だけ許可」を MCP で書きたい場合、deny を外して **allow 列挙(b)だけ**にする
  (書かなかったものは既定 ask = headless では動かない)。例外を彫れる向きは h(広 allow + 狭 deny)のみ。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/g-deny-server-beats-allow-tool
python3 harness/run.py -m sdk P11-mcp-tool-rules/g-deny-server-beats-allow-tool
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1・2 とも DENIED(除去型・sdk=DENIED_HARD)) |

## 対応する知識

- グループ [P11 README](../README.md) / P2-e(同型の原理)/ h(彫れる向き)

