# S8-b: `.git/config` は allowWrite 内でも書けない → allow ❌(Denied within allowed)

## 目的

- `allowWrite` が repo 全体を覆っていても、`.git/config` への書込だけは sandbox が拒否することを確認する。
- 拒否の一次証跡(`Operation not permitted`)を捕捉し、`allow ❌`(permission は通るが OS 層で遮断)を裏づける。

## 前提(設定)

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": { "allowWrite": [".../b-gitconfig-denied-within-allowed/wr"] }
  },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- `arrange.prep` が **sandbox の外で** `git init wr`(sandbox 内では init が失敗するため → S8-a)。
- `wr` は `allowWrite` に含む。よって `wr` 直下への通常書込は成功する。止まるのは `.git/config` だけ。

## 実行内容

1. Bash で `echo x >> wr/.git/config`(subshell 経由で stderr を捕捉)。成功時のみ `W5MARK.txt` を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo >> wr/.git/config`(allowWrite 内) | allow | ❌ | allowWrite に入っていても `.git/config` は write 拒否。マーカー W5MARK は出ない |

## なぜそうなるか

- 捕捉した stderr(実測): `operation not permitted: wr/.git/config`(EPERM)。
- **`allowWrite` で書込許可した領域の内側でも、`.git/config` は組み込みで write 拒否される("Denied within allowed")。** `&&` が短絡し、後続の W5MARK は書かれない。
- worker が `.git/config`(例: `core.hooksPath` を書き換えて任意 hook を仕込む)を乗っ取る経路は、allowWrite を広く取っても塞がれる。

> 【要裏取り】公式 docs(sandboxing.md)が `.git/config`/`.git/hooks` の deny を明記しているのは **linked worktree の共有 `.git`** の文脈のみ。ここは **plain repo** の `.git/config` で docs は沈黙している。よって「deny される」事実は**実測(EPERM)**で確定し、それが sandbox 組み込み保護なのか permission 保護パスの波及なのかの**層は docs から断定しない**(Bash は sandbox を通るので OS 層と解する。2軸では `allow ❌`)。

## 運用時の留意事項

- `.git/config` の改竄防止を allowWrite の絞り込みだけに頼らない設計で問題ない(領域内でも保護される)。ただし保護の**層**が docs 未記載なので、モード(bypass 等)を変える運用に移す前に空撃ちで再確認する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。`wr` 直下には書けるのに `.git/config` だけ `Operation not permitted` になる様子が確認できる。

```bash
cd cases/S8-sandbox-git-interop/b-gitconfig-denied-within-allowed && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/b-gitconfig-denied-within-allowed
```

> sandbox(OS 層)の I/O を観測するケース。**canUseTool は permission 層しか見えず OS 境界は測れない**ため headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.x | headless / sdk(1プローブとも一致) | 捕捉 stderr: `operation not permitted: wr/.git/config` |

## 対応する知識

- docs/FINDINGS.md: 「`.git/config` は allowWrite 内でも書込拒否("Denied within allowed")」
- 関連: S8-a(git init 失敗)/ S8-e(共有 `.git` の config/hooks deny の対照)/ P5(`.git` 保護パス=permission 層)/ 一次 docs: sandboxing.md
