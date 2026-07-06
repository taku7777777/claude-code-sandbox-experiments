# P5-i: `.claude/worktrees` は保護の明示例外 — 保護ディレクトリ内で唯一 acceptEdits が自動承認する場所

## 目的

- 保護ディレクトリ `.claude` の**公式例外 `.claude/worktrees`** を実測で確定する
- c(`.claude/PROBE.txt` = ask)との 1 変数対照(サブパスを worktrees/ 配下に変えるだけで
  ask → allow に反転)— 保護が単純な前方一致ではなく明示の例外を持つことの実証

## 前提(設定)

```json
{}
```

- settings.json は空。`--permission-mode acceptEdits`
- c との差分は書込先のサブパスのみ(`.claude/PROBE.txt` → `.claude/worktrees/wt/OK.txt`)

## 実行内容

1. Write で `.claude/worktrees/wt/OK.txt` を作成(acceptEdits)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `.claude/worktrees/wt/OK.txt`(acceptEdits) | allow | ✅ | 保護ディレクトリ内だが公式例外。自動承認 |

## なぜそうなるか

- **公式リストの `.claude` には例外が明記されている**: ".claude, **except for `.claude/worktrees`**
  where Claude stores its own git worktrees"。Claude 自身が worktree(→ S8-c)を作る場所なので、
  ここを保護すると自分の機能が自分の防護に引っかかる — そのための carve-out。
- c(同モード・同 `.claude` 配下)が ask になるのと 1 変数差なので、この allow は
  「保護マッチャが worktrees/ を明示的に除外している」ことの直接の実証になる。

## 運用時の留意事項

- 「保護ディレクトリ配下なら書けないはず」は `.claude/worktrees` には**成立しない**。
  `.claude` 配下を丸ごと防護されている前提の運用(監査・レビュー省略など)はこの例外を見落とす。
- モードによらず `.claude/worktrees` も止めたいなら明示 `deny` 規則を置く(deny は保護パス機構とは
  別系統で、例外の穴も塞げる)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude --permission-mode acceptEdits` を起動し、
[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。c では ask になる `.claude` 配下への書込が、
worktrees/ 配下ではプロンプトなしで通ることが確認できる。

```bash
cd cases/P5-protected-paths/i-worktrees-exception && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

allow 系(非 ask)なので結論は全形態で同じ(headless の1回で代表値)。

```bash
python3 harness/run.py P5-protected-paths/i-worktrees-exception
# SDK でも同結論(canUseTool 非発火のまま副作用が出る = ALLOWED)
python3 harness/run.py -m sdk P5-protected-paths/i-worktrees-exception
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(ALLOWED・副作用あり)/ sdk(ALLOWED・canUseTool 非発火。1プローブ一致) |

## 対応する知識

- グループ [P5 README](../README.md) / 公式 permission-modes「Protected paths」(.claude の except 注記)
- 関連: P5-c(`.claude` 直下は ask=対照)/ S8-c(sandbox 下の worktree add=この場所の用途)
