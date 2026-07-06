# S9. tool-write-scope（W1）— `scripts/` を守る2ベクタ: 編集系ツール deny(ハード) vs sandbox denyWrite(OS ハード)、そして `Write(dir/**)` という no-op トラップ

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。

## このグループで学ぶこと

- `multi-repo-workspace.md`（W1）は `scripts/` 保護を**2つの層**に依存させている: ①ツール層 `permissions.deny Write/Edit(scripts/**)` と ②sandbox 層 `filesystem.denyWrite`。本グループはこの**2ベクタ**を実測で撮り比べ、各層がどのツール経路を、どの強度で止めるかを確定する。
- 非自明な看板(いずれも実測):
  - **`Write(<dir>/**)` は no-op**。dir スコープの Write deny は Write ツールを**まったく止めない**(中立 5/5 作成)。P3(`Write(**)`・完全パス)と同族の no-op トラップ。→ 旧 S9-a の「`Write(dir/**)` は効く(ASK ゲート)」は**誤りで訂正**。
  - **`Edit(<dir>/**)` は編集系ツール全体をハードに止める**。Edit 規則は Write を含む編集系(Write/Edit/MultiEdit)に適用され(docs)、Write ツールも 0/5 でブロック。acceptEdits でも承認でも lift されない**ハード deny**。→ **W1 のツール層保護の“効く正体”は Edit 規則**。
  - **sandbox `denyWrite` は Bash 経路の OS ハード境界**(`allow ❌`＝EPERM)。permission は allow なのに OS が止める。Write/Edit ツールには効かない(docs: sandbox は Bash とその子プロセスのみ)。
  - → **2ベクタは別々の経路を別々の層がハードに守る**: 編集系ツール経路＝`Edit(dir/**)` deny / Bash 経路＝sandbox `denyWrite`。互いに相手の経路はカバーしない。そして `Write(dir/**)` は**どちらでもない偽の安心**。
- 効く形 `Edit(dir/...)` の**効き幅**(2026-07-06 追加実測):
  - **深度の抜け穴なし**: 単一星 `Edit(assets/*)` でも深度2(`assets/x/y.txt`)まで止まる(子ディレクトリにマッチ→サブツリー全体が拒否)。`dir/*` ≒ `dir/**`(e / a3)。
  - **モードの抜け穴なし**: `Edit(assets/**)` deny は bypassPermissions でも残存(f)。旧「ASK ゲート」説のモード軸からの反証。
  - **アンカーの抜け穴はある**: `additionalDirectories` で別ルートを足すと acceptEdits の自動承認だけ広がり、無印(cwd 起点)の `Edit(scripts/**)` は**その中にマッチしない**(d=マルチルートの罠)。ルートごとに `~/`/`//` アンカー形を書くのが修正(d2)。

## サブケース一覧

| サブ | 設定の差分（1変数ずつ） | 論点 | 詳細 |
|---|---|---|---|
| a | `deny Write(assets/**)+Edit(assets/**)` / acceptEdits（W1 元設定） | Write は止まるか・どの規則が止めるか | [a-subdir-file-write](./a-subdir-file-write/README.md) |
| a2 | ← から `Edit(assets/**)` を外す（`Write` のみ） | `Write(dir/**)` 単独の効果（G3） | [a2-write-only](./a2-write-only/README.md) |
| a3 | a2 の代わりに `Edit(assets/**)` のみ | `Edit(dir/**)` は Write も止めるか（編集系全体） | [a3-edit-only](./a3-edit-only/README.md) |
| b | ツール層 deny をやめ `sandbox.denyWrite:["assets"]` / Bash | OS 層の硬境界（別ベクタの肯定側） | [b-scripts-denywrite-bash](./b-scripts-denywrite-bash/README.md) |
| d | `additionalDirectories` + 無印 `deny Edit(scripts/**)` | 別ルートに cwd 相対 deny は届くか（G5） | [d-additionaldir-scope](./d-additionaldir-scope/README.md) |
| d2 | d の deny を `~/` アンカー形へ | マルチルートの修正形 | [d2-additionaldir-home-anchor](./d2-additionaldir-home-anchor/README.md) |
| e | a3 の glob を単一星 `Edit(assets/*)` へ | 効く形の glob 深度（G6） | [e-edit-glob-depth](./e-edit-glob-depth/README.md) |
| f | a3 のモードを bypassPermissions へ | deny × モードの相互作用（G7） | [f-bypass-hard-deny](./f-bypass-hard-deny/README.md) |

> c は**欠番**: refactor-plan 旧レイアウト（S9-workspace-guardrails）の `c-excluded-exact-allow-chain-ask` は、[S5-h](../S5-sandbox-excluded-and-unsandboxed/h-excluded-without-bashstar/README.md)（excluded × 狭 allow のチェーン = ask）が実測して充足したため本グループでは新設しない。

## 対比

同一の `assets/` を **操作(行)× 設定(列)** で撮り比べたマトリクス（セル = `許諾 結果`）:

| No | 操作 | a（deny W+E・tool） | a2（deny W・tool） | a3（deny E・tool） | b（sandbox denyWrite・OS） |
|---|---|:---:|:---:|:---:|:---:|
| 1 | Write `assets/data.txt` | **deny -** | **allow ✅** | **deny -** | （allow ✅）† |
| 2 | Edit `assets/note.txt` | deny - | allow ✅ | deny - | （allow ✅）† |
| 3 | Bash `echo x > assets/data.txt` | （allow ❌）‡ | （allow ❌）‡ | （allow ❌）‡ | **allow ❌** |

- **deny -（ハードブロック）**: 中立 control で 0/5 作成、canUseTool=allow でも 0/4、acceptEdits でも lift されない=**承認しても通らないハード deny**（`Edit(assets/**)` 由来）。in-repo は headless=INCONCLUSIVE（モデル安全拒否・Edit deny は Write ツールを toolset から除去しないので自動 DENIED にできない）/ -m sdk=DENIED_HARD。
- **allow ✅（no-op）**: `Write(assets/**)` は Write ツールを止めない（中立 5/5 作成、in-repo headless も ALLOWED）。P3 の no-op 仲間。
- **†（Write 側は実測済み・Edit 側のみ docs 由来）**: sandbox `denyWrite` は Write/Edit ツールに効かない（docs: file tools は permission 直轄、sandbox は Bash のみ）。**Write ツール側は [S1-f](../S1-sandbox-scope-vs-tools/f-write-tool-vs-denywrite/README.md) が同一命題を実測済み**（`denyWrite` 先へ Write ツールで書けた = 迂回）。Edit ツール側のみ docs 由来の推定セル。
- **‡（未実測・docs 由来）**: ツール層 deny は Bash に効かない（S1・docs。近縁の実測は [P3-f](../../01-permission/P3-write-glob-asymmetry-DANGER/f-deny-write-star-bash-redirect/README.md) = `deny Write(*)` が Bash リダイレクトを塞がない）。b 行3 の `allow ❌` が本グループ内の唯一の Bash 側実測。
- **allow ❌（b の実測）**: permission は sandbox 自動許可で通るが、OS が EPERM で実書込を遮断。canUseTool には現れない OS 境界。

### 設定を1つずつ変えると挙動がどう動くか（a を基準に）

| 手順 | 足した/変えた設定 | 変化するプローブ | 起きること |
|---|---|---|---|
| a（基準） | `deny Write+Edit(assets/**)`・tool | 1・2=deny - | Write/Edit ともハードブロック（ただし帰属が曖昧） |
| a → a2 | `Edit(assets/**)` を外す | 1: deny → **allow**（Write が通る）/ 2: deny → allow | **`Write(assets/**)` は no-op**＝止めていたのは Write 規則ではない |
| a → a3 | `Write(assets/**)` を外す | 1・2 は deny のまま | **`Edit(assets/**)` 単独で Write も Edit も止まる**＝ブロックの正体は Edit 規則（編集系全体） |
| a → b | tool deny を捨て `sandbox.denyWrite` へ | 3: （allow❌）が**実測 allow❌**に / 1・2 は OS 非対象 | 守るベクタが Bash 経路へ移り、境界が **OS 強制（EPERM）** になる |

- 変えたのは毎回1変数だけなので「変化したプローブ ⇔ 足した設定」が1対1で結びつく。a→a2 で 1 が deny→allow になったこと自体が「`Write(dir/**)` は no-op / ブロックは Edit 規則」の決定的証拠。

### 効く形 `Edit(dir/...)` の効き幅マトリクス（2026-07-06 追加実測・全セル headless+sdk）

a3 を基準に、glob 形・モード・ルート(アンカー)を1変数ずつ動かした結果（セル = `許諾 結果`）:

| 軸 | 動かした変数 | 操作 | 結果 | ケース |
|---|---|---|:---:|---|
| 深度 | glob を `assets/*`（単一星）へ | Write `assets/data.txt`（深度1） | **deny -** | e-1 |
| 深度 | 〃 | Write `assets/x/y.txt`（深度2） | **deny -**（`*` が子 dir にマッチ=サブツリー保護） | e-2 |
| 深度 | glob は `assets/**` のまま | Write `assets/x/y.txt`（深度2） | **deny -**（`**`=横断、docs どおり） | a3-2 |
| モード | acceptEdits → bypassPermissions | Write `assets/data.txt` | **deny -**（deny は bypass でも残存） | f |
| ルート | `additionalDirectories` に `~/s9d-extra` を追加 | Write `~/s9d-extra/other/x.txt` | **allow ✅**（additional dir 内は acceptEdits 自動承認） | d-1 |
| ルート | 〃（deny は無印 `Edit(scripts/**)` のまま） | Write `~/s9d-extra/scripts/x.txt` | **allow ✅** ⚠️（cwd 起点アンカー→別ルートに不マッチ=**罠**） | d-2 |
| ルート | 〃（対照: cwd 側） | Write `<cwd>/scripts/x.txt` | **deny -**（同じ規則が cwd では効く） | d-3 |
| ルート | deny を `Edit(~/s9d-extra/scripts/**)` へ | Write `~/s9d-extra/scripts/x.txt` | **deny -**（アンカー形が修正） | d2-1 |
| ルート | 〃（対照: deny 対象外） | Write `~/s9d-extra/other/x.txt` | **allow ✅**（deny は scripts サブツリー限定） | d2-2 |

- まとめ: `Edit(dir/...)` deny に**深度とモードの抜け穴は無い**が、**アンカー(ルート)の抜け穴はある**。マルチルート workspace ではルートごとにアンカー付き deny を書く。

## 要点

- **`Write(<dir>/**)` deny は書いても効かない（no-op トラップ）**。ツール層で dir を守るには **`Edit(<dir>/**)` deny**（Write/MultiEdit まで一括で効くハード deny）を書く。旧 S9-a の「`Write(dir/**)` は ASK ゲートとして効く」は誤りで、実測は「Write 規則=no-op / Edit 規則=ハード deny」。
- **`scripts/` 保護は2ベクタ併記が正解**: 編集系ツール経路は `Edit(dir/**)` deny（ハード・ツール層）、Bash 経路は sandbox `denyWrite`（ハード・OS 層）。どちらも相手の経路はカバーしない。
- **`Edit(dir/...)` deny の効き幅**: 深度の抜け穴なし（単一星でもサブツリー全体、e）・モードの抜け穴なし（bypass でも残存、f）。ただし**アンカーは cwd 起点**なので、`additionalDirectories` の別ルートには届かない（d ⚠️）——マルチルートは**ルートごとに `~/`/`//` アンカー形の deny を併記**（d2）。additionalDirectories は未 trust だと丸ごと無視される点も注意（P7-c）。
- **additionalDirectories の合成（他群で実測）**: additionalDirectories は acceptEdits 自動承認域（d）だけでなく **sandbox の Bash 書込境界も広げる**（[S2-o](../S2-sandbox-fs-write/o-additionaldir-extends-boundary/README.md) = OS 層の第5マージ源）。一方その別ルート内の**保護パス（.git）はなお ask で守られる**（[P5-k](../../01-permission/P5-protected-paths/k-additionaldir-protected/README.md)）。つまり additionalDirectories は境界を広げるが保護パスは貫通しない。
- **層の観測面**: ツール層 deny は permission エンジンの判定（SDK では DENIED_HARD、in-repo headless はモデル拒否で INCONCLUSIVE に化ける）。sandbox は OS の EPERM（`allow ❌`、canUseTool から不可視、headless で実測）。
- **P3 との関係**: 効かない Write deny 形の一覧に **`Write(<dir>/**)` も加わる**（従来 P3 は `Write(**)`・完全パスのみ）。効くのはツール除去 `Write(*)`（P2-b）と編集系 `Edit(dir/**)`。

## 対応する知識

- 勉強会セクション: refactor-plan.md §2.5（W1）/ §2.3・P3（Write deny の glob 非対称）
- 一次 docs（2026-07-05 確認）: permissions（「Edit rules apply to all built-in tools that edit files」「Deny rules apply in every mode」「scoped rule leaves the tool available and blocks matching calls」、パスは gitignore 準拠・無印=cwd 起点・`~/`=home）/ permission-modes（acceptEdits は working directory または additionalDirectories 内を自動承認）/ sandboxing（「Built-in file tools: Read, Edit, and Write use the permission system directly rather than running through the sandbox」）
- 関連: P2-b（`Write(*)`＝ツール除去 hard）/ P2-d（`Write(*)` deny × bypass ⇔ f はスコープ形×bypass）/ P3（`Write(**)`・完全パス＝no-op、`Write(dir/**)` も同族）/ P7-c（未 trust で additionalDirectories 無視 ⇔ d の trust 前提）/ S1（sandbox 自動許可は Bash 限定）/ S2（sandbox fs-write）/ SHARE-to-workspace-repo.md（「ask 止まり/no-op」懸念 → no-op 側が的中）
