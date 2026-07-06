# P7. settings-scope-precedence — スコープ間マージは順位どおり、deny だけが順位を飛び越え、未 trust は allow だけ無効化する

## このグループで学ぶこと

- settings のスコープ precedence は **managed > CLI 引数 > local(`.claude/settings.local.json`) > project(`.claude/settings.json`) > user(`~/.claude/settings.json`)**(公式 docs permissions / Settings precedence)。同一キー(`defaultMode`)の衝突は順位どおり上位が採用される(b: local > project / d: CLI > project、実測)。
- ただし **deny はどのスコープからでも勝つ**(a: user deny が project allow をハード拒否、実測)。公式原文: *"deny rules from any scope are evaluated before allow rules"*。precedence は「マージ順」、deny は「評価順」の別ルール。
- **workspace trust**: project settings の `allow` / `additionalDirectories` は trust 承認後にのみ適用。`-p`(headless)ではダイアログが出ず**無視されたまま**(c、実測。stderr に "Ignoring N permissions.allow entry ... not been trusted" 警告)。**deny/ask は trust に縛られない**(c の対照プローブで実測)。
- **managed(precedence #1)は本リポジトリの射程外**(配置に管理者権限/MDM が要る)。`--settings <file>` は precedence 上「CLI 引数」に属し **#2(managed の下・local の上)**(公式 docs permissions / Settings precedence で確認、2026-07-06)。本リポジトリでは未実測(扱うなら探索ケース)。

## サブケース一覧

| サブ | スコープ配置(project 側 / 他スコープ側) | 論点 | 詳細 |
|---|---|---|---|
| a | project: `allow=[Write(*)]` / **user**: `deny=[Write(*)]` | deny はどのスコープからでも勝つ | [a-user-deny-vs-project-allow](./a-user-deny-vs-project-allow/README.md) |
| b | project: `defaultMode=plan` / **local**: `defaultMode=acceptEdits` | local は project に勝つ(precedence) | [b-local-over-project](./b-local-over-project/README.md) |
| c | project: `allow=[Write(*)]` + `deny=[Bash(*)]`(**未 trust**) | 未 trust では allow だけ無視され deny は効く(workspace trust) | [c-workspace-trust-headless](./c-workspace-trust-headless/README.md) |
| d | project: `defaultMode=plan` / **CLI**: `--permission-mode acceptEdits` | CLI 引数は project に勝つ(precedence) | [d-cli-over-project](./d-cli-over-project/README.md) |
| e | project: `deny=[Write(*)]` / **user**: `allow=[Write(*)]` | deny はどちらのスコープでも勝つ(a の鏡像) | [e-project-deny-vs-user-allow](./e-project-deny-vs-user-allow/README.md) |
| f | project: `allow=[Write(*)]` / **user**: `ask=[Write(*)]` | ask もスコープ横断で allow に勝つ(deny-first の ask 版) | [f-ask-user-vs-project-allow](./f-ask-user-vs-project-allow/README.md) |

## 対比(実測)

同一プローブ(Write で `PROOF.txt` 作成)を各スコープ配置で(セル = `許諾 結果`、結果は approve 前提):

| | a(user deny × project allow) | b(local × project の defaultMode) | c(未 trust の project allow) | d(CLI × project の defaultMode) | e(project deny × user allow) | f(user ask × project allow) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 許諾 結果 | **deny -** | allow ✅ | **ask** ✅ | allow ✅ | **deny -** | **ask ✅** |
| 効いている機構 | deny のスコープ横断勝ち(評価順) | precedence local > project(マージ順) | workspace trust(allow のみゲート) | precedence CLI > project(マージ順) | deny のスコープ横断勝ち(a の鏡像) | ask のスコープ横断勝ち(評価順の中間項) |

- a は「precedence の**例外**(deny は順位を飛び越える)」、b・d は「precedence **本体**(順位どおり)」、c は「project スコープの allow が**そもそも有効化されない**条件」——T2 のスコープ次元を三方向から実測で埋めた。
- **e/f は評価順(deny→ask→allow)がスコープ横断でも成立することを両端で固める**: e=deny(a の allow/deny を入替えた鏡像。※ deny が上位 project にあり単独では precedence と非分離 — 分離は a 側) / f=ask(P6-b の同一スコープ ask>allow をスコープ横断へ拡張。SDK で canUseTool=Write 発火 + onAsk=allow で書込完遂 = ask ✅)。
- c の同居対照(未 trust + project `deny Bash(*)` → **deny のまま**)が「trust がゲートするのは緩める方向だけ」を実証。
- 全セル SDK 併測済み(a: DENIED_HARD / b: byModality=ASK — SDK は settings の defaultMode を適用しないため / c: ASK + DENIED_HARD / d: ALLOWED / e: DENIED_HARD / f: ASK(askFired=Write))。

## 要点(実測で確定)

- deny の優先は同一スコープ内(P2-b)だけでなく**スコープをまたいでも**成立する(a、鏡像 e)。実測では deny 対象ツールが**ツールセット自体から除去**される(init tools に不在)。**中間項 ask も同じくスコープ横断で allow に勝つ**(f: user ask × project allow → ask ✅)——評価順 deny→ask→allow はマージ後の規則集合に効き、スコープ順位(precedence)とは独立。
- 同一キーの衝突は precedence 順にマージされる(b・d)。`settings.local.json` は v2.1.196–199 に扱いのリグレッション歴あり・v2.1.200 で復元(実測は 2.1.201。バージョン記録必須)。
- 「project に allow を書いたのに `-p` で効かない」は workspace trust による仕様挙動(c)。CI/headless 運用の落とし穴。trust は **git repo root 単位**で config dir の `.claude.json`(`projects[<root>].hasTrustDialogAccepted`)に保存される(実測)。未 trust の帰属は stderr の Ignoring 警告で直接観測できる。
- 検証インフラの知見: user スコープ/trust 状態は**分離 `CLAUDE_CONFIG_DIR`**(credentials コピー + trust 制御)で実環境を汚さず制御できる(ハーネス `arrange.configDir`)。local スコープは `arrange.localSettings`(実行中だけ生成・撤去)。**SDK は明示しない限り project スコープしか読まない**(`settingSources`。a の実測で確認)。

## 対応する知識

- 関連: P2(単一スコープ内の allow/deny 優先)/ P1(defaultMode)/ P6(ask の形態依存)/ P8(サブエージェントへの継承)
