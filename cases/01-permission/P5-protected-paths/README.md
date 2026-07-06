# P5. protected-paths — 保護パスは acceptEdits/allow の上流で ask、bypass だけがそれも省略する

## このグループで学ぶこと

- `.git` `.claude` `.vscode` 等の**保護パス**は、`acceptEdits` や `allow` 規則による事前承認の**対象外**で、
  常に承認プロンプト(**ask**)になる。拒否の原因は「ネストの深さ」ではなく「保護パス」。
- その ask は **hard deny ではない**(承認すれば書ける・SDK で canUseTool が発火)。headless の ❌ は auto-deny。
- **allow は保護パスを事前承認できない**(実測: f)。安全チェックは settings の allow 評価より**前**に走る —
  実効が実証済みの `Write(*)` を置いてもなお ask のまま。
- **モード境界**: default/acceptEdits/plan = ask(Prompted)/ **dontAsk = 即 deny**(ask を経ない。g)/
  **bypassPermissions = allow**(プロンプト機構ごと省略。e)。同じ `.git` 書込がモードだけで 3 区分に割れる。
- 保護対象は**ディレクトリ + ファイル**の2カテゴリ(`.mcp.json` 等のファイルも ask。h)。
  例外は `.claude/worktrees` だけ(保護ディレクトリ内で唯一自動承認。i)。
- 保護パスは **Bash 面でも効く**: acceptEdits の FS コマンド自動承認(`touch` 等)からも除外(j)。

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | acceptEdits / 書込先 `.git/hooks/` | 保護パス → ask(自動承認されない) | [a-git-deny](./a-git-deny/README.md) |
| b | + 書込先を通常ネスト `sub/deep/` に | 保護パスでなければ allow(a の対照) | [b-nested-ok](./b-nested-ok/README.md) |
| c | + 書込先を `.claude/` に | 別の保護ディレクトリでも ask | [c-claude-protected](./c-claude-protected/README.md) |
| d | + 書込先を `.vscode/` に | 保護は広い一群(ディレクトリ+ファイル) | [d-vscode-protected](./d-vscode-protected/README.md) |
| e | + モードを **bypassPermissions** に(書込先は a と同じ) | bypass は保護パスも skip → allow(アンチパターン) | [e-bypass-git](./e-bypass-git/README.md) |
| f | c + **allow 規則**(`Write(*)` 含む) | allow でも保護パスは事前承認できない → ask のまま | [f-allow-no-preapprove](./f-allow-no-preapprove/README.md) |
| g | f 相当 + モードを **dontAsk** に | 保護パスは ask を経ず**即 deny**(通常パスは allow が効く) | [g-dontask-protected](./g-dontask-protected/README.md) |
| h | a + 書込先を保護**ファイル** `.mcp.json` に | ファイルも保護対象(第2カテゴリ) | [h-protected-file](./h-protected-file/README.md) |
| i | c + サブパスを `.claude/worktrees/` に | 保護ディレクトリ内の唯一の**例外** → allow | [i-worktrees-exception](./i-worktrees-exception/README.md) |
| j | a + ツールを **Bash**(`touch`)に | FS Bash 自動承認からも保護パスは除外 → ask | [j-bash-touch-git](./j-bash-touch-git/README.md) |
| k | a + `additionalDirectories:["~/lab-f4-p5"]`(cwd 外の追加ルート) | 追加ルート内の保護パスも ask（保護は additionalDir にも及ぶ）。対照: 追加ルート内の通常パスは allow | [k-additionaldir-protected](./k-additionaldir-protected/README.md) |

## 対比

同一プローブを書込先 × モード/設定で走らせた結果マトリクス(セル = `許諾 結果`、結果は approve 前提):

| No | 書込先(ツール) | acceptEdits | acceptEdits + allow `Write(*)` | dontAsk + allow `Write(*)` | bypassPermissions |
|---|---|:---:|:---:|:---:|:---:|
| 1 | `.git/hooks/`(Write・保護) | ask ✅ <br>(a) | - | - | allow ✅ <br>(e) |
| 2 | `.claude/`(Write・保護) | ask ✅ <br>(c) | ask ✅ <br>(f) | **deny -** <br>(g) | (対象外) |
| 3 | `.vscode/`(Write・保護) | ask ✅ <br>(d) | - | - | (対象外) |
| 4 | `.mcp.json`(Write・保護**ファイル**) | ask ✅ <br>(h) | - | - | (対象外) |
| 5 | `.claude/worktrees/`(Write・**例外**) | allow ✅ <br>(i) | - | - | - |
| 6 | 通常ネスト `sub/deep/`(Write・非保護) | allow ✅ <br>(b) | - | allow ✅ <br>(g 対照) | - |
| 7 | `.git/hooks/`(**Bash** `touch`・保護) | ask ✅ <br>(j) | - | - | - |
| 8 | 通常 cwd 直下(**Bash** `touch`・非保護) | allow ✅ <br>(j 対照) | - | - | - |

- **2 行目が本グループの核心**: 同じ `.claude` 書込が acceptEdits=ask / +allow でも ask(allow 無効)/
  dontAsk=**即 deny**(ask を経ない)。1 行目の bypass=allow と合わせ、公式のモード表
  (Prompted / Denied / Allowed)の 3 区分をすべて実測で埋めた。
- ask ✅ は「承認すれば書ける」= headless では承認者不在で auto-deny(❌ に見える)。
  g の deny は auto-deny ではなく**エンジンの即 deny**(SDK: canUseTool 非発火 = DENIED_HARD)。
- 全セル実測(a/c/d/f/h/j=SDK で canUseTool 発火=ASK、g 保護=非発火 DENIED_HARD、
  b/e/i/対照=ALLOWED)。

### 設定を1つずつ変えると挙動がどう動くか(a を基準に)

各行は基準ケースに1変数だけ足したもの。足した差分と、それで変化する許諾:

| 手順 | 変えた点 | 変化 | 起きること |
|---|---|---|---|
| a(基準) | acceptEdits / `.git/hooks/` | ask ✅ | 保護パスは acceptEdits でも承認要求(自動承認されない) |
| a → b | 書込先を通常ネストに | ask → **allow** | 保護パスでなければ自動承認(途中ディレクトリも作成) |
| a → c | 書込先を `.claude/` に | ask(不変) | 別の保護ディレクトリでも同じ機構 |
| a → d | 書込先を `.vscode/` に | ask(不変) | 保護は `.idea`/`.husky`/… にも及ぶ |
| a → h | 書込先を保護ファイル `.mcp.json` に | ask(不変) | **ファイル**も保護対象(第2カテゴリ) |
| a → j | ツールを Bash `touch` に | ask(不変) | 保護は Write ツール限定ではなく Bash 面でも効く |
| c → f | allow 規則(`Write(*)` 含む)を追加 | ask(不変) | **allow では保護パスを事前承認できない**(安全チェックが上流) |
| c → i | サブパスを `worktrees/` に | ask → **allow** | `.claude/worktrees` だけは公式の明示例外 |
| f → g | モードを dontAsk に | ask → **deny** | プロンプト行き=即 deny。allow は通常パスにしか効かない |
| a → e | モードを bypass に | ask → **allow** | bypass はプロンプト機構ごと省略 → 保護パスも通る |

- **allow に反転する経路は3つ**(b=書込先を非保護に / i=公式例外サブパス / e=モードを bypass に)、
  **deny に反転する経路は1つ**(g=dontAsk)。それ以外はどう設定を足しても ask のまま
  (保護パスの普遍性: ディレクトリ/ファイル、Write/Bash、allow の有無に依らない)。

## 要点

- a と b の唯一の差が「保護パスか否か」なので、a/c/d/h の ask は**ネスト深さではなく保護パス由来**と確定する。
- 保護パスの ask は **allow 規則や acceptEdits では事前承認できない**(公式 permission-modes: 保護パス write は
  安全チェックが allow 評価より前に走る。**実測 f**: 実効形 `Write(*)` を置いてもなお ask)。
  承認できるのは対話の承認プロンプトのみ(headless では auto-deny)。プロンプトには
  「このセッション中 .claude 編集を許可」の選択肢が出る。
- **モード別マトリクス(公式表と実測の対応)**: default/acceptEdits/plan = Prompted(実測 a/c/d/f/h/j)/
  dontAsk = **Denied**(実測 g: canUseTool 非発火の即 deny)/ bypassPermissions = **Allowed**(実測 e)/
  auto = 分類器行き(eligibility 制約により本環境では対象外・未実測)。
- 公式の保護対象(permission-modes, 2026-07-05):
  - **ディレクトリ**: `.git` `.config/git` `.vscode` `.idea` `.husky` `.cargo` `.devcontainer` `.yarn` `.mvn`
    `.claude`(**例外: `.claude/worktrees`** — 実測 i で allow を確認)
  - **ファイル**: `.gitconfig` `.gitmodules` / shell rc 系(`.bashrc` `.zshrc` 等)/ `.npmrc` `.yarnrc` /
    `.mcp.json` `.claude.json` / `.pre-commit-config.yaml` ほか(実測 h: `.mcp.json` = ask)
- 保護パスは Bash の FS コマンド(acceptEdits の自動承認対象)にも効く(実測 j)。ただし
  **リダイレクト(`echo x > .git/x`)等まで及ぶかは docs に明文がなく未検証**(P3-f の deny 抜けとは別機構)。
- ⚠️ **bypassPermissions はこれら保護パスへの write プロンプトも skip する**(= 通る)。
  bypass で残る境界は明示 `ask` 規則(→ P6-d)・`deny` 規則・`rm -rf /`/`~` circuit breaker・
  (v2.1.199+)MCP `requiresUserInteraction` のみ。**「保護パスがあるから bypass でも最悪は防げる」は誤り** —
  `.git/hooks` 書換 = 任意コード実行が成立し得る。bypass は隔離環境専用が唯一の安全側運用(→ e)。
  【裏取り: 公式 permission-modes doc「Protected paths」「Skip all checks」, https://code.claude.com/docs/en/permission-modes.md, 2026-07-05 取得。"As of v2.1.126 this includes writes to protected paths…" と明記】

## 対応する知識
- docs/FINDINGS.md: Q1 / 保護パスの注(保護パスは allow・acceptEdits の上流の別系統)
- 関連: P1-b(acceptEdits の基準挙動)/ P1-d・P1-g(dontAsk の基準挙動と allow 併用)/
  P1-e(bypass の基準挙動)/ P6-d(ask 規則は bypass でも残る)/ P3(パス限定 Write allow の glob 非対称)
