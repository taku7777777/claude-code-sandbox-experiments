# P9-a: hook の allow は deny 規則を緩められない — **deny マッチ時は hook が発火すらしない**

## 目的

- **PreToolUse hook の allow は deny 規則を bypass できない**(permissions docs: "Hook decisions don't
  bypass permission rules. Deny and ask rules are evaluated regardless of what a PreToolUse hook returns")
  ことを、`deny Edit(PROOF.txt)` × 「無条件で allow を返す hook」の組で実測する。
- 対照プローブで **hook の allow 自体は生きている**(規則が無ければ既定の ask を上書きして通す)ことも
  同時に示し、「hook は機能しているが deny だけは緩められない」を1ケース内で閉じる。

## 前提(設定)

```json
{
  "permissions": { "deny": ["Edit(PROOF.txt)"] },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write",
        "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-allow.sh" } ] }
    ]
  }
}
```

- `hook-allow.sh` は何が来ても `{"hookSpecificOutput": {"permissionDecision": "allow", ...}}` を返し、
  **発火の証跡として `hook-ran.marker` を残す**(ハーネスは `observe.evidenceFile` で存在を記録)。
- deny は **scoped 形**(`Edit(PROOF.txt)`。Edit 規則は Write ツールにも適用 = P3-e で実測済み)。
  bare 形 `deny Write(*)` にしないのは、bare 形が**ツール除去型**(P2-c/d)で Write の呼び出し自体が
  起きず、hook との優先関係を測る土俵に乗らないため(初版設計の是正。→ P9 GAPS G1)。

## 実行内容(Write ツールのみ・フォールバック禁止)

1. Write で deny 対象名 `PROOF.txt` を作成 → 止まるはず
2. Write で対象外 `OTHER.txt` を作成 → 規則なしだが hook の allow で通るはず(対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(hook は allow を返す) | deny | - | **hook 不発火**(marker なし)= deny は hook より前段で評価 |
| 2 | Write `./OTHER.txt`(規則マッチなし) | allow | ✅ | **hook の allow が既定の ask を上書き**して自動承認(marker あり) |

- プローブ 1 の headless は P3-e と同型で denials 非記録 → `byModality` で INCONCLUSIVE を明示
  (機構の確定は SDK: toolUses に Write が載り副作用なし = DENIED_HARD)。

## なぜそうなるか

- **評価の層構造(実測)**: `deny 規則 → PreToolUse hook → ask/allow 規則`。deny 規則にマッチした
  呼び出しは **hook の実行前に**拒否されるため、hook がどう答えるか以前に「答える機会」が無い
  (プローブ 1 で marker が出ないのが直接証拠)。
- docs の "Deny and ask rules are evaluated regardless of what a PreToolUse hook returns" は
  この実装(deny が hook に先行)によって満たされている。
- 規則が何もマッチしない場合(プローブ 2)は hook が発火し、`permissionDecision: "allow"` が
  **既定の ask を上書き**する — これが「hook で permission を拡張する」の正の方向。
  ただし**明示の ask 規則は上書きできない**(→ P9-d)。

## 運用時の留意事項

- **deny 規則は hook で緩められない最終防壁**。逆に言うと、PreToolUse hook で「特定条件だけ許可」を
  実装しても、deny 規則と競合する範囲では hook 側が一切呼ばれない(ログ取り hook も deny 拒否分は
  観測できない)ことに注意。
- hook の allow は「規則が沈黙している領域の既定 ask」を自動承認へ変える強い力を持つ。
  allow を返す hook のバグ(条件判定ミス)は事実上の全面 allow になりうるので、締める用途(deny/ask)
  より慎重に扱う。

## 試し方(本リポジトリでの実測)

- **お手軽に試す(対話)**: このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける
  (hook のコマンドパスは `$CLAUDE_PROJECT_DIR` 起点なのでそのまま動く)。
- ハーネス実測:

```bash
python3 harness/run.py P9-hooks-vs-permission/a-hook-allow-cannot-override-deny
python3 harness/run.py -m sdk P9-hooks-vs-permission/a-hook-allow-cannot-override-deny
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(P1: INCONCLUSIVE=byModality 明示・marker なし / P2: ALLOWED・marker あり)/ sdk(P1: DENIED_HARD / P2: ALLOWED。evidenceFileFound も同値) |

- 実測メモ: `$CLAUDE_PROJECT_DIR` は**セッション cwd(=このケース dir)**に解決される(git repo root ではない)。

## 対応する知識

- グループ [P9 README](../README.md)
- 関連: P9-d(明示の ask 規則も hook allow で緩められない)/ P3-e(scoped `Edit(path)` deny の実測)/ P2-c,d(bare deny のツール除去型)
