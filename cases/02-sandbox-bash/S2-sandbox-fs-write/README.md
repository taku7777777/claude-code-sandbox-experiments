# S2. sandbox-fs-write — Bash 書込は allowlist(cwd + 付替え $TMPDIR が既定。permission 規則もマージ)

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。特に $TMPDIR 付替え(j)と `/tmp`→`/private/tmp` symlink 解決(k)は macOS 固有機構。

## このグループで学ぶこと

- sandbox の Bash 書込は **ホワイトリスト方式**。既定境界は cwd + **付け替えられた `$TMPDIR`**(実測 `/tmp/claude-<uid>`。リテラル `/tmp` 直下は書けない=j)だけで、`allowWrite` にフルパスを足して穴を開ける。
- **実効境界はそれだけではない**: permission の Edit/Write 系 allow 規則が sandbox 境界に**マージ**される(h)。さらに **`permissions.additionalDirectories` も第5のマージ源**(o、trust 済み)。
  実効 write 境界 = **cwd + 付替え $TMPDIR + allowWrite ∪ Edit 系 allow 規則 ∪ additionalDirectories**。
- 境界外の書込は **`allow ❌`** — permission は sandbox 自動許可で通るのに、OS サンドボックスが EPERM で実 write を止める(承認プロンプト=ask は出ない。SDK で askFired 空を実測)。
- 罠と限界: `denyWrite:["~"]` は cwd 暗黙許可まで潰す(d)/ `allowWrite` の `*` はリテラルで no-op(e)/
  **deny は常勝で、名指しの再 allow でも開けられない**(g, i。read 側の `allowRead` とは非対称)/
  deny はスコープ横断でも外せない(l)/ settings ファイル(project / local / user 全スコープ)は自己保護で書けず、
  **allowWrite で名指しで開けても破れない**(f, m)。

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | sandbox on(allowWrite なし) | ベースライン。cwd 内だけ書ける・cwd 外は `allow ❌` | [a-inside-cwd](./a-inside-cwd/README.md) |
| b | + `allowWrite:["~/lab-fs-write"]` | 列挙したフルパスだけ開く | [b-allowwrite-adds](./b-allowwrite-adds/README.md) |
| c | sandbox on(a と同設定) | 「cwd 外は拒否」の明示 + `allow ❌`(≠ask)を SDK で確定 | [c-outside-cwd](./c-outside-cwd/README.md) |
| d | b + `denyWrite:["~"]`(アンチパターン) | cwd 暗黙許可も allowWrite 例外も潰れる | [d-denywrite-pitfall](./d-denywrite-pitfall/README.md) |
| e | `allowWrite:["~/lab-glob-*"]`(glob 風) | `*` はリテラル → no-op(列は a と同一) | [e-glob-literal](./e-glob-literal/README.md) |
| f | sandbox on(プローブ先が settings ファイル群) | **自分の settings.json / settings.local.json への write は自動 deny**(自己保護。解決済みスコープの実ファイル単位 — 入れ子 `sub/.claude/settings.json` は対象外) | [f-settings-self-protect](./f-settings-self-protect/README.md) |
| g | `allowWrite:["~/lab-nest"]` + `denyWrite:["~/lab-nest/sub"]` | 外は書けて内だけ deny 勝ち | [g-nested-deny-wins](./g-nested-deny-wins/README.md) |
| h | sandbox on + `permissions.allow:["Edit(~/lab-permrule/**)"]` | **Edit 規則が sandbox 書込境界にマージ**され cwd 外に書ける | [h-permrule-merges-into-sandbox](./h-permrule-merges-into-sandbox/README.md) |
| i | g + `allowWrite` に `~/lab-nest/sub/inner` を追加 | **deny 領域内の再 allow は無効**(write 側に allowRead 相当なし) | [i-reallow-inside-deny](./i-reallow-inside-deny/README.md) |
| j | sandbox on(プローブ先が $TMPDIR / リテラル /tmp) | 既定境界の tmp 側 = **付替え先だけ**書ける | [j-tmpdir-default](./j-tmpdir-default/README.md) |
| k | `allowWrite:["/private/tmp/…","/tmp/…"]`(表記の対) | **絶対パスは symlink 解決して照合**(socket=S6-f と非対称) | [k-abs-path-resolution](./k-abs-path-resolution/README.md) |
| l | project `allowWrite:["~/lab-merge"]` × user `denyWrite:["~/lab-merge/sub"]` | **スコープ間は配列マージ**。project の allow で user の deny は外せない | [l-scope-merge](./l-scope-merge/README.md) |
| m | `allowWrite:["~/.claude", "~/.claude/settings.json"]`(settings を名指し allow) | **自己保護 deny は明示 allow より強い**(組込 deny > allowWrite)。user スコープも保護 | [m-allowwrite-vs-selfprotect](./m-allowwrite-vs-selfprotect/README.md) |
| n | project `denyWrite` × **local** `settings.local.json` の `permissions.allow:["Edit(...)"]` | **local の permission 規則も sandbox 境界にマージ = 穴が開く**(「don't ask again」の書込先)。釘付けは project の denyWrite | [n-local-permrule-hole](./n-local-permrule-hole/README.md) |
| o | `additionalDirectories:["~/lab-f4-addir"]`(trust 済み) | **additionalDirectories も sandbox 書込境界にマージ**。cwd 外でも記載ルートは Bash で書ける・記載外は EPERM | [o-additionaldir-extends-boundary](./o-additionaldir-extends-boundary/README.md) |

## 対比

セル = `許諾 結果`。probe=`fs-write`(対象パスがディスクに出来たかで判定。j-1 のみ付替え先が事前に知れないため番兵の読み戻し=fs-read 方式)。sandbox の OS 境界は denials を出さず EPERM で止めるため、判定は副作用の有無で行う(SDK でも境界外書込は askFired 空=ask ではない)。

### 全体マトリクス(a〜e: 共通3プローブ)

| No | 操作(書込先) | a(cwd only) | b(+allowWrite ~/lab-fs-write) | c(a と同設定) | d(+denyWrite ~) | e(allowWrite glob) |
|---|---|:---:|:---:|:---:|:---:|:---:|
| 1 | cwd 内 `inside.txt` | allow ✅ | allow ✅ | allow ✅ | allow ❌ | allow ✅ |
| 2 | `~/lab-fs-write/probe.txt` | allow ❌ | allow ✅ | allow ❌ | allow ❌ | allow ❌ |
| 3 | `~/lab-glob-XYZ/probe.txt` | allow ❌ | allow ❌ | allow ❌ | allow ❌ | allow ❌ |

全 15 セル実測(headless / sdk 一致)。**c 列は a 列と同一**(同設定)で、c の役割は ❌ の内訳が `allow ❌`(OS ブロック)であることを SDK で確定すること。**e 列も a 列と同一**(glob allowWrite が no-op)。

### f〜m: 境界の中身と合成規則(各2プローブの対。f は 2 対 4 プローブ)

| サブ | プローブ 1(本命) | プローブ 2(対照) |
|---|---|---|
| f | `.claude/settings.json` 追記 = allow ❌(自己保護) | `.claude/other.txt` = allow ✅(保護はファイル単位) |
| f' | `.claude/settings.local.json` 追記 = allow ❌(local スコープも保護) | 入れ子 `sub/.claude/settings.json` = allow ✅(パターン保護ではなく解決済みスコープの実ファイル) |
| g | `~/lab-nest/sub/f.txt`(deny 領域)= allow ❌ | `~/lab-nest/f.txt`(allow 内・deny 外)= allow ✅ |
| h | `~/lab-permrule/probe.txt`(Edit 規則あり)= allow ✅ | `~/lab-permrule-ctrl/probe.txt`(規則なし)= allow ❌ |
| i | `~/lab-nest/sub/inner/f.txt`(名指し再 allow)= allow ❌ | `~/lab-nest/f.txt`(外周)= allow ✅ |
| j | `"$TMPDIR"/lab-tmp-probe.txt` = allow ✅(付替え先 `/tmp/claude-501`) | リテラル `/tmp/lab-tmp-literal.txt` = allow ❌ |
| k | `/tmp/lab-abs-resolved/f.txt`(設定は `/private/tmp` 表記)= allow ✅ | `/tmp/lab-abs-literal/g.txt`(設定は `/tmp` 表記)= allow ✅(両表記とも解決) |
| l | `~/lab-merge/sub/f.txt`(user deny × project allow)= allow ❌ | `~/lab-merge/f.txt`(deny 外)= allow ✅ |
| m | `~/.claude/settings.json` 追記(名指し allowWrite あり)= allow ❌ | `~/.claude/lab-m-probe.txt` = allow ✅(allowWrite 自体は効いている) |
| n | `~/lab-localrule/probe.txt`(**local** の Edit 規則のみ)= allow ✅(穴) | `~/lab-localrule-ctrl` = allow ❌(規則なし)/ `~/lab-localrule-pin` = allow ❌(**project denyWrite が local allow に勝つ**) |

どの行も「本命 ❌ × 対照 ✅」(k は両 ✅ が結論)の対で、**その ❌ が設定・合成規則のせい**(そもそも書けない環境ではない)と1ケース内で確定する。

### 設定を1つずつ変えると(a を基準に)

各列は前の設定に1変数だけ足したもの。足した設定と、それで変化するプローブの対応:

| 手順 | 足した設定 | 変化するプローブ | 起きること |
|---|---|---|---|
| a(基準) | sandbox on のみ | 1=✅ / 2=❌ / 3=❌ | 書けるのは cwd(+付替え $TMPDIR)だけ。cwd 外は `allow ❌` |
| a → b | + `allowWrite:["~/lab-fs-write"]` | **2: ❌ → ✅** | ホワイトリストが**その1パスだけ**開ける(3 は不一致で ❌ のまま) |
| b → d | + `denyWrite:["~"]` | **1: ✅ → ❌ / 2: ✅ → ❌** | deny が勝ち、~ 配下(cwd も allowWrite 先も)が全滅 |
| a → e | `allowWrite:["~/lab-glob-*"]` | 変化なし(3 は ❌ のまま) | **`*` はリテラル**。`lab-glob-*` という名の dir にしか効かず `lab-glob-XYZ` は不一致 → a と同一 |
| a → h | + `permissions.allow:["Edit(~/lab-permrule/**)"]` | (h-1: ❌ → ✅) | **permission 規則が sandbox 境界にマージ**され、そのパスが開く |
| g → i | + `allowWrite:["~/lab-nest/sub/inner"]` | 変化なし(i-1 は ❌ のまま) | **deny 領域内の再 allow は無効**(deny 常勝) |

- 変化しない対照: プローブ3(`~/lab-glob-XYZ`)は a〜e 全列で ❌(どの設定もこのパスを開けない。b は別パスを開け、e の glob は no-op)。
- 変えたのは毎回1変数なので「変化したプローブ ⇔ 足した設定」が1対1に結びつき、原因が確定できる。

## 要点

- **書込は allowlist**。開けたいパスは `allowWrite` に**フルパスで**列挙する(`*` は効かない=e で確定 → refactor-plan §2.3)。
- **実効境界は「cwd + 付替え $TMPDIR + allowWrite ∪ permission の Edit 系 allow 規則 ∪ additionalDirectories」**(h/o)。**cwd 境界を動かす `additionalDirectories` は OS 層の書込境界も動かす**(o) — 監査では allowWrite/Edit allow だけでなく additionalDirectories も write 境界の構成要素として見る。
  `allowWrite` を絞っても `permissions.allow` の Edit/Write 系規則で穴が開く — 監査は両方を見る。
  **規則のスコープは問わない**(n): レビューを通らない `settings.local.json` の allow 規則
  (承認ダイアログの「don't ask again」の書込先)でも OS 層の境界が広がる。
  **死守したいパスは project の `denyWrite` で釘付けする**(n: deny 常勝は「filesystem の deny vs
  permission 規則由来の allow」の層跨ぎ・「project deny vs local allow」のスコープ跨ぎでも成立)。
  なお write 側には read の `allowManagedReadPathsOnly` に当たる管理ロックダウンが無い(docs 2026-07-06 時点)
  ため、この denyWrite が実質唯一の釘。
- **境界外は `allow ❌`**。permission は通っても OS 層が EPERM で止め、承認フォールバック(ask)は起きない(c を SDK で確定)。対話で承認しても通らない。cf S5-c(allow + `allowUnsandboxedCommands` があると脱出する)。
- **`denyWrite:["~"]` は使わない**(d)。deny が allow に勝つため、allowWrite 例外も cwd 暗黙許可も両方潰す。
- **write 側の deny は常勝**: 内側の名指し再 allow も無効(i)、スコープをまたいでも project 側から外せない(l = 配列マージ)。deny の中に allow の島は作れない — 「一部だけ書かせたい」は allowWrite を絞る設計に倒す。
- **tmp 側の暗黙許可は付替え先 `$TMPDIR` に付く**(j)。リテラル `/tmp` ハードコードは失敗する。
- **パス照合は symlink 解決済みの実パス**(k)。FS では `/tmp` 表記でも効く(socket=S6-f は非解決で非対称)。
- **settings ファイルは自己保護**(f, m)。sandbox 中の Bash が自分の境界設定を書き換える経路は既定で閉じている。
  保護は project / local / user の**全スコープ**に効き(f=project・local / m=user)、`allowWrite` で
  ディレクトリや settings.json のフルパスを名指しで開けても**破れない**(m。組込 deny > 明示 allow —
  docs は自己保護の存在のみ明記で優先関係は【docs 未記載】→ 実測で確定)。ただし保護対象は
  「そのセッションでスコープとして解決される settings ファイル」だけで、cwd 内の入れ子
  `sub/.claude/settings.json` のような**スコープ外の settings ファイルは保護されない**(f)。
  スコープの読込有無にも依存しない(SDK が user/local を読まない構成でも EPERM)。
- read/write は非対称: 書込=allowlist、読取=blacklist(→ S3)。**再許可も非対称**: read の `allowRead` は deny 内を開けられる(S3-b)が write には無い(i)。
- パスのプレフィックス体系(一次 docs): sandbox FS は `/`=絶対 / `~/`=home / `./`・無印=**project settings なら project root、user settings なら `~/.claude`** 起点。permission 規則の `//`=絶対・`/`=settings 起点とは**別体系**。S2 実測済みは `~/`(a〜i,l)と `/` 絶対(j,k)。無印のスコープ差は未実測。

## 対応する知識
- docs/FINDINGS.md: Q2(sandbox の Bash 書込境界)+ 追補4(f〜l の合成規則)
- refactor-plan.md §2.3(glob リテラル決着)
- 一次 docs: sandboxing(既定境界 = cwd + 付け替え `$TMPDIR` / permission 規則と sandbox 境界のマージ / settings.json 自己保護 / スコープ間の配列マージ)、permissions(deny 優先)
- 関連: S4(autoAllowBashIfSandboxed = 自動許可の出所)/ S3(read=blacklist・allowRead の再許可)/ S9-b(sandbox denyWrite の Bash `allow ❌`)/ S1(Write ツールは sandbox 対象外)/ S6-f(socket パスは非解決)/ S7(スコープ合成は credentials も同型)/ P7(permission 層のスコープ precedence)
