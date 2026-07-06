# S8-c: `git worktree add` は sandbox 内で成功する → allow ✅(git init と対照)

## 目的

- 既存 repo に対する `git worktree add` が sandbox 内で**成功**することを確認する(init が失敗するのと対照)。
- 「repo の用意が要るのは init/clone だけで、worktree add 自体は sandbox 内で可能」を実測で確定する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- `arrange.prep` が sandbox の外で `git init wr2` + 空コミット1個(worktree add には HEAD が要る)。
- allowWrite 指定なし(cwd = ケースディレクトリが既定で書込可)。

## 実行内容

1. Bash で `git -C wr2 worktree add ../wt2`。成功時のみ `WTMARK.txt` を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `git worktree add`(既存 repo) | allow | ✅ | `.git/worktrees/` と worktree の `.git` ファイルへ書くだけ。`.git/config`/`.git/hooks` 非接触 |

## なぜそうなるか

- 捕捉した出力(実測): `Preparing worktree (new branch 'wt2') / HEAD is now at ... c`(成功)。
- **worktree add は `wr2/.git/worktrees/wt2/` と worktree 側の `.git` ファイルを書くだけ**で、いずれも書込可能領域の内側、かつ **`.git/config`/`.git/hooks` に触れない**。だから S8-a(hooks テンプレ)・S8-b(config)の deny に当たらず通る。
- これは multi-repo-workspace.md の旧主張「worktree add は `.git/config` を書くため保護に阻まれる」を**実測で否定**する。sandbox の外(prep)が必須なのは init/clone(hooks/config テンプレ書込・ネットワーク)であって、worktree add ではない。

## 運用時の留意事項

- worktree の**作成**自体は sandbox 内 worker でも実行できる(prep に必ず追い出す必要はない)。ただし作成後に worktree の中で `git commit` する運用は S8-d を参照(共有 `.git` への書込可否)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。git init が失敗する S8-a と違い、worktree add は成功する様子が確認できる。

```bash
cd cases/S8-sandbox-git-interop/c-worktree-add-in-sandbox && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/c-worktree-add-in-sandbox
```

> sandbox(OS 層)の I/O を観測するケース。**canUseTool は OS 境界を測れない**ため headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.x | headless / sdk(1プローブとも一致) | 捕捉出力: `Preparing worktree ... / HEAD is now at ...` |

## 対応する知識

- docs/FINDINGS.md: 「worktree add は sandbox 内で成功(prep が要るのは init/clone)」
- 関連: S8-a(git init 失敗)/ S8-d(worktree 内 commit → 共有 `.git` 書込)/ multi-repo-workspace.md(旧主張の是正)
