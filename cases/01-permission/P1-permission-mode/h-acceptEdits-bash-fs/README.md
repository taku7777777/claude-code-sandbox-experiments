# P1-h: acceptEdits は Bash の FS コマンド(mkdir/touch)も自動承認する — ただし cwd 内限定

## 目的

- acceptEdits の自動承認範囲が**編集ツール(Write/Edit)だけではない**ことを実測する。
  docs は「file edits **and common filesystem commands such as `mkdir`, `touch`, `mv`, `cp`**」と明記
- その Bash 自動承認にも Write と同じ **cwd 境界**(P1-b write-home)が適用されるかを確認する

## 前提(設定)

```json
{}
```

- settings.json は空。`--permission-mode acceptEdits` を付けて実行する
- P1-b との差分はプローブが Bash コマンドであること

## 実行内容

1. Bash で `mkdir -p ./mkd_proof`(cwd 内)
2. Bash で `touch ./touched_proof.txt`(cwd 内)
3. Bash で `mkdir -p ~/p1h-proof-dir`(cwd 外)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `mkdir`(cwd 内) | allow | ✅ | FS コマンドも自動承認(allow 規則なしで) |
| 2 | Bash `touch`(cwd 内) | allow | ✅ | 同上 |
| 3 | Bash `mkdir`(cwd 外 `~`) | ask | ✅ | **cwd 境界は Bash 自動承認にも適用**(headless では ❌) |

## なぜそうなるか

- acceptEdits の自動承認は「編集ツール」ではなく「**ファイルシステム操作**」が単位。
  docs の列挙: `mkdir` `touch` `rm` `rmdir` `mv` `cp` `sed`(対象パスが working directory /
  `additionalDirectories` 内のもの)。
- 境界は Write の場合(P1-b)と同じ cwd。「acceptEdits なら何でも書ける」わけではない。

## 運用時の留意事項

- acceptEdits は `rm` も自動承認対象(docs 記載)。cwd 内とはいえ削除系が確認なしで走る点は
  意識しておく(本ケースでは安全のため mkdir/touch のみをプローブにしている)。
- `additionalDirectories` 内への適用は未実測(→ GAPS.md G6 残項)。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P1-permission-mode/h-acceptEdits-bash-fs
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(3プローブとも一致) |

## 対応する知識

- グループ [P1 README](../README.md)
- 関連: P1-b(Write/Edit の acceptEdits 挙動と cwd 境界)/ P5(保護パスは acceptEdits の自動承認対象外)
