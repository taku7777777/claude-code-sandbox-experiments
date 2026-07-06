# P10-d: `WebFetch(domain:*.example.com)` のワイルドカードはサブドメインにマッチ → allow

## 目的

- `WebFetch(domain:…)` の **ワイルドカード表記** `*.example.com` がサブドメイン（www.example.com）にマッチして事前承認することを確認する（sandbox network の `allowedDomains` ワイルドカード=S6-c2 と同型）。

## 前提(設定)

```json
{ "permissions": { "allow": ["WebFetch(domain:*.example.com)", "Write(*)"] } }
```

## 実行内容

1. WebFetch ツールで `https://www.example.com` を取得し、**成功したら** Write で `WF_MARKER.txt`（内容 `FETCHED`）を作る

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebFetch `https://www.example.com`（+成功時マーカー） | allow | ✅ | ワイルドカードがサブドメインに一致 |

## なぜそうなるか

- `WebFetch(domain:*.example.com)` は `www.example.com` のようなサブドメインにマッチし、確認なしで通す。permission 層の domain ワイルドカードが、sandbox network の `allowedDomains:["*.example.com"]`（S6-c2）と同じ形で効く。
- 判定は c と同じ「fetch 成功時にだけ Write するマーカー」方式。

## 運用時の留意事項

- **apex（`example.com` 本体）が `*.example.com` にマッチするかは未検証**（一般に glob はラベルを要求するため apex 不一致の可能性）。本ケースはサブドメイン一致のみを確定する。apex も許可したいなら `example.com` を別途列挙するのが安全。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P10-webfetch-rules/d-wildcard-domain
python3 harness/run.py -m sdk P10-webfetch-rules/d-wildcard-domain
```

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless / sdk（ALLOWED・WF_MARKER.txt 生成で確定） |

## 対応する知識

- グループ [P10 README](../README.md)
- 関連: S6-c2（sandbox network の `*.example.com` ワイルドカード＝同型）/ c-allow-match（完全一致 allow）
