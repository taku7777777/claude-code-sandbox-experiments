# P11-b: `allow mcp__server__tool` はそのツールだけ事前承認(兄弟ツールは ask のまま)

## 目的

- ツール名リテラル形 allow の**粒度**を確定する: 1 ツール単位の allowlist が組めるか。

## 前提(設定)

```json
{ "permissions": { "allow": ["mcp__probe__read_path"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む(allow 対象)
2. `mcp__probe__net_get` で https://example.com を取得(allow 対象外の兄弟ツール)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path(allow 列挙済み) | allow | ✅ | 番兵返答で ALLOWED 確定(fs-read probe) |
| 2 | net_get(列挙外) | ask | ✅ | allow はツール名完全一致・兄弟に波及しない |

## なぜそうなるか

- MCP の allow 規則は **tool 名の完全一致**。`mcp__probe__read_path` は `mcp__probe__net_get` を含意しない。
  組込ツールの「規則はツール単位」(P2)と同じ評価系。

## 運用時の留意事項

- **最小権限は 1 ツール単位で書ける**。参照系ツールだけを列挙すれば、同サーバの書込系は ask に残る
  (headless では auto-deny = 使われない)。
- ツール名はサーバ実装依存。**init tools 一覧で実名を確認してから書く**(スペルミスは無言の no-op)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/b-allow-tool
python3 harness/run.py -m sdk P11-mcp-tool-rules/b-allow-tool
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1=ALLOWED / 2=headless DENIED(auto-deny)・sdk ASK) |

## 対応する知識

- グループ [P11 README](../README.md) / c(サーバ形)/ h(広 allow + 狭 deny)/ P2(規則はツール単位)

