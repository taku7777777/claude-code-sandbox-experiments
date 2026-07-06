# P4. bash-command-matching — チェーンも「剥がされるラッパー」も防げる、防げないのは剥がされないラッパー/サブシェル

## このグループで学ぶこと

- Claude Code は複合コマンドを**サブコマンド単位で照合**する。`&&`/`;`/`|` 等どの区切りの
  チェーンでも deny をすり抜けない(b, g)。
- **ラッパーは一律ではない**。`nice`/`timeout`/`nohup`/`stdbuf`/フラグ無し `xargs` は照合前に
  **剥がされ**中身が照合されるので deny に当たる(e)。一方 `sh -c '...'` の**文字列内**や `$(...)` は
  照合されずすり抜ける(c)。**「ラッパー＝すり抜け」は誤りで、剥がしリストに載るかどうかで決まる**。
- スコープの包含は向きで決まる: **広い allow + 狭い deny なら curl だけ塞げる(a)**が、規則は
  サブコマンド個別照合なので **allow の prefix はチェーン先の別コマンドに及ばない(d)**。
- 規則を何も書かなくても **read-only コマンド集合(cat/ls/echo…)は無プロンプトで通る**(i)。

## サブケース一覧

| サブ | 設定 / コマンドの呼び方 | 論点 | 詳細 |
|---|---|---|---|
| a | allow `Bash(*)` + deny `Bash(curl:*)` / `curl` と `echo` の2形 | 狭い deny は curl だけ塞ぎ echo は通す(例外を彫れる向き) | [a-direct](./a-direct/README.md) |
| b | 同上 / `echo hi && curl ...` | `&&` チェーンでもサブコマンド個別照合 → deny | [b-chained](./b-chained/README.md) |
| c | 同上 / `sh -c 'curl ...'` | 剥がされないラッパーの文字列内は照合されず → すり抜け(アンチパターン) | [c-wrapper-bypass](./c-wrapper-bypass/README.md) |
| d | allow `Bash(echo:*)` のみ / `echo hi && touch ...` | allow prefix はチェーン先に及ばず → ask | [d-allow-prefix](./d-allow-prefix/README.md) |
| e | 同上(a と同設定) / `nice curl ...` | **剥がされるラッパー**は中身 curl として照合 → deny(c の否定対照) | [e-wrapper-stripped](./e-wrapper-stripped/README.md) |
| g | 同上(b と同設定) / `echo hi ; curl` と `echo hi \| curl` | `;` `\|` 区切りでも個別照合 → deny(b の `&&` を拡張) | [g-separators](./g-separators/README.md) |
| i | 規則なし / `cat` と `touch` | read-only 集合は無条件承認 / 集合外は ask(d の echo 交絡を切り分け) | [i-readonly-set](./i-readonly-set/README.md) |

> f・h は**欠番**: GAPS 提案の `f-runner-passthrough` は環境ランナー(devbox/npx/docker)未導入で実測不能、`h-word-boundary` は `lsof` が read-only 分類で自動承認され ask 差を示せないため見送り(→ 下の「未カバー」注記)。

## 対比 — 呼び方 × 許諾/結果(全セル実測)

サブケースごとに**コマンドの呼び方**を変えた結果マトリクス(セル = `許諾 結果`、結果は approve 前提)。
a は同一設定内で curl/echo の2プローブを持ち、狭い deny の効き方(マッチする形だけ塞ぐ)を1行で示す:

| No | 呼び方 | 設定 | 許諾/結果 | 意味 |
|---|---|---|:---:|---|
| a1 | `curl … -o CURLED.txt`(直接) | allow `Bash(*)` + deny `Bash(curl:*)` | deny - | prefix deny に素直に当たる |
| a2 | `echo ok > ECHOED.txt` | 同上 | allow ✅ | deny に不マッチ → `Bash(*)` の allow が効く |
| b | `echo hi && curl … -o CURLED.txt` | 同上 | deny - | 各サブコマンド個別照合 → curl が deny |
| g1 | `echo hi ; curl …` | 同上 | deny - | `;` 区切りでも個別照合 → curl が deny |
| g2 | `echo hi \| curl …` | 同上 | deny - | `\|` 区切りでも個別照合 → curl が deny |
| e | `nice curl … -o CURLED.txt` | 同上 | deny - | **剥がされるラッパー** → 中身 curl として照合 → deny |
| c | `sh -c 'curl … -o CURLED.txt'` | 同上 | allow ✅ | **剥がされない**ラッパーの文字列内は不可視 = deny の抜け穴 |
| d | `echo hi && touch scratch.txt` | allow `Bash(echo:*)` のみ | ask ✅ | 未許可 touch を含む複合は自動承認されず ask |
| i1 | `cat existing.txt` | 規則なし | none ✅ | read-only 集合は無条件承認(規則ゼロでも通る) |
| i2 | `touch made.txt` | 規則なし | ask ✅ | 集合外+規則無し → ask |

- **a1/a2**: 同じ設定でも deny の形にマッチするか否かで許諾が割れる。狭い deny は「マッチした形の分だけ」
  例外を彫る(→ P2-e の逆方向で、包含関係3パターンを完成)。
- **b/g1/g2 → e → c**: curl の**包み方**を1変数ずつ変える対照。`&&`/`;`/`|` チェーン = deny(区切りに
  依らず個別照合で隠せない)、`nice`(剥がされるラッパー)= deny(中身が照合される)、`sh -c`(剥がされない
  ラッパー)= すり抜け。**防げるのはチェーンと剥がされるラッパー、防げないのは剥がされないラッパー/サブシェル**。
- **d**: deny 側(b)と同じサブコマンド個別照合が allow 側にも現れる。ただし deny 規則が無いので
  hard deny ではなく **ask**(承認すれば touch は完遂)。allow の prefix はチェーン先に波及しない。
- **i1/i2**: 規則ゼロでも read-only 集合(cat 等)は無プロンプト、集合外(touch)は ask。d の `echo` が
  この集合に属す交絡を切り分ける(allow prefix の効果は集合外コマンドで測るのが正しい)。
- 全セル実測(推定なし)。a1/b/g/e は SDK で canUseTool 非発火の DENIED_HARD、c は副作用で ALLOWED、
  d/i2 は canUseTool 発火の ASK、i1 は read-only 自動承認の ALLOWED を確認済み。

### 呼び方/設定を1つずつ変えると(a を基準に)

| 手順 | 変えた点 | 変化するプローブ | 起きること |
|---|---|---|---|
| a(基準) | allow `Bash(*)` + deny `Bash(curl:*)` | a1=deny / a2=allow | curl だけ deny、echo は allow(狭い deny の例外彫り) |
| a → b | 呼び方を `echo && curl` に | b=deny | サブコマンド個別照合で curl が deny(チェーンで隠せない) |
| b → g | 区切りを `;` / `\|` に | g1/g2=deny | 区切り種別に依らず curl が個別照合で deny |
| b → e | 呼び方を `nice curl …` に | e=deny | 剥がされるラッパーは中身 curl として照合 → deny |
| e → c | 呼び方を `sh -c 'curl …'` に | c: deny → **allow** | 剥がされないラッパーの文字列内は不可視ですり抜ける |
| a → d | 設定を allow `Bash(echo:*)` のみに / `echo && touch` | d=ask | deny が無いので、未許可 touch を含む複合は ask に落ちる |
| a → i | 設定を規則なしに / `cat` と `touch` | i1=none / i2=ask | read-only 集合は無条件承認、集合外は ask |

- a1(curl 直接)と a2(echo)の対照が**狭い deny の効き方**の対照群、b→g→e→c が**チェーン/剥がされる
  ラッパー vs 剥がされないラッパー**の対照群。変えたのは毎回1変数なので「変化したプローブ ⇔ 変えた
  呼び方/設定」が1対1で結びつく。
- **未カバー(documented-only)**: 環境ランナー(`devbox run`/`npx`/`docker exec`)の allow 無差別通過は
  本ホストに未導入で実測できず未検証(`env` は剥がされずインスペクトされ ask になるのを確認済みで
  ランナーの代替にならない)。語境界(`Bash(ls *)` vs `lsof`)は `lsof` が read-only 分類で自動承認
  されるため ask 差で示せず、本グループでは扱わない(いずれも一次 docs 記載事項)。
- **documented-only(対話フロー・未実測)**: 対話で Bash の複合コマンドを承認する際、規則の保存は
  **サブコマンドごとに最大 5 規則**(公式 permissions doc / spec-inventory §2)。headless/SDK では
  観測できず、対話観測とセットの残バックログ。

## 要点

- **文字列ベースの deny は「うっかり防止」であって「悪意の境界」ではない**(`sh -c` / 変数展開 /
  `$(...)` で崩れる)。本当にネットワークを止めるなら sandbox の network 制御(→ S6, F2)。
- **ただし「ラッパー＝すり抜け」は誤り**。`nice`/`timeout`/`nohup`/`stdbuf`/フラグ無し `xargs` は
  照合前に剥がされ中身が照合されるので deny に当たる(e)。すり抜けるのは中身が文字列として不可視な
  `sh -c`/`bash -c`/`$(...)` 等の**剥がされない**ラッパー/サブシェルだけ(c)。
- **例外を彫れるのは deny 側だけ**。広い allow + 狭い deny なら curl だけ塞げる(a)が、逆(広い deny +
  狭い allow)では穴を開け直せない(→ P2-e)。allow の prefix もチェーン先には波及しない(d)。
- deny のハード拒否(a1/b/g/e)と ask(d/i2)は「どちらも複合が通らない」ように見えても機構が別。
  d は deny 規則が無いだけで、承認さえあれば通る(SDK の canUseTool 発火で切り分け済み)。
- **規則ゼロ ≠ 全部 ask**。read-only 集合(cat/ls/echo…)は設定に依らず無条件承認される(i)。
  機微な読取を止めるには ask/deny 規則で明示的に上書きが要る。

## 対応する知識

- docs/FINDINGS.md: Q3「deny/allow をコマンドチェーンですり抜けられる」
- 関連: P2-e(広い deny + 狭い allow は穴を開けられない=a の逆方向)/ P3-d(Write ではパス限定が
  表現できず包含構成を作れない)/ S6・F2(sandbox のネットワーク制御=本当の境界)
