# P11-c: `allow mcp__server`(サーバ形)は同サーバの全ツールを事前承認

## 目的

- サーバ名だけの allow が**全ツールへ波及**することを実測する(docs CONFIRMED の実効確認)。

## 前提(設定)

```json
{ "permissions": { "allow": ["mcp__probe"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む
2. `mcp__probe__net_get` で https://example.com を取得

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path | allow | ✅ | サーバ形が波及 |
| 2 | net_get | allow | ✅ | 同上(2 ツールとも無プロンプト) |

## なぜそうなるか

- docs: 「`mcp__puppeteer` は puppeteer サーバが提供する**任意の**ツールにマッチ」。サーバ形は
  そのサーバの全ツールの事前承認になる。

## 運用時の留意事項

- 便利だが**将来そのサーバに追加されるツールまで自動で開く**。サーバのツールセットを管理できない場合は
  b(ツール列挙)か h(サーバ allow + 危険ツール deny)に倒す。
- サーバ形で開けても **MCP サーバ自体はホスト直実行**(S1-h)。開ける相手は「信頼するサーバ」だけ。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/c-allow-server
python3 harness/run.py -m sdk P11-mcp-tool-rules/c-allow-server
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1・2 とも ALLOWED) |

## 対応する知識

- グループ [P11 README](../README.md) / b(ツール形との対)/ S1-h(サーバはホスト直実行)

