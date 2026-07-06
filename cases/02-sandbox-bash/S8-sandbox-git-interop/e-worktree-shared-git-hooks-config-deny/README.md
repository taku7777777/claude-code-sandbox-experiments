# S8-e: 共有 `.git` でも `config` と `hooks/` は依然 deny → allow ❌(worktree 特例の例外)

## 目的

- worktree の中では共有 `.git` へ書ける(S8-d)一方で、その共有 `.git` の中でも **`config` と `hooks/` への書込は拒否**されることを実測する。
- 公式 docs が明記する「hooks/ と config のみ deny」の**例外の対照**を、EPERM の一次証跡で裏づける。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- `arrange.prep` が sandbox の外で `git init mainrepo` + 初期空コミット + `git worktree add ../wt`(S8-d と同構成)。
- allowWrite 指定なし。共有 `.git`(`mainrepo/.git`)はケースディレクトリの内側。

## 実行内容

1. Bash で共有 `mainrepo/.git/config` へ追記(subshell で stderr 捕捉)。成功時のみ `CFGMARK.txt`
2. Bash で共有 `mainrepo/.git/hooks/pre-commit` へ書込。成功時のみ `HKMARK.txt`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo >> mainrepo/.git/config`(共有 `.git`) | allow | ❌ | 共有 `.git` でも `config` は write 拒否 |
| 2 | Bash `echo > mainrepo/.git/hooks/pre-commit`(共有 `.git`) | allow | ❌ | 共有 `.git` でも `hooks/` は write 拒否 |

## なぜそうなるか

- 捕捉した stderr(実測): `operation not permitted: mainrepo/.git/config` / `operation not permitted: mainrepo/.git/hooks/pre-commit`(いずれも EPERM)。
- **公式 docs(sandboxing.md)明記**: worktree の共有 `.git` への write 許可には例外があり、「Writes to `hooks/` and `config` inside that directory remain denied.」= **`hooks/` と `config` だけは deny のまま**。
- S8-d(commit=logs/refs/objects への write は成功)と本ケース(config/hooks は失敗)が、docs の「共有 `.git` は許可、ただし hooks/config は例外」を**両側から実測**で確定する。

## 運用時の留意事項

- worktree 運用で共有 `.git` が書けるようになっても、**`.git/config`(例: `core.hooksPath`)や `.git/hooks/*` を仕込む攻撃経路は塞がれたまま**。commit が通ることと hook 注入が通ることは別で、後者は依然 deny。
- この deny は docs 上 worktree の共有 `.git` について明記(plain repo は S8-b で実測・docs は沈黙)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。commit は通る(S8-d)のに config/hooks だけ `Operation not permitted` になる様子が確認できる。

```bash
cd cases/S8-sandbox-git-interop/e-worktree-shared-git-hooks-config-deny && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/e-worktree-shared-git-hooks-config-deny
```

> sandbox(OS 層)の I/O を観測するケース。**canUseTool は OS 境界を測れない**ため headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.x | headless / sdk(2プローブとも一致) | 捕捉 stderr: `operation not permitted: mainrepo/.git/config` / `.../hooks/pre-commit`。docs: sandboxing.md「Git worktrees」 |

## 対応する知識

- docs/FINDINGS.md: 「worktree の共有 `.git` でも config/hooks は deny のまま」
- 関連: S8-d(共有 `.git` の logs/refs は許可の対照)/ S8-b(plain repo の config deny)/ S8-a(init の hooks 書込 deny)/ 一次 docs: sandboxing.md「Git worktrees」
