# 04. filesystem-write — Write 制御（allowWrite ホワイトリスト）

## このグループで学ぶこと

- Write はデフォルト全拒否のホワイトリスト方式（allowWrite に列挙したパスだけ書ける）。
- CWD（.）は暗黙的に書けるが、denyWrite:["~"] を足すとその暗黙許可も allowWrite 例外も両方潰れる（アンチパターン）。

## サブケース一覧

| サブ | 設定の差分（1変数ずつ） | 論点 | 詳細 |
|---|---|---|---|
| a | allowWrite: [] | ベースライン。CWD だけ書ける | [a-write-inside-workspace](./a-write-inside-workspace/README.md) |
| b | + allowWrite:["~/.cache/sandbox-w-test"] | ホワイトリストで1パス開ける | [b-allowwrite-adds-path](./b-allowwrite-adds-path/README.md) |
| c | + denyWrite:["~"]（アンチパターン） | denyWrite が許可を打ち消す | [c-denywrite-pitfall](./c-denywrite-pitfall/README.md) |

## 対比

3プローブを 3設定で走らせた結果マトリクス（echo x > <path> の成否）:

| No | プローブ（書込先） | a allowWrite:[] | b +["~/.cache/sandbox-w-test"] | c + denyWrite:["~"] |
|---|---|:---:|:---:|:---:|
|1| CWD 内 ./probe.txt | ✅ | ✅ | ❌ |
|2| CWD 外 /tmp/... | ❌ | ❌ | ❌ |
|3| ホーム配下 ~/.cache/sandbox-w-test/... | ❌ | ✅ | ❌ |

### 設定を1つずつ変えると挙動がどう動くか（a を基準に）

各列は前の設定に1変数だけ足したもの。足した設定と、それで変化するプローブの対応:

| 手順 | 足した設定 | 変化するプローブ | 起きること |
|---|---|---|---|
| a（基準） | allowWrite: [] | 1=✅ / 2=❌ / 3=❌ | CWD だけ書ける |
| a → b | + allowWrite:["~/.cache/sandbox-w-test"] | 3: ❌ → ✅ | ホワイトリストが穴を開ける |
| b → c | + denyWrite:["~"] | 1: ✅ → ❌、3: ✅ → ❌ | deny が CWD 暗黙許可も allowWrite 例外も両方潰す |

- プローブ 2（/tmp）は全設定で ❌ ＝対照群（CWD 外は何をしても常にブロック）。
- 変えたのは毎回1変数だけなので、「変化したプローブ ⇔ 足した設定」が1対1で結びつき、原因が確定できる。

## 要点

- Write は allowWrite（ホワイトリスト）だけで制御する。 ~ 配下でも列挙すれば書ける（例: worktree の repositories/<repo>/.git/ → Case 06b）。
- denyWrite:["~"] は使わない。 3 の allowWrite 例外だけでなく 1 の CWD 暗黙許可まで潰す＝自分の作業ディレクトリにも書けなくなる（b→c が決定的証拠）。
- 2 CWD 外は常にブロック（Bash も Python subprocess も OS レベル/seatbelt で一律）。
- read/write は非対称: 読取は denyRead(ブラックリスト)+allowRead(例外)、書込は allowWrite(ホワイトリスト)のみ。denyRead:["~"] 下では「CWD に書けても cat で読み戻せない」ため、書込確認は exit code か Read ツールで。

## 対応する知識
- 勉強会セクション: 2（できること / できないこと）
- knowledge: 02-behavior-facts/layers-and-tools.md §3
- 検証ログ: 03-verification-log/2026-07-02-write-cwd-denywrite.md