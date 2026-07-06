# S8-h: `git clone` は network を排した file:// でも失敗する → 機構は init と同じ `.git/hooks`・`.git/config` へのパス deny(network 遮断は遠隔 URL の追加関門)

## 目的

- グループタイトルの「clone も失敗する」を documented-only から実測に昇格させる(旧 GAPS G5)。
- clone の失敗が **network 遮断(S6)によるものか、init と同じ `.git` パス deny によるものか**を、ローカル repo の `file://` clone(local 転送・egress ゼロ)で network を完全に排除して切り分ける。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- クローン元 `srcrepo` は `arrange.prep` が sandbox の外で作成(`git init` + 空コミット)。
- `file://` はローカル転送(git-upload-pack をローカル fork)なので、sandbox の network 層は一切関与しない。

## 実行内容

1. `git clone file://<ケースdir>/srcrepo cloned`(既定テンプレ)。成功時のみ `CLONEMARK.txt`、stderr は `err.txt` に捕捉
2. `git clone --template= file://<ケースdir>/srcrepo cloned2`(テンプレ無効の対照)。成功時のみ `CLONE2MARK.txt`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `git clone file://…`(local。`.git/hooks/` テンプレコピー) | allow | ❌ | S8-a と同一の fatal。clone は転送より先に init 相当(テンプレコピー)を走らせるため network 以前に落ちる |
| 2 | Bash `git clone --template= file://…`(`.git/config` 作成) | allow | ❌ | テンプレを外しても S8-f と同じ第 2 関門(`.git/config` 作成 deny)で落ちる |

## なぜそうなるか

- 捕捉した stderr(実測):
  - 1: `fatal: cannot copy '/Library/Developer/CommandLineTools/usr/share/git-core/templates/hooks/commit-msg.sample' to '.../cloned/.git/hooks/commit-msg.sample': Operation not permitted`(exit=128)
  - 2: `error: could not write config file .../cloned2/.git/config: Operation not permitted` / `fatal: could not set 'core.repositoryformatversion' to '0'`(exit=128)
- **核心: clone の失敗機構は network ではなく、init と同じ `.git/config`・`.git/hooks/` へのパス write deny。** clone はデータ転送の前に新規 repo の init(テンプレコピー → config 作成)を行うため、`file://` で network を完全に排しても同じ 2 関門で止まる。
- 遠隔 URL(https 等)の clone では **network 遮断(S6)が「さらに手前ではなく、さらに別」の関門として重なる**(仮に network を許可しても本ケースの機構で失敗する)。旧・グループ README の「clone はネットワーク遮断で失敗するのが実態のはず」という推定は**不正確**だったと実測で確定。
- plain repo への `.git` パス deny 一般則は docs に無い(S8-f と同じ【要裏取り】)。証跡は捕捉 stderr。

## 運用時の留意事項

- **clone は sandbox 内では成立しない**(local でも remote でも)。multi-repo 運用でワークスペースに repo を並べるのは prep(sandbox の外)で行う、が唯一の経路。
- 「`alloweddomains` に git ホスティングを足せば clone できる」という発想は通らない(network を通しても `.git` パス deny で落ちる)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ(srcrepo が無ければ prompt.ja.txt 冒頭の手順で先にホスト側で作る)。network 無関係に 2 つの clone が落ちる様子が確認できる。

```bash
cd cases/S8-sandbox-git-interop/h-clone-in-sandbox && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S8-sandbox-git-interop/h-clone-in-sandbox
```

> sandbox(OS 層)の I/O を観測するケース。**canUseTool は OS 境界を測れない**ため headless の disk 観測で実測する(sdk でも同結論)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) | 捕捉 stderr: 1=hooks テンプレコピーの fatal(S8-a と同一)、2=`could not write config file`(S8-f と同一)。ケース化前に scratch 最小プローブで確認 |

## 対応する知識

- docs/FINDINGS.md: 「clone は network 以前に `.git` パス deny で失敗(file:// でも不可)」
- 関連: S8-a(init の同機構)/ S8-f(`.git/config` 作成 deny の分離)/ S6(network 遮断 = 遠隔 clone の別関門)/ multi-repo-workspace.md(prep で clone を外出しする根拠)
