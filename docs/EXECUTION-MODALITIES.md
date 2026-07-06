# 実行形態の軸 — headless / 対話 / SDK

検証環境: **Claude Code 2.1.201 / Agent SDK 0.3.200 / macOS / 2026-07-05**

## TL;DR — 挙動は「2軸」で確定する（実行形態に依存しない）

permission/sandbox の挙動は、次の **2つの事実**さえ分かれば、対話・headless・SDK の**どの実行形態でも
機械的に確定できる**。これがこのリポジトリの検証設計の土台。

1. **許諾（permission エンジンの判定）** … `allow` / `deny` / `ask` / `-`（判定に到達せず※）
2. **実行結果（approve した場合に完遂できるか）** … `ok` / `ng` / `-`（deny で実行に至らない）
   ※ `ng` には **sandbox（OS 層）で遮断される場合を含む**。「許諾 allow だが結果 ng」＝ permission は
   通ったが sandbox が止めた、が典型。

この2軸から各実行形態の結果が導ける（実行形態が変えるのは **`ask` の行だけ**）:

| 許諾 | 実行結果(approve時) | headless | 対話(approve) | SDK(canUseTool) |
|---|---|:---:|:---:|:---:|
| allow | ok | ✅ | ✅ | ✅ |
| allow | ng（sandbox 遮断） | ❌ | ❌ | ❌ |
| deny | -（実行に至らない） | ❌ | ❌ | ❌ |
| ask | ok | ❌(auto-deny) | ✅ | deny→❌ / allow→✅ |
| ask | ng（approve でも sandbox で ❌） | ❌ | ❌ | ❌ |

- 各実行形態は **`ask` をどう解決するか**だけが違う（headless=auto-deny / 対話=人間が承認 / SDK=`canUseTool`）。
  `allow`/`deny` の行は3形態で一致する。
- 唯一この2軸に収まらないのは **SDK の `canUseTool` が `updatedInput` で入力を書き換えて許可する**場合
  （＝「approve as-is」から外れる別前提）。これは別ケースとして扱う（→ [CASE-FORMAT.md](./CASE-FORMAT.md)）。
- 帰結: `case.json` は **`expected.engine`（許諾）＋観測結果（実行結果）を1回書けば全形態に展開できる**。
  だから全ケースを3形態で総当たりする必要はない（下記）。

---

このリポジトリのケース群は基本 **headless（`claude -p`）** で測っている。
だが実行形態には少なくとも 3 つある——**headless / 対話（TUI）/ SDK**——ので、
「全ケースを 3 形態で総当たりすべきか?」という疑問が出る。答えは **No**。理由を以下に示す。

## permission エンジンは共通。実行形態が変えるのは `ask` の解決だけ

permission/sandbox の判定エンジンはどの実行形態でも同じで、結論は 3 値になる:

| エンジンの結論 | 意味 |
|---|---|
| **allow** | 規則にマッチ → 事前承認（プロンプトなし） |
| **deny** | 規則にマッチ → ハードブロック（承認の余地なし） |
| **ask** | どちらでもない → 人間の承認を求める |

`allow` / `deny` は実行形態に依存しない（規則マッチは承認より前に起きる）。
**実行形態が変えるのは `ask` をどう解決するか、そこだけ**:

| 実行形態 | `ask` の解決 | 備考 |
|---|---|---|
| **headless** (`claude -p`) | 承認者がいない → **自動 deny** | 例外: `--dangerously-skip-permissions` / `--permission-prompt-tool` |
| **対話** (TUI) | **人間にプロンプト** → その場で許可/拒否 | 承認すれば実行される |
| **SDK** | `canUseTool` コールバック / `permissionMode` に**委譲** | プログラムで allow/deny を返す |

### 用語と「2つの軸」（補足）

この3区分は厳密には1軸ではなく、2つの軸が交差したもの:

- **軸A: 入口** — CLI か SDK か（他に IDE 拡張・デスクトップ/Web アプリ。ただし permission の観点では対話/ヘッドレスに還元される）
- **軸B: 対話性** — 対話（人間がループ内）か 非対話（ヘッドレス）か

「対話/ヘッドレス」は軸B、「SDK」は軸A。**3つを1軸として意味あるものにしているのが上表の「`ask` の解決方法」**（人間 / 自動 deny / コールバック）。

正式名称の注記:
- **ヘッドレス** = CLI の `-p` / `--print`（"print mode" / 非対話）で起動する一モード。「headless」は通用する俗称。
- **SDK** = **Claude Agent SDK**（旧 "Claude Code SDK" から改称。`@anthropic-ai/claude-agent-sdk` / `claude-agent-sdk`）。
- permission mode（`default`/`acceptEdits`/`plan`/`dontAsk`/`bypassPermissions`/`auto`）や `--permission-prompt-tool` は3区分と**直交**する別概念。例えばヘッドレスでも `--permission-prompt-tool` で ask を外部ツールに委譲でき、SDK の `canUseTool` に近づく（＝「ヘッドレス=常に auto-deny」ではない）。

## だから「形態ごとの再検証」が要るのは ask ケースだけ

| 分類 | 該当ケース | 形態間で結論が変わるか |
|---|---|---|
| **allow/deny 規則のマッチング** | P2-a, P2-b, P4-a〜e/g/i, P3-a〜c, P5-b | **変わらない**（headless で 1 回測れば代表値。P4 は a〜i すべて SDK 併測で確定） |
| **`ask`（headless で auto-deny されているだけ）** | P1-a, P1-b※, P5-a, S1-a | **変わる**（headless=deny / 対話=承認可 / SDK=callback 次第） |
| **settings の解釈差（`defaultMode`）** | P1-i | **変わる**（CLI=settings の defaultMode を適用 / **SDK=`options.permissionMode` のみ**。規則 allow/deny は SDK でも settings から効くのと対照的） |

※ P1-b は acceptEdits により `ask` が `allow` に変わるケース。

つまり **16×3 の総当たりは不要**。必要なのは (1) ask/deny を判定軸として分離すること、
(2) SDK でその分離を経験的に裏づけること、(3) 対話形態を文書化すること。

## headless だけでは ask と deny を区別できない（計測の穴）

headless の `claude -p` は、ブロック時に `permission_denials[]` を出すが、
**「deny 規則によるハード拒否」と「ask が auto-deny されただけ」に同じ形で入る**。
つまり P1-a（ask）と P2-b（hard deny）は headless からは**どちらも同じ `DENIED`** に見える。

- P1-a の `result` 文言: `"blocked pending permission approval ... requiring authorization"` ← **ask**
- P4-a の `result` 文言: `"denied by your permission settings"` ← **deny**

文言（モデルの語り）にニュアンスは出るが不安定。**ask と呼び出し時 deny の構造的な区別は
headless では取れない。**

### deny には2つの現れ方がある（片方は headless でも構造検出できる）

| 現れ方 | 観測 | 例 |
|---|---|---|
| **呼び出し時拒否** | ツールは存在し、呼び出しが拒否されて `permission_denials[]` に記録される | P2-b（allow+deny 併記） |
| **ツールセットからの除去** | ツール自体が消え、モデルは「X tool is not enabled」と報告。**呼び出しが起きないため denials も副作用も出ない** | P2-c / P2-d（deny のみの設定） |

除去型は denials が空なので、素朴に見ると INCONCLUSIVE に化ける。ただし **init メッセージの
tools 一覧から target が欠けていること**が構造的シグナルになり、headless でも検出できる
（`harness/run.py` は `--output-format stream-json` で init を取得し、この判定を実装済み。
SDK 側の `initTools` 判定と同じロジック）。

## SDK を「ask を観測する計測器」に使う

Agent SDK の `canUseTool` コールバックは **engine が `ask` を返したときだけ呼ばれる**。
`deny` 規則にマッチした呼び出しは callback に届く前にブロックされ、`allow` は callback を経ずに実行される。
だから「callback が発火したか」を見れば ask/deny/allow を切り分けられる:

| 観測 | エンジンの判定 |
|---|---|
| target ツールで `canUseTool` が**発火** | **ASK** |
| 発火せず副作用が起きた | **ALLOWED**（規則/モードで事前承認） |
| 発火せず副作用も無くブロック | **DENIED_HARD**（deny 規則） |

実装は `harness/sdk/exec_case.mjs`(SDK 実行アダプタ。`harness/run.py -m sdk` から呼ばれる → [../harness/sdk/README.md](../harness/sdk/README.md))。
交絡（Write 拒否後の Bash フォールバック等）を避けるため callback は常に deny を返し、
**「ask が発火したか」だけ**を ground truth として記録する。

### 実測: 同一設定でも実行形態で結論が変わる（`results/summary-sdk.json`＝生成物・非コミット。`harness/aggregate_summary.py` で再生成）

既存ケースの `.claude/settings.json` をそのまま SDK 形態で回した結果:

| case | 設定 | engine | headless | 対話（TUI） | SDK |
|---|---|:---:|:---:|:---:|:---:|
| `P1-permission-mode/a-default-deny` | default・規則なし | **ask** | ❌ auto-deny | 🔶 承認可 | 🔶 ASK（callback 発火） |
| `P2-allow-deny-precedence/a-allow` | allow `Write(*)` | allow | ✅ | ✅ | ✅ ALLOWED |
| `P2-allow-deny-precedence/b-deny-beats-allow` | allow+deny `Write(*)` | deny | ❌ | ❌ | ❌ DENIED_HARD |
| `P4-bash-command-matching/a-direct` | deny `Bash(curl:*)` | deny | ❌ | ❌ | ❌ DENIED_HARD |
| `S1-sandbox-scope-vs-tools/a-bash-vs-tools` | sandbox+Write | **ask** | ❌ auto-deny | 🔶 承認可 | 🔶 ASK（callback 発火） |

凡例: ✅=許可 / ❌=ブロック / 🔶=`ask`（形態により解決が異なる）

- **P1-a・S1-a**: headless の `❌ DENIED` は **ハード拒否ではなく approvable な ask**。
  対話なら人間が承認でき、SDK なら callback で `allow` を返せば通る。
  「deny してないのに拒否」「sandbox なのに permission 要求」の正体はこの `ask` × headless。
- **P2-a・P2-b・P4-a**: 全形態で結論一致。allow/deny 規則は実行形態に依存しない。
- **P1-i（2026-07-05 追加実測）**: ask の解決以外に**settings 解釈の形態差**がもう1つある。
  CLI は settings の `permissions.defaultMode: acceptEdits` を適用する（headless write-cwd=ALLOWED）が、
  **SDK は `settingSources: ["project"]` で settings を読み込んでも defaultMode を適用しない**
  （モードは `options.permissionMode`（既定 `default`）で決まり、同じ write-cwd が SDK=ASK）。
  規則（allow/deny）は SDK でも settings から効く（P2 実測）ので、**「規則は settings から、モードは options から」**が SDK の実挙動。`case.json` は `expected.byModality.sdk` でこの差を記録している。

## canUseTool の判断ロジックと安全性の位置づけ

### どう判断されるか

**SDK 自身は判断しない。判断は 100% コールバックのコード**で、**呼ばれるのは engine の判定が `ask` のときだけ**（`deny` はコールバック前にブロック、`allow`/モードは経ずに実行）。型（`@anthropic-ai/claude-agent-sdk` v0.3.200）:

```ts
canUseTool = (
  toolName,                    // "Bash" / "Write" / "Read" …
  input,                       // ツールの全パラメータ（Bash なら command、Write なら file_path+content）
  { decisionReason,            // なぜ ask になったか（自分で推測しなくてよい）
    blockedPath, title, toolUseID, agentID, signal, suggestions }
) => Promise<
  | { behavior: 'allow', updatedInput?, updatedPermissions? }   // 許可（入力書換え/権限永続化も可）
  | { behavior: 'deny',  message, interrupt? }                  // 拒否（理由をモデルに返す/ターン中断）
>
```

SDK 固有の力: `input` を検査してプログラムで allow/deny、`updatedInput` で**入力を書き換えて許可**（秘密マスク・パス強制）、`updatedPermissions` で「今後自動許可」を永続化、`deny` の `message` はモデルに返り軌道修正させられる。

> 実測: `canUseTool` の返り値が結果を決めることは `harness/run.py -m sdk`（P1-a=ASK で発火 / P2-b・P4-a=DENIED_HARD で発火せず / P2-a=ALLOWED で発火せず）と `verify_w1_modality.mjs` で確認済み。

### canUseTool（あなたのコード） ≠ auto mode（モデル分類器）

**混同注意**: 「Claude Code が判断してくれる」のは `canUseTool` **ではなく** `permissionMode: 'auto'` の方。

| 手段 | 判断者 | 性質 |
|---|---|---|
| **`canUseTool`** | **あなたのコード** | 決定的・モデル非介在。「明確な基準」そのもの |
| **`permissionMode: 'auto'`** | **モデル分類器** | Claude が承認/拒否を判断（research preview） |
| `permissions.allow/deny` | ルールエンジン | 静的規則 |

- 「基準を明確に決めたい」→ `canUseTool`。「基準を決めずモデルに任せたい」→ `auto`。**逆に理解しやすい点**。
- 実測メモ: `--permission-mode auto` はフラグとして受理される（本環境）が、default で拒否される書込を auto が承認する挙動は**再現できず**（default 相当。auto は eligibility 要の preview）。「auto=モデル分類器」は SDK 型定義（`'auto' - Use a model classifier to approve/deny permission prompts`）で確定・承認挙動は本環境では未実証。

### 安全性の位置づけ（線形の優劣ではない）

| 観点 | 対話 (TUI) | ヘッドレス (`-p`) | SDK (canUseTool) |
|---|---|---|---|
| ask を誰が解決 | 人間 | 誰もいない→自動 deny | **あなたのコード** |
| 既定の安全度（無設定） | 人が承認するまで動かない | **fail-closed（最も安全）** | callback 無し=ヘッドレス同等 / 有り=コード次第 |
| 一貫性 | 低（承認疲れ） | 完全 | コード通りに完全 |
| 文脈判断 | 高いが可謬（injection に弱い） | 無し | 構造化入力を検査可・ただし書いた通り |
| 監査性 | 低 | 自明 | **高（全判断をログ可）** |
| アクション改変 | 不可 | 不可 | **可（updatedInput）** |
| fail-open スイッチ | "Yes, don't ask again" | `--dangerously-skip-permissions` | 全部 allow を返す callback |

- **SDK は最も強力＝「ポリシーコードと同じだけ安全」**。両者より厳しくも賢くもできるが、雑な callback は実質 bypass。
- **ヘッドレスは既定が最も安全（fail-closed）**。危険は skip フラグでの fail-open 反転。
- **対話は人間が強み＝弱み**（承認疲れ・プロンプトインジェクション）。

### このリポジトリの発見に基づく注意

1. **canUseTool は「ask」しか見ない**。broad な allow 規則や `acceptEdits`/`bypass` を併用するとそれらは**コールバックを素通り**する（盲点）。唯一の関所にしたいなら allow 規則を置かず default モードで。
2. **callback で Bash の command 文字列を見て判断するのは脆い**。`P4-c` の実証どおり `sh -c 'curl ...'` はラッパー内が見えず、`deny Bash(curl:*)` と同じ理由で騙せる。**文字列パースは境界にならない**。
3. **canUseTool は ask 帯の制御に過ぎない**。deny 規則も sandbox(OS 層)も canUseTool では緩められない。→ 実運用は **「deny 規則 + sandbox で硬い境界、その上で canUseTool を ask のポリシーエンジンに」** が最も堅い。
4. **sandbox は Bash とその子プロセス限定。ツールは sandbox を迂回する**（実測）: Read/Edit/Write は sandbox FS を迂回（`S1` / `S3-d` / `S7-b`）、**WebFetch は sandbox network を迂回**（`S6-h`: `allowedDomains:[]` でも WebFetch は到達。`verify_webfetch_bypass.mjs`）。→ ファイル・ネットワークをツール経由でも塞ぐには **permission.deny（Read/Edit/WebFetch）を併用**する。sandbox 単体では不十分。

## 対話（TUI）形態について（cmux で自動駆動して実測）

対話形態は **`ask` → 画面プロンプト → 人間が y/n** で一意に説明でき、
挙動は上表の 🔶 列（= SDK が callback で機械的に再現する分岐）と同じ。SDK が同じ分岐を機械再現するため
「対話は文書化に留める」方針だったが、**2026-07-06 に cmux（socket 制御可能なターミナル）で対話 TUI を
自動駆動し、代表 ask ケースで承認プロンプトの実出現を実測**した（`recordedBy: "cmux-driven (agent)"`）。

**cmux 駆動の手順**（`harness/run.py -m interactive` の prepare/judge と組み合わせる）:

1. `--step prepare <case>` で settings 実体化・fixture 配置。出力の起動コマンド（`claude --model … <flags>`）と
   env（configDir ケースは `CLAUDE_CONFIG_DIR`）・貼り付けプロンプトを取得。
2. `cmux new-workspace --cwd <case dir> --command "<起動コマンド>"` で claude TUI を起動 →
   `cmux send <prompt>` + `send-key Enter` でプロンプト投入 → `cmux read-screen` で承認プロンプトの有無を観測 →
   `send-key`（`Enter`=1.Yes）で承認 → `read-screen` で実行完遂を確認。
3. **configDir ケースは judge の前に workspace を close**（claude プロセスが生きていると rmtree した config dir を
   再生成する。credentials コピーを残さないため）。
4. `--step judge <case> --answer prompted=y --answer approved=y` で `results/interactive.json` に記録・後片付け。

**実測した代表 ask ケース（3 点セット headless/SDK/対話 完成、各 verdict=ASK 一致）**:

| case | 層 | 対話で観測した承認プロンプト（実キャプチャ） |
|---|---|---|
| P1-a `a-default-deny` | mode(default) | 4 プローブとも承認プロンプト（既存・human 記録） |
| P6-a `a-ask-alone` | 規則(ask 単独) | `Do you want to create PROOF.txt? / 1.Yes / 2.Yes, allow all edits… / 3.No` |
| P5-a `a-git-deny` | 保護パス | **acceptEdits でも** `.git/hooks/PROBE.txt` に承認プロンプト（保護パスは自動承認されない） |
| P7-f `f-ask-user-vs-project-allow` | スコープ横断 | project allow でも user ask が勝ち承認プロンプト |
| P9-e `e-hook-ask-over-allow` | hook×規則 | allow 済みでも hook の JSON ask で承認プロンプト |
| S4-d `d-autoallow-false-strict` | sandbox | `autoAllowBashIfSandboxed:false` で Bash に `Do you want to proceed?` |
| S5-i `i-content-ask-under-excluded` | sandbox 脱出 | TUI が **`Bash command (unsandboxed)`** と表示しつつ `Permission rule Bash(touch *) requires confirmation` |

- いずれも承認すると書込/実行が完遂（`ask ✅`）＝上表 🔶 の実挙動を headless の auto-deny（❌）と対比して確定。
- `deny` ケース（例 `P2-b` / `P4-a`）では**プロンプトすら出ずブロック**される（hard deny）＝ SDK 実測どおり。
- 残る ask-headline 群（S1 の Write/Edit ツール ask 等）は SDK で ASK 確定済みのため文書化優先で未駆動。手で確かめる場合も同手順。

## 環境ケース(srt / devcontainer)も同じ2軸で確定する

外側の分離手段(手段2=srt / 手段3=devcontainer)を検証する 03/04 の環境ケースも、この2軸に乗る。
srt/コンテナが足すのは **OS 境界**であって、許諾エンジンの外側で効くから、実行形態を変えても結論は同じ:

- srt 配下のツール経路失敗は **`allow`(permission 通過)× `ng`(OS が EPERM / socket 遮断)**。
  ask ではないので、**対話で承認しても・SDK で `canUseTool` allow を返しても通らない**(OS 層は緩められない)。
  これは本文表の「allow × ng(sandbox 遮断)」の行そのもので、3形態すべてで ❌ に揃う。
- **実測(2026-07-06)**: srt の a(FS read)/ b(FS write)/ e(Edit)/ h(WebFetch)を **headless と SDK の
  両方**で回し、同じ verdict(builtin~=ALLOWED / srt=DENIED_OS)を確認(各ケース `results/sdk.json`)。SDK が
  spawn する claude プロセスも Seatbelt 内に入る。→ 残りの srt ケースは形態を変えて再実測不要(2軸から導出)。
- **形態の選び方**(→ [cases/03-sandbox-runtime](../cases/03-sandbox-runtime/README.md) 試し方):
  対話=各ケース `prompt.ja.txt`(手軽に体感)/ ヘッドレス=`run_srt_cases.py`(記録の正)/
  SDK=`run_srt_cases.py -m sdk`(プログラムから)。
- ⚠️ **srt 配下の TUI は cmux 等の socket 自動駆動が効かない**(srt のプロセス包みが端末のキーボード
  プロトコル交渉と干渉し、キー入力が届かない)。対話は人間が手で駆動する用途で、自動記録は headless/SDK を使う。
  (組み込み側の代表 ask ケースは cmux で駆動できた ↔ srt を挟むと不可、という差。)

## まとめ

- 実行形態が変えるのは `ask` の解決だけ。allow/deny は共通。
- したがって形態別の再検証が要るのは `ask` ケース（P1-a/P5-a/S1-a・P1-b/P5-b）だけで、総当たりは不要。
  （S2-c は旧分類では ask 扱いだったが、実測で `allow ❌`＝OS ブロック(ask ではない・SDK askFired 空)に確定し、この表から外した。）
- headless は ask と deny を構造的に区別できない。**SDK の `canUseTool` がその区別の計測器**。
- 対話は「ask→人間プロンプト」で説明でき、**cmux で TUI を自動駆動して 7 群の代表 ask ケースを実測**（3 点セット完成）。残りは SDK 実測で足りるため文書化に留める。

## 対応する知識
- FINDINGS.md（headless での実測・sandbox 章）/ COVERAGE.md（全キー×グループ×状態）
- harness/sdk/README.md（SDK 計測器のセットアップと判定ロジック）
- 関連ケース: P1-a / P2-a / P2-b / P4-a / S1-a（`results/sdk.json` を併置）
