# P1. permission-mode — モードが書込系ツールの「許諾の既定値」を決める

## このグループで学ぶこと

- 同じ「規則なし」でも、モードによって許諾が `ask` / `allow` / `deny` / `-`(試行されない)に分かれる。
- `acceptEdits` の自動承認は **cwd 内限定**。cwd 外への書込は ask のまま(モード×操作の対比で確定)。
  対象は編集ツールだけでなく **Bash の FS コマンド(mkdir/touch 等)も含む**(h)。
- モードが動かすのは「ask になるはずの判定」だけ。**読取専用ツール(Read)はどのモードでも素通し**
  (a/c/g の read プローブ)、**allow 済みは dontAsk でも通る**(g)。

## サブケース一覧

| サブ | 設定/モードの差分 | 論点 | 詳細 |
|---|---|---|---|
| a | default(規則なし) | ベースライン。全書込が ask | [a-default-deny](./a-default-deny/README.md) |
| b | acceptEdits | ファイル編集を自動承認(cwd 内限定) | [b-acceptEdits](./b-acceptEdits/README.md) |
| c | plan | 読取専用。書込を試みない | [c-plan-mode](./c-plan-mode/README.md) |
| d | dontAsk | 未承認は ask せず即 deny | [d-dontAsk](./d-dontAsk/README.md) |
| e | bypassPermissions | プロンプト省略で全許可 | [e-bypassPermissions](./e-bypassPermissions/README.md) |
| f | auto(research preview) | 🔬 本環境では自動承認が発現せず default 相当 | [f-auto-mode](./f-auto-mode/README.md) |
| g | dontAsk + `allow: ["Write(*)"]` | 事前承認済みは dontAsk でも通る(d の肯定対照) | [g-dontAsk-with-allow](./g-dontAsk-with-allow/README.md) |
| h | acceptEdits(プローブ=Bash) | FS コマンド(mkdir/touch)も自動承認。cwd 境界も同じ | [h-acceptEdits-bash-fs](./h-acceptEdits-bash-fs/README.md) |
| i | settings の `defaultMode: acceptEdits` | CLI フラグと同結果(指定経路の等価性) | [i-defaultMode-in-settings](./i-defaultMode-in-settings/README.md) |

- a〜f はモードだけを CLI フラグ `--permission-mode` で変える対比。g は規則との交差、h はプローブ側の拡張、
  i は指定経路(settings)の対照。
- v2.1.200 以降、CLI 上 `default` は **Manual** と表示され、`--permission-mode manual` エイリアスも受理される。
- **モード封じ設定**(documented-only・2026-07-06 一次 docs 確認・本リポジトリ未実測): `permissions.disableBypassPermissionsMode` /
  `permissions.disableAutoMode` に文字列 `"disable"` を設定すると **bypassPermissions / auto モードの使用を禁止**できる
  (`--permission-mode` フラグは起動時拒否、auto は Shift+Tab サイクルからも消える)。任意スコープで書けるが、
  上書きされない **managed settings に置くのが定石**(permissions / settings / permission-modes docs 明記。
  実測は managed 環境が前提)。防御設計の型は
  [docs/BEST-PRACTICES.md §3](../../../docs/BEST-PRACTICES.md)。

## 対比 — モード × 操作(全セル実測)

全ケース同一の4プローブ(Write cwd内 / Write cwd外 / Write サブdir / Edit)を各モードで実測した。
セル = `許諾 結果`(結果は approve 前提。ask の headless auto-deny は結果に含めない):

| No | 操作 | a default | b acceptEdits | c plan | d dontAsk | e bypass | f auto※ |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Write `./PROOF.txt`(cwd 内) | ask ✅ | allow ✅ | - ❌ | deny - | allow ✅ | ask ✅ |
| 2 | Write `~/…`(cwd 外) | ask ✅ | **ask ✅** | - ❌ | deny - | allow ✅ | ask ✅ |
| 3 | Write `./sub/…`(サブdir) | ask ✅ | allow ✅ | - ❌ | deny - | allow ✅ | ask ✅ |
| 4 | Edit `./note.txt`(既存) | ask ✅ | allow ✅ | - ❌ | deny - | allow ✅ | ask ✅ |

- **各列は縦に一様、例外は b の 2 だけ**。acceptEdits の自動承認境界が cwd で切れている証拠
  (これが多プローブ対比で初めて見える差分)。
- 24セルすべて実測(推定なし)。
- ※ f(auto)は eligibility 制の research preview。この列は**未充足の本環境での実測**で、
  a(default)と完全一致 = 自動承認は発現していない(仕様上は 1・3・4 が allow のはず → 詳細は f README)。

### 追加プローブ(肯定対照と範囲の確定・全セル実測)

上の 4 プローブ行列を補う実測。書込「以外」と規則・経路との交差:

| 操作 | モード/設定 | 許諾 結果 | 何が分かるか |
|---|---|:---:|---|
| Read `./sentinel.txt` | a default | allow ✅ | **default が止めるのは書込系だけ**。読取は承認不要ティア |
| Read `./sentinel.txt` | c plan | allow ✅ | plan は「読取専用」であって「何もしない」ではない |
| Read `./sentinel.txt` | g dontAsk | allow ✅ | dontAsk は読取専用ティアに影響しない |
| Write `./PROOF.txt` | g dontAsk + `allow: ["Write(*)"]` | allow ✅ | **allow 済みは dontAsk でも通る**(CI レシピの肯定対照) |
| Bash `mkdir`/`touch`(cwd 内) | h acceptEdits | allow ✅ | 自動承認は編集ツール限定でなく **FS コマンドも対象** |
| Bash `mkdir ~/…`(cwd 外) | h acceptEdits | ask ✅ | Bash 自動承認にも **cwd 境界**が適用される |
| Write `./PROOF.txt` | i settings `defaultMode: acceptEdits` | allow ✅ | settings 経路でも CLI フラグと同結果(cwd 外 ask も再現) |

> ⚠️ i は **SDK ではモードが settings から持ち上がらない**(`options.permissionMode` が唯一の経路)という
> モダリティ差を実測している → [i README](./i-defaultMode-in-settings/README.md)。

### モードで何が変わるか

`許諾`=permission エンジンの判定 / `結果`=approve した前提で完遂できたか。

| モード | 許諾 | 結果 | 機構 |
|---|:---:|:---:|---|
| default | ask | ✅ | 書込系は毎回人間の承認を求める |
| acceptEdits | allow(cwd 内)</br>ask(cwd 外) | ✅ | プロジェクト内編集を自動承認 |
| plan | - | ❌ | 読取専用フェーズ。**主にモデル誘導**(SDK 実測: canUseTool 非発火=書込を試みない)。まれに試みた場合も deny される(c の headless で 1 プローブに denial 記録)。読取は通る |
| dontAsk | deny | - | allow 未登録は **ask せず即 deny**(SDK 実測: canUseTool 非発火の hard deny = deny-not-ask を確認)。allow 済みは通る(→ g)。CI 向け・完全非対話 |
| bypassPermissions | allow | ✅ | プロンプト省略(`--dangerously-skip-permissions` 相当。**保護パス write も skip**。残る例外は明示 `ask` 規則と `rm -rf /`・`rm -rf ~` の circuit breaker のみ) |
| auto(preview) | ask(本環境)</br>仕様: allow(wd 内) | ✅ | 分類器(モデル)が判定する唯一のモード。eligibility 未充足だと default 相当 |

## 要点

- モードが決めるのは書込系ツールの「許諾の既定値」。deny 規則が無くても素通しにはならない(a)。
- **acceptEdits は cwd 境界**。cwd 外へ書くなら allow 規則を明示するか bypass(隔離環境)を使う(b/e の対比)。
- headless/CI では ask は auto-deny になる(→ [EXECUTION-MODALITIES.md](../../../docs/EXECUTION-MODALITIES.md))。
  CI で書き込むなら acceptEdits(cwd 内)か allow の明示。**完全非対話の正解形は
  「必要最小の allow を列挙 + dontAsk」**(g で肯定・d で否定の両対照を実測済み)。
- モードの指定は CLI フラグと settings の `defaultMode` で等価(i)。ただし **SDK は例外**で、
  settings を読み込んでもモードは `options.permissionMode` でしか変わらない(i の SDK 実測)。

## 対応する知識

- docs/FINDINGS.md: Q1「deny していないのに write が拒否される」
- docs/EXECUTION-MODALITIES.md TL;DR(2軸モデル。この対比表のセル表記の根拠)
