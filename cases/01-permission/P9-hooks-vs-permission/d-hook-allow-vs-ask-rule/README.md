# P9-d: hook の allow は明示の ask 規則も緩められない — **hook は発火するが prompt は残る**

## 目的

- **明示の ask 規則は hook の allow でも消えない**(permissions docs: "a matching ask rule still
  prompts even when the hook returned 'allow' or 'ask'")ことを、`ask Write(*)` × allow hook の組で実測する。
- P9-a(deny 版)と対で「**緩める方向は deny も ask も越えられない**」を埋める。

## 前提(設定)

```json
{
  "permissions": { "ask": ["Write(*)"] },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write",
        "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-allow.sh" } ] }
    ]
  }
}
```

- `hook-allow.sh` は P9-a と同一(無条件 allow + `hook-ran.marker`)。差分は規則が deny → ask の1変数。

## 実行内容(Write ツールのみ)

1. Write で `PROOF.txt` を作成 → hook が allow を返しても承認プロンプトが出るはず

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(ask 規則 × hook allow) | ask | ✅ | **hook は発火する**(marker あり)が prompt は消えない。approve すれば完遂 |

## なぜそうなるか

- **deny 規則との機構差が本ケースの見どころ**: deny 規則は hook を発火させずに止める(P9-a)が、
  **ask 規則では hook は発火する**(marker が残る)。それでも hook の allow は ask 規則を上書きできず、
  最終判定は ask のまま — 「hook の判断と規則の判断は独立に評価され、厳しい方が勝つ」。
- hook の allow が上書きできるのは**規則が沈黙している領域の既定 ask だけ**(P9-a プローブ 2)。
  明示の ask 規則は「ユーザが確認したい」という意思表示なので hook より強い。

## 運用時の留意事項

- **ask 規則は hook で自動化できない**。「原則確認、特定条件だけ自動承認」を作りたい場合、
  ask 規則 + allow hook では実現できず、規則を書かず(既定 ask のまま)hook 側で条件付き allow を
  返す構成にする必要がある(その場合の力加減は P9-a の留意事項を参照)。
- headless/CI ではこの ask は auto-deny になる(全ケース共通の規約)。

## 試し方(本リポジトリでの実測)

- **お手軽に試す(対話)**: このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける
  (hook が allow を返しているのに承認プロンプトが出る、が肉眼で見える)。
- ハーネス実測(ask 系の類型A。SDK の canUseTool 発火が決定的シグナル):

```bash
python3 harness/run.py P9-hooks-vs-permission/d-hook-allow-vs-ask-rule
python3 harness/run.py -m sdk P9-hooks-vs-permission/d-hook-allow-vs-ask-rule
python3 harness/run.py -m interactive --step prepare P9-hooks-vs-permission/d-hook-allow-vs-ask-rule
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED=ask の auto-deny・marker あり)/ sdk(**ASK=canUseTool 発火**・marker あり) |

## 対応する知識

- グループ [P9 README](../README.md)
- 関連: P9-a(deny 版+「既定 ask は上書きできる」対照)/ P6(ask 規則同士の優先: deny>ask>allow)
