# S5. sandbox-excluded-and-unsandboxed — sandbox の抜け穴（脱出経路）

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201(2026-07-05〜06 実測)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)・Windows(native は Bash sandbox 非対応)では結論が変わり得る — 越境時は再実測。詳細は下の「検証環境と越境ノート」参照。

## このグループで学ぶこと

- sandbox の FS 境界からの**脱出穴は2系統**ある。どちらも「cwd 外 `$HOME` へ書けたか」を probe=`fs-write` で実測して露呈させる。
  1. **`excludedCommands`**：一致トークンを含む**行全体**が無条件で sandbox 外実行。チェーンした**非 excluded** コマンドまで巻き込んで脱出する（a=両 echo の基準 / b=非 excluded の `cat` を分離）。
  2. **`allowUnsandboxedCommands:true`（既定）× 広い `Bash(*)` allow**：sandbox で失敗したコマンドの unsandboxed 再試行が **regular permission flow** に載り、`Bash(*)` に**自動承認**されて脱出する（c を実測で訂正 → 2026-07-05）。
- **脱出の因果は「フラグ単体」ではなく「`Bash(*)` による自動承認」**。`Bash(*)` を外すと、allowUnsandboxed 経路の再試行は **ask**（e）、excludedCommands 経路の非 excluded 後段も **ask**（h）に落ちる。`allowUnsandboxedCommands:false` にすると再試行は**完全無視＝OS 層 `allow ❌`**（d）。この c/d/e（+ b/h の対称）の対比がグループの看板。

## サブケース一覧

| サブ | 設定の差分 | 論点 | 詳細 |
|---|---|---|---|
| a | `excludedCommands:["echo *"]` + `Bash(*)` / `echo hi && echo > $HOME` | excluded を含む行全体が sandbox 外（両サブコマンド echo の基準） | [a-excluded-escapes-line](./a-excluded-escapes-line/README.md) |
| b | a と同設定 / `echo hi && cat … > $HOME`（後段=非 excluded） | 非 excluded コマンドも行ごと脱出する分離 | [b-excluded-nonexcluded-chain](./b-excluded-nonexcluded-chain/README.md) |
| c | `allowUnsandboxedCommands:true` + `Bash(*)` / cwd 外書込 | **再試行が `Bash(*)` に自動承認され脱出** | [c-allowunsandboxed-fallback](./c-allowunsandboxed-fallback/README.md) |
| d | `allowUnsandboxedCommands:false` + `Bash(*)` / cwd 外書込 | Strict＝再試行を完全無視（OS 層で封鎖） | [d-allowunsandboxed-false-strict](./d-allowunsandboxed-false-strict/README.md) |
| e | `allowUnsandboxedCommands:true` + `allow:[]` / cwd 外書込 | **`Bash(*)` を外すと再試行は ask（allowUnsandboxed 経路の因果を分離）** | [e-allowunsandboxed-no-bashstar](./e-allowunsandboxed-no-bashstar/README.md) |
| h | `excludedCommands:["echo *"]` + `Bash(echo *)` / `echo hi && cat … > $HOME` | **`Bash(*)` を外すと非 excluded 後段は ask（excludedCommands 経路の因果を分離）** | [h-excluded-without-bashstar](./h-excluded-without-bashstar/README.md) |
| g | a と同設定 / `echo hi ; cat … > $HOME` と `echo hi \| tee $HOME` | **行全体脱出は `;` / `\|` でも起きる（separator 非依存）** | [g-excluded-separators](./g-excluded-separators/README.md) |
| i | `excludedCommands:["touch *"]` + `ask:["Bash(touch *)"]` / `touch $HOME` | **excluded で sandbox 外に出ても content-scoped ask は貫通（permission 層は独立）** | [i-content-ask-under-excluded](./i-content-ask-under-excluded/README.md) |

> f は**欠番**（未実測のまま記号を予約）: `f-excluded-managed-cannot-lock`（managed settings 対応のハーネス拡張が前提・据え置き。文書化は「要点」に済み）。
> g（`;`/`|` の separator マトリクス・旧 G6）は **2026-07-06 に実測して新設**（`&&` 断面が separator に一般化することを確定）。

## 対比

セル = `許諾 結果`（approve 前提）。probe=`fs-write`（cwd 外 `$HOME` への書込が成立＝脱出したか。副作用ファイルの有無で判定）。e / h のみ probe=`permission`（`Bash(*)` を外したときの permission 判定を測る）。

### 脱出の有無（各サブケースの escape 実測）

| No | 経路 / 操作 | a（excluded 両 echo） | b（excluded + 非excluded） | c（unsandboxed:true × Bash(*)） | d（unsandboxed:false） | e（unsandboxed:true × allow:[]） | h（excluded × Bash(echo *)） |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | cwd 外 `$HOME` への書込（脱出したか） | allow ✅ | allow ✅ | allow ✅ | allow ❌ | ask ✅ | ask ✅ |

- **a / b / c が脱出（`allow ✅`）** = 無条件（承認なし）で cwd 外へ抜ける。a/b は excludedCommands の行全体脱出、c は再試行の `Bash(*)` 自動承認。SDK でいずれも askFired 空。**共通因子は広い `Bash(*)`**。
- **d は `allow ❌`** = Strict（`allowUnsandboxedCommands:false`）が `dangerouslyDisableSandbox` を完全無視。再試行が起きず OS 層 EPERM（askFired 空＝param 無視）。
- **e / h は `ask ✅`** = `Bash(*)` を外した対照。自動承認されず承認プロンプトに落ちる（承認すれば脱出）。SDK で askFired=`Bash`、headless では auto-deny。**e は allowUnsandboxed 経路、h は excludedCommands 経路**の同型分離で、どちらも「無条件脱出の増幅要因は `Bash(*)`」を示す。

### 因果の分離（各経路とも1変数ずつ）

2 経路それぞれで、無条件脱出（`allow ✅`）が「どの設定」由来かを、1変数だけ変えた対照で切り分ける（実測 SDK の askFired が機構を露呈）:

**allowUnsandboxed 経路（c を基準に）:**

| 手順 | 変えた設定 | 変化 | 起きること（機構） |
|---|---|---|---|
| c（基準） | `unsandboxed:true` + `Bash(*)` | `allow ✅`（askFired 空） | 再試行が `Bash(*)` に**自動承認**され無条件脱出 |
| c → d | `unsandboxed:true` → **`false`** | ✅ → `allow ❌`（askFired 空） | 再試行が**完全無視**され OS 層で止まる |
| c → e | `Bash(*)` → **`allow:[]`** | ✅ → **`ask`**（askFired=Bash） | 再試行が regular permission flow で**不一致 → ask**（自動承認されない） |

**excludedCommands 経路（b を基準に）:**

| 手順 | 変えた設定 | 変化 | 起きること（機構） |
|---|---|---|---|
| b（基準） | `excluded:["echo *"]` + `Bash(*)` | `allow ✅`（askFired 空） | excluded を含む行が `Bash(*)` に**自動承認**され、非 excluded の `cat` ごと無条件脱出 |
| b → h | `Bash(*)` → **`Bash(echo *)`** | ✅ → **`ask`**（askFired=Bash） | 後段 `cat` が permission に**不一致 → ask**（excludedCommands は sandbox 層だけ緩め、permission 層は別レイヤ） |

- **d / e / h はどれも「脱出しない」が機構が違う**：d=param 無視（再試行が起きない）、e/h=ask（呼び出しは起きるが承認待ち）。SDK の askFired が分ける（d 空 / e=h=Bash）。
- 変えたのは毎回1変数なので、**両経路とも無条件脱出の増幅要因は `Bash(*)` による自動承認**（`unsandboxed:true` / `excludedCommands` の各フラグは必要条件に過ぎない）と確定できる。

## 要点

- **危険なのは `excludedCommands`（a/b）と `allowUnsandboxedCommands:true`（c）の両方だが、どちらも無条件脱出の増幅要因は広い `Bash(*)` allow**。worker は `excludedCommands:[]` かつ `allowUnsandboxedCommands:false`、かつ `Bash(*)` を使わない。この「`Bash(*)` を使わない」は e（allowUnsandboxed 経路）と h（excludedCommands 経路）の両方で因果を実測済み。
- **`excludedCommands` が緩めるのは sandbox 層だけ**：一致トークンを含む行を丸ごと sandbox 外実行し（b で非 excluded の `cat` まで脱出）、しかし **permission 層は別レイヤ**。`Bash(*)` があれば行全体が自動承認されて無条件脱出、`Bash(*)` を外すと後段非 excluded は ask に落ちる（h）。【要裏取り】「行全体巻き込み」は公式 docs 未記載＝観測駆動。
- **行全体脱出は区切り記号に依らない**（g）：`&&`（a/b）だけでなく `;` / `|` でも、excluded な `echo` を1つ含む行の非 excluded 後段（`cat`/`tee`）が cwd 外へ抜ける。permission 層は `;`/`|` を個別照合する（P4-g）のに対し、sandbox 脱出は行単位。「permission は個別・excluded 脱出は行全体」の層対比。
- **`allowUnsandboxedCommands:true` の再試行は regular permission flow を通る**（公式 docs 明記）。差は「脱出する/しない」ではなく「無条件（`Bash(*)` 自動承認）か / 承認依存（ask）か / 無効（`false`）か」。
- **`excludedCommands` には managed-only lockdown が無い**（公式 docs 明記）。managed 設定で固定できず、project/local で開発者や侵害リポジトリがいつでも追記できる → S4/S6 の `allowManaged*Only` 系と対照的な穴の非対称性。最小化しか防御手段がない。
- 「本当に止める」なら `allowUnsandboxedCommands:false` + excludedCommands 最小化 + allow を狭く。境界は sandbox FS/network に張る。

## 検証環境と越境ノート

- **プラットフォーム**: 本グループは macOS/Seatbelt で検証。Linux/WSL2=bubblewrap では sandbox 実装が異なり、**native Windows は Bash sandbox 非対応**（sandbox が効かない）。excludedCommands / allowUnsandboxedCommands のキー挙動そのものはクロスプラットフォームだが、脱出後の OS 層挙動は実装差があり得る。【要裏取り】WSL2 で Windows バイナリを sandbox 外実行させるために excludedCommands が要る、というプラットフォーム固有の運用差は一次 docs 未記載＝要裏取り扱い。
- **content-scoped ask 規則との相互作用（✅実測解消・2026-07-06, i）**: excludedCommands で sandbox 外に出たコマンドでも、**content-scoped ask 規則は貫通してプロンプトを強制する**（i: `excludedCommands:["touch *"]` + `ask:["Bash(touch *)"]` → SDK で ASK 発火・askFired=['Bash']）。excludedCommands は sandbox 層だけを緩め、permission 層の content ask は独立に効く（S4-f の auto-allow 経路と同型）。「excluded 化が ask 規則を無効化する」危険な穴は**存在しない**。ただし bare `Bash` ask は sandbox 実行分をスキップする（S4-e）ので、締めるなら content-scoped 形で書く。

## 対応する知識
- refactor-plan.md §2.2（excludedCommands / allowUnsandboxedCommands）— F4「allowUnsandboxed は FS 脱出を自動許可しない」は c の実測で**反証済み**（`Bash(*)` 同居下では脱出する）。
- docs/FINDINGS.md / docs/COVERAGE.md（S5 の脱出2系統）
- 一次 docs: sandboxing（escape hatch = dangerouslyDisableSandbox の再試行は regular permission flow / `allowUnsandboxedCommands:false`=Strict でパラメータ完全無視 / excludedCommands は managed-only lockdown 無し）
- 関連: S2-a（cwd 外書込は本来 `allow ❌`）/ S4（autoAllowBashIfSandboxed = sandbox の Bash 自動許可）/ S6（network は OS 層で脱出不可）
