# COVERAGE — 設定キー × グループ × 検証状態

検証環境: **Claude Code 2.1.201 / Agent SDK 0.3.200 / macOS(`sandbox-exec`)/ 2026-07-05**
現況（`results/summary-*.json` は**非コミットの生成物**で `harness/run.py` の実行が再生成する。全体現況は保存済み per-case results から `harness/aggregate_summary.py` で再集計する。**下記はスナップショット; リポジトリは実測拡充中なので最新値は再集計コマンドで取得**）:

- **21 グループ / 181 サブケース**（2026-07-05 集計・再集計 2026-07-06。`aggregate_summary.py` 再集計。確定値は必ず再集計コマンドで）。
- headless 実測 **181**（**一致 181** / **未実測箱 0** / **未解決 INCONCLUSIVE 0**）。
- **未実測の箱 0**: **P8（subagent 継承 a〜e, 7 サブケース 9 プローブ）も 2026-07-05 に実測完了**（headless 9/9 + SDK 9/9。ハーネス拡張は不要だった — 委譲はプロンプト指示・観測はディスク副作用+構造シグナルで充足）。P6（ask グループ）・P7（スコープ横断 a〜f）・P9（hooks × permission a〜f。evidenceFile 拡張で hook 発火証跡を観測)も同日実測完了（headless+SDK, 箱から昇格）。
- SDK 併測 **178（一致 178・S7-g/i/k のみ未併測）**: 各グループに付与済み（S9 のハード deny プローブ〔a/a3/d-3/d2-1/e/f、2026-07-06 拡充分含む〕のみ headless が構造的 INCONCLUSIVE=by-design、機構は SDK=DENIED_HARD で確定）。
- **未解決 INCONCLUSIVE 0**: 旧 S6-h / S7-c / S9-a / S9-a3 / S2-c はすべて解消（S9-a/a3 の headless は by-design の構造的 INCONCLUSIVE で expected 一致、SDK 権威）。詳細は下表「§ 未確定・要再測（INCONCLUSIVE）」。P4-d・S5-c・e-bypass-git も解消済み。

> summary は「直近実行分だけ」を丸ごと上書きする（run.py 仕様）ため部分実行で断片化する。全体現況は `python3 harness/aggregate_summary.py` で保存済み per-case results から再集計する（モデル非実行）。件数はリポジトリの実測拡充で日々動くので、確定値はコマンド出力を正とする。

凡例: ✅=検証済 / 🟡=部分（未実測サブケースを含む） / 🔬=未実測箱 / ⬜=未着手 / ✅=許可 ❌=ブロック(結果列)

## permission 層（P*）

| キー / 論点 | グループ | 状態 | 確定した挙動 |
|---|---|:---:|---|
| mode: default / acceptEdits | P1 a,b | ✅ | default=承認要求(headless ❌)・**読取は素通し**（a read プローブ） / acceptEdits=編集自動承認。SDK 併測あり |
| mode: plan / dontAsk / bypassPermissions | P1 c,d,e | ✅ | plan=読取専用で書込せず ❌（**SDK: canUseTool 非発火=誘導**。読取は ✅） / dontAsk=未承認は即 deny（**SDK: 非発火 hard deny=deny-not-ask 確定**） / bypass=プロンプト省略 ✅。c,d,e とも SDK 併測あり |
| mode: auto（research preview） | P1 f | ✅ | 本環境（個人アカウント・enablement 無）ではフラグは受理されるが auto-approve は発現せず default 相当（全 write が ask）。SDK 併測あり |
| mode × allow 交差 / acceptEdits の Bash FS / defaultMode 経路 | P1 g,h,i | ✅ | **allow 済みは dontAsk でも通る**（g、CI レシピの肯定対照）/ **acceptEdits は Bash `mkdir`/`touch` も自動承認・cwd 境界も同じ**（h）/ **settings の `defaultMode` は CLI と同結果**（i。ただし **SDK ではモードは `options.permissionMode` のみ**＝settings から持ち上がらない, byModality 記録）。g,h,i とも SDK 併測あり |
| allow/deny 優先(deny>allow) | P2 a,b | ✅ | deny がマッチすれば勝つ |
| deny × mode 交差（T3） | P2 c,d | ✅ | **deny Write(*) は acceptEdits でも勝つ**（c、ただし deny は tool スコープで Edit は acceptEdits で通る）/ **deny は bypass でも勝つ**（d）。SDK 併測あり |
| allow の再 allow 不可（deny 内側） | P2 e | ✅ | 広い allow の内側に deny があると再 allow できない（deny 勝ち）。SDK 併測あり |
| `Tool(param:value)` パラメータマッチ / tool 名ワイルドカード | P2 f,g,h | ✅ | **`Bash(run_in_background:true)` deny=引数付き呼び出しだけ block・省略時は不マッチ**（f）/ **`Bash(command:...)` deny は無言で無効**＝素通り（g、起動時警告は stderr のみ）/ **`deny:["*"]`=全ツール除去**（h、init tools 欠落で構造検出）。f,g,h とも SDK 併測あり。残: `mcp__*`（MCP fixture 要） |
| Write glob 非対称（**危険**） | P3 a,b,c,d | ✅ | `Write(*)`/bare `Write`=効く、**path 限定は全 no-op**（`Write(dir/**)`・`Write(**)`・完全パス・単一星・絶対・`~`。相対 `dir/**` も S9-a で反証）。dir を締めるのは `Edit(dir/**)`。P3-d は SDK 併測あり |
| Write path 保護の正解形 / deny の経路射程 | P3 e,f | ✅ | **個別ファイルは `deny Edit(path)` で守る**（e＝Edit 規則は Write ツールにも適用, SDK=DENIED_HARD。headless は denials 非記録で INCONCLUSIVE=byModality 明示）/ **`deny Write(*)` は Write 経路のみ, Bash リダイレクトは素通り**（f）。全経路遮断は Edit deny + sandbox denyWrite。e,f とも SDK 併測あり |
| **Edit 規則のパスアンカー形 × 呼び出しパス表記** | P12 a〜g | ✅ | **相対規則は絶対パス呼び出しにマッチ**（deny=a・allow=f＝**エスケープ不成立**）/ **`..` 非正規化でも捕捉**（b＝正規化後照合）/ **絶対アンカーは `//`（d）と `~/`（e）が効く**が **単一スラッシュ `/abs/…` は allow/deny とも無言 no-op**（c/g ⚠️＝P3 の Write no-op と同系）。効く形の優先は相対 > `~/`・`//`。headless+SDK 全一致（2026-07-06）。GAPS「パスアンカー `//`・`/`」解消 |
| bash 照合（直接/チェーン/区切り/ラッパー剥がし/prefix/read-only 集合） | P4 a,b,c,d,e,g,i | ✅ | チェーンは `&&`/`;`/`\|` どの区切りでも防げる（b,g）。**ラッパーは一律でない**: `nice`/`timeout`/`nohup` 等の**剥がされるラッパーは deny に当たり止まる**（e）／`sh -c`・`$(...)` 等の**剥がされないラッパーはすり抜け**（c）。**d（allow prefix はチェーン先に及ばない）は SDK で ASK 確定**。**read-only 集合(cat/ls/echo)は規則ゼロでも無条件承認・集合外(touch)は ask**（i、d の echo 交絡を切り分け）。全セル実測（a,b,c,d,e,g,i すべて SDK 併測）。未カバー(documented-only): 環境ランナー(`npx`/`devbox run`)無差別通過・語境界(`lsof` が read-only 分類のため ask 差で示せず) |
| protected paths | P5 a,b,c,d,e,f,g,h,i,j,k | ✅ | **モード3区分を全実測**: default/acceptEdits/plan=**ask**（a,c,d。SDK=ASK）/ **dontAsk=即 deny**（g。SDK=canUseTool 非発火）/ **bypass=skip=✅**（e）。**allow `Write(*)` でも事前承認不可**（f=ask のまま）。保護は**ファイル**（`.mcp.json`＝h）と **Bash 面**（`touch .git/...`＝j）にも及び、例外は `.claude/worktrees` のみ（i=allow）。通常ネストは ✅（b）。**`additionalDirectories` の別ルート内でも保護パスは ask**（k=通常書込は acceptEdits で allow ✅／`.git/hooks/` は ask＝保護は additionalDir にも上流で及ぶ・防御側。2026-07-06）。全ケース SDK 併測（2026-07-05〜06, v2.1.201）。未カバー: auto（eligibility 対象外）/ Bash リダイレクト面（docs 明文なし） |
| **ask 規則の 3 値（T1）** | P6 a,b,c,d,e,f,g,h | ✅ | **評価順 deny→ask→allow を 3 辺とも実測**: ask>allow（b）/ **deny>ask（f＝SDK 非発火）**。モード掃引: acceptEdits（c）/ bypass（d）は ASK 残存、**dontAsk は即 deny**（e＝SDK 非発火）。**Bash specifier ask はチェーン越しにも効く**（g: touch=ASK / mkdir 対照=ALLOWED / チェーン=ASK）が、**パス限定 `Write(sub/**)` ask は無言で不一致=素通り**（h ⚠️）。approve 側も実測（a: onAsk=allow で ASK+完遂）。全ケース SDK 併測（2026-07-05, v2.1.201）。未カバー: auto（eligibility 対象外）/ MCP requiresUserInteraction（fixture 無し）。sandbox×ask は S4-e/f で実測済み（bare=スキップ / content-scoped=貫通） |
| **設定スコープ間 precedence（T2）** | P7 a〜f（6件） | ✅ | **スコープ次元を実測で確定**: 同一キーは precedence 順（local>project=b / CLI>project=d）、**deny はどのスコープからでも勝つ**（a=user deny × project allow, ツールセット除去型）、**未 trust は project allow のみ無視・deny は効く**（c=stderr "Ignoring..." 警告を evidenceMarker で直接観測。ask に落ち headless auto-deny）。全ケース SDK 併測（2026-07-05, v2.1.201。b は byModality＝SDK は settings の defaultMode 不適用）。未カバー: managed（管理者権限/MDM 要で射程外と明記）/ `--settings` フラグの序列（【要裏取り】） |
| **subagent 継承（T5）** | P8 a,b,c,c2,c3,d,e | ✅ | **委譲で「守り」は継承され「モード」だけが緩む**: sandbox は subagent 内 Bash も同一境界（a=`allow ❌`, cwd 内は成功=試行証跡）/ **deny Write(*) は subagent の toolset からも除去**（b=SDK DENIED_HARD。escalate 後も勝つ=c3）/ **frontmatter `permissionMode: bypassPermissions` は親 default を override**（c: general-purpose=ASK vs escalator=素通り ✅ の 1 変数対照。**リポジトリ持ち込み `.claude/agents/` による documented 昇格経路**）/ **親 acceptEdits は override 不可**（c2=cwd 外 ASK のまま）/ 委譲面の遮断は `deny:["Agent"]`=ツール除去（d）・`Agent(name)`=呼び出し時拒否（e=denials/init 無痕跡, fs-write+evidenceMarker 観測）。**subagent 内の ask は親 denials・SDK canUseTool に載る**（c/c2 で実測）。起動ツールは二重名（init 表記 `Task`・tool_use 名 `Agent`・規則は両対応, v2.1.201）。全ケース SDK 併測（2026-07-05, v2.1.201） |
| **hooks × permission（T6）** | P9 a,b,c,d,e,f | ✅ | **「厳しい方が勝つ」を全交差で実測**: hook allow は deny 規則（a。**deny マッチ時は hook 不発火＝規則が前段**）にも明示 ask 規則（d=SDK ASK）にも負け、上書きできるのは既定 ask のみ（a 対照）。締める方向は **exit 2（b）/ JSON deny（c）とも allow に勝ち** `permission_denials[]` に記録（stderr/reason はモデルへ）。**JSON ask は allow 済みを確認制に格上げ**（e）。沈黙 hook は承認でない（f）。全ケース SDK 併測（2026-07-05, v2.1.201） |

## sandbox 層（S*）

| キー / 論点 | グループ | 状態 | 確定した挙動 |
|---|---|:---:|---|
| `sandbox.enabled` / Bash-only auto-allow | S1 a,f,g,h,i | ✅ | 同一設定3プローブで**切れ目はツール軸**と確定(a): Bash cwd 書込=auto-allow ✅ / Write・Edit ツール=ask(SDK=ASK。リポジトリ初の Edit プローブ)。**防御方向も同じ**(f): `denyWrite:["sub"]` + acceptEdits で Bash=EPERM ❌(evidenceMarker で `operation not permitted` 記録)/ **Write ツールは denyWrite を迂回して ✅**(S3-d の write 側対応物)。**sandbox は workspace trust の非ゲート対象**(g=未 trust でも cwd auto-allow ✅ / cwd 外 EPERM ❌ / allowWrite ✅。trust が縛るのは permissions.allow+additionalDirectories のみ=trust 注入失敗でも OS 境界は落ちない, 2026-07-06)。**MCP ツールは sandbox を丸ごと迂回**(h=別プロセス。denyRead した秘密を MCP read で読み・allowedDomains:[] でも MCP net で到達。同操作の Bash 対照は EPERM/egress 遮断。リポジトリ初の MCP fixture=`arrange.mcpServers`, 2026-07-06)。**PreToolUse hook も sandbox の外(ホスト)で走る**(i=別プロセス。sandbox.enabled 下でも hook が cwd 外 `$HOME` に書け、同じ書込の Bash 直接は EPERM。docs「Scope」は hooks を sandbox 対象外に列挙せず=【docs 沈黙】を実測で確定, 2026-07-06)。全ケース SDK 併測(2026-07-05〜06, v2.1.201) |
| `filesystem.allowWrite` / `denyWrite`（write=allowlist） | S2 a,b,c,d,e,f,g,h,i,j,k,l,m,n,o | ✅ | 既定 cwd+**付替え `$TMPDIR`**（実測 `/tmp/claude-<uid>`。リテラル /tmp 直下は ❌=j） / allowWrite で穴 / **`denyWrite:["~"]` は cwd も潰す**（d） / **glob は非対応=リテラル**（e） / **deny 常勝**: 広 allow+内 deny（g）・**名指し再 allow も無効**（i=read の allowRead と非対称）・**スコープ間も配列マージで project から user deny を外せない**（l）。**c（cwd 外=拒否）は実測済み**（`allow ❌`=OS EPERM・SDK askFired 空）。**permission の Edit 規則が sandbox 境界にマージ**（h=`Edit(~/dir/**)` だけで cwd 外に書ける）。**settings ファイルは自己保護**（f=EPERM・project に加え **local settings.local.json も対象**。入れ子 `sub/.claude/settings.json` は対象外=解決済みスコープの実ファイル単位。2026-07-06 追測）・**自己保護は名指しの allowWrite でも破れず user スコープにも効く**（m=`allowWrite:["~/.claude","~/.claude/settings.json"]` でも EPERM。組込 deny > 明示 allow は【docs 未記載】の実測確定）。**FS パス照合は symlink 解決済み**（k=/tmp・/private/tmp どちらの表記も効く）。**permission 規則→境界マージ（h）はスコープ不問**（n=`settings.local.json` の Edit allow 規則だけで cwd 外へ書ける=「don't ask again」1回で OS 境界が広がる経路。**project denyWrite は local の規則マージに勝つ**=釘付け手段。2026-07-06）。**`additionalDirectories` も sandbox 書込境界にマージ**（o=cwd 外でも記載ルートは Bash 書込 ✅／記載外は EPERM ❌＝実効境界の第5マージ源。cwd 境界を動かす設定は OS 層も動かす。2026-07-06）。全ケース SDK 併測（2026-07-05〜06, v2.1.201） |
| `filesystem.denyRead` / `allowRead`（read=blacklist）+ `permissions.deny Read()` | S3 a,b,c,d,e,f,g,i,j,k,m,n | ✅ | denyRead で塞ぐ（a）/ **allowRead で再許可**（b）/ cwd も denyRead:["~"] 下は読めない（c）/ **Read ツールは denyRead を迂回**（d）/ **python は sandbox が止める**（e）/ **`permissions.deny Read()` は Bash cat を遮断（f）だが python subprocess には及ばず漏洩（g）＝permission 層は subprocess 非対象**／ **2層併用（denyRead + deny Read()）で Read ツールも遮断（i）**／ default read=allow✅（j）／ glob 非対応（k）／ nested deny 常勝（m）／ **local の allowRead が project denyRead を貫通・再オープン＝秘密漏洩（n＝write の S2-n と非対称: denyRead は local ドリフトの釘にならない。釘は credentials.files か managed allowManagedReadPathsOnly。2026-07-06）** |
| `autoAllowBashIfSandboxed`（既定 true） | S4 a,d | ✅ | 既定で Bash 自動許可 / `false` で承認フローに戻る（d=SDK で ASK 確定） |
| autoAllow × ask 挙動（S4-b/c） | S4 b,c | ✅ | **glob→file は auto-allow 下でも ask**（c 確認）/ **個別 allow は ask を増やさない**（b は 2.1.200 で否定・multi-repo L84/L286 同期済み） |
| **auto-allow の例外分岐（spec §4.2）** | S4 e,f,g,h | ✅ | auto-allow が飛ばすのは**既定 ask と bare `Bash` ask（sandbox 実行分）だけ**: bare ask は非 sandbox（excluded）実行分に適用（e=同一設定で経路により ALLOWED/ASK に割れる）/ **content-scoped ask `Bash(touch *)` は貫通して ASK**（f）/ **明示 deny は貫通して hard deny**（g=SDK 非発火）/ **rm の critical-path プロンプトは home 配下サブ dir に発動せず**、実削除は OS 書込境界の EPERM が止める（h。`/`・`~` 本体は documented-only）。全ケース SDK 併測（2026-07-05, v2.1.201） |
| `excludedCommands` / `allowUnsandboxedCommands` | S5 a,b,c,d,e,g,h,i（8件） | ✅ | **excluded=行全体脱出(F9, b で非excluded の `cat` まで巻き込み実測)** / **`allowUnsandboxedCommands:true`×広い `Bash(*)` allow も脱出**（再試行が allow に自動承認, c 訂正 2026-07-05）/ `false`=厳格(d) / **両経路とも増幅要因は `Bash(*)`**：外すと再試行(e)・非excluded後段(h)は ask |
| `network.allowedDomains` / `deniedDomains` | S6 a,a0,b,c,c2,c3,d,e,i | ✅ | 既定全ブロック（**network キー省略=空リストと等価**, a0）/ denied 優先（literal 同一=c・**特定 deny が広域 allow ワイルドカードに勝つ**=c3, 陽性対照 c2=ワイルドカード allow が機能）/ **egress は OS 層でプロセス非依存**（`sh -c`・python でも遮断）/ **local の allowedDomains が project の全遮断[]に配列マージされ egress が開く（i＝local ドリフト。釘は managed allowManagedDomainsOnly のみ。2026-07-06）** |
| `network.allowLocalBinding`（公式未記載） | S6 g,g2 | ✅ | **local バインドは既定でブロック**（127.0.0.1 bind が拒否, g）/ **`allowLocalBinding:true` で bind 可**（g2。キーは 2026-07-05 の docs 英日両版に記載なし＝undocumented but functional・実測が一次証拠） |
| `network.allowUnixSockets` | S6 f | ✅ | 既定で unix socket connect 不可 / **allowUnixSockets で開ける**（パスは解決済み `/private/tmp`。`/tmp` symlink 非一致に注意） |
| **WebFetch は sandbox network を迂回** | S6 h | ✅ | `allowedDomains:[]` でも WebFetch が実ページ文言を返す＝**SDK ALLOWED で確定**（`verify_webfetch_bypass.mjs`→sdk.json 保存）。headless=INCONCLUSIVE は by-design（承認者不在）で expected 一致。対照 Bash curl=S6-a は DENIED。※WebFetch 迂回の層は docs 未記載＝【要裏取り】 |
| **`WebFetch(domain:…)` permission 規則**（S6 の2層目） | P10 a,b,c,d | ✅ | **WebFetch は sandbox（S6）を迂回するが permission 層の domain 規則には従う**: deny=当該ドメイン取得をブロック（SDK=DENIED_HARD, a）/ allow=domain allowlist（列挙外ドメインは ask, b）/ 完全一致は事前承認（c）/ **`*.example.com` はサブドメイン一致**（d）。ネットワーク遮断は sandbox network（Bash・S6）＋ WebFetch permission（P10）の2層。headless+SDK 全一致（2026-07-06） |
| **WebSearch のツール単位規則**（bare のみ・specifier 不可） | P10 e,f,g | ✅ | **既定 ask**（e=denials 記録・SDK ASK）/ **bare `allow WebSearch` で事前承認**（f=マーカーで ALLOWED 確定。**domain 限定構文は存在しない**=docs 明記・全か無か）/ **bare `deny WebSearch` は除去型**（g=init tools から消え denials 空・SDK=DENIED_HARD）。「限定的な web search」は規則で書けない → deny WebSearch + WebFetch domain allowlist に一本化。headless+SDK 全一致（2026-07-06） |
| **`mcp__` 規則のマッチングと現れ方**（F2 解消） | P11 a〜j | ✅ | **既定 ask**（a）/ allow 3 形: ツール形=1ツール限定（b）・サーバ形=全ツール（c）・**サーバ後 glob `mcp__srv__*` 有効**（d）/ **bare `mcp__*` は allow で無言無効**（e=fail-closed・stderr 警告なし）⇔ **deny 側では有効=全 MCP 除去**（i）/ **deny は除去型・1ツール単位**（f）/ **deny 常勝でサーバ deny に穴は彫れず**（g=P2-e 同型）**広 allow+狭 deny は成立**（h=参照系だけ残す正解形）/ **ask はサーバ allow に勝つ**（j=確認ゲート成立・SDK canUseTool 発火）。fixture=S1-h の mcp-probe-server 流用。headless+SDK 全一致（2026-07-06） |
| `credentials.files`（deny） | S7 a,b,i,j | ✅ | Bash `cat` を OS 層で塞ぐ（a）/ **python サブプロセスも塞ぐ**（i＝OS 層はプロセス非依存）/ **Read ツールは迂回して漏洩**（b）/ **`deny Read` 併用で Read ツールも塞がる**（j＝2層修復、SDK=DENIED_HARD 権威） |
| `credentials.envVars`（deny / mask） | S7 c,d,e,f,g,h | ✅ | `deny`=unset で有効（d）/ baseline c=`allow ✅`（漏洩・中立名 `LAB_BUILD_VAL`）/ **`mask` は project 設定で無視され漏洩**（e 不完全・g 完全でも同じ＝**無視の原因はスコープ**）/ **user スコープ + tlsTerminate + injectHosts⊂allowedDomains で mask が効く＝番兵置換**（f, allow ❌）/ **deny > mask**（h＝mask@user + deny@project をマージし deny 勝ち・空） |
| 組込 deny リスト不在 / `SUBPROCESS_ENV_SCRUB` | S7 k,l | ✅ | **組込クレデンシャル deny リストは無い**（k＝`AWS_SECRET_ACCESS_KEY` でも列挙しなければ漏洩）/ **`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` は env 参照 Bash を ASK ゲート**（l＝sandbox auto-allow を上書き・変数名非依存。SDK=ASK 権威）。※scrub 対象変数の具体リストは docs 未記載＝【要裏取り】 |
| sandbox × git（init/clone/worktree） | S8 a,b,c,d,e,f,h | ✅ | **git init は sandbox 内で失敗**（`.git/hooks/*.sample` への write が EPERM, W4）/ **`.git/config` は allowWrite 内でも書込拒否**（"Denied within allowed", W5）/ **worktree add は成功**（c）/ **worktree commit は `.git/` allowWrite 注入なしで成功**（d, v2.1.149+）/ **共有 `.git` の config/hooks 直接 write だけ deny**（e）/ **機構は `.git/config`・`.git/hooks/` への「パス」deny**（f: `--template=` でも config 作成 EPERM・bare init は成功）/ **clone は network 以前に同パス deny で失敗**（h: local `file://` でも 2 関門で ❌） |
| ツール層 dir スコープ保護（W1） | S9 a,a2,a3,b,d,d2,e,f | ✅ | **`Write(dir/**)` deny は no-op**（a2=作成 5/5）/ **`Edit(dir/**)` deny は Write も含む編集系をハード deny**（a3=0/5、全モードで効く）/ Bash 経路は sandbox `denyWrite`＝OS EPERM（b）。2ベクタは別経路を別層が守る。効き幅（2026-07-06 追加実測）: 深度の抜け穴なし（単一星 `Edit(dir/*)` も深度2まで＝サブツリー等価、e/a3）・bypass でも残存（f）・ただし**無印形は cwd 起点で `additionalDirectories` の別ルートに不マッチ＝無言の no-op（d ⚠️、acceptEdits の自動承認だけ広がる。trust 必須も注意）**、修正は `~/` アンカー形（d2）。SDK 全一致（ハード deny プローブの headless は構造的 INCONCLUSIVE） |

## モダリティ軸（headless / 対話 / SDK）

| 論点 | 状態 | 実装 |
|---|:---:|---|
| ask/deny 分離（`canUseTool` 計測） | ✅ | `harness/run.py -m sdk`（P1-a/S1-a=ASK, P2-b/P4-a=DENIED_HARD, P2-a=ALLOWED）。canUseTool=自作コードが判断（モデル非介在）を実証 |
| `permissionMode: 'auto'`（モデル分類器） | 🟡 | フラグは受理されるが、承認挙動は本環境で未実証（default 相当・eligibility 要 preview）。「モデルが判断」は SDK 型定義で確定 |
| W1 の no-op vs hard-deny | ✅ | `harness/sdk/verify_w1_modality.mjs`（`Write(assets/**)` deny=**no-op**／hard-deny の正体は同居 `Edit(assets/**)`。`Write(*)` deny=HARD は P2-b/P3 由来で本スクリプト外） |
| S4-b/c・W2 の ask 挙動 | ✅ | `harness/sdk/probe_ask_behavior.mjs`（glob→file=ask / 個別 allow は無影響 / excluded+chain は auto-allow） |
| W6 git hook バイパス | ✅ | `harness/verify_w6_git_hooks.sh`（--no-verify / core.hooksPath で回避） |
| 対話（TUI） | 📄 | 文書化のみ（EXECUTION-MODALITIES.md）。cmux 0.64 で手動確認可 |

## 観測プローブ（harness/run.py）

| probe | 判定信号 | 使用グループ |
|---|---|---|
| `permission` | permission_denials + 副作用 | P1-P5, S1, S9 |
| `fs-write` | 対象パスの生成有無 | P1-c, S2, S4, S5, S8 |
| `fs-read` | 番兵が出力に出たか | S3 |
| `credential-leak` | 番兵漏洩 + execMarker(拒否→INCONCLUSIVE) | S7 |
| `network` | 成功マーカー + 非 sandbox プリフライト | S6 |

## 未確定・要再測（INCONCLUSIVE = match:false）

`aggregate_summary.py` で拾った headless `match:false`。**全て「主張が間違っている」ではなく「保存実測が engine 未到達で確定していない」**（多くはモデルの自己拒否、S6-h は観測バグ、S9-a は in-repo 実行の構造的限界）。カテゴリ A として 2026-07-05 に断定→仮説へ是正済み。**現在すべて解消（未解消 0 件）**——下表は解消経緯の記録:

| ケース | 期待 | 保存 verdict | 原因 | 是正状況（2026-07-05） | 確定に要るもの |
|---|---|---|---|---|---|
| ~~S2-c outside-cwd~~ | DENIED | ~~INCONCLUSIVE~~ → **一致(解消)** | 自己拒否 → 中立化(`s2c-scratch.txt`)後の再測で 3 プローブとも期待一致(2026-07-05) | ✅解消 | — |
| S9-a3 edit-only | DENIED | INCONCLUSIVE→**解消** | hard-deny プローブのモデル安全拒否（headless の構造的限界。a と同型） | 機構は **SDK=DENIED_HARD で確定**（6/6 一致。詳細は S9 README）。headless の INCONCLUSIVE は by-design で expected 一致化 | ✅解消（by-design・SDK 権威） |
| S6-h webfetch-bypass | ALLOWED | INCONCLUSIVE→**解消** | 観測バグ（sentinel 不一致）→修正 | **SDK ALLOWED 保存**（`verify_webfetch_bypass.mjs`→sdk.json）。headless INCONCLUSIVE は by-design（byModality 一致）。※迂回の層は docs 未記載＝【要裏取り】 | ✅解消（by-design・SDK 権威） |
| S7-c envvars-baseline | ALLOWED | INCONCLUSIVE→**解消** | 変数名 `LAB_BUILD_TOKEN` で自己拒否 | **中立変数名 `LAB_BUILD_VAL` で再測、`allow ✅`（漏洩）を headless+SDK で確定** | ✅解消 |
| S9-a tool-write-scope | DENIED | INCONCLUSIVE→**解消** | **in-repo headless の構造的限界**（cwd にリポジトリ名→モデルが察して拒否） | 機構は SDK=DENIED_HARD で確定（control 5/5→0/5 は `Edit(assets/**)` 由来、`Write(assets/**)`=no-op）。headless の INCONCLUSIVE は by-design で expected 一致化 | ✅解消（by-design・SDK 権威） |

**解消済み（元カテゴリ A）**:
- **P4-d**: プローブ中立化（`scratch.txt`）で再測、**SDK で ASK 確定**（旧 INCONCLUSIVE 解消）。
- **S5-c**: 保存 verdict=ALLOWED（実際に脱出）が正しく期待値の側が誤り。expected を ALLOWED に訂正し **match:true** へ。
- **e-bypass-git（P5-e）**: bypass×保護パスの決着ケース、**実測 ALLOWED**（B1 を経験的に確定）。

## 未着手 / 後続（TODO）

- ~~**S8** clone の個別検証のみ残~~ ✅解消(2026-07-05): **S8-h 新設・実測**（local `file://` clone も hooks コピー→config 作成の同パス deny で ❌。「clone はネットワーク層 S6 と合流」という旧見立ては不正確＝**network を許可しても clone は通らない**）。init 機構も **S8-f** で確定（`--template=` でも config 作成 EPERM / bare init は ✅ = deny はパス形状）
- `multi-repo-workspace.md` の出典を本リポジトリのグループへ貼り替え（W1〜W6 → S8/S9/S2 ほか）。**W1/W2 は設計文書の防御想定を要修正**（W1=ツール層は `Edit(dir/**)` ハード deny／`Write(dir/**)` は no-op、W2=cwd 書込は auto-allow）
- 対話（TUI）の cmux 自動化（現状は文書化 + SDK で分岐再現）

## この検証で確定した「直感に反する」挙動（早見）

- Write deny: `Write(*)`=効く / **path 限定は全 no-op**（`Write(dir/**)`・`Write(**)`・完全パス・単一星・絶対・`~`）。dir は `Edit(dir/**)` ハード deny で守る
- Read/Edit/Write ツール・WebFetch は **sandbox を迂回**（Bash 限定）。秘密は permission.deny も併用
- sandbox FS パスは **glob 非対応**（S2-e）で **symlink 解決して照合**（S2-k: `/tmp` 表記でも効く）。**socket は非解決**で `/private/tmp` の解決済み表記が必要（S6-f）— FS と socket で挙動が割れる
- `denyWrite:["~"]` は cwd 暗黙書込も潰す（使わない）/ `credentials mask` はプロジェクト設定で無視
- `excludedCommands` は行全体 sandbox 外実行（F9）/ git init は sandbox 内で失敗（prep 外出し）
