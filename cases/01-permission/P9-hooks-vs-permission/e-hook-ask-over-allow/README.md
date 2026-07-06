# P9-e: hook の ask は `allow Write(*)` を確認制に格上げできる — 「広く allow + 個別に確認」が成立

## 目的

- hook の `permissionDecision: "ask"` が **allow 規則で自動許諾のはずの操作をユーザ確認へ
  エスカレートできる**(hooks docs: ask = Escalate to user)ことを実測する。
- 運用価値の高い形 —「広い allow を配りつつ、危険な操作だけ確認を挟む」の実装可否を確定する。

## 前提(設定)

```json
{
  "permissions": { "allow": ["Write(*)"] },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write",
        "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-ask.sh" } ] }
    ]
  }
}
```

- `hook-ask.sh` は exit 0 で `permissionDecision: "ask"`(reason `P9_HOOK_ASK`)を返す。
  発火証跡として `hook-ran.marker` を残す。b/c との差分は hook の応答が deny → ask の1変数。

## 実行内容(Write ツールのみ)

1. Write で `PROOF.txt` を作成 → allow 済みだが確認プロンプトに格上げされるはず

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(allow 規則 × hook ask) | ask | ✅ | **allow 単独なら ALLOWED のはず**が ASK に格上げ。approve すれば完遂 |

## なぜそうなるか

- hook の ask は「ユーザへエスカレート」の判断。**allow 規則より厳しい判断なので勝つ**
  (「厳しい方が勝つ」— deny 系の b/c と同じ原理の ask 版)。
- 対照: allow 規則単独(P2-a)は ALLOWED、hook なしの既定は ask(P1-a)。本ケースで ASK が出るのは
  hook 由来であることが、この 2 つの既存実測と marker で確定する。

## 運用時の留意事項

- **「広く allow + 特定操作だけ hook で確認」は成立する**。deny で完全に塞ぐほどではないが
  無確認は嫌な操作(本番設定の書き換え、特定ディレクトリへの書込等)に適した形。
- hook 側で `tool_input` を見て条件分岐すれば「この引数のときだけ確認」も書ける(stdin に
  `tool_name` / `tool_input` / `permission_mode` の JSON が来る)。
- headless/CI ではこの ask は auto-deny になる = **hook ask はそのまま CI では「止める」に等しい**。

## 試し方(本リポジトリでの実測)

- **お手軽に試す(対話)**: このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける
  (allow 済みの Write に確認プロンプトが出る、が肉眼で見える)。
- ハーネス実測(ask 系の類型A。SDK の canUseTool 発火が決定的シグナル):

```bash
python3 harness/run.py P9-hooks-vs-permission/e-hook-ask-over-allow
python3 harness/run.py -m sdk P9-hooks-vs-permission/e-hook-ask-over-allow
python3 harness/run.py -m interactive --step prepare P9-hooks-vs-permission/e-hook-ask-over-allow
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED=ask の auto-deny・marker あり・reason をモデルが復唱)/ sdk(**ASK=canUseTool 発火**・marker あり) |
| 2026-07-06 | v2.1.201 | **対話(cmux 駆動)**: allow Write(*) 済みでも hook の JSON ask で `Do you want to create PROOF.txt?` の承認プロンプトが実出現(hook ask が allow を確認制に格上げ)→承認で書込完遂(ask ✅)。3 点セット完成 |

## 対応する知識

- グループ [P9 README](../README.md)
- 関連: P9-c(同じ JSON 経路の deny 版)/ P9-d(逆方向: ask 規則は hook allow で消えない)/ P2-a(allow 単独=ALLOWED の対照)
