# S1. sandbox-scope-vs-tools — sandbox の適用範囲は Bash 限定(auto-allow も denyWrite も。ツール × 迂回層の索引)

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。

## このグループで学ぶこと

- `sandbox.enabled` の OS レベル auto-allow は **Bash とその子プロセスのみ**に及ぶ。
- **Read / Edit / Write / WebFetch の組込ツールは sandbox を通らず permission システムで直接判定される**。
  だから sandbox を on にしても、これらのツールは permission 層の規則(default なら ask)に従う。
- 「切れ目はパスではなくツール」— 同一設定で Bash 書込は auto-allow(✅)、Write/Edit ツールは ask になる(a)。
- この切れ目は**防御方向にも効く**: sandbox `denyWrite` で塞いだパスも、Write **ツール**経由なら書けてしまう(f。同じパスへの Bash は EPERM で遮断)。denyRead の秘密漏れ(S3-d)と対称の落とし穴。
- **Bash 以外の「別プロセス実行経路」(MCP サーバ=h / hook スクリプト=i)は sandbox を丸ごと迂回する**: どちらも Bash ツールの子ではなく Claude Code 本体が spawn する別プロセスなので、denyRead した秘密読取・egress 遮断越え・cwd 外書込が OS 境界を受けずに通る。締めるのは sandbox でなく「何を刺すか / 何を hook に置くか」の管理。

## サブケース一覧

| サブ | 設定 / 操作 | 論点 | 詳細 |
|---|---|---|---|
| a | sandbox on / Bash 書込 + Write + Edit の3プローブ | auto-allow は Bash 限定・ツール軸で切れる | [a-bash-vs-tools](./a-bash-vs-tools/README.md) |
| f | + `denyWrite:["sub"]` + acceptEdits / Bash と Write の2プローブ | **denyWrite もツール経路には効かない**(迂回) | [f-write-tool-vs-denywrite](./f-write-tool-vs-denywrite/README.md) |
| g | **未 trust** workspace / sandbox on + allowWrite の3プローブ | **sandbox は trust 非ゲート** — 未 trust でも境界は生きる(trust 注入失敗時の安全側フォールバック) | [g-untrusted-sandbox-enforced](./g-untrusted-sandbox-enforced/README.md) |
| h | sandbox on + denyRead + allowedDomains:[] / **MCP ツール** vs Bash 対照の4プローブ | **MCP は sandbox を丸ごと迂回**(別プロセス。denyRead した秘密を読み・egress 遮断を越える) | [h-mcp-bypasses-sandbox](./h-mcp-bypasses-sandbox/README.md) |
| i | sandbox on + **PreToolUse hook** / hook 書込 vs Bash 対照の2プローブ | **hook は sandbox の外(ホスト)で走る**(cwd 外 `$HOME` に書ける・同じ書込を Bash でやると EPERM) | [i-hooks-bypass-sandbox](./i-hooks-bypass-sandbox/README.md) |

## 対比

同一設定内で Bash とツールを対比した実測マトリクス(セル = `許諾 結果`):

| No | 操作 | a(sandbox on / default) | f(+ `denyWrite:["sub"]` / acceptEdits) |
|---|---|:---:|:---:|
| 1 | Bash 書込(cwd 内 / f は `sub/` 内) | allow ✅ | allow **❌**(OS が EPERM) |
| 2 | Write ツール書込(同上) | ask ✅ | allow **✅**(denyWrite を迂回) |
| 3 | Edit `./note.txt`(ツール) | ask ✅ | - |

- a: 1 は sandbox の auto-allow で承認なしに通る(=sandbox が効いている肯定対照)。2・3 は同じ設定でも ask。**変えたのはツールだけ**なので、切れ目がパスではなくツール(Bash か否か)にあることが1変数対照で確定する。
- f: a と**同じツール軸の切れ目が防御方向に反転して現れる** — Bash は denyWrite に遮断され(`operation not permitted` を evidenceMarker で記録)、Write ツールは同じ場所に書ける。sandbox は「Bash を守る/縛る」層であって、ツール経路には許可も禁止も及ばない。

## ツール × 迂回する sandbox 層(索引)

S1 は「sandbox の対象範囲 vs ツール」の総括グループ。各ツールがどの sandbox 層を迂回するか、
実証済みケースへのポインタで索引化する(セル = 実測済みケース):

| ツール | sandbox の扱い | 実測ケース |
|---|---|---|
| Bash | **sandbox 対象**(auto-allow / OS 遮断が効く) | S1-a(cwd 書込 auto-allow=✅)/ S1-f(denyWrite 先=EPERM ❌)/ S2(書込境界)/ S3(読取 blacklist)/ S6(egress) |
| Write | sandbox 対象外(auto-allow 迂回・**denyWrite も迂回**) | S1-a(default で ask=✅)/ [S1-f](./f-write-tool-vs-denywrite/README.md)(denyWrite 先に書ける=✅) |
| Edit | sandbox 対象外(permission 層直轄) | S1-a(default で ask=✅・リポジトリ初の Edit プローブ) |
| Read | sandbox 対象外(`denyRead` を迂回して秘密を読む) | [S3-d](../S3-sandbox-fs-read/d-read-tool-bypasses-denyread/README.md) / [S7-b](../S7-sandbox-credentials/b-files-read-tool-bypass/README.md) |
| WebFetch | sandbox 対象外(egress 遮断を迂回) | [S6-h](../S6-sandbox-network/h-webfetch-bypasses-egress/README.md) |
| **MCP** | **sandbox 対象外(別プロセス。`denyRead` も `allowedDomains` も迂回)** | [S1-h](./h-mcp-bypasses-sandbox/README.md)(read=秘密漏洩 / net=egress 到達を1ケースで) |
| **hooks** | **sandbox 対象外(別プロセス=ホスト実行。cwd 外書込・egress も OS 境界を受けない)** | [S1-i](./i-hooks-bypass-sandbox/README.md)(PreToolUse hook が cwd 外 `$HOME` に書ける / 同書込の Bash は EPERM) |

- Read ツールの迂回は S3-d(`denyRead`)と S7-b(credentials.files)で実証済みのため、S1 では**再実装せず参照**する。
- **MCP は最も広い口**: read も net も(サーバ実装次第で任意コマンドも)持ちうるため、上記の個別ツールの迂回を1本で兼ねる。締めるのは sandbox でなく「どの MCP を刺すか」+ permission 層の `mcp__*` 規則(→ S1-h 運用留意)。
- **hooks は「ツール」ではなく実行経路**だが、同じ「Bash 以外の別プロセス」理由で sandbox を素通りする(i)。締めるのは sandbox でなく「どの hook を settings に置くか」の管理(hook は登録した時点で無条件にホストで走る)。MCP と対で「別プロセス経路 = sandbox 対象外」を成す。
- subagent の sandbox 継承(docs §4.6)は P8 相当で本グループでは扱わない(GAPS.md G3 のバックログ)。

## 要点

- 「sandbox なのに permission 要求」の正体は、auto-allow が Bash 限定でファイル編集ツールに及ばないこと。
- ファイル編集の自動化は permission 側(`allow` / `acceptEdits`)で別途許可する。
- **防御も同じ切れ目で破れる**: `denyWrite` で守ったつもりのパスは Write ツール経由で書ける(f)。ディレクトリ保護は sandbox `denyWrite`(Bash 経路)+ `permissions.deny Edit(dir/**)`(ツール経路・ハード deny)の**2層併記**が正解形(→ S9)。
- 一次資料(sandboxing docs)が「Read/Edit/Write は permission システム直轄」「sandbox は Bash とその子プロセス限定」を明記しており、このグループの主張(a=許可方向 / f=禁止方向)と一致する。
- **trust の切れ目も層で違う**(g): workspace trust が縛るのは permission 層の `permissions.allow` と `additionalDirectories` だけで、**sandbox の OS 境界(`enabled`/`allowWrite` 等)は trust 非依存**。未 trust で失われるのは permission 層の利便化(allow 済みが通る等)だけで、安全側に倒れる。ただし trust は local ドリフト(S2-n/S3-n/S6-i)の防波堤ではない。

## 対応する知識

- docs/FINDINGS.md: Q2「sandbox を使っているのに permission が要求される」
- 一次資料: [Claude Code sandboxing docs](https://code.claude.com/docs/en/sandboxing.md)
- 関連: S2(Bash の書込境界)/ S3-d(Read ツールの denyRead 迂回)/ S6-h(WebFetch の egress 迂回)/ S7-b(credentials の Read 迂回)/ S9-b(f と同じ denyWrite の Bash 側単独観測)・S9-a3(ツール経路の正解形 `deny Edit(dir/**)`)
