# P10-f: `allow WebSearch`(bare)は事前承認 — specifier は取れない(domain 限定不可=全か無か)

## 目的

- WebSearch の allow が bare 形で効くことを陽性対照で確定する。
- **domain 限定の書式が存在しない**(docs 明記)ことを運用制約として記録する。

## 前提(設定)

```json
{ "permissions": { "allow": ["WebSearch", "Write(*)"] } }
```

- `Write(*)` は観測用マーカーのための同居 allow(P10-c と同じ手法)。

## 実行内容

1. WebSearch で固定クエリを検索し、結果が返った場合のみ Write でマーカーを作る

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | WebSearch(bare allow) | allow | ✅ | 検索成功 → マーカー出現で ALLOWED 確定 |

## なぜそうなるか

- docs(tools-reference): 「**WebSearch permission rules take no specifier. A bare `WebSearch` entry
  in allow or deny is the only form**」。WebFetch の `domain:` のような限定構文が存在しない。

## 運用時の留意事項

- **「限定的な web search」を permission 規則で書く手段は無い**(全か無か)。検索クエリ自体が外部送信で
  ある点も含め、allow は「このロールには web 検索を信頼して渡す」という判断そのもの。
- 取得先を絞った web 参照が要件なら、**WebSearch は deny(g)し WebFetch の domain allowlist(a〜d)に
  一本化**する構成が規則で書ける唯一の形。
- オンライン前提(オフラインでは検索失敗 → マーカー不出現で誤 DENIED になり得る)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P10-webfetch-rules/f-websearch-allow
python3 harness/run.py -m sdk P10-webfetch-rules/f-websearch-allow
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch 探索 → headless / sdk(ALLOWED(マーカー出現)) |

## 対応する知識

- グループ [P10 README](../README.md) / a〜d(WebFetch domain 規則=絞れる側)/ S6-h(sandbox 迂回)

