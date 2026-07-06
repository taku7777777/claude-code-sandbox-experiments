# P9. hooks-vs-permission — hook は「締める」方向にだけ信頼できる(規則との優先は「厳しい方が勝つ」)

> **状態: 実測済み(headless + SDK, 2026-07-05)**。hook(PreToolUse)次元を埋めるグループ。
> 各ケースの hook スクリプトは fixture としてケース dir に同梱(`hook-*.sh`。発火すると `hook-ran.marker` を残し、
> ハーネスが `observe.evidenceFile` で記録する)。ハーネス拡張は evidenceFile 観測のみで、hooks の配置機能は不要だった
> (hooks は cwd の `.claude/settings.json` から読まれ、コマンドパスは `$CLAUDE_PROJECT_DIR` 起点で書ける)。

## このグループで学ぶこと

- hook は「permission を拡張する公式手段」。その **permission 規則との優先関係**を全交差で実測した。
- 結論は一貫して「**厳しい方が勝つ**」:
  1. **緩める方向は規則を越えられない** — hook の allow は deny 規則(a)にも明示の ask 規則(d)にも負ける。
     上書きできるのは「規則が沈黙している領域の既定 ask」だけ(a の対照プローブ)
  2. **締める方向は allow 規則を越えられる** — exit 2 の blocking hook(b)も JSON deny(c)も
     allow 規則に勝つ。JSON ask は allow 済みの操作を確認制に格上げできる(e)
  3. **沈黙は承認ではない** — exit 0 で JSON を返さない hook は permission に影響しない(f)
- **機構の層構造(実測)**: `deny 規則 → PreToolUse hook → ask/allow 規則` の順で評価される。
  - deny 規則にマッチすると **hook は発火すらしない**(a: marker なし。ログ取り hook も deny 拒否分は見えない)
  - ask 規則では hook は**発火する**が、hook の allow は prompt を消せない(d: marker あり)
  - hook の deny/ask は、後段の allow 規則より優先される(b/c/e)

## サブケース一覧

| サブ | 設定の差分(1変数ずつ) | 論点 | 詳細 |
|---|---|---|---|
| a | `deny=[Edit(PROOF.txt)]` + 無条件 allow hook | hook allow は deny に負ける(**発火すらしない**)。対照: 規則なしなら既定 ask を上書き | [a-hook-allow-cannot-override-deny](./a-hook-allow-cannot-override-deny/README.md) |
| b | `allow=[Write(*)]` + **exit 2** hook | blocking hook(exit-code 経路)は allow に勝つ。stderr がモデルに返る | [b-blocking-hook-beats-allow](./b-blocking-hook-beats-allow/README.md) |
| c | `allow=[Write(*)]` + **JSON deny** hook | JSON 経路(exit 0 + permissionDecision=deny)も allow に勝つ | [c-json-deny-beats-allow](./c-json-deny-beats-allow/README.md) |
| d | `ask=[Write(*)]` + 無条件 allow hook | hook allow は明示の ask 規則も緩められない(発火はする) | [d-hook-allow-vs-ask-rule](./d-hook-allow-vs-ask-rule/README.md) |
| e | `allow=[Write(*)]` + **JSON ask** hook | hook ask は allow 済みを確認制に格上げできる | [e-hook-ask-over-allow](./e-hook-ask-over-allow/README.md) |
| f | 規則なし + **沈黙** hook(exit 0・JSON なし) | 沈黙は承認ではない(c〜e の対照) | [f-silent-hook-not-approve](./f-silent-hook-not-approve/README.md) |

## hook の応答 × 規則のマトリクス(実測)

同一プローブ(Write で `PROOF.txt` 作成)。セルは最終判定(hook 発火の有無):

| hook の応答 \ 規則 | deny 規則 | ask 規則 | allow 規則 | 規則なし(既定 ask) |
|---|:---:|:---:|:---:|:---:|
| JSON `allow` | **deny**・不発火(a) | **ask**・発火(d) | (自明: allow) | **allow**・発火(a 対照) |
| JSON `deny`(exit 0) | (自明: deny) | - | **deny**・発火(c) | - |
| JSON `ask` | - | - | **ask**・発火(e) | - |
| exit 2 block | (自明: deny) | - | **deny**・発火(b) | - |
| 沈黙(exit 0・JSON なし) | - | - | - | **ask**・発火(f) |

> どの行・列を見ても**厳しい側の判断が最終結果**になっている。`-` は自明または優先関係の判別に寄与しないため箱なし。

## 要点

- **防御設計への含意**: 「広い allow + hook で締める」(b/c/e)は機構として成立する。逆に
  「deny/ask 規則を hook で緩める」(a/d)は不可能 — deny・ask 規則はユーザ/管理者の意思として hook より強い。
- **hook の allow は「既定 ask の自動承認」にだけ効く**強い力(a 対照)。allow を返す hook の条件バグは
  事実上の全面 allow になるので、締める用途より慎重に。
- **deny 規則下では hook が呼ばれない**(a)。PreToolUse hook を監査ログに使う場合、deny で拒否された
  試行はログに残らないことに注意。
- hook の出力契約(hooks docs で裏取り・実測一致): exit 0 + stdout JSON
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"|"deny"|"ask"|"defer", "permissionDecisionReason": "..."}}` /
  **exit 2 = blocking error**(stdout 無視・stderr がモデルへ)/ exit 0 + JSON なし = 判断なし。
  deny/ask/block の拒否はいずれも `permission_denials[]` に記録され、reason / stderr 文言はモデルに返る。
- スコープ注記: 本グループが扱うのは **PreToolUse hook × permission 規則**のみ。`PermissionRequest` hook や
  他イベント(PostToolUse 等)、`hooks[].if`(規則構文での絞り込み)は T6 の射程外(将来ケースの種)。

## 対応する知識

- 関連: P2(規則同士の allow/deny 優先)/ P6(ask 規則。「規則同士」の優先はそちら、本グループは「hook × 規則」)/
  P1-a(既定 ask のベースライン)
- 一次資料: 公式 docs `permissions`(Extend permissions with hooks)/ `hooks`(設定スキーマ・出力契約)
