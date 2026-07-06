# S8-d: worktree の中からの `git commit` は共有 `.git` へ書けて成功する → allow ✅(allowWrite 注入は不要)

## 目的

- linked worktree を cwd として `git commit` したとき、メイン repo の**共有 `.git`**(logs/refs/objects)への書込が **allowWrite 注入なしで**通ることを実測する。
- これは本グループの看板となる公式 docs の記述を直接検証し、**「worktree commit には `.git/` の allowWrite 注入が必要」という逆主張(refactor-plan §W4)と対決**する MUST MEASURE ケース。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- **allowWrite は敢えて指定しない**(自動許可されるかどうか自体を測るため)。
- `arrange.prep` が sandbox の外で `git init mainrepo` + 初期空コミット + `git worktree add ../wt`。
- 共有 `.git`(`mainrepo/.git`)はケースディレクトリ(書込可領域)の内側に置かれる。

## 実行内容

1. `cd wt`(cwd = linked worktree)してから `git commit --allow-empty`。成功時のみ `COMMITMARK.txt` を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `git commit`(cwd=worktree、共有 `.git` へ書込) | allow | ✅ | 共有 `.git` の logs/refs/objects/worktrees は deny 対象外。allowWrite 注入なしで通る |

## なぜそうなるか

- 捕捉した出力(実測): `[wt 0b7a2fc] x`(commit 成功、exit=0)。
- **公式 docs(sandboxing.md)明記**: 「when the working directory is a linked git worktree, the sandbox also allows writes to the main repository's shared `.git` directory so commands such as `git commit` can update refs and the index.」= 共有 `.git` への write は自動許可。
- commit が書くのは `.git/logs`・`.git/refs`・`.git/objects`・`.git/worktrees/wt/` で、**deny 対象の `.git/config`/`.git/hooks` を含まない**。したがって allowWrite を注入しなくても通る。
- **【対決の結論】refactor-plan §W4 の「worktree での `git commit` には `.git/` を allowWrite 注入が必要」は本環境の実測で否定された。** docs 側(自動許可)が正しい。
- 補足(本ケースの構成上の注意): 本ケースでは共有 `.git` が書込可領域(ケースディレクトリ)の内側にある。そのため commit は「一般の書込可領域ルール」と「docs の worktree 特例」の両方で許可されうる。いずれにせよ**allowWrite の明示注入は不要**、が finding。共有 `.git` が workspace の外に置かれる multi-repo 構成でこそ worktree 特例が効く点は docs の記述どおり。

## 運用時の留意事項

- worker が worktree の中で `git commit` する運用に、**`.git/` を allowWrite に足す設定は(この挙動が効く版では)不要**。過剰な allowWrite は攻撃面を広げるので、必要性を空撃ちで確認してから入れる。
- ただし版によって挙動が変わりうる(下記 検証記録の版に依存)。設計を移す前に本ケースで再実測する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。allowWrite を入れていないのに worktree 内の commit が成功する様子が確認できる。

```bash
cd cases/S8-sandbox-git-interop/d-worktree-commit-shared-git && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/d-worktree-commit-shared-git
```

> sandbox(OS 層)の I/O を観測するケース。**canUseTool は OS 境界を測れない**ため headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.x | headless / sdk(1プローブとも一致) | 捕捉出力: `[wt 0b7a2fc] x`(exit=0)。共有 `.git` はケースdir内。docs: sandboxing.md「Git worktrees」/ 版ゲート v2.1.149 |

## 対応する知識

- docs/FINDINGS.md: 「worktree の中からの commit は共有 `.git` へ書けて成功(allowWrite 注入不要)」
- 関連: S8-c(worktree add)/ S8-e(共有 `.git` の config/hooks は依然 deny)/ refactor-plan §W4(逆主張の否定)/ multi-repo-workspace.md(`.git/` allowWrite 注入の記述の見直し)/ 一次 docs: sandboxing.md「Git worktrees」
