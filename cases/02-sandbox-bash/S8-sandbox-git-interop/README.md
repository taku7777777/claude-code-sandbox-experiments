# S8. sandbox-git-interop — sandbox 内で git 操作の何が通り何が止まるか

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。init 失敗 stderr のテンプレパス(CLT 配下)は macOS 固有。

## このグループで学ぶこと

- sandbox 有効・`Bash(*)` 許可のもとで、git 操作は permission 層では全て通る(`allow`)。**止まるのは OS(sandbox)層**なので、対比は 2軸の `結果`(✅/❌)で読む(`allow ❌` = 許諾は通ったが OS が書込を止めた)。
- **止まるのは `.git/config`・`.git/hooks/` という「パス」への write だけ**(既存/新規・処理の種類を問わない)。テンプレコピーを外しても `.git/config` の作成で落ち(S8-f)、config が `.git/` 配下でない bare repo の init は通る(S8-f)。これ以外の `.git` 書込(worktree の作成・commit の logs/refs/objects)は通る。
- **clone も network 以前に同機構で失敗**する: ローカル `file://` clone(egress ゼロ)でも hooks テンプレコピー → config 作成の同じ 2 関門で落ちる(S8-h)。
- 本グループの看板 = **worktree の中からの `git commit` は共有 `.git` へ allowWrite 注入なしで書けて成功**(S8-d)。これは公式 docs(sandboxing.md)どおりで、旧設計主張(refactor-plan §W4「commit には `.git/` の allowWrite 注入が必要」)を**実測で否定**する。

## サブケース一覧

| サブ | 設定 / 操作(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | sandbox on + `Bash(*)` / `git init newrepo` | git init は `.git/hooks` 書込 EPERM で失敗 | [a-git-init-in-sandbox](./a-git-init-in-sandbox/README.md) |
| b | + allowWrite:[wr] / `echo >> wr/.git/config` | `.git/config` は allowWrite 内でも write 拒否 | [b-gitconfig-denied-within-allowed](./b-gitconfig-denied-within-allowed/README.md) |
| c | prep で repo 用意 / `git worktree add` | worktree add は成功(init と対照) | [c-worktree-add-in-sandbox](./c-worktree-add-in-sandbox/README.md) |
| d | prep で repo+worktree / cwd=wt で `git commit` | **共有 `.git` への commit は allowWrite なしで成功**(docs 中心命題) | [d-worktree-commit-shared-git](./d-worktree-commit-shared-git/README.md) |
| e | 同上 / 共有 `.git/config`・`.git/hooks` へ write | 共有 `.git` でも config/hooks は依然 deny(例外) | [e-worktree-shared-git-hooks-config-deny](./e-worktree-shared-git-hooks-config-deny/README.md) |
| f | a の機構分離 / `git init --template=` と `--bare --template=` | deny はテンプレ処理でなく **`.git/config`・`.git/hooks/` のパス**(bare は成功) | [f-init-mechanism-probe](./f-init-mechanism-probe/README.md) |
| h | prep で srcrepo / `git clone file://…`(±`--template=`) | clone は **network 以前に**同パス deny で失敗(local でも不可) | [h-clone-in-sandbox](./h-clone-in-sandbox/README.md) |

(g は欠番: 旧 GAPS G3 が提案した「plain repo `.git/hooks` への Bash write deny」は、e の shared-hooks プローブ(mainrepo=plain な main repo への直接 write)と a の捕捉 stderr(newrepo/.git/hooks への copy が EPERM)で充足済みのため新設しない。)

## 対比

各行 = 実測した git 書込操作、セル = `許諾 結果`(sandbox on・`Bash(*)`)。すべて実測:

| No | 操作(書込先) | 許諾/結果 | 機構(捕捉 stderr / 出力) |
|---|---|:---:|---|
| 1 | `git init newrepo`(`.git/hooks/*.sample`) | allow ❌ | `fatal: cannot copy ... .git/hooks/commit-msg.sample: Operation not permitted`(S8-a) |
| 2 | `echo >> wr/.git/config`(allowWrite 内) | allow ❌ | `operation not permitted: wr/.git/config`(S8-b) |
| 3 | `git worktree add ../wt2`(`.git/worktrees/`) | allow ✅ | `Preparing worktree ... / HEAD is now at ...`(S8-c) |
| 4 | `git commit`(cwd=worktree、共有 `.git` の logs/refs/objects) | allow ✅ | `[wt ....] x`(S8-d、allowWrite 注入なし) |
| 5 | `echo >> mainrepo/.git/config`(共有 `.git`) | allow ❌ | `operation not permitted: mainrepo/.git/config`(S8-e) |
| 6 | `echo > mainrepo/.git/hooks/pre-commit`(共有 `.git`) | allow ❌ | `operation not permitted: .../hooks/pre-commit`(S8-e) |
| 7 | `git init --template=`(`.git/config` の新規作成) | allow ❌ | `error: could not write config file .../.git/config: Operation not permitted`(S8-f) |
| 8 | `git init --bare --template=`(config は `barerepo/config`) | allow ✅ | `Initialized empty Git repository`(S8-f。config が `.git/` 配下でないと通る) |
| 9 | `git clone file://…`(local。`.git/hooks/*.sample`) | allow ❌ | 1 と同一の `fatal: cannot copy ...`(S8-h。network 非関与) |
| 10 | `git clone --template= file://…`(`.git/config` 作成) | allow ❌ | 7 と同一の `could not write config file`(S8-h) |

読み: **deny されるのは `.git/config` と `.git/hooks/` という「パス」への write だけ**(1,2,5,6,7,9,10)。既存への追記(2,5)も新規作成(7,10)も同じく EPERM で、config が `.git/` 配下に無い bare repo(8)は通る = deny はパス形状で決まる。それ以外の `.git` 書込(3=worktrees、4=logs/refs/objects)は通る。`git init` が失敗する(1)のは cwd への書込全般ではなく deny パスに最初に触れる write(テンプレコピー)で落ちるからで、テンプレを外しても次の deny パス(config 作成=7)で止まる。clone(9,10)も同じ 2 関門で、network 遮断(S6)は遠隔 URL のときに重なる別関門にすぎない。

### 設定を1つずつ変えると挙動がどう動くか(a を基準に)

| 手順 | 変えたもの | 変化 | 起きること |
|---|---|---|---|
| a(基準) | `git init`(新規 repo) | 1 = allow ❌ | `.git/hooks` テンプレ書込が EPERM。repo は sandbox 内で作れない |
| a → b | allowWrite で repo を覆い、`.git/config` へ write | 2 = allow ❌ | 書込許可領域の内側でも `.git/config` は deny(Denied within allowed) |
| a → c | prep で repo を用意し worktree add | 3 = allow ✅ | `.git/config`/`.git/hooks` 非接触なので通る(init との差はコピー先) |
| c → d | worktree の中(cwd=wt)で commit | 4 = allow ✅ | 共有 `.git` の logs/refs/objects へ write が通る(**allowWrite 注入不要**) |
| d → e | 共有 `.git` の config/hooks へ直接 write | 5,6 = allow ❌ | 共有 `.git` でも config/hooks だけは deny のまま(例外) |
| a → f | init のテンプレコピーを `--template=` で外す | 7 = allow ❌ / 8 = allow ✅ | 次の deny パス(`.git/config` 作成)で止まる。bare(config が `.git/` 外)は成功 = deny はパス形状 |
| a → h | init を clone(local `file://`)に替える | 9,10 = allow ❌ | network ゼロでも init と同じ 2 関門(hooks コピー → config 作成)で失敗 |

## 層の注意(P5 との違い)

- 本グループはすべて **Bash 経由**(`Bash(*)` で permission は auto-allow)。よって deny はすべて **sandbox / OS 層**で、2軸では `allow ❌`。
- **P5**(protected-paths)は Read/Edit/Write **ツール**に対する **permission 層**の `.git` 保護。層が異なる(ツール層は bypass/モードで挙動が変わりうるが、sandbox 層は OS で硬い)。
- 公式 docs(sandboxing.md)が `.git/config`/`.git/hooks` の deny を明記するのは **linked worktree の共有 `.git`**(S8-d/e の文脈)のみ。**plain repo(非 worktree)への `.git/config`・`.git/hooks/` パス deny 一般則(S8-a/b/f/h)は docs に無い** → 事実は実測(EPERM。新規作成にも効き bare は通る=パス形状)で確定、層は断定しない(`【要裏取り】`)。

## 要点

- **prep(sandbox の外)が要るのは init / clone だけ**。worktree add(S8-c)も worktree 内 commit(S8-d)も sandbox 内で通る。init/clone に `--template=` 回避策は無く(S8-f/h)、外出しは機構レベルで必然。
- **worktree commit に `.git/` の allowWrite 注入は不要**(S8-d)。docs どおりで、refactor-plan §W4 の逆主張は本環境の実測で否定。ただし共有 `.git` の `config`/`hooks` は依然 deny(S8-e)なので、hook 注入経路は塞がれたまま。
- **clone の失敗は network 遮断が原因ではない**(S8-h で実測)。local `file://` でも init と同じ `.git` パス deny(hooks コピー → config 作成)で落ちる。遠隔 URL では network 遮断(S6)が別関門として重なるだけで、network を許可しても clone は通らない。
- 例外として **bare repo は sandbox 内で作れる**(S8-f。config が `.git/` 配下でないため)。「repo を一切作れない」とは過信しないこと。

## 対応する知識

- docs/FINDINGS.md: git init 失敗 / `.git/config` deny / worktree add 成功 / worktree commit 成功 / 共有 `.git` の config・hooks deny / init・clone の機構=パス deny(bare は通る・clone は network 非依存)
- 一次 docs: sandboxing.md「Filesystem isolation → Git worktrees」(共有 `.git` 許可・hooks/config は deny・read=全域)
- 関連: P5(`.git` 保護パス=permission 層)/ S3(sandbox のシステムパス)/ S6(network 遮断=遠隔 clone の別関門)/ refactor-plan §W4・multi-repo-workspace.md(doc 同期済み)
