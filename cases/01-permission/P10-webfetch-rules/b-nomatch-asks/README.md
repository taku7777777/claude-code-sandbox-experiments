# P10-b: `allow WebFetch(domain:example.com)` は列挙ドメインだけ許可。別ドメインは不一致 → ask

## 目的

- `WebFetch(domain:…)` の allow が **domain allowlist** として働き、列挙したドメインだけを事前承認する（別ドメインは既定 ask に落ちる）ことを確認する。

## 前提(設定)

```json
{ "permissions": { "allow": ["WebFetch(domain:example.com)"] } }
```

- allow は workspace trust 済みでのみ有効（repo root は trusted）。

## 実行内容

1. WebFetch ツールで **`https://example.org`** を取得（allow は example.com のみ、example.org は列挙外）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebFetch `https://example.org` | ask | ✅ | 列挙外ドメインは不一致 → 既定 ask（承認すれば取得可） |

- `ask ✅` = 承認すれば通る。headless では承認者不在で auto-deny、SDK では canUseTool が WebFetch で発火（ASK）。

## なぜそうなるか

- `WebFetch(domain:example.com)` は **example.com に完全一致するドメインだけ**を事前承認する。example.org はマッチせず、規則が沈黙している領域の既定（ask）に落ちる = allowlist の特異性。c-allow-match（example.com は allow）と対で「列挙ドメインだけ通す」ことを確定する。

## 運用時の留意事項

- WebFetch を絞るときは**必要ドメインを列挙**する。広く開けたいならワイルドカード（`domain:*.example.com`=d）を使うが、範囲を広げすぎない。

## 試し方(本リポジトリでの実測)

ask 系なので3形態で ask の解決が変わる（headless=auto-deny / SDK=canUseTool 発火 / 対話=承認プロンプト）:

```bash
python3 harness/run.py P10-webfetch-rules/b-nomatch-asks            # headless: auto-deny
python3 harness/run.py -m sdk P10-webfetch-rules/b-nomatch-asks     # sdk: ASK
```

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless(DENIED=auto-deny・denials=[WebFetch]) / sdk(ASK・askFired=[WebFetch]) |

## 対応する知識

- グループ [P10 README](../README.md)
- 関連: c-allow-match（example.com は allow＝本ケースの対照）/ d-wildcard-domain（広げるならワイルドカード）
