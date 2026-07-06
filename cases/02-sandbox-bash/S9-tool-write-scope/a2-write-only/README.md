# S9-a2: `deny Write(assets/**)` は no-op — Write も Edit も止まらない(`Write(dir/**)` は P3 の no-op 仲間)

## 目的

- a の2変数(`Write(assets/**)` と `Edit(assets/**)` を両方 deny)を1変数に分離し、**`Write(assets/**)` 単独が何を止めるか**を確定する(GAPS G3 の是正)。
- 結論の先取り: **何も止めない(no-op)**。a のブロックは `Write` 規則ではなく `Edit` 規則由来(→ [a3](../a3-edit-only/README.md))。

## 前提(設定)

```json
{ "permissions": { "deny": ["Write(assets/**)"] } }
```

- deny は `Write(assets/**)` のみ(a と違い `Edit(assets/**)` は入れない)。`--permission-mode acceptEdits` で起動。

## 実行内容

1. Write ツールで `assets/data.txt` を作成(deny の対象ツール)
2. Read → Edit で `assets/note.txt` を編集(deny していないツール=対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `assets/data.txt` | allow | ✅ | **`Write(assets/**)` は no-op**。Write ツールを止めない(中立 control 5/5 作成) |
| 2 | Edit `assets/note.txt` | allow | ✅ | Write 規則は Edit に波及しない。acceptEdits が自動承認 |

- **1=allow ✅ が核心**: dir スコープの Write deny があっても Write が通る(5/5)→ **`Write(dir/**)` は効かない**。a の 0/5 ブロックは `Write` 規則ではなかった。

## なぜそうなるか

- **`Write(<dir>/**)` は no-op**: 中立 /tmp・acceptEdits・5回の control で **5/5 作成**(baseline と同じ)。P3(`Write(**)`・完全パス)と同族で、dir スコープの Write deny も Write ツールを止めない。
- **規則はツール単位で、しかも Write 規則は今回イン効**: Write 規則は Edit ツールにも当然波及しない(2 も通る)。→ `deny Write(assets/**)` は Write も Edit も止めない。
- 対して `Edit(<dir>/**)` は Write を含む編集系全体をハードに止める(→ [a3](../a3-edit-only/README.md)、docs「Edit rules apply to all built-in tools that edit files」)。**a の“効く2層目”は Edit 規則**。

## 運用時の留意事項

- **`Write(<dir>/**)` deny を書いても保護にならない(no-op トラップ)**。ツール層で dir を守るなら `Edit(<dir>/**)` deny を書く(Write/MultiEdit まで一括で効く)。必ず空撃ちで実測すること。
- SDK で canUseTool を登録すると Write の ask がコールバックに現れるが、これは acceptEdits の通常の ask-surfacing であって deny 規則が効いているわけではない(コールバック無しの素の headless では acceptEdits が自動承認 → 書ける)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで acceptEdits で `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1(Write)も 2(Edit)も承認なしで通る(=`Write(assets/**)` は効いていない)ことが確認できる。

```bash
cd cases/S9-tool-write-scope/a2-write-only && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S9-tool-write-scope/a2-write-only
```

> 両プローブとも allow(no-op)なので全形態で同結論。ブロックが無いためモデル拒否の構造的不安定も起きにくく、in-repo headless でも安定して ALLOWED(Write プローブでファイル作成を実測)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(2プローブとも ALLOWED)/ control(Write-only 5/5 作成=no-op) |

## 対応する知識

- グループ [S9 README](../README.md)
- 関連: [a](../a-subdir-file-write/README.md)(両 deny=Edit 規則で止まる)/ [a3](../a3-edit-only/README.md)(`Edit(dir/**)`=編集系ハード deny)/ P3(`Write(**)`・完全パス=no-op / `Write(dir/**)` も同族)
- 一次 docs: permissions(スコープ Write deny の効き方 / 「Edit rules apply to all built-in tools that edit files」)
