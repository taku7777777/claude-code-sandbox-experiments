# S3. sandbox-fs-read — 読取は blacklist、しかし経路と層で穴が開く

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。

## このグループで学ぶこと

- sandbox の読取は **ブラックリスト方式**(`denyRead` に挙げた所だけ塞ぎ、`allowRead` で例外を戻す。既定は全域読取可)。
- **同じ秘密を読む経路(Bash cat / Read ツール / python open)と、塞ぐ層(sandbox denyRead / permission deny Read)を掛け合わせると穴が可視化される**:
  - sandbox denyRead は **Bash とその子プロセス限定**。Read ツールは sandbox を迂回して漏らす。
  - permission deny Read は **認識コマンド(cat 等)限定**。python の自前 open は素通しする。
- どちらの層も片方だけでは穴が残り、**2層併用(denyRead + deny Read)で初めて全経路が塞がる**。

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | denyRead:["~"] + allow Read(~/**) | 読取経路の共通プローブ列(cat/Read/python)を1ケースで対比 | [a-denyread-blocks](./a-denyread-blocks/README.md) |
| b | a から allowRead:["~/lab-note-b.txt"] | 例外で1パスだけ再許可 | [b-allowread-reallow](./b-allowread-reallow/README.md) |
| c | `denyRead:["~"]`(allowRead なし) | cwd も ~ 配下 → 読めない(write/read 非対称) | [c-cwd-read-under-denyread](./c-cwd-read-under-denyread/README.md) |
| d | denyRead:["~"] + allow Read(~/**) | Read ツール単独 = sandbox 迂回で漏洩 | [d-read-tool-bypasses-denyread](./d-read-tool-bypasses-denyread/README.md) |
| e | denyRead:["~"] / python open | サブプロセスも sandbox は止める | [e-script-read-only-sandbox-stops](./e-script-read-only-sandbox-stops/README.md) |
| f | **sandbox off** + deny Read(~/**) / cat | permission deny は cat を止める(肯定側) | [f-permdeny-cat](./f-permdeny-cat/README.md) |
| g | **sandbox off** + deny Read(~/**) / python | permission deny は python を止められない(否定側) | [g-permdeny-python-leaks](./g-permdeny-python-leaks/README.md) |
| i | denyRead:["~"] + deny Read(~/**) / Read ツール | 2層併用で d の穴を塞ぐ | [i-two-layer-fix](./i-two-layer-fix/README.md) |
| j | sandbox on・denyRead なし / cat | 読取ベースライン(既定で全域可) | [j-default-read-baseline](./j-default-read-baseline/README.md) |
| k | `denyRead:["~/lab-rd-*"]`(+ literal 対照) | denyRead の `*` はリテラル → glob 風は fail-open で漏洩 | [k-denyread-glob-literal](./k-denyread-glob-literal/README.md) |
| m | denyRead:["~"] + allowRead + 内側 denyRead | allowRead 内の入れ子 deny が勝つ(S2-g の read 側) | [m-nested-denyread-wins](./m-nested-denyread-wins/README.md) |
| n | project denyRead × **local** settings.local.json の allowRead | **local の allowRead が project denyRead を貫通して再オープン**=秘密漏洩。denyRead は local ドリフトの釘にならない(write=S2-n と非対称) | [n-local-allowread-reopens](./n-local-allowread-reopens/README.md) |

> h・l は**欠番**: h は旧 GAPS G2 案「sandbox 有効下で permission `deny Read` が OS 境界へマージされ python も止まるか」を未実測のまま予約。l は `l-grep-tool-vs-denyread` として設計したが、本 build(v2.1.201)の init tools に Grep/Glob ツールが露出せず撤去。

## 対比

セル = 2軸表記「許諾 結果」(approve 前提。`allow ✅`=読めた/漏洩、`allow ❌`=permission は通ったが OS 層が遮断、`deny -`=permission 層で拒否)。番兵の漏洩/非漏洩 + 実行痕跡マーカーで全セル実測。

### (1) 経路 × 層 マトリクス(このグループの看板)

同じ home 秘密ファイルを、読取経路(行)× 塞ぐ層(列)で読む:

| 読取経路 | sandbox denyRead(sandbox on) | permission deny Read(sandbox off) |
|---|:---:|:---:|
| Bash `cat` | allow ❌ (a-1) | **deny -** (f) |
| **Read ツール** | **allow ✅** 迂回漏洩 (a-2 / d) | **deny -**(+denyRead, i) |
| python `open()` | allow ❌ (a-3 / e) | **allow ✅** 漏洩 (g) |

- **Read ツール行**: sandbox denyRead は迂回されて漏洩(a-2/d)。止めるのは permission deny Read(i)。
- **python 行**: permission deny Read は素通しで漏洩(g)。止めるのは sandbox denyRead(a-3/e)。
- **各層に相補的な穴がある** → 対角に漏洩セルが残る。2層併用(denyRead + deny Read)で cat/Read/python すべて塞がる。

### (2) Bash cat を基準にした設定差分(a を基準に)

Bash `cat` 1経路だけ取り出し、sandbox の設定を1変数ずつ動かした列:

| 設定 | Bash cat の結果 | 起きること |
|---|:---:|---|
| j: sandbox on・denyRead なし | allow ✅ | 既定で全域読取可(home も読める。~/.aws ~/.ssh も) |
| a: + denyRead:["~"] | allow ❌ | home 読取を OS 層で遮断(cwd も巻き込む → c) |
| b: + allowRead:["~/lab-note-b.txt"] | allow ✅ | blacklist に例外の穴 |

- j → a は denyRead:["~"] を足しただけで ✅→❌。a → b は allowRead を足しただけで ❌→✅。**変えた1変数と反転したセルが1対1**。
- c は a と同設定で cwd のファイルを読むだけ(allow ❌)。「cwd に書けても cat で読み戻せない」write/read 非対称。

## 要点

- **秘密を本当に塞ぐには2層併用**: sandbox `denyRead`(Bash・サブプロセス)+ `permissions.deny Read(~/.ssh/**)` 等(Read/Edit ツール・cat 等の認識コマンド)。片方だけでは相補的な穴が残る(Read ツール = d / python = g が証拠、塞いだのが i)。
- sandbox denyRead は **Bash とその子プロセス限定**(Read/Edit/Write ツールは permission システムを直接使い sandbox を通らない)。permission deny Read は **認識コマンド限定**(任意サブプロセスには効かない)。両者は docs でも確認済み(sandboxing "Scope" / permissions "Read and Edit")。
- 読取は blacklist。**sandbox を有効にしただけでは既定で home 全域が読め、`~/.aws` `~/.ssh` も読める**(j)。credentials を塞ぐのは denyRead / `sandbox.credentials`(→ S7)。
- `denyRead:["~"]` は作業ディレクトリ(home 配下)の Bash 読取も巻き込む(c)。cwd を読むなら実パスを `allowRead` に足す。
- **`denyRead` / `allowRead` のパスはリテラル。`*` は glob 展開されない**(k)。`denyRead:["~/secrets-*"]` のような glob 風の記述は黙って何も保護しない(**fail-open**)ので、塞ぎたい所は実名で列挙する。write 側(`allowWrite`)の同じリテラル性(S2-e)は fail-closed だが、read 側は fail-open で危険度が高い。
- **再許可(`allowRead`)した領域の内側は、より狭い `denyRead` で塞ぎ直せる**(m)。sandbox FS 層は記述順でなく具体度で deny が allow に勝つ(write 側 S2-g と同じ優先則)。
- **`denyRead` は local ドリフトの釘にならない**(n=**運用上の重要点**)。project で `denyRead` を敷いても、`settings.local.json`(gitignore され・レビューに乗らない)に `allowRead` を一行足せばその領域が**貫通・再オープン**され秘密が漏れる。これは write の「project `denyWrite` が local allow に常勝(S2-n)」とは**非対称**——read は allowRead という再オープン機構を持つため。秘密は `denyRead` 単独ではなく **`sandbox.credentials.files`(deny・スコープ跨ぎで narrow のみ=どのスコープも外せない)** か **managed 設定の `allowManagedReadPathsOnly`** で釘付けする。
- 補足(docs §「How sandboxing relates to permissions」): sandbox 有効時は Read/Edit deny 規則も OS 境界へ**マージ**される。本グループは f/g で **sandbox を切って** permission 層単体を測り、その交絡を避けている(sandbox 有効下では deny Read が実質2層目としても働く点は S7 と併せて要追検証)。

## 対応する知識

- docs/FINDINGS.md: Q2(sandbox FS は Bash 限定)/ 3層モデル(refactor-plan.md 付録B)
- 関連: S2(write=allowlist の対)/ S1(Write ツールの sandbox 迂回)/ S7(credentials, F3)/ S4(autoAllowBashIfSandboxed)
