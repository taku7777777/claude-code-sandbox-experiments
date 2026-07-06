# S8-f: `git init --template=` でも `.git/config` 作成で失敗する → deny は「テンプレコピー」ではなく `.git/config`・`.git/hooks/` というパスへの write(bare init は成功)

## 目的

- S8-a(`git init` 失敗)の**機構分離**: a はテンプレ hook のコピー(`.git/hooks/` への write)で落ちるが、それは「原因」なのか「deny パスに最初に触れた write」に過ぎないのかを、`--template=` でテンプレ処理を丸ごと外して切り分ける。
- 1 変数対照として `--bare` を足し、**config が `.git/` 配下でないパス**(`barerepo/config`)に置かれる場合に init が通るかを見る = deny が「パス形状」か「git の設定ファイルという意味」かを判別する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- allowWrite 指定なし(cwd = ケースディレクトリは既定で書込可領域)。プローブはすべて cwd 内への書込。

## 実行内容

1. `git init --template= newrepo`(テンプレコピー無効)。成功時のみ `TPLMARK.txt` を書き、stderr は `err.txt` に捕捉
2. `git init --bare --template= barerepo`(config の置き場所が `barerepo/config` = `.git/` 配下でない)。成功時のみ `BAREMARK.txt`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `git init --template=`(`.git/config` の新規作成) | allow | ❌ | テンプレを外しても次の write(`.git/config` 作成)が EPERM。deny は新規作成にも効く(S8-b の既存追記と対) |
| 2 | Bash `git init --bare --template=`(config は `barerepo/config`) | allow | ✅ | 同じ「repo の config 作成」でも `.git/` 配下でないパスなら通る = deny はパス形状 |

## なぜそうなるか

- 捕捉した stderr(実測):
  - 1: `error: could not write config file .../newrepo/.git/config: Operation not permitted` / `fatal: could not set 'core.repositoryformatversion' to '0'`(exit=128、TPLMARK 不在)
  - 2: `Initialized empty Git repository in .../barerepo/`(exit=0、BAREMARK 生成)
- **核心: sandbox の deny は `**/.git/config`・`**/.git/hooks/` という「パス」への write に効いており、テンプレコピーという処理にも、ファイルの既存/新規にも依存しない。**
  - S8-a の失敗点(hooks テンプレコピー)は「init のシーケンスで deny パスに最初に触れる write」だっただけで、そこを外しても次の deny パス(`.git/config` 作成)で止まる。**通常(非 bare)の init に `--template=` 回避策は存在しない**。
  - bare repo は config が `.git/` 配下に無いため素通り = deny がパス形状であることの対照証明。ついでに「bare repo なら sandbox 内で作れる」という運用上の抜け道も判明。
- 旧 a README の「システムテンプレパスの読取を sandbox が阻む」説は否定(sandbox の既定 read は全域。実測の EPERM はすべて write 側)。
- なお公式 docs(sandboxing.md)が config/hooks deny を明記するのは linked worktree の共有 `.git` のみで、**plain repo への一般則としてのパス deny は docs に無い**。本ケースの主張は捕捉 stderr(一次証跡)に基づく実測【要裏取り】。

## 運用時の留意事項

- sandbox 内で通常の repo を作る手段は無い(`git init` も `--template=` も不可)。**repo の新規作成(init/clone)は prep フェーズで sandbox の外に出す**、という multi-repo 設計の前提はこの機構レベルで確定。
- bare repo(`git init --bare`)は作れてしまう点に注意。「sandbox 内では repo を一切作れない」と過信しない(bare + worktree 系の組み合わせは未検証)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。1 が config 作成で落ち、2 だけ成功する対照が確認できる。

```bash
cd cases/S8-sandbox-git-interop/f-init-mechanism-probe && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/f-init-mechanism-probe
```

> sandbox(OS 層)の I/O を観測するケース。**canUseTool は OS 境界を測れない**ため headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) | 捕捉 stderr: 1=`could not write config file .../.git/config: Operation not permitted`、2=`Initialized empty Git repository`。ケース化前に scratch 最小プローブで機構を確認(CASE-FORMAT 手順0) |

## 対応する知識

- docs/FINDINGS.md: 「init 失敗の機構 = `.git/config`・`.git/hooks/` へのパス deny(テンプレ非依存・bare は通る)」
- 関連: S8-a(deny パスに最初に触れる write で fatal)/ S8-b(既存 `.git/config` への追記も同じ deny)/ S8-h(clone も同 2 関門)/ 一次 docs: sandboxing.md「Git worktrees」(config/hooks deny の明記は worktree 文脈のみ)
