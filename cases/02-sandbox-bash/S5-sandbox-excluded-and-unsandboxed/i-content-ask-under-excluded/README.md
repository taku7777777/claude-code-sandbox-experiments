# S5-i: excludedCommands で sandbox 外に出るコマンドでも content-scoped ask 規則は貫通する（permission 層は sandbox 脱出と独立）

## 目的

⚠️ S5 README が「未検証」として残していた核心の1つ——**excludedCommands で sandbox 外に出たコマンドは、permission 層の content-scoped ask 規則を素通りするか**——を実測で決着させる。

- もし素通りするなら「excluded 化が ask を無効化する」危険な穴になる。実測はそうならず、**ask は貫通してプロンプトを強制する**（excludedCommands は sandbox 層だけを緩め、permission 層は別レイヤ）。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "excludedCommands": ["touch *"] },
  "permissions": { "ask": ["Bash(touch *)"] }
}
```

- `excludedCommands:["touch *"]` = sandbox 層で touch を **unsandboxed 実行**にする。
- `ask:["Bash(touch *)"]` = permission 層で touch を **確認制**にする。
- `Bash(*)` allow は**置かない**（ask 規則が支配的になるように）。
- 実行コマンドは `touch $HOME/s5i-proof.txt`（cwd 外 `$HOME` を対象）。excluded なので unsandboxed だが、同時に content-scoped ask の対象でもある。

## 実行内容

1. Bash で `touch $HOME/s5i-proof.txt` を実行（excluded かつ content-ask 対象のコマンド）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `touch ~/s5i-proof.txt`（excluded かつ ask 対象） | ask | ✅ | excluded で sandbox 外に出ても content-scoped ask は貫通して承認要求 |

- `ask ✅` = 承認すれば通る。SDK で `canUseTool` が `Bash` で発火（askFired=['Bash']）＝ask が実際にゲートしている。headless では承認者不在で auto-deny（denials=['Bash']・ファイル未作成）。

## なぜそうなるか

- **`excludedCommands` が緩めるのは sandbox 層だけで、permission 層（allow/ask/deny 規則）は別レイヤ**（S5-b/h で確立）。だから touch が unsandboxed 実行になっても、content-scoped ask `Bash(touch *)` はそのまま評価され、プロンプトを強制する。
- **S4-f と同型**: auto-allow（`autoAllowBashIfSandboxed`）という別の緩和経路でも content-scoped ask は貫通した。excludedCommands という**別の sandbox 脱出**でも、permission 層の content ask は独立に効く——「sandbox をどう緩めても、content-scoped ask の確認ゲートは permission 層で生き残る」。
- 対照（bare ask との差）: S4-e では **bare `Bash` ask** は sandbox 実行分でスキップされた。content-scoped（`Bash(touch *)`）は貫通する（本ケース）。ask の効き方は「bare か content-scoped か」で割れる（S4-e/f と同じ非対称）。

## 運用時の留意事項

- **content-scoped ask は excludedCommands の脱出穴を部分的に塞ぐ**: `excludedCommands` で sandbox 外に出したコマンドでも、危険操作に content-scoped ask（例 `Bash(git push *)` / `Bash(rm *)`）を張れば確認ゲートは残る。
- ただし ask は **dontAsk モードでは deny に化け**（P6-e）、headless/CI では auto-deny。非対話で確実に止めたいなら ask ではなく deny を、境界そのものは sandbox FS/network を使う。
- bare `Bash` ask は sandbox 実行分をスキップする（S4-e）ので、ask で締めるなら**必ず content-scoped 形**で書く。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。excluded な touch でも承認プロンプトが出るのが見どころ。

```bash
cd cases/S5-sandbox-excluded-and-unsandboxed/i-content-ask-under-excluded && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので **3 形態で ask の解決が変わる**（headless=auto-deny / SDK=canUseTool 発火 / 対話=承認プロンプト）:

```bash
python3 harness/run.py S5-sandbox-excluded-and-unsandboxed/i-content-ask-under-excluded            # headless: auto-deny
python3 harness/run.py -m sdk S5-sandbox-excluded-and-unsandboxed/i-content-ask-under-excluded     # sdk: ASK（askFired=Bash）
```

> headless 単独では ask と deny を区別できない（両方 DENIED）。engine=ask の確定には SDK の `canUseTool` 発火が要る（→ docs/EXECUTION-MODALITIES.md）。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin/sandbox-exec) | headless(DENIED=auto-deny・denials=['Bash']) / sdk(ASK・askFired=['Bash']) |
| 2026-07-06 | v2.1.201 | macOS(darwin/sandbox-exec) | **対話(cmux 駆動)**: TUI が **`Bash command (unsandboxed)`** と表示しつつ `Permission rule Bash(touch *) requires confirmation for this command.` の承認プロンプトを実出現(excluded=sandbox 外でも content ask は貫通)→承認で完遂(ask ✅)。3 点セット完成 |

- 一次 docs 裏取り: content-scoped ask が auto-allow を貫通することは公式 docs（permissions / sandboxing）に明記（S4-f 参照）。**excludedCommands 経路での貫通は docs 未記載**【要裏取り】＝本ケースの観測で確定（sandbox 脱出の種類に依らず permission 層は独立、という一般則の一断面）。

## 対応する知識

- docs/FINDINGS.md: excludedCommands は sandbox 層のみ緩め permission 層は独立（content ask 貫通）
- グループ [S5 README](../README.md)
- 関連: S5-b/h（excludedCommands は sandbox 層だけ緩める）/ S4-f（auto-allow でも content-scoped ask は貫通）/ S4-e（bare `Bash` ask は sandbox 実行分スキップ＝ask の形依存）/ P6（ask 規則の 3 値）
