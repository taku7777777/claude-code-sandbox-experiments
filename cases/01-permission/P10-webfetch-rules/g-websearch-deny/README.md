# P10-g: `deny WebSearch`(bare)は除去型 — init tools から消え denials も出ない

## 目的

- WebSearch のツール単位 deny が「効く形」であることと、その現れ方(除去型)を確定する。
- egress を絞るロール(coder / reader 等)の `deny: ["WebSearch"]` の直接根拠。

## 前提(設定)

```json
{ "permissions": { "deny": ["WebSearch"] } }
```

## 実行内容

1. WebSearch で固定クエリを検索する(ツールが存在しない想定下)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebSearch(bare deny) | deny | - | **除去型**: init tools に WebSearch が無い・denials 空 |

## なぜそうなるか

- bare ツール名 deny はツールセットからの除去として現れる(P2-c/d と同じ)。モデルは WebSearch の存在
  自体を知らずに起動する。

## 運用時の留意事項

- WebSearch/WebFetch は **sandbox network(S6)を迂回する**ため、egress を絞る設定はこの permission 層
  でしか書けない。`sandbox.network.allowedDomains: []` と `deny: ["WebFetch", "WebSearch"]` はセットで書く
- 除去型なので**試行の監査ログは残らない**(denials 空)。効いていることの確認は init tools の欠落で。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P10-webfetch-rules/g-websearch-deny
python3 harness/run.py -m sdk P10-webfetch-rules/g-websearch-deny
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(DENIED(除去型・WebSearch が init tools に不在・sdk=DENIED_HARD)) |

## 対応する知識

- グループ [P10 README](../README.md) / P2-c/d(除去型)/ S6-h(sandbox 迂回=本規則が唯一の層である理由)

