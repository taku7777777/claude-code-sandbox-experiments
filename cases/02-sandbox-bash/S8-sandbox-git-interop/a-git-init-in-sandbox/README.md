# S8-a: sandbox 内で `git init` は完了しない → allow ❌(`.git/hooks` へのテンプレコピーが OS 層で EPERM)

## 目的

- sandbox 有効時、Bash は permission で自動許可(`Bash(*)`)されるのに `git init` が**実行時に**失敗することを確認する。
- 失敗の一次証跡(git の `fatal:` stderr)を捕捉し、「ファイルが出来なかった」ではなく **OS 層の `Operation not permitted`** で裏づける。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- Bash はすべて事前承認(`Bash(*)`)。よって止まるのは permission 層ではなく sandbox(OS)層。
- `arrange` なし(`git init newrepo` が新規に repo を作ろうとするところを観測)。

## 実行内容

1. Bash で `git init newrepo` を実行し、stderr を `err.txt` に捕捉、成功時のみ `INITMARK.txt` を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `git init newrepo`(成功マーカー方式) | allow | ❌ | git が `.git/hooks/*.sample` を**書けず** `fatal: ... Operation not permitted`。成功マーカー INITMARK は出ない |

- `allow × ❌` = Bash は通ったが OS 層が書込を止めた、の典型。

## なぜそうなるか

- 捕捉した stderr(実測):
  `fatal: cannot copy '/Library/Developer/CommandLineTools/usr/share/git-core/templates/hooks/commit-msg.sample' to '.../newrepo/.git/hooks/commit-msg.sample': Operation not permitted`
- **止めているのはシステムテンプレの「読取」ではなく、コピー先 `newrepo/.git/hooks/` への「書込」**。sandbox は `.git/hooks` への write を EPERM で拒否する。これは公式 docs の「既定 read=全域(deny 指定を除く)」と整合する(読取は塞がれていない)。
- 補足: `git init --template=`(hook テンプレ無効化)にしても、今度は `error: could not write config file .../.git/config: Operation not permitted` で失敗する(→ [S8-f](../f-init-mechanism-probe/README.md) で正式ケース化・実測)。**`.git/config` の write も OS 層で拒否**されるため、`git init` は sandbox 内では**どの経路でも完了しない**(bare init のみ例外的に成功 = deny は `.git/` というパス形状。S8-f)。

> 【要裏取り】公式 docs(sandboxing.md)が `.git/config`・`.git/hooks` の deny を明記しているのは **linked worktree の共有 `.git`** の文脈のみ。「新規 plain repo の `.git/hooks`/`.git/config` も deny」は docs には無い一般化で、ここでは**実測(EPERM)**に基づく記述に留める。

## 運用時の留意事項

- **git init / clone は sandbox の外(prep フェーズ)で行う**。エージェント(worker)が sandbox 内で repo を新規作成する運用は成立しない(multi-repo-workspace の open-task.sh Phase 1 の根拠)。
- 「失敗した理由」を運用ログに残すなら、モデルの散文ではなく git の `fatal:`/`Operation not permitted` 行を残す(機構が確定する)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。Bash は承認なしで動くのに `git init` だけ `Operation not permitted` で失敗する様子が確認できる。

```bash
cd cases/S8-sandbox-git-interop/a-git-init-in-sandbox && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/a-git-init-in-sandbox
```

> sandbox(OS 層)の I/O を観測するケース。**SDK の canUseTool は permission 層しか見えず OS 境界は測れない**ため、headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.x | headless / sdk(1プローブとも一致) | 捕捉 stderr: `.git/hooks/commit-msg.sample ... Operation not permitted`。`--template=` でも `.git/config` write が EPERM は S8-f で正式に実測 |

## 対応する知識

- docs/FINDINGS.md: 「git init は sandbox 内で失敗(hook テンプレの書込不可)」
- 関連: S8-b(`.git/config` 書込拒否)/ S8-c(worktree add は成功)/ S8-e(共有 `.git` の hooks/config deny)/ 一次 docs: sandboxing.md「Filesystem isolation」
