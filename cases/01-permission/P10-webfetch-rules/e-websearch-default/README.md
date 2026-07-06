# P10-e: WebSearch は既定 ask(規則なしで承認要求・read-only 無条件集合に入らない)

## 目的

- WebSearch のツール単位規則の baseline: 規則ゼロでの既定挙動を確定する(f=allow / g=deny の参照点)。

## 前提(設定)

```json
{ "permissions": {} }
```

## 実行内容

1. WebSearch ツールで固定クエリを検索する

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebSearch(規則なし) | ask | ✅ | denials=[WebSearch]・ツールは init tools に存在 |

## なぜそうなるか

- docs(tools-reference): WebSearch は Permission required=**Yes**。Read 等の read-only 組込ツール
  (全モード素通し=P1)や read-only Bash 集合(P4-i)と違い、外部アクセスを持つため既定 ask。

## 運用時の留意事項

- headless/CI で WebSearch を使うには `allow: ["WebSearch"]`(f)が必須。刺さっているだけでは auto-deny。
- 「検索は許すが取得先を絞りたい」は WebSearch では書けない(f)— WebFetch の domain allowlist(a〜d)に寄せる。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P10-webfetch-rules/e-websearch-default
python3 harness/run.py -m sdk P10-webfetch-rules/e-websearch-default
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(headless=DENIED(auto-deny) / sdk=ASK) |

## 対応する知識

- グループ [P10 README](../README.md) / P1-a(既定 ask の同型)/ f・g(allow/deny 側)

