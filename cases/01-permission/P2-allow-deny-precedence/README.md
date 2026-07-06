# P2. allow-deny-precedence — deny は allow にもモードにも勝つ(マッチした範囲で)

## このグループで学ぶこと

- 評価順は **deny → ask → allow で最初のマッチが勝つ**。同一対象なら deny が allow に勝ち、
  さらに **acceptEdits / bypassPermissions といったモードにも勝つ**(deny 規則は全モードで適用)。
- ただし規則は**ツール単位**。deny `Write(*)` は Edit に効かず、deny 対象外のツールはモードの
  挙動(ask / 自動承認 / 素通し)がそのまま出る。

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | allow=`[Write(*)]` | ベースライン。Write は全パスで事前承認 | [a-allow](./a-allow/README.md) |
| b | + deny=`[Write(*)]` | deny > allow | [b-deny-beats-allow](./b-deny-beats-allow/README.md) |
| c | deny のみ + acceptEdits モード | deny > モード(自動承認) | [c-deny-vs-acceptEdits](./c-deny-vs-acceptEdits/README.md) |
| d | deny のみ + bypassPermissions モード | deny > bypass | [d-deny-vs-bypass](./d-deny-vs-bypass/README.md) |
| e | deny `Bash(*)` + allow `Bash(echo:*)` | ネスト allow で deny に穴は開けられない | [e-nested-allow-cannot-reopen-deny](./e-nested-allow-cannot-reopen-deny/README.md) |
| f | deny `Bash(run_in_background:true)` | **パラメータマッチ deny**。引数付き呼び出しだけ block、省略時は不マッチ | [f-param-match-deny](./f-param-match-deny/README.md) |
| g | deny `Bash(command:touch *)` | **対象外パラメータの deny は無言で無効**(起動時警告のみ) | [g-param-unsupported-ignored](./g-param-unsupported-ignored/README.md) |
| h | deny `["*"]` | ツール名ワイルドカード。**全ツールがコンテキストから除去** | [h-wildcard-deny-all](./h-wildcard-deny-all/README.md) |

## 対比 — 規則/モード × 操作(全セル実測)

全ケース同一の4プローブを各設定で実測した。セル = `許諾 結果`(結果は approve 前提):

| No | 操作 | a allow | b allow+deny | c deny+acceptEdits | d deny+bypass |
|---|---|:---:|:---:|:---:|:---:|
| 1 | Write `./PROOF.txt`(cwd 内) | allow ✅ | deny - | deny - | deny - |
| 2 | Write `~/…`(cwd 外) | allow ✅ | deny - | deny - | deny - |
| 3 | Write `./sub/…`(サブdir) | allow ✅ | deny - | deny - | deny - |
| 4 | Edit `./note.txt`(既存) | **ask ✅** | **ask ✅** | **allow ✅** | **allow ✅** |

- **1〜3 行(Write)**: `Write(*)` はパスを問わずマッチし、deny があれば allow にもモードにも勝つ。
- **4 行(Edit)**: どの設定でも deny/allow は `Write(*)` 限定なので Edit には効かず、
  残ったモードの挙動が出る(default=ask / acceptEdits=自動承認 / bypass=素通し)。
  **列で読むと「deny の優先」、行で読むと「規則のツール境界」が1表で見える。**
- 16セルすべて実測(推定なし)。SDK で 1〜3 は canUseTool 発火なしの DENIED_HARD、
  4(a/b)は発火して ASK = 同じ「書けない」でも機構が違うことを構造的に確認済み。

### 設定を1つずつ変えると(a を基準に)

| 手順 | 変えた点 | 変化するプローブ | 起きること |
|---|---|---|---|
| a(基準) | allow `Write(*)` | 1〜3=allow / 4=ask | Write だけ事前承認 |
| a → b | + deny `Write(*)` | 1〜3: allow → deny | deny が allow より先に評価され勝つ |
| b → c | allow を外し acceptEdits に | 4: ask → allow | deny は維持されたまま、Edit だけモードが自動承認 |
| c → d | モードを bypass に | 変化なし(1〜3=deny / 4=allow) | bypass でも deny は生き残る |

### スコープの包含関係3パターン(e で完成)

deny と allow のスコープが重なるとき、どちらが勝つかは**包含の向きによらず deny**:

| 包含関係 | 設定例 | 結果 | ケース |
|---|---|---|---|
| 同一スコープ | allow `Write(*)` + deny `Write(*)` | deny(全部 ❌) | P2-b |
| 広 allow + **狭 deny** | allow `Bash(*)` + deny `Bash(curl:*)` | **狭い deny の分だけ ❌**(例外を作れる) | P4-a |
| 広 deny + **狭 allow** | deny `Bash(*)` + allow `Bash(echo:*)` | **deny(echo も ❌。穴は開かない)** | P2-e |

- 例外を彫れるのは deny 側だけ。「基本 deny + 例外 allow」は書けない(→ e)。
- ※ Write 規則ではパス限定が表現できないため、スコープ差の検証は Bash 規則で行う(→ P3-d)。
  sandbox 層にも同型がある(S2-g: nested denyWrite wins)。

## 要点

- **deny > ask > allow、かつ deny > モード**。危険操作の禁止は deny 規則で書けばモード運用と独立に効く。
  3 値の中間項 **ask の実測は P6 グループ**(ask は allow に勝ち、acceptEdits/bypass でも残る)。
  canUseTool の発火パターンで 3 値は構造的に区別できる: allow=非発火+副作用 / deny=非発火+block / ask=発火。
- **規則の具体性(狭さ)は評価順を変えない**。広い deny の内側に狭い allow を書いても穴は開かない(e)。
  例外を作るなら「広い allow + 狭い deny」の向きで書く(P4-a)。
- **deny の優先は「その形が実際にマッチする」ことが前提**。ツールが違えば素通り(4行目)、
  表記が違えば無言で不一致(`Write(**)` → P3)、ラッパーですり抜け(→ P4-c)。
- **deny には 2 つの現れ方がある**(いずれも実測済み):
  - **除去型**: bare / `Tool(*)` / ツール名 glob の deny は、対象ツールを**ツールセットから除去**する
    (b の `Write(*)`、h の `"*"`)。呼び出し自体が起きず denials も出ないため、ハーネスは
    init tools の欠落で検出する。モデルは代替ツールへフォールバックを試みる点にも注意。
  - **呼び出し時 block 型**: スコープ付き deny(P4-a の `Bash(curl:*)`)やパラメータマッチ deny
    (f の `Bash(run_in_background:true)`)はツールが見えたまま、マッチした呼び出しだけが
    `denials` に記録されて止まる。
- **deny の構文には効かない形がある**: `Bash(command:...)` のような対象外パラメータ指定は
  **無言で無効**(g。stderr に起動時警告は出る)。`Write(**)` 等の glob 落とし穴(P3)と並ぶ地雷。

## 対応する知識

- docs/FINDINGS.md: Q3(deny のすり抜け)/ ボーナス発見「glob 構文が直感と違う」
- 関連: P3(マッチしない deny は素通り)/ P4(Bash コマンドのマッチング)/ P6(ask 規則の 3 値)
