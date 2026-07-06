# GLOSSARY — 用語・判定値・記号の正本

このリポジトリで使う独自用語・判定値・記号の定義を1箇所に集約する(**用語と記号はこの文書が正本**)。
挙動の実測結果は [FINDINGS.md](./FINDINGS.md)、ケース定義の仕様は [CASE-FORMAT.md](./CASE-FORMAT.md) が正本。

## 1. 構造の単位

| 用語 | 定義 |
|---|---|
| **グループ** | `cases/<GROUP>/` の1単位(P1〜P12 / S1〜S9 の21個)。1グループ = 1検証軸。`P*`=permission 層 / `S*`=sandbox 層。一覧は [cases/README.md](../cases/README.md)。※旧表記の「群」「章」は「グループ」に統一済み |
| **サブケース** | グループ内の `a-*`〜 ディレクトリ。`a` がベースライン、以降は「a に1変数足したもの」(対照実験)。`c2` のような数字サフィックスは既存サブケースの派生、`a0` は a よりさらに素の既定。欠番は各グループ README に注記 |
| **ケース** | サブケース1つ分の検証定義一式(`.claude/settings.json` + `case.json` + `prompt.ja.txt` + README)。ID は `<GROUP>/<SUB>` 形式(例: `P1-permission-mode/a-default-deny`)。省略表記は `P1-a` |
| **プローブ** | 1ケース内で同一設定に当てる操作(`case.json` の `probes[]` の1要素)。**1プローブ = 1独立セッション**で実行される。設定を動かすならサブケースを分け、操作を動かすならプローブを足す(→ CASE-FORMAT.md) |
| **標準4プローブセット** | 書込制御系ケースで使う共通プローブ列: `write-cwd` / `write-home`(cwd 外) / `write-subdir` / `edit-cwd`。グループ間で「設定 × 操作」マトリクスを比較可能にする |

## 2. 2層モデルと実行形態

| 用語 | 定義 |
|---|---|
| **permission 層** | Claude Code 内部の許諾エンジン。ツール呼び出しを規則(allow / ask / deny)・permission mode・hooks で判定する。P* グループの検証対象 |
| **sandbox 層(OS 層)** | OS レベルの実行境界(macOS では `sandbox-exec`)。**Bash とその子プロセスだけ**に効く(filesystem / network / credentials)。S* グループの検証対象 |
| **ツール経路 / Bash 経路** | 同じ操作でも、組込ツール(Write/Read/Edit/WebFetch …)経由と Bash コマンド経由では通る層が違う。**ツール経路は sandbox 層を迂回する**(S1 / S3-d / S6-h) |
| **モダリティ(実行形態)** | headless(`claude -p`) / SDK(Claude Agent SDK) / 対話(TUI) の3形態。**モダリティが変えるのは ask の解決方法だけ**(→ EXECUTION-MODALITIES.md) |
| **2軸(許諾 + 結果)** | 期待値の書き方。①許諾 = permission エンジンの判定、②結果 = approve した前提で完遂できたか。この2つを書けばハーネスが全モダリティの期待 verdict に機械展開できる |
| **auto-allow** | `sandbox.autoAllowBashIfSandboxed`(既定 true)による「sandbox 内 Bash の無プロンプト自動許可」。permission mode の `auto`(モデル分類器・research preview)とは**別機構** |
| **保護パス** | `.git` `.claude` `.vscode` `.mcp.json` 等。allow / acceptEdits があっても常に ask になる特別扱い(例外: bypassPermissions では skip される。→ P5) |
| **剥がされるラッパー / 剥がされないラッパー** | Bash 照合の前に中身が展開されて照合されるラッパー(`nice` `timeout` `nohup` 等 → deny に当たる)と、中身が文字列で不可視なもの(`sh -c '...'` `$(...)` 等 → 照合されず deny をすり抜ける)。→ P4-c/e |
| **脱出** | sandbox の FS 境界の外(cwd 外)へ書けてしまうこと。経路は `excludedCommands`(行全体が sandbox 外実行)と `allowUnsandboxedCommands:true` × 広い `Bash(*)` allow の2系統(→ S5) |

## 3. 判定値

### 許諾(`expected.permission` = permission エンジンの判定)

| 値 | 意味 |
|---|---|
| `allow` | 規則/モードで事前承認(プロンプトなしで実行) |
| `deny` | ハードブロック(承認の余地なし) |
| `ask` | 人間の承認を要求(解決方法はモダリティ依存 → 下記) |
| `none` / `-` | permission 判定に到達せず(ツール検証エラー等) |
| `blocked` | headless で塞がれたが ask か deny か未分離の TODO マーカー(SDK 実測で昇格) |

### 結果(`expected.result` = approve した前提で完遂できるか)

| 値 | 表記 | 意味 |
|---|---|---|
| `ok` | ✅ | 完遂できる |
| `ng` | ❌ | 失敗する(**sandbox = OS 層による遮断を含む**) |
| `-` | - | deny で実行に至らない |

### verdict(ハーネスの実測判定)

| 値 | 意味 |
|---|---|
| `ALLOWED` | 実行された(副作用あり / 番兵漏洩あり) |
| `DENIED` | ブロックされた(headless では「deny 規則」と「ask の auto-deny」を区別できない点に注意) |
| `DENIED_HARD` | deny 規則によるハード拒否と確定(SDK: `canUseTool` 非発火 + 副作用なし) |
| `ASK` | ask と確定(SDK: `canUseTool` 発火 / 対話: 承認プロンプト表示) |
| `INCONCLUSIVE` | 判定不能(ツール未試行等。**by-design** = 構造的に headless では測れないと分かっているものは expected 一致扱い) |

### ask の解決(モダリティ別)

| モダリティ | ask の解決 |
|---|---|
| headless (`claude -p`) | 承認者不在 → **auto-deny**(deny 規則によるハード拒否とは別物) |
| SDK | `canUseTool` コールバックが決定(**発火 = ask の証跡** = `askFired`) |
| 対話(TUI) | 人間に承認プロンプト |

### 合成署名(グループ README の対比表で使う `許諾 結果` 表記)

- **`allow ❌`** = permission は通ったが sandbox(OS 層)が実行時に止めた、の典型署名。
- **`ask ✅`** = 承認すれば通る。headless の実測が ❌ でもそれは auto-deny であって deny ではない。

### deny の2つの現れ方

| 現れ方 | 観測 |
|---|---|
| **呼び出し時拒否** | ツールは存在し、呼び出しが拒否されて `permission_denials[]` に記録される |
| **ツールセット除去(除去型)** | ツール自体がモデルから消える(「X tool is not enabled」)。呼び出しが起きないため denials も副作用も出ない。init メッセージの tools 一覧の欠落が ground truth |

## 4. 観測・計測の用語

| 用語 | 定義 |
|---|---|
| **probe(観測方法)** | 何を一次情報として観測するかの種別: `permission`(ブロックされたか) / `fs-write`(書けたか) / `fs-read`(読めたか) / `credential-leak`(秘密が漏れたか) / `network`(到達できたか) |
| **番兵(sentinel)** | 秘密ファイル・環境変数に仕込む実値。**出力に現れたら「読めた(漏洩した)」の証拠**。プロンプトには含めない(復唱を漏洩と誤判定しないため) |
| **副作用(sideEffects)** | ツールが成功したときディスク上にできるはずのファイル。存在の有無が ALLOWED/DENIED の一次証拠 |
| **execMarker** | コマンドが実際に実行された痕跡(出力中のマーカー)。無ければ「試行されなかった」= INCONCLUSIVE |
| **evidenceMarker / evidenceFile** | WHY の証跡(stderr の警告文言・hook の発火マーカーファイル等)。verdict には影響させず記録だけする |
| **askFired** | SDK 実測で `canUseTool` が発火したかの記録。ask/deny/allow を構造的に切り分ける ground truth |
| **preflight** | network probe の事前到達性確認(sandbox 外から)。オフラインを「遮断された」と誤判定しないため |
| **ground truth** | モデルの自己申告ではなくハーネス/OS が記録した一次情報(`permission_denials[]`・ディスク観測・init tools 一覧・askFired)。モデルの言い訳は判定に使わない |

## 5. 状態・注記ラベル

| ラベル | 意味 |
|---|---|
| **未実測箱** | ケースの箱(定義)はあるが実測がまだのもの(現在 0 件) |
| **by-design** | headless では構造的に測れない(承認者不在等)と分かっている INCONCLUSIVE。SDK 実測を権威として expected 一致扱い |
| **documented-only** | 一次 docs には記載があるが本リポジトリでは実測していない(破壊リスク・環境要件等の理由つき) |
| **【要裏取り】** | 一次 docs で未確認の主張。docs で裏取りするまで断定しない印 |
| **追補** | FINDINGS.md 末尾に時系列で追加された実測知見の節(追補1〜6) |

## 6. 記号の凡例

| 記号 | 文脈 | 意味 |
|---|---|---|
| ✅ / ❌ / - | 期待結果・対比表の**結果列** | 成功(ok) / 失敗・ブロック(ng) / 実行に至らない |
| ✅ / 🟡 / 🔬 / ⬜ / 📄 | COVERAGE の**状態列** | 検証済 / 部分(未実測サブケースあり) / 未実測箱 / 未着手 / 文書化のみ |
| 🔶 | モダリティ対比表 | `ask`(モダリティにより解決が異なる) |
| ⚠️ | 全域 | 危険・アンチパターン・無言の no-op 等の注意 |
| 🖥️ | S* グループ冒頭 | 実測環境の注記(sandbox は OS 実装依存のため) |
| 🔬 | P1 | research preview(eligibility 制)の印 |
| ★ | ルート README | 必読ドキュメントの印 |

> ⚠️ ✅/❌ は「結果列」(成功/ブロック)と「状態列」(検証済/未着手)で意味が変わる。表の列名・凡例で判別すること。

## 7. ケース README「期待結果」表の凡例(正本)

サブケース README の期待結果は `| No | 操作 | 許諾 | 結果 | 補足 |` の5列固定(1行 = 1プローブ。書式仕様は [CASE-FORMAT.md](./CASE-FORMAT.md))。

- **No** = 1 からの連番(`case.json` の `probes[]` と同順)
- **操作** = 実行するコマンド/ツールと実行の仕方(例: `Bash: curl example.com`)
- **許諾** = permission エンジンの判定 … `allow`(確認なしで通過) / `ask`(承認要求) / `deny`(拒否) / `-`(判定に到達せず)
- **結果** = **approve した前提で**最終的に完遂できたか … `✅`(ok) / `❌`(ng) / `-`(deny で実行に至らない)
- **補足** = 非自明な機構のみ。許諾/結果から読み取れる当たり前のことは書かず、無ければ `-`
- **`allow × ❌`** は「permission は通ったが sandbox(OS 層)が実行時に止めた」の典型署名

「headless/CI では ask は auto-deny になる」等の全ケース共通の前提は各行に書かない(この凡例に1回だけ置く)。

グループ README の対比表はこの2列を `許諾 結果` の1セルに合成した表記(例: `allow ❌`)を使う。
