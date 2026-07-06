# P3. write-glob-asymmetry（アンチパターン）— Write の glob は直感と違う

⚠️ このグループは「効いているつもりで効いていない」危険な地雷を集めたもの。運用でこの形に依存してはいけない。

## このグループで学ぶこと

- Write ツールの allow/deny で効くのは **`Write(*)` / bare `Write`（ツール単位）だけ**。パス限定形——`Write(<dir>/**)`（相対ディレクトリ glob）・`Write(**)`（bare ダブルスター）・**パス完全指定**・**単一星の dir 形 `Write(dir/*)`**・**絶対パス形**（`$CASE_DIR/sub/**` 等）・`~` 形——は**すべて無言で不一致**（allow なら許可されない、deny なら素通り）。dir を守りたいなら Write 規則ではなく **`Edit(<dir>/**)`**（Edit 規則は Write ツールも覆う → 後述の正解形）。
- ⚠️ **重要な訂正（2026-07-05・再訂正）**: 一時期「相対ディレクトリ接頭のダブルスター `Write(<dir>/**)` は効く（ASK ゲート）」と書いたが、これは**実測で反証された**。S9 の 1 変数分離実測（acceptEdits 下で `deny Write(assets/**)`＝ファイル作成 **5/5＝no-op** / `deny Edit(assets/**)`＝**0/5＝ブロック**）により、**`Write(<dir>/**)` は何も守らない no-op**（＝**false-security トラップ**）と確定。dir を締める“効く形”は **`Edit(<dir>/**)`**（Edit 規則は Write/Edit/MultiEdit すべてに適用＝docs「Edit rules apply to all built-in tools that edit files」。しかも **ASK ゲートではなくハード deny**で全モードで効く）。→ [S9](../../02-sandbox-bash/S9-tool-write-scope/README.md)。
- つまり **Write の specifier では path 限定は一切効かない**（相対 dir + `**` も含め no-op）。効くのはツール単位の `Write(*)` / bare `Write` のみ。dir/file を path で締めるのは **Edit 規則**の役目。

## サブケース一覧

| サブ | 設定 | 論点 | 詳細 |
|---|---|---|---|
| a | allow=`[Write(**)]` | allow の bare `**` が効かない → ask のまま | [a-allow-starstar-noop](./a-allow-starstar-noop/README.md) |
| b | allow=`[Write(*)]` + deny=`[Write(**)]` | deny の `**` が効かず素通り → allow が勝つ | [b-deny-starstar-noop](./b-deny-starstar-noop/README.md) |
| c | allow=`[Write(*)]` + deny=`[Write(PROOF.txt), Write(./PROOF.txt)]` | 名指しパス deny が素通り → allow が勝つ | [c-deny-path-noop](./c-deny-path-noop/README.md) |
| d | allow=パス限定5形態(単一星 dir/`./`/絶対/絶対`**`/`~`)を全部載せ | どの形態も不一致 → ask のまま | [d-path-scoped-noop](./d-path-scoped-noop/README.md) |
| e | allow=`[Write(*)]` + deny=`[Edit(PROOF.txt)]` | **個別ファイル保護の正解形**。Edit 規則は Write ツールも止める | [e-deny-edit-path](./e-deny-edit-path/README.md) |
| f | allow=`[Bash(*)]` + deny=`[Write(*)]` | 効く deny も守るのは**Write 経路だけ**。Bash リダイレクトは素通り | [f-deny-write-star-bash-redirect](./f-deny-write-star-bash-redirect/README.md) |

## 対比

同一プローブ（Write ツールで cwd 直下に `PROOF.txt` 作成）を各設定で走らせた結果マトリクス（セル = `許諾 結果`、結果は approve 前提）。対照として P2-a（`allow Write(*)`）と P2-b（`+deny Write(*)`）を併記:

| No | プローブ | P2-a `Write(*)` | a `Write(**)` | b `+deny Write(**)` | c `+deny path` | P2-b `+deny Write(*)` |
|---|---|:---:|:---:|:---:|:---:|:---:|
|1| Write `PROOF.txt`（cwd） | allow ✅ | ask ✅ | allow ✅ | allow ✅ | deny - |

- **`Write(*)` は効く（P2-a=`allow ✅`）。bare `**`・名指しパス・単一星 dir・絶対パスは効かない**。allow 側（a: `**` が不一致 → `ask` に落ちる）でも deny 側（b/c: deny が不一致 → allow が勝ち `allow ✅`）でも同じ非対称。
- a の `ask ✅` に注意: `Write(**)` は deny ではなく**マッチ無し → default の ask**。headless では auto-deny で ❌ に見えるが、approve すれば書ける。
- 効く deny は `Write(*)`（P2-b=`deny -`）**だけ**。path 限定の Write deny（相対 dir glob `Write(<dir>/**)` を含む）はすべて no-op（S9-a: `deny Write(assets/**)` は 5/5 素通り）。dir を締めるハード deny は Write ではなく **`Edit(<dir>/**)`**（→ 正解形・S9）。

## じゃあどう守るのか（正解形）

「特定ファイルを守りたい」の**正しい書き方は `deny Write(...)` ではなく `deny Edit(...)`**:

| やりたいこと | ❌ 効かない(無言 no-op) | ✅ 効く |
|---|---|---|
| 1 ファイルを名指しで守る | `deny Write(PROOF.txt)`(→ c) | **`deny Edit(PROOF.txt)`**(→ e。Edit 規則は Write ツールにも適用) |
| dir 単位で締める | `Write(dir/**)`・`Write(dir/*)`・`Write(<絶対>/dir/**)`(すべて no-op → d/S9) | **`deny Edit(dir/**)`**(Edit 規則は Write ツールも覆うハード deny → S9-a) |
| ツール単位で全部止める | `Write(**)`(→ a/b) | `deny Write(*)` / bare `Write`(→ P2-b) |

- ただし **permission 層の deny はツール経路単位**。`deny Edit(PROOF.txt)` も `deny Write(*)` も
  **Bash リダイレクト(`printf ok > PROOF.txt`)は塞がない**(→ f)。全経路を止めるには OS 強制の
  sandbox `denyWrite`(→ S2)を併用する。

## 要点

- **「deny を書いた ≠ 守られている」**。`deny Write(secret.txt)`（完全パス）や `deny Write(~/secret/*)`（単一星）や `deny Write(**)`（bare）は何も守らない。エラーも警告も出ない＝最も危険。マッチャは allow/deny 共通なので、この no-op は deny 側でも同じ（d）。
- **Write specifier で効く形は 1 系統だけ**: `Write(*)`／bare `Write`（ツール単位）。path 限定形はすべて no-op（相対 dir glob `Write(<dir>/**)` も含む＝S9-a で反証）。dir 単位で締めたいなら Write ではなく **`Edit(<dir>/**)`**（Edit 規則は Write/Edit/MultiEdit を覆う**ハード deny**、全モードで効く＝S9-a）。Bash 経路まで塞ぐなら OS 境界の sandbox `denyWrite`（→ S2）を併用する。
- ⚠️ **`Write(dir/**)` は「効きそうで効かない」最悪の紛らわしさ**（`Write(dir/*)`・絶対形と同じく no-op）。必ず空撃ち（+反復）で実測する。Write の path 依存は一切避け、dir 保護は `Edit(dir/**)` に寄せる。
- **個別ファイル保護は Edit 規則で書ける**（e）。`Write` specifier の path 版が no-op なのは Write の path マッチが docs 未保証だから。**docs が保証しているのは Read/Edit の path 規則**なので、そちらに寄せる。
- **効く deny も守るのは 1 経路**（f）。`deny Write(*)` は Write ツールを止めるが Bash 書込は通る。
- 帰結: Write 規則で「ネストした allow/deny」は構成できない（path 限定が全 no-op のため）。dir スコープが要るなら Edit 規則、規則のネスト一般の検証は Bash 規則で(→ P2-e)。
- ⚠️ **docs 未保証領域 vs 保証領域の切り分け**: ここが本グループの肝。docs のパス規則は **Read/Edit（と Bash・WebFetch 等の固有構文）にのみ gitignore 準拠と明記**され、**Write ツールの path specifier は docs 未規定**。本グループの a〜d は「Read/Edit の構文を Write に外挿すると無言で破れる」ことの実測であり（docs 違反ではなく**外挿の破れ**）、e は「docs が保証する Edit 規則に寄せれば守れる」ことの実測。未保証領域はバージョンで変わり得る（「Write の path 限定は相対 `dir/**` 含め全て no-op」は **2.1.201 の実測**）ので、Write の path 依存は避け、必ず空撃ちで再確認する。

## 対応する知識
- docs/FINDINGS.md: ボーナス発見1/2（allow・deny とも bare `**`/完全パス/単一星 dir/絶対パスは無言で不一致）
- 関連: P2（`Write(*)` は効く / deny の 2 形態）/ **S9（`Write(<dir>/**)` は no-op トラップ＝反証、dir 保護の正解は `Edit(dir/**)` ハード deny）** / S2（sandbox denyWrite=OS 強制。f の全経路遮断の正解）
