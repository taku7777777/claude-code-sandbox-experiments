# P9-b: blocking hook(exit 2)は `allow Write(*)` に勝つ — 拒否は denials に記録され stderr がモデルに返る

## 目的

- **exit code 2 の blocking hook は allow 規則にも勝つ**(permissions docs: "A blocking hook also takes
  precedence over allow rules. A hook that exits with code 2 stops the tool call before permission
  rules are evaluated")ことを、`allow Write(*)` × exit 2 hook の組で実測する。
- 『hook で締める』防御設計(広く allow しつつ hook で個別に止める)の exit-code 経路が成立するかの確認。

## 前提(設定)

```json
{
  "permissions": { "allow": ["Write(*)"] },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write",
        "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-block.sh" } ] }
    ]
  }
}
```

- `hook-block.sh` は stderr に `P9_HOOK_BLOCKED: ...` を出して **exit 2**(hooks docs の blocking error 契約:
  stdout は無視・**stderr がモデルに返り**、ツール呼び出しはブロック)。発火証跡として `hook-ran.marker` を残す。

## 実行内容(Write ツールのみ・フォールバック禁止)

1. Write で `PROOF.txt` を作成 → allow 済みだが hook に止められるはず

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(allow 規則あり・hook が exit 2) | deny | - | **止める機構は規則 deny ではなく hook block**。拒否は `permission_denials[]` に記録され、stderr 文言がモデルに返る |

- 許諾列の `deny` は観測面(headless DENIED / SDK DENIED_HARD)。機構は hook block である点に注意
  (下記「なぜそうなるか」の 3 層を参照)。

## なぜそうなるか

- 「止める」機構は 3 層ある(→ グループ README の層構造):
  1. **規則 deny** — permission エンジンの判定(hook より前段。→ P9-a)
  2. **hook block(exit 2)** — 規則の allow 評価より前に呼び出しを止める(本ケース)
  3. **hook JSON deny** — hook の判断として deny を返す(→ P9-c)
- exit 2 は「blocking error」契約: stdout は無視され、**stderr の文言がそのままモデルへのエラーとして
  返る**(実測: result_text に `P9_HOOK_BLOCKED` が現れる = evidenceMarker で観測)。
- 実測では hook block の拒否も **`permission_denials[]` に記録される**(設計時は未知だった点。
  probe=permission の denials 判定がそのまま使えた)。

## 運用時の留意事項

- **『hook で締める』は allow 規則に対して成立する**。広い allow を配りつつ、危険条件だけ hook で
  止める設計は機構として有効。
- stderr がそのままモデルに返るので、**ブロック理由をモデルに伝えたい文言を stderr に書く**
  (「なぜ止めたか」「代わりに何をすべきか」を書けばモデルの次アクションを誘導できる)。
- exit 2 は「エラーとしてブロック」。ユーザに判断を委ねたい(確認プロンプトに落としたい)場合は
  JSON `permissionDecision: "ask"` を使う(→ P9-e)。

## 試し方(本リポジトリでの実測)

- **お手軽に試す(対話)**: このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける。
- ハーネス実測(permission≠ask の類型B。headless/SDK 同結論を確認済み):

```bash
python3 harness/run.py P9-hooks-vs-permission/b-blocking-hook-beats-allow
python3 harness/run.py -m sdk P9-hooks-vs-permission/b-blocking-hook-beats-allow
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED・denials=[Write]・marker あり・stderr 文言をモデルが復唱)/ sdk(DENIED_HARD・canUseTool 非発火) |

## 対応する知識

- グループ [P9 README](../README.md)
- 関連: P9-c(JSON deny 経路=もう1つの「締める」形)/ P9-a(緩める方向は deny を越えられない)/ P2(規則同士の allow/deny 優先)
