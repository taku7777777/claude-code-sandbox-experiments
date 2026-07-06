# P12-f: 相対 allow `Edit(sub/**)` は絶対パス呼び出しを事前承認する(deny 側 a と対称)

## 目的

- allow 側でも相対規則が絶対パス呼び出しにマッチする(表記差で事前承認が漏れない)ことを実測する。

## 前提(設定)

```json
{ "permissions": { "allow": ["Edit(sub/**)"] } }
```

- モード: `default`(無指定。この allow が無ければ Edit は ask=headless で auto-deny)。

## 実行内容

1. Read で `$CASE_DIR/sub/note.txt`(絶対パス)を読み、Edit で `hello`→`EDIT_APPLIED`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Edit(絶対パス) | allow | ✅ | 相対 allow が絶対呼び出しを事前承認・編集成立(canUseTool 非発火) |

## なぜそうなるか

- allow 側もマッチは解決済みパスで行われる(deny 側 a と同じ機構)。相対で書いた allow は、default モードで
  本来 ask になる絶対パス Edit を事前承認する。

## 運用時の留意事項

- CI で「特定ディレクトリの編集だけ通す」は相対 `Edit(dir/**)` で書ける(絶対パスで呼ばれても効く)。
- ただし絶対で書くなら単一スラッシュは no-op(g)。**allow も相対形が最も堅い**。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで **default モードで** claude を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P12-path-anchor-matching/f-rel-allow-abs-call
python3 harness/run.py -m sdk P12-path-anchor-matching/f-rel-allow-abs-call
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch → headless / sdk(ALLOWED(編集成立=事前承認)) |

## 対応する知識

- グループ [P12 README](../README.md) / a(deny 側の対称)/ g(単一スラッシュ allow=no-op)

