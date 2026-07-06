# P9-f: 沈黙する hook(exit 0・JSON なし)は承認ではない — 既定の ask が残る(c〜e の対照)

## 目的

- hooks docs の **"staying silent doesn't approve"**(exit 0 で JSON を返さない = 判断なし、
  通常の permission フローへ)を実測する。
- c〜e(明示の permissionDecision を返す hook)の**対照プローブ**: 挙動を変えるのは
  「hook が発火したこと」ではなく「hook が明示の判断を返したこと」だと確定させる。

## 前提(設定)

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write",
        "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-silent.sh" } ] }
    ]
  }
}
```

- permission 規則は**なし**(Write は既定の ask)。`hook-silent.sh` は `hook-ran.marker` を残して
  exit 0、stdout には何も出さない。

## 実行内容(Write ツールのみ)

1. Write で `PROOF.txt` を作成 → hook は発火するが、既定どおり承認プロンプトが出るはず

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(規則なし × 沈黙 hook) | ask | ✅ | **marker あり + 挙動は素の default(P1-a)と同一** = 沈黙は承認でない |

## なぜそうなるか

- exit 0 + JSON なしは「hook は正常終了したが判断を返さなかった」= permission フローは
  hook が無いのと同じに進む(既定の ask)。
- 対照の意味: P9-a プローブ 2 では**同じ状況(規則なし)で allow を返す hook が自動承認に変えた**。
  つまり ask → allow の変化は `permissionDecision: "allow"` という明示の判断があって初めて起きる。

## 運用時の留意事項

- 監査ログ取りなど「観測だけしたい」PreToolUse hook は、**何も出力せず exit 0 すれば permission に
  一切影響しない**ことが保証される(安心して仕込める)。
- 逆に「hook を書いたのに挙動が変わらない」ときは、JSON の形式ミス(`hookSpecificOutput` の欠落等)で
  沈黙扱いになっている可能性を疑う — 形式が正しくないと**エラーにならず単に無視される**。

## 試し方(本リポジトリでの実測)

- **お手軽に試す(対話)**: このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける。
- ハーネス実測(ask 系の類型A):

```bash
python3 harness/run.py P9-hooks-vs-permission/f-silent-hook-not-approve
python3 harness/run.py -m sdk P9-hooks-vs-permission/f-silent-hook-not-approve
python3 harness/run.py -m interactive --step prepare P9-hooks-vs-permission/f-silent-hook-not-approve
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED=ask の auto-deny・marker あり)/ sdk(**ASK=canUseTool 発火**・marker あり) |

## 対応する知識

- グループ [P9 README](../README.md)
- 関連: P1-a(素の default=同じ観測結果になる対照)/ P9-a プローブ 2(allow を返す hook は既定 ask を上書き)
