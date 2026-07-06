# P11-f: `deny mcp__server__tool` は除去型(init tools から消え denials 空)。兄弟ツールは ask のまま

## 目的

- MCP ツール deny の**現れ方**(除去型か呼出時 block 型か)と**粒度**(1 ツール単位か)を確定する。

## 前提(設定)

```json
{ "permissions": { "deny": ["mcp__probe__read_path"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む(deny 対象)
2. `mcp__probe__net_get` で https://example.com を取得(deny 対象外の兄弟)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path(deny) | deny | - | **除去型**: init tools に read_path が無い・denials 空 |
| 2 | net_get(対象外) | ask | ✅ | deny は 1 ツール単位・兄弟に波及しない |

## なぜそうなるか

- ツール名 deny は**ツールセットからの除去**として現れる(モデルは「そのツールは存在しない」状態で起動)。
  組込ツールの「deny のみ=除去型」(P2-c/d)と同じ現れ方。ground truth は init メッセージの tools 欠落。

## 運用時の留意事項

- **denials にも副作用にも痕跡が出ない**ため、「deny が効いている」ことの監視は init tools の欠落で行う
  (本ハーネスの除去型判定と同じロジック)。試行の監査が要る操作は deny でなく ask(j)に寄せる。
- 書込系ツールだけ deny する運用(h)の基礎: deny の単位が 1 ツールであることの直接証拠。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/f-deny-tool
python3 harness/run.py -m sdk P11-mcp-tool-rules/f-deny-tool
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(1=DENIED(除去型・sdk=DENIED_HARD) / 2=headless DENIED(auto-deny)・sdk ASK) |

## 対応する知識

- グループ [P11 README](../README.md) / P2-c/d(除去型 deny の同型)/ h(実運用形)

