# P6. ask-rules — ask は allow に勝ち deny に負ける。プロンプトが残るのは bypass まで、dontAsk では deny に化ける

## このグループで学ぶこと

- permission 規則は allow / **ask** / deny の 3 値。P2 が allow/deny の優先を扱うのに対し、このグループは**真ん中の ask**を主役にする。
- **評価順 deny → ask → allow を 3 辺すべて実測で確定**: ask は allow に勝ち(b)、deny は ask に勝つ(f)。
- **モード別の ask 規則の解決**(全実測):
  - default(a)/ acceptEdits(c)/ **bypassPermissions**(d)→ **プロンプト**(承認すれば通る)
  - **dontAsk**(e)→ **即 deny**(プロンプト機会なし。「全モードでプロンプト」ではない)
  - auto → プロンプト強制(docs 明記。eligibility 制約により本環境では対象外・未実測)
- ask の specifier は**形で効き方が割れる**: Bash の prefix 形は効きチェーン越しにも働く(g)が、
  **パス限定 `Write(sub/**)` は無言で不一致**(h ⚠️ = P3 glob 地雷の ask 版)。
- ask は headless では承認者不在で auto-deny に化ける。**SDK の `canUseTool` 発火が ask/deny の計測器**
  ——このグループ自体が「headless では ask/deny を区別できない」ことの実例(→ [EXECUTION-MODALITIES.md](../../../docs/EXECUTION-MODALITIES.md))。

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | `ask=[Write(*)]` | ベースライン。ask 単独 → 承認要求(approve 側も実測) | [a-ask-alone](./a-ask-alone/README.md) |
| b | + `allow=[Write(*)]` | ask は allow に勝つ | [b-ask-beats-allow](./b-ask-beats-allow/README.md) |
| c | `ask` + `--permission-mode acceptEdits` | acceptEdits でも ask が残る | [c-ask-with-acceptEdits](./c-ask-with-acceptEdits/README.md) |
| d | `ask` + `--permission-mode bypassPermissions` | bypass でも ask が残る | [d-ask-with-bypass](./d-ask-with-bypass/README.md) |
| e | `ask` + `--permission-mode dontAsk` | dontAsk では ask は**即 deny** に化ける | [e-ask-with-dontask](./e-ask-with-dontask/README.md) |
| f | b の allow を `deny=[Write(*)]` に | deny は ask に勝つ(3値順序の上辺) | [f-deny-beats-ask](./f-deny-beats-ask/README.md) |
| g | `allow=[Bash(*)]` + `ask=[Bash(touch *)]` | 「広い allow + 狭い ask」の実型(Bash・チェーン込み) | [g-ask-bash-specifier](./g-ask-bash-specifier/README.md) |
| h | `allow=[Write(*)]` + `ask=[Write(sub/**)]` | ⚠️ パス限定 ask は無言で不一致 → 素通り | [h-ask-path-scope](./h-ask-path-scope/README.md) |

## 対比 — 設定 × 操作(全セル実測)

同一プローブ(Write で `PROOF.txt` 作成)を規則・モードだけ変えて実測(セル = `許諾 結果`、結果は approve 前提):

| No | 操作 | a(ask 単独) | b(+allow) | c(+acceptEdits) | d(+bypass) | e(+dontAsk) | f(deny+ask) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Write `./PROOF.txt` | ask ✅ | ask ✅ | ask ✅ | ask ✅ | **deny -** | **deny -** |

- a〜d は `ask ✅`(SDK: 全て askFired=['Write'])。**e/f だけ deny**(SDK: canUseTool 非発火)——
  ただし機構が違う: e は**モードが ask を deny に解決**(呼び出し時 deny・denials 記録)、
  f は**規則の deny が先勝ち**(ツール除去型・init tools 欠落で構造検出)。
- specifier の面(同一設定内の対照): g は `touch`(ask)/`mkdir`(allow)/`echo && touch`(ask)が
  規則どおりに分岐。h は sub/ 内外どちらも allow ✅ = **ask 規則が不一致で存在していない**。

### 設定を1つずつ変えると(a を基準に)

| 手順 | 足した/変えた設定 | プローブの結果 | 起きること |
|---|---|---|---|
| a(基準) | `ask=[Write(*)]` | ask ✅ | ask 規則単独で承認要求(approve すれば通る=実測) |
| a → b | + `allow=[Write(*)]` | ask ✅(変化なし) | allow が同居しても評価順で ask が先に当たり勝つ |
| a → c | + acceptEdits モード | ask ✅(変化なし) | acceptEdits の自動承認を明示 ask 規則が上書き |
| a → d | + bypassPermissions モード | ask ✅(変化なし) | bypass のプロンプト省略を明示 ask 規則が上書き |
| a → e | + dontAsk モード | ask → **deny** | プロンプト行き = 即 deny。ask が「プロンプト」として残るのは bypass まで |
| b → f | allow を deny に | ask → **deny** | deny → ask → allow の先頭が当たり ask は評価されない |
| a → h | ask をパス限定 `Write(sub/**)` に(+広 allow) | ask → **allow** ⚠️ | 規則が無言で不一致 = 確認ゲート不成立(P3 系地雷) |

- b/c/d は「ask を消しにかかる圧力が**効かない**」ことを見る対照(変化なし)。
  e/f/h は「ask が**消える**3経路」——モード(e)・上位規則(f)・specifier 不一致(h)。

## 要点(実測で確定)

- **評価順 deny → ask → allow の 3 辺を実測で完結**: deny>allow(P2-b)/ ask>allow(b)/
  **deny>ask(f)**。ask にマッチした時点で allow は見られず、deny にマッチした時点で ask も見られない。
- **明示 ask 規則がプロンプトとして残るのは default/acceptEdits/plan/bypass まで**(a/c/d)。
  **dontAsk では deny に解決される**(e。公式 permission-modes: "explicit ask rules are denied rather
  than prompting")。auto ではプロンプト強制(docs 明記・対象外)。
  「素通りしない」という意味では全モードで効くが、「承認機会がある」わけではない。
- **d は P5-e と対で読む**: bypassPermissions は保護パス write すら skip する(P5-e=✅)が、
  **明示 ask 規則だけは skip されず残る**(d)。「bypass で残るのは明示 ask 規則と `rm -rf`
  circuit breaker だけ」を ask 側から実証。
- **specifier の効き方は形で割れる**(g/h): Bash prefix 形(`Bash(touch *)`)は効き、チェーン
  (`echo hi && touch ...`)の部分コマンド照合でも働く。**パス限定 `Write(sub/**)` は無言で不一致**
  (h ⚠️)——「ask を書いた ≠ 確認される」。P3(deny/allow の glob 地雷)と同根で、ask も撃って確かめる。
- **approve 側も実測済み**(a: SDK onAsk=allow で ASK 発火+書込完遂)。`ask ✅` の ✅ は仮定ではない。
- **headless 単独では ask と deny を区別できない**(a〜f は headless で全て DENIED)。
  engine=ask の確定には SDK(`canUseTool` 発火)が要る——本グループがその実例。
- 対象外(未実測・fixture/eligibility 制約): **auto モード**(ask はプロンプト強制 = docs 明記)/
  **MCP `requiresUserInteraction`**(v2.1.199+: bypass で prompt 残存・dontAsk で deny)/
  **sandbox との交差**——bare `Bash` ask 規則は sandbox の auto-allow に**置換されて発火しない**
  (content-scoped は残る。公式 permissions 明記)。sandbox 例外は S4 側の追加ケース候補(→ GAPS G3)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 結果 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(a〜d) | 全て DENIED(ask→auto-deny) |
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | sdk(a〜d) | 全て ASK(`askFired=['Write']`)= engine=ask 確定 |
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless+sdk(e〜h 追加、a は onAsk=allow で再測) | 全プローブ期待一致。e/f=deny(SDK 非発火)/ g=ask/allow/ask / h=**ask 不一致で allow**(⚠️)/ a=ASK+書込完遂 |

## 対応する知識

- docs/FINDINGS.md: ask 規則の 3 値中間項 / glob 地雷の章(h の ask 側追記)
- 関連: P1(モード単独の挙動)/ P2(deny→ask→allow の両端)/ P5-e・P5-g(bypass / dontAsk の保護パス側)/
  P4(Bash 照合機構 = g の土台)/ P3(Write specifier の glob 非対称 = h の同根)/
  [EXECUTION-MODALITIES.md](../../../docs/EXECUTION-MODALITIES.md)(ask の形態依存)
