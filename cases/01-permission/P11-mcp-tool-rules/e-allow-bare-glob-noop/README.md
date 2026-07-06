# P11-e: `allow mcp__*`(サーバ名なしの bare glob)は無言で無効 — ask のまま(fail-closed 側の no-op)

## 目的

- allow 側 glob の**効かない形**を確定する: サーバ名を glob にした `mcp__*` は allow で機能しないこと、
  および docs の言う「警告付きスキップ」の警告が実運用で見えるかの観測。

## 前提(設定)

```json
{ "permissions": { "allow": ["mcp__*"] } }
```

## 実行内容

1. `mcp__probe__read_path` で note.txt を読む(「全 MCP を allow したつもり」の設定下)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | read_path | ask | ✅ | allow は不発 → 既定 ask のまま(a と同じ挙動) |

## なぜそうなるか

- docs: 「unanchored な allow glob(`"*"`, `"B*"`, `"mcp__*"`)は**警告付きでスキップされ、何も
  自動承認しない**」。allow の glob はサーバ名リテラル必須(d)で、サーバ段を glob にできない。
- **実測では headless 実行の stderr に警告は観測されなかった**(P2-g「規則形式ミスの警告は見落とされ
  がち」と同型)。警告がどの面に出るかは未特定。

## 運用時の留意事項

- 「全 MCP をまとめて許可」する規則は**存在しない**(サーバごとに c/d の形で書く)。bare `mcp__*` を
  書いても倒れる先は fail-closed(全 ask)なので事故にはならないが、「書いたのに効かない」型の混乱源。
- deny/ask 側は逆に bare `mcp__*` が**効く**(i)。allow と deny で glob の受理が非対称である点を覚える。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで claude を `--mcp-config` 付きで起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける
(fixture の刺し方はグループ [README](../README.md) 参照。ハーネスは case.json の `arrange.mcpServers` から自動で刺す)。

### ハーネスで実測する

```bash
python3 harness/run.py P11-mcp-tool-rules/e-allow-bare-glob-noop
python3 harness/run.py -m sdk P11-mcp-tool-rules/e-allow-bare-glob-noop
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(headless=DENIED(auto-deny)・stderr 警告なし / sdk=ASK) |

## 対応する知識

- グループ [P11 README](../README.md)(e⇔i の非対称表)/ P2-g(無言で無効な規則の同型)/ P3(no-op 規則の系譜)

