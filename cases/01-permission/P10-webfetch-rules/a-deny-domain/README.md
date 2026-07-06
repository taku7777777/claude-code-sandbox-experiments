# P10-a: `deny WebFetch(domain:example.com)` は WebFetch の当該ドメイン取得を permission 層でブロック

## 目的

- **WebFetch は sandbox network（OS 層）を迂回する**（S6-h）が、**permission 層の `WebFetch(domain:…)` 規則には従う**ことを deny 側で確認する。
- 「ネットワークを止める2層目」（S6 = sandbox egress の後段）の主軸。

## 前提(設定)

```json
{ "permissions": { "deny": ["WebFetch(domain:example.com)"] } }
```

- deny は workspace trust のゲート対象外（未 trust でも効く。P7-c）。

## 実行内容

1. WebFetch ツールで `https://example.com` を取得

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebFetch `https://example.com` | deny | - | permission 層でブロック（SDK=DENIED_HARD・headless denials=[WebFetch]） |

## なぜそうなるか

- `WebFetch(domain:example.com)` は WebFetch ツールの取得先ドメインにマッチする permission 規則。deny にマッチした WebFetch 呼び出しはブロックされる。**sandbox network（Bash egress）とは別の層** — WebFetch は S6 の allowedDomains を迂回するが、この permission 規則には従う。

## 運用時の留意事項

- ネットワークを本当に絞るには **sandbox network（S6・Bash/サブプロセス）＋ WebFetch permission（本規則）の2層**。片方だけでは WebFetch（S6 迂回）または Bash curl（本規則の対象外）が残る。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P10-webfetch-rules/a-deny-domain
python3 harness/run.py -m sdk P10-webfetch-rules/a-deny-domain
```

> deny 規則で結論が決まるため全形態で同結論（headless=DENIED / SDK=DENIED_HARD）。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless(DENIED・denials=[WebFetch]) / sdk(DENIED_HARD) |

## 対応する知識

- グループ [P10 README](../README.md)（ネットワーク2層モデル）
- 関連: S6-h（WebFetch は sandbox network を迂回＝本群が必要な理由）/ c-allow-match（同ドメインの allow 対照）
