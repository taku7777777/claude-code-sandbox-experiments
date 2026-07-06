# P10-c: `allow WebFetch(domain:example.com)` は当該ドメイン取得を事前承認（陽性対照）

## 目的

- `WebFetch(domain:example.com)` の allow が example.com の取得を**確認なしで通す**ことを確認する（a=deny / b=no-match の陽性対照）。

## 前提(設定)

```json
{ "permissions": { "allow": ["WebFetch(domain:example.com)", "Write(*)"] } }
```

- `Write(*)` は判定用マーカーのため（下記）。

## 実行内容

1. WebFetch ツールで `https://example.com` を取得し、**成功したら** Write ツールで `WF_MARKER.txt`（内容 `FETCHED`）を作る（ブロックされたら何も書かない）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebFetch `https://example.com`（+成功時マーカー） | allow | ✅ | 完全一致ドメインは事前承認 |

## なぜそうなるか

- `WebFetch(domain:example.com)` は example.com への WebFetch 取得にマッチし、確認なしで通す。同じ設定は S6-h（sandbox `allowedDomains:[]` でも WebFetch は到達）でも使われており、本ケースは**permission 層の視点**でその allow を確認する。
- **判定方法**: WebFetch はディスク副作用を持たないため、fetch 成功時にだけ Write する `WF_MARKER.txt` の存在で ALLOWED を観測する（WebFetch が deny/ask なら fetch できずマーカーも出ない → DENIED に落ちる設計）。

## 運用時の留意事項

- 到達性前提: example.com が到達可能であること（S6-h の preflight で確認済み）。オフライン時は fetch 失敗でマーカーが出ず誤 DENIED になり得る。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P10-webfetch-rules/c-allow-match
python3 harness/run.py -m sdk P10-webfetch-rules/c-allow-match
```

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless / sdk（ALLOWED・WF_MARKER.txt 生成で確定） |

## 対応する知識

- グループ [P10 README](../README.md)
- 関連: a-deny-domain（同ドメインの deny 対照）/ b-nomatch-asks（別ドメインは ask）/ S6-h（同設定で sandbox 迂回を実測）
