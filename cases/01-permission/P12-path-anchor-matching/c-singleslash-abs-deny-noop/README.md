# P12-c: ⚠️ 単一スラッシュ絶対 `Edit(/abs/sub/**)` の deny は無言 no-op(編集が通る)

## 目的

- 絶対パスで死守パスを指定したつもりの deny が、**単一スラッシュ表記だと無言で効かない**ことを実測する。
- d(二重スラッシュ=効く)との**1 スラッシュ差**の対照。

## 前提(設定)

```json
{ "permissions": { "deny": ["Edit($CASE_DIR/sub/**)"] } }
```

- `$CASE_DIR` は先頭 1 スラッシュの絶対パス(`/Users/.../sub/**`)に展開される。
- モード: `acceptEdits`(deny が効けばブロック、no-op なら cwd 内自動承認で編集成立)。

## 実行内容

1. Read で `$CASE_DIR/sub/note.txt` を読み、Edit で `hello`→`EDIT_APPLIED`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Edit(絶対パス) | allow | ✅ | ⚠️ deny が no-op → acceptEdits の自動承認に素通り・**編集成立** |

## なぜそうなるか

- **単一スラッシュ絶対アンカー `Edit(/abs/sub/**)` は Edit deny として認識されない**(no-op)。
  エラーも警告も出ず、「deny を書いた=守られている」が成立しない。効く絶対形は `//`(d)か `~/`(e)。

## 運用時の留意事項

- **これは P3(Write path no-op)と同系の最も危険な罠**。絶対で死守パスを書くなら `~/` か `//` を使い、
  **必ず空撃ちで編集がブロックされるか確認**する(BEST-PRACTICES §0)。
- 単一スラッシュの絶対パスをそのまま貼り付けた deny は、静かに無効化される。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで **acceptEdits で** claude を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P12-path-anchor-matching/c-singleslash-abs-deny-noop
python3 harness/run.py -m sdk P12-path-anchor-matching/c-singleslash-abs-deny-noop
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch → headless / sdk(ALLOWED(編集成立=deny no-op)) |

## 対応する知識

- グループ [P12 README](../README.md) / d(二重スラッシュ=効く・1 スラッシュ差)/ g(allow 側の同じ no-op)/ P3(Write path no-op の同系)

