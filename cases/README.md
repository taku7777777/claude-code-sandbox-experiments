# cases インデックス — 21 グループの地図と逆引き

1グループ = 1検証軸。`P*` = permission 層(許諾エンジン) / `S*` = sandbox 層(OS 境界)。
サブケースは `a` がベースラインで、以降は「a に1変数足したもの」(→ [docs/CASE-FORMAT.md](../docs/CASE-FORMAT.md)。
用語・記号は [docs/GLOSSARY.md](../docs/GLOSSARY.md))。
**各グループが権限制御全体のどの制御点を検証しているか**は [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §5 の地図を参照。

> `cases/` は番号バケツで分かれる: **01-permission**(許諾エンジン・全手段共通)/ **02-sandbox-bash**(手段1=組み込み
> sandbox)/ **03-sandbox-runtime**(手段2)/ **04-devcontainer**(手段3)。物理パスは番号つきだが、参照 ID は
> 短縮形(`S3-d` 等)のまま(ハーネスも短縮 ID で解決)。

## permission 層(P1〜P12) — 許諾エンジン(allow / ask / deny)の挙動

| ID | グループ | 1行サマリ |
|---|---|---|
| P1 | [permission-mode](01-permission/P1-permission-mode/README.md) | モードが書込系ツールの「許諾の既定値」を決める(default=ask / acceptEdits / plan / dontAsk / bypass) |
| P2 | [allow-deny-precedence](01-permission/P2-allow-deny-precedence/README.md) | deny は allow にもモードにも勝つ(マッチした範囲で)。除去型 deny の観測方法も |
| P3 | [write-glob-asymmetry-DANGER](01-permission/P3-write-glob-asymmetry-DANGER/README.md) | ⚠️ Write のパス限定規則は**どの表記でも無言の no-op**。個別保護の正解形は `deny Edit(path)` |
| P4 | [bash-command-matching](01-permission/P4-bash-command-matching/README.md) | チェーン(`&&`/`;`/`\|`)も剥がされるラッパーも防げる。防げないのは `sh -c` 等の剥がされないラッパー |
| P5 | [protected-paths](01-permission/P5-protected-paths/README.md) | `.git` `.claude` 等の保護パスは acceptEdits/allow の上流で常に ask。bypass だけがそれも省略 |
| P6 | [ask-rules](01-permission/P6-ask-rules/README.md) | ask 規則は allow に勝ち deny に負ける。プロンプトが残るのは bypass まで、dontAsk では deny に化ける |
| P7 | [settings-scope-precedence](01-permission/P7-settings-scope-precedence/README.md) | スコープ間マージは順位どおり、deny だけが順位を飛び越え、未 trust は allow だけ無効化される |
| P8 | [subagent-inheritance](01-permission/P8-subagent-inheritance/README.md) | 委譲で「守り」(deny/sandbox)は継承され、「モード」だけが frontmatter で緩みうる |
| P9 | [hooks-vs-permission](01-permission/P9-hooks-vs-permission/README.md) | hook は「締める」方向にだけ信頼できる(規則との優先は「厳しい方が勝つ」) |
| P10 | [webfetch-rules](01-permission/P10-webfetch-rules/README.md) | `WebFetch(domain:…)` は domain allowlist / WebSearch は bare 二値(domain 限定不可・deny は除去型)。両ツールは sandbox network(S6)を迂回するが本規則には従う=ネットワークを絞る2層目 |
| P11 | [mcp-tool-rules](01-permission/P11-mcp-tool-rules/README.md) | `mcp__server(__tool)` 規則は組込ツールと同じ評価系(既定 ask・deny 除去型・広 allow+狭 deny のみ彫れる・ask は allow に勝つ)。glob は deny/ask 側だけ全域可(allow の bare `mcp__*` は無言 no-op) |
| P12 | [path-anchor-matching](01-permission/P12-path-anchor-matching/README.md) | 相対規則は絶対パス呼び出しにマッチ(表記差でエスケープ不成立)。絶対で書くと `~/`・`//` は効くが**単一スラッシュ `/abs` は allow/deny とも無言 no-op** |

## sandbox 層(S1〜S9) — OS レベルの境界(Bash とその子プロセス限定)

| ID | グループ | 1行サマリ |
|---|---|---|
| S1 | [sandbox-scope-vs-tools](02-sandbox-bash/S1-sandbox-scope-vs-tools/README.md) | sandbox の適用範囲は Bash 限定(auto-allow も denyWrite も)。ツール × 迂回層の索引 |
| S2 | [sandbox-fs-write](02-sandbox-bash/S2-sandbox-fs-write/README.md) | Bash 書込は allowlist(既定 = cwd + 付替え `$TMPDIR`)。permission の Edit 系規則も境界にマージ |
| S3 | [sandbox-fs-read](02-sandbox-bash/S3-sandbox-fs-read/README.md) | 読取は blacklist(`denyRead`)。ただし Read ツール等の経路と層で穴が開く → 2層併用が正解形 |
| S4 | [sandbox-autoallow-behavior](02-sandbox-bash/S4-sandbox-autoallow-behavior/README.md) | `autoAllowBashIfSandboxed` が何を飛ばし何を飛ばさないか(deny・content-scoped ask は貫通) |
| S5 | [sandbox-excluded-and-unsandboxed](02-sandbox-bash/S5-sandbox-excluded-and-unsandboxed/README.md) | ⚠️ sandbox の抜け穴2系統(`excludedCommands` / `allowUnsandboxedCommands`)。増幅要因は広い `Bash(*)` |
| S6 | [sandbox-network](02-sandbox-bash/S6-sandbox-network/README.md) | egress は既定全ブロック・OS 層でプロセス非依存(`sh -c` でも遮断)。ただし WebFetch は迂回する |
| S7 | [sandbox-credentials](02-sandbox-bash/S7-sandbox-credentials/README.md) | 秘密の保護(`credentials.files` / `envVars`)とその穴(Read ツール迂回・mask のスコープ条件) |
| S8 | [sandbox-git-interop](02-sandbox-bash/S8-sandbox-git-interop/README.md) | sandbox 内で git 操作の何が通り何が止まるか(init/clone=失敗、worktree add/commit=成功) |
| S9 | [tool-write-scope](02-sandbox-bash/S9-tool-write-scope/README.md) | ディレクトリを守る2ベクタ: `Edit(dir/**)` deny(ツール層) vs `denyWrite`(OS 層)。`Write(dir/**)` は no-op トラップ |

## 外側の分離手段(03 / 04)— プロセス全体を包む環境

`claude -p` では回らず srt / Docker が要るため run.py 対象外(case.json の `runner` を見て run.py は skip 表示。
再現コマンドは各 README・srt の現行ランナーは `harness/srt/run_srt_cases.py`(`run_differential.sh` は旧・簡易差分)。フォーマットの差分規約は
[docs/CASE-FORMAT.md](../docs/CASE-FORMAT.md) 「環境ケースの変形」)。組み込み(手段1)で
迂回されるツール経路が、これらの環境では OS 層で塞がる/塞がらないを対比する。

| バケツ | 手段 | 検証内容 |
|---|---|---|
| 03 | [sandbox-runtime](03-sandbox-runtime/README.md) | 手段2。srt がツール経路(Read/Write/Edit)も別プロセス経路(MCP/hook)も WebFetch も OS 層で塞ぐ・permission 層は不変・env は対象外(a〜j) |
| 04 | [devcontainer](04-devcontainer/README.md) | 手段3。bind mount の fail-closed・iptables egress firewall・**claude 無人実行 e2e**(ツール経路まで境界内・非 root 必須・認証は読める→egress で出せない=d の2段構成)(a〜d,g,h) |

総括: [docs/SANDBOX-RUNTIME-FINDINGS.md](../docs/SANDBOX-RUNTIME-FINDINGS.md) / [docs/DEVCONTAINER-FINDINGS.md](../docs/DEVCONTAINER-FINDINGS.md) / [docs/SANDBOX-ENVIRONMENTS.md](../docs/SANDBOX-ENVIRONMENTS.md)(6手段の選択)

## 逆引き — 疑問・症状からケースへ

| 疑問・症状 | まず見る |
|---|---|
| deny してないのに write が拒否される | [FINDINGS Q1](../docs/FINDINGS.md) → P1-a |
| sandbox を有効にしたのに permission を要求される | [FINDINGS Q2](../docs/FINDINGS.md) → S1-a |
| deny をチェーンやラッパーですり抜けられる? | [FINDINGS Q3](../docs/FINDINGS.md) → P4 |
| 特定パスの Write を deny したのに効かない | P3(glob 地雷) / S9(効く形は `Edit(dir/**)`) |
| 相対/絶対パスで規則を書くとマッチが変わる? 絶対実行で抜けない? | P12(相対規則は絶対呼び出しに効く・単一スラッシュ絶対は no-op) |
| CI / headless で ask が全部 deny になる | [EXECUTION-MODALITIES](../docs/EXECUTION-MODALITIES.md) → P1 / P7-c(未 trust) |
| 秘密ファイル・環境変数を読ませたくない | S7(credentials) / S3(denyRead + 2層併用) |
| ネットワークを本当に止めたい | S6(OS 層・Bash 経路) + P10(WebFetch/WebSearch permission) の2層 ⇔ P4-c(文字列 deny は境界にならない) |
| MCP ツールを絞りたい(sandbox が効かない) | S1-h(MCP は sandbox 丸ごと迂回) → P11(`mcp__` 規則の効く形/効かない形) |
| settings をどのスコープに書けば効く? | P7(precedence / trust) |
| subagent に委譲されたら守りは残る? | P8 |
| hook で権限を締めたい / 緩めたい | P9 |
| `.git` / `.claude` に書けない | P5(保護パス) |
| sandbox から抜けられる穴は? | S5(脱出2系統) / S1(ツール迂回) |
| git init / clone が sandbox 内で失敗する | S8 |
| bypassPermissions でも残る防御は? | [BEST-PRACTICES 鉄則E](../docs/BEST-PRACTICES.md) → P2-d / P5-e / S9-f |

実測で確定した挙動の総覧は [docs/FINDINGS.md](../docs/FINDINGS.md)、設定キー × グループの網羅状況は [docs/COVERAGE.md](../docs/COVERAGE.md)。
