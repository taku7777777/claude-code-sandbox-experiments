# P11-d: `allow mcp__server__*`(サーバ後の glob)は有効(サーバ形と等価に全ツール承認)

## 目的

- allow 側 glob の**効く形**を確定する: リテラルなサーバ接頭辞の後ろの `*` は機能するか(e の bare glob との対)。

## 前提(設定)

```json
{ "permissions": { "allow": ["mcp__probe__*"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む
2. `mcp__probe__net_get` で https://example.com を取得

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path | allow | ✅ | glob がマッチ |
| 2 | net_get | allow | ✅ | 同上(c と等価の範囲) |

## なぜそうなるか

- docs: 「allow 規則の glob はリテラルな `mcp__<server>__` 接頭辞の後ろでのみ受け付ける。
  `mcp__puppeteer__*` は puppeteer サーバの全ツールにマッチ」— その実効確認。
- S1-h 時点ではツール名を 2 本列挙していた(glob の効きは未分離)。本ケースで glob 単独の効きを確定。

## 運用時の留意事項

- docs 上は**部分 glob**(`mcp__github__get_*` = get_ 系だけ)も書ける。参照系ツールが命名規約を持つ
  サーバなら「参照だけ開ける」を 1 行で書ける(本ケースは全域 `*` のみ実測。部分 glob は未実測)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/d-allow-tool-glob
python3 harness/run.py -m sdk P11-mcp-tool-rules/d-allow-tool-glob
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1・2 とも ALLOWED) |

## 対応する知識

- グループ [P11 README](../README.md) / e(bare glob=無効との対)/ c(等価なサーバ形)

