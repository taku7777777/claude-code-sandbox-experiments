# P5-b: acceptEdits は通常のネストした in-project 書込を自動承認する(allow・P5-a/c/d の対照)

## 目的

- `acceptEdits` はネストしたプロジェクト内パス(途中ディレクトリの新規作成込み)への書き込みを
  プロンプトなしで自動承認する(= allow)ことを確認する
- これにより a/c/d の保護パス拒否が「ネストの深さ」ではなく「保護パス」由来だと切り分ける肯定対照にする

## 前提(設定)

```json
{}
```

- settings.json は空。`--permission-mode acceptEdits` を付けて実行する
- 書込先は `sub/deep/OK.txt`(存在しないディレクトリを含む通常のネストパス)。
  a/c/d との唯一の差分は「先頭セグメントが保護ディレクトリでない」こと

## 実行内容

1. Write で `sub/deep/OK.txt` を作成(acceptEdits・途中の `sub/`・`sub/deep/` も作成)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `sub/deep/OK.txt`(acceptEdits) | allow | ✅ | 承認プロンプトなしで自動承認(canUseTool 非発火) |

## なぜそうなるか

- `acceptEdits` はプロジェクト内のファイル編集を、途中ディレクトリの作成を含めて自動承認する。
  ネストの深さは制限要因ではない。
- **P5-a/c/d(同じ acceptEdits で `.git`/`.claude`/`.vscode` は ask)と本ケースを並べると、拒否の原因が
  「ネスト」ではなく「保護パス」だと確定する。** 変えたのは書込先の先頭セグメントだけ。

## 運用時の留意事項

- acceptEdits で「書けない」場合は基本的に保護パス(`.git` 等)が理由。通常のネストパスは書ける前提でよい。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude --permission-mode acceptEdits` を起動し、
[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。承認プロンプトなしで `sub/deep/OK.txt` が
作成されることが確認できる(a の `.git` では ask が出るのと対照)。

```bash
cd cases/P5-protected-paths/b-nested-ok && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P5-protected-paths/b-nested-ok
```

> acceptEdits の自動承認(allow)で結論が決まるため**全形態で同結論**
> (→ [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。SDK でも canUseTool は
> 発火せず ALLOWED になることを確認済み。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(ともに ALLOWED・canUseTool 非発火。1プローブ一致) |

## 対応する知識

- docs/FINDINGS.md: Q1 / 保護パスの注
- 関連: P5-a(.git)/ P5-c(.claude)/ P5-d(.vscode)= 保護パスは ask(本ケースの対照)/ P1-b(acceptEdits の基準挙動)
