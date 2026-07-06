# P11-h: 広 allow(サーバ)+ 狭 deny(ツール)は成立 — 「参照系だけ残す MCP」の正解形

## 目的

- MCP 最小権限の**実運用形**を実測で裏づける: サーバを allow で開け、危険ツールを deny で塞ぐ。

## 前提(設定)

```json
{ "permissions": { "allow": ["mcp__probe"], "deny": ["mcp__probe__read_path"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む(deny 対象)
2. `mcp__probe__net_get` で https://example.com を取得(allow 側に残る)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path(狭 deny) | deny | - | 除去型(init tools から消える) |
| 2 | net_get(広 allow) | allow | ✅ | deny 対象外は事前承認のまま |

## なぜそうなるか

- 「広 allow + 狭 deny」は評価順(deny が先)と整合する唯一の彫れる向き。P4-a(`Bash(*)` allow +
  `Bash(curl:*)` deny)と同型が MCP 次元でも成立する。

## 運用時の留意事項

- **researcher 型ロールの「Slack/Notion は参照のみ」はこの形で書く**:
  `allow: ["mcp__slack"]` + `deny: ["mcp__slack__post_message", ...]`。
  deny は全モード・全スコープで生存(P2-c/d / P7-a)し、subagent にも継承される(P8-b)。
- ただし deny は**ツール名の列挙**なので、サーバの**ツール追加**で書込系が増えると穴になる。
  サービス側の read-only トークンを土台にし、この規則は縦深の 2 層目として使う

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/h-allow-server-deny-tool
python3 harness/run.py -m sdk P11-mcp-tool-rules/h-allow-server-deny-tool
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1=DENIED(除去型・sdk=DENIED_HARD) / 2=ALLOWED) |

## 対応する知識

- グループ [P11 README](../README.md) / P4-a(同じ向きの組込版)/ g(彫れない向きとの対)/ S1-h(規則の前にサーバ選定)

