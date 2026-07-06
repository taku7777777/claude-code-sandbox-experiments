# S5-h: `excludedCommands` はあっても `Bash(*)` が無ければ、非 excluded の後段は permission で ask に落ちる → 自動では脱出しない

## 目的

- S5-b の脱出の**原因を分離する対照**。`excludedCommands:["echo *"]`（a/b と同じ）だが `allow` を `Bash(*)` から `Bash(echo *)` のみに絞ると、excluded を含む行でも**非 excluded の後段（`cat`）が自動承認されず ask に落ちる**ことを確認する。
- これにより「b の**無条件**脱出は excludedCommands 単体ではなく、`Bash(*)` による**行全体の自動承認**との積」であることを実証する。**allowUnsandboxed 経路を分離した S5-e の、excludedCommands 経路版**。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "excludedCommands": ["echo *"] },
  "permissions": { "allow": ["Bash(echo *)"] }
}
```

- b と唯一違うのは `allow`：`["Bash(*)"]` → `["Bash(echo *)"]`。sandbox 側（`excludedCommands`）は b と同一。
- 実行コマンドは b と同一（`echo hi && cat /etc/hostname > $HOME/lab-h.txt`、後段 `cat` は**非 excluded**）。

## 実行内容

1. Bash で `echo hi && cat /etc/hostname > $HOME/lab-h.txt`（1 コマンド）を実行

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo hi && cat … > ~/lab-h.txt`（cwd 外・後段非excluded） | ask | ✅ | 後段 `cat` が `Bash(echo *)` に不一致 → 承認プロンプト。承認すれば b 同様に脱出 |

- **`ask ✅` = 行に excluded の `echo` を含んでも、Bash 呼び出し自体の permission 判定で後段 `cat` が承認待ちに落ちる。** b（`Bash(*)` あり）は同じ行が `allow ✅`（無条件で `cat` ごと脱出）だったのと対照的で、差は `Bash(*)` の有無だけ。
- headless では承認者不在で auto-deny → 脱出しない。SDK で `canUseTool` が Bash 呼び出しに発火（askFired=`Bash`）することを実測。

## なぜそうなるか

- **`excludedCommands` が緩めるのは sandbox 層だけ**（列挙トークンを含む行は sandbox 外で実行される）。**permission 層は別レイヤ**で、Bash 呼び出しには依然として allow/ask/deny 判定が走る（一次 docs: sandboxing / P4 の複合コマンド規則＝各サブコマンドが独立にマッチ）。
- 複合コマンド `echo hi && cat …` は、後段 `cat` が `Bash(echo *)` にマッチしないため自動承認されず ask。よって b の脱出の十分条件は「excludedCommands」ではなく「**`Bash(*)` が行全体を自動承認すること**」。excludedCommands は「sandbox 内/外」を決めるだけで「承認する/しない」は決めない。
- **2 経路の対称性**: allowUnsandboxed 経路の増幅要因を分離した S5-e と機構が一致する。どちらも `Bash(*)` を外すと再試行/呼び出しが ask に落ち、無条件脱出が塞がる。SDK の askFired=`Bash`（両者共通）。

## 運用時の留意事項

- **`excludedCommands` を最小化しても、`Bash(*)` を併用すると行全体が自動承認され、チェーンした任意の非 excluded コマンドが sandbox 外で走る**（b）。逆に **allow を狭く保つ（`Bash(*)` を使わない）だけで、excluded を含む行の後段も ask ゲートに落ちる**（本ケース）。
- ただし headless/CI（承認者不在）では ask は auto-deny になる一方、対話で人が承認すれば脱出する。excludedCommands そのものを最小化する（理想は `[]`）のが一次防御で、`Bash(*)` 回避は二次防御。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。後段 `cat` で承認プロンプトが出る（b では出なかった）ことが観察できる。

```bash
cd cases/S5-sandbox-excluded-and-unsandboxed/h-excluded-without-bashstar && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
# ヘッドレス: ask は承認者不在で auto-deny → DENIED（脱出しない）
python3 harness/run.py S5-sandbox-excluded-and-unsandboxed/h-excluded-without-bashstar

# SDK(canUseTool = ask の計測器): Bash 呼び出しの ask 発火を観測 → ASK
python3 harness/run.py -m sdk S5-sandbox-excluded-and-unsandboxed/h-excluded-without-bashstar
```

> probe=`permission`：excluded を含む行の Bash 呼び出しに対する permission 判定（自動承認 / ask）を測る対照ケース。ask の解決は形態で変わる（headless=auto-deny / SDK=ASK 観測 / 対話=承認プロンプト）。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(DENIED=auto-deny) / sdk(ASK, askFired=Bash) |

- 一次 docs 裏取り: 「`excludedCommands` は sandbox 外実行を許すが permission は別レイヤ」「複合コマンドは各サブコマンドが独立にマッチ」は公式 docs（sandboxing）/ P4 の実測に整合。本ケースは「excludedCommands があっても `Bash(*)` を外すと後段が ask になる」ことを実測し、b の無条件脱出の因果（`Bash(*)` との積）を分離した。

## 対応する知識

- グループ [S5 README](../README.md)（脱出の有無 / 因果の分離マトリクス）
- 関連: S5-b（`Bash(*)` ありで非 excluded の `cat` ごと無条件脱出）/ S5-e（allowUnsandboxed 経路の同型分離、askFired=Bash）/ P4（複合コマンドの permission マッチ）
