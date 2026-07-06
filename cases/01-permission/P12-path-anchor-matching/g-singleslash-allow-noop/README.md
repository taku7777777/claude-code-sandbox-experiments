# P12-g: ⚠️ 単一スラッシュ絶対 `Edit(/abs/sub/**)` の allow も no-op(ask のまま・事前承認されない)

## 目的

- c(deny 側)と対に、**allow 側でも単一スラッシュ絶対アンカーが no-op** であることを実測する。

## 前提(設定)

```json
{ "permissions": { "allow": ["Edit($CASE_DIR/sub/**)"] } }
```

- `$CASE_DIR` は単一スラッシュ絶対(`/Users/.../sub/**`)に展開される。
- モード: `default`(allow が効けば事前承認、no-op なら ask=headless で auto-deny)。

## 実行内容

1. Read で `$CASE_DIR/sub/note.txt` を読み、Edit で `hello`→`EDIT_APPLIED`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Edit(絶対パス) | ask | ✅ | ⚠️ allow が no-op → 既定 ask のまま(headless=auto-deny / SDK=ASK) |

## なぜそうなるか

- **単一スラッシュ絶対アンカーは allow でも認識されない**(c の deny 側と同根)。事前承認が働かず default の ask に落ちる。

## 運用時の留意事項

- **「allow を書いたのに CI で通らない」の一因**。P7-c(未 trust)とは別の、表記由来の無言 no-op。
  絶対で allow するなら `~/` か `//`、迷ったら相対形(f)。書いたら空撃ちで承認されるか確認する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで **default モードで** claude を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P12-path-anchor-matching/g-singleslash-allow-noop
python3 harness/run.py -m sdk P12-path-anchor-matching/g-singleslash-allow-noop
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch → headless / sdk(ASK / headless DENIED(auto-deny)) |

## 対応する知識

- グループ [P12 README](../README.md) / c(deny 側の同じ no-op)/ f(相対 allow=効く)/ P7-c(allow が効かない別要因=未 trust)

