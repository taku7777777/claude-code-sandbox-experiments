# P9-c: JSON deny hook(exit 0 + `permissionDecision: "deny"`)も `allow Write(*)` に勝つ

## 目的

- 『hook で締める』の**もう1つの経路**: exit 2(→ P9-b)ではなく、exit 0 で JSON
  `permissionDecision: "deny"` を返す形でも allow 規則に勝つことを実測する。
- hooks docs の実装例で一般的なのはこちらの形。b と対で「締める 2 経路はどちらも allow を越える」を埋める。

## 前提(設定)

```json
{
  "permissions": { "allow": ["Write(*)"] },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write",
        "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-deny-json.sh" } ] }
    ]
  }
}
```

- `hook-deny-json.sh` は exit 0 で
  `{"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "P9_HOOK_JSON_DENY"}}`
  を stdout に返す。発火証跡として `hook-ran.marker` を残す。
- b との差分は hook スクリプトの応答形だけ(1変数)。

## 実行内容(Write ツールのみ・フォールバック禁止)

1. Write で `PROOF.txt` を作成 → allow 済みだが hook の JSON deny に止められるはず

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(allow 規則あり・hook が JSON deny) | deny | - | 拒否は `permission_denials[]` に記録。**`permissionDecisionReason` がモデルに返る** |

## なぜそうなるか

- hook の JSON 出力契約(hooks docs): exit 0 + stdout の `hookSpecificOutput.permissionDecision` が
  `allow | deny | ask | defer` の判断として扱われる。**deny は規則の allow より優先**される
  (「厳しい方が勝つ」— グループ README の層構造)。
- exit 2(b)との違いは経路: exit 2 は「規則評価より前に止める blocking error」(stderr がモデルへ)、
  JSON deny は「hook の判断」として返り、**reason 文言がモデルへのエラーになる**
  (実測: result_text に `P9_HOOK_JSON_DENY` が現れる)。観測面はどちらも同じ deny。

## 運用時の留意事項

- 条件判定して deny を返す hook を書くなら **JSON 形が正攻法**(reason で理由を構造的に返せる。
  exit 2 + stderr は簡易形)。どちらでも allow 規則は越えられる。
- reason はモデルに返る文言なので、「なぜ止めたか / 代わりの手順」を書くとモデルの次アクションを誘導できる。

## 試し方(本リポジトリでの実測)

- **お手軽に試す(対話)**: このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける。
- ハーネス実測(permission≠ask の類型B。headless/SDK 同結論を確認済み):

```bash
python3 harness/run.py P9-hooks-vs-permission/c-json-deny-beats-allow
python3 harness/run.py -m sdk P9-hooks-vs-permission/c-json-deny-beats-allow
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED・denials=[Write]・marker あり・reason をモデルが復唱)/ sdk(DENIED_HARD・canUseTool 非発火) |

## 対応する知識

- グループ [P9 README](../README.md)
- 関連: P9-b(exit 2 経路)/ P9-e(同じ JSON 経路の ask 版)/ P9-f(JSON なし=判断なし、の対照)
