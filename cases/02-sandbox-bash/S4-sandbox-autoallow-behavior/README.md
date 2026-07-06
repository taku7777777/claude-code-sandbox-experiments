# S4. sandbox-autoallow-behavior — `autoAllowBashIfSandboxed` の効きと ask の正体

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。

## このグループで学ぶこと

- `autoAllowBashIfSandboxed`(**公式キー・既定 true**)が、sandbox 有効時に Bash を無プロンプトで自動許可する。`false` にすると通常の permission フロー(=ask)に戻る。
- 自動許可下でも **ask に落ちる形がある**: ask を左右するのは allow 構成ではなく**コマンド形状**(glob→変数→ファイルは ask)。個別 allow を足しても ask は増えない。
- ⚠️ 用語注意: 本グループの *auto-allow* は `autoAllowBashIfSandboxed`(sandbox 由来の Bash 無プロンプト)であり、permission mode の `auto`(サーバ分類器・§1.4)とは**別機構**(docs: sandboxing「auto-allow は auto mode とは別・独立して働く」)。

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | sandbox on(autoAllow 既定 true) | cwd 書込が無プロンプトで自動許可 | [a-empty-allow-autoallows](./a-empty-allow-autoallows/README.md) |
| d | a + `autoAllowBashIfSandboxed:false` | 自動許可が消え ASK に戻る | [d-autoallow-false-strict](./d-autoallow-false-strict/README.md) |
| c | sandbox on + `allow:[]`(baseline) | glob→ファイルは auto-allow 下でも ASK | [c-glob-file-ask-fallback](./c-glob-file-ask-fallback/README.md) |
| b | c + `allow:["Bash(echo:*)"]` | 個別 allow を足しても ask は増えない | [b-individual-allow-no-ask-increase](./b-individual-allow-no-ask-increase/README.md) |
| e | sandbox on + `ask:["Bash"]`(bare)+ excluded `touch *` | bare ask は **sandbox 実行分スキップ・非 sandbox 実行分に適用** | [e-bare-ask-skipped](./e-bare-ask-skipped/README.md) |
| f | sandbox on + `ask:["Bash(touch *)"]`(content-scoped) | content-scoped ask は **auto-allow を貫通**してプロンプト強制 | [f-content-ask-forced](./f-content-ask-forced/README.md) |
| g | sandbox on + `deny:["Bash(echo:*)"]` | **明示 deny は auto-allow に勝つ** | [g-deny-overrides-autoallow](./g-deny-overrides-autoallow/README.md) |
| h | sandbox on(プローブが rm) | home 配下サブ dir の rm は**プロンプト対象外**(守るのは OS 境界) | [h-rm-critical-path](./h-rm-critical-path/README.md) |

## 対比

セル = `許諾 結果`(approve 前提)。全セル実測(headless / sdk 一致)。

### 対比1: a ↔ d(autoAllowBashIfSandboxed の1変数対照)

同一プロンプト `echo data > inside.txt`・同一 base 設定。差は `autoAllowBashIfSandboxed` だけ。

| No | 操作 | a(既定 true) | d(false) |
|---|---|:---:|:---:|
| 1 | Bash `echo data > inside.txt`(cwd 内) | allow ✅ | ask ✅ |

| 手順 | 足した設定 | 変化 | 起きること |
|---|---|---|---|
| a(基準) | sandbox on のみ | allow ✅ | 既定 true で sandboxed Bash を無プロンプト自動許可 |
| a → d | `autoAllowBashIfSandboxed:false` | **allow ✅ → ask ✅** | 自動許可が消え通常の承認フロー(ask)に戻る。headless は auto-deny、承認すれば書ける |

### 対比2: b ↔ c(個別 allow で ask は増えるか / コマンド形状 × allow 構成)

行=コマンド形状、列=allow 構成。同一プローブを両設定で実測:

| No | 操作(コマンド形状) | c(allow:[]) | b(allow:[Bash(echo:*)]) |
|---|---|:---:|:---:|
| 1 | `echo hi > out.txt`(単純) | allow ✅ | allow ✅ |
| 2 | `for f in *.txt; do wc -l "$f"; done`(glob→変数→ファイル) | ask ✅ | ask ✅ |

- **列 c と列 b は完全に同一** = 個別 allow `Bash(echo:*)` を足しても ask は増えない。
- **行1と行2で結果が割れる** = ask を決めるのは**コマンド形状**。単純 echo は auto-allow、glob→変数→ファイルは ask。

### 対比3: auto-allow が飛ばすもの・飛ばさないもの(e/f/g/h。spec §4.2 の例外を全実測)

| 規則 / 対象 | sandbox 実行での結果 | 実証 |
|---|:---:|---|
| 規則なし(既定 ask 相当) | **スキップ** → 無プロンプト実行 | a |
| bare `Bash` ask | **スキップ** → 無プロンプト実行(※非 sandbox 実行分には適用= e probe 2) | e |
| content-scoped ask `Bash(touch *)` | **貫通** → ASK(SDK canUseTool 発火) | f |
| 明示 deny `Bash(echo:*)` | **貫通** → DENIED(SDK 非発火の hard deny) | g |
| コマンド形状(glob→変数→ファイル / `$?` 展開) | **ASK に落ちる**(規則がなくても) | c / h 設計メモ |
| `rm -rf ~/サブdir` | **スキップ**(critical-path プロンプト対象外)→ 実削除は OS 境界の EPERM | h |

読み方: auto-allow が飛ばすのは「**既定 ask と bare `Bash` ask**」だけ。**明示の内容指定(deny / content-scoped ask)と
コマンド形状の ask は残る**。rm の critical-path プロンプトは home 配下サブ dir には及ばず、実際に守っているのは
sandbox の書込境界(→ S2)。`/`・`~` 本体の rm circuit breaker は documented-only(破壊リスクのため非実測)。

## 要点

- **worker 構成が `sandbox + 規則なし`で回るのは autoAllow=true のおかげ**(a)。厳格運用にしたいなら `autoAllowBashIfSandboxed:false`(全 Bash が ask に戻る = d)。
- **d の反転は ASK であって OS ブロックではない**(SDK で canUseTool 発火を確定)。対話なら承認で通る/headless では auto-deny で止まる。旧 record の "strict mode" 帰属は誤り(`allowUnsandboxedCommands` とは別キー)。
- **ask を左右するのはコマンド形状**(c/b)。`multi-repo-workspace.md` の「個別 allow は ask を増やす/`allow:[]`+autoAllow が最善」は v2.1.201 で**否定**(→ b。L84/L286 同期済み 2026-07-05)。
- **auto-allow 下でも残る例外を全実測**(対比3): 明示 deny は常に有効(g)/ content-scoped ask は sandbox 下でも強制(f)/ bare `Bash` ask は sandbox 実行分スキップ・非 sandbox 実行分に適用(e)。**sandbox 運用でも「deny で禁止」「content-scoped ask で確認」のゲートはそのまま書ける**。
- **rm の critical-path プロンプトは home 配下サブ dir には発動しない**(h)。消されたくないパスを守るのは permission ではなく sandbox 書込境界(または deny 規則)。`/`・`~` 本体の circuit breaker は documented-only。

## 対応する知識
- 一次 docs: settings(`autoAllowBashIfSandboxed` 既定 true)/ sandboxing(auto-allow ≠ mode auto / auto-allow 下でも残る例外)
- refactor-plan.md 付録A(autoAllowBashIfSandboxed は既定 true の公式キー)/ multi-repo-workspace.md(個別 allow 主張=b で否定・要同期)
- 関連: S2-a(cwd 書込=sandbox 境界の視点)/ S1(Write ツールは sandbox 対象外)
