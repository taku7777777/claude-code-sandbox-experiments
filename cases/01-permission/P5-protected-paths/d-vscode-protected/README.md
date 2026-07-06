# P5-d: acceptEdits でも `.vscode/` への Write は保護パスとして ask(保護ディレクトリ/ファイル群の代表)

## 目的

- `.vscode/` が保護パスで、acceptEdits でも自動承認されず ask になることを確認する
- `.vscode` を代表に、保護対象が広い一群(ディレクトリ+ファイル)であることを示す

## 前提(設定)

```json
{}
```

- `--permission-mode acceptEdits`。書込先 `.vscode/PROBE.txt`
- a(`.git`)・c(`.claude`)と機構は同一。異なる保護ディレクトリで再現する

## 実行内容

1. Write で `.vscode/PROBE.txt` を作成(acceptEdits)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `.vscode/PROBE.txt`(acceptEdits) | ask | ✅ | 保護パス。承認すれば書ける(SDK で canUseTool 発火) |

## なぜそうなるか

- **`.vscode` は公式の保護ディレクトリ。** 公式リスト(permission-modes):
  - 保護**ディレクトリ**: `.git` `.config/git` `.vscode` `.idea` `.husky` `.cargo` `.devcontainer`
    `.yarn` `.mvn` `.claude`(例外: `.claude/worktrees`)
  - 保護**ファイル**: `.gitconfig` `.gitmodules` / shell rc 系(`.bashrc` `.zshrc` 等)/ `.npmrc` `.yarnrc` /
    `.mcp.json` `.claude.json` / `.pre-commit-config.yaml` ほか
- これらは default/acceptEdits/plan で常に **"Prompted"(= ask、承認すれば書ける)**。headless の DENIED は
  auto-deny で、SDK では canUseTool が Write で発火する。

## 運用時の留意事項

- IDE 設定・ツールチェーン設定(`.vscode` `.npmrc` `.mcp.json` 等)の誤書換え事故を防ぐ安全側の挙動。
- ⚠️ **bypassPermissions ではこれら保護パスへの write プロンプトも skip される**(公式 permissions.md 明記)。
  プロンプトが残るのは acceptEdits まで。→ [グループ README](../README.md) / [e-bypass-git](../e-bypass-git/README.md)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude --permission-mode acceptEdits` を起動し、
[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。`.vscode/PROBE.txt` の書込で承認プロンプト(ask)が
出ることが確認できる。

```bash
cd cases/P5-protected-paths/d-vscode-protected && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので3形態で ask の解決差を実測できる。

```bash
# ヘッドレス: ask は auto-deny → DENIED
python3 harness/run.py P5-protected-paths/d-vscode-protected

# SDK(canUseTool = ask の計測器): Write の ask 発火を観測 → ASK
python3 harness/run.py -m sdk P5-protected-paths/d-vscode-protected

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P5-protected-paths/d-vscode-protected
python3 harness/run.py -m interactive --step judge P5-protected-paths/d-vscode-protected \
  --answer prompted=y --answer approved=y
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(DENIED=auto-deny)/ sdk(ASK・canUseTool 発火。1プローブ一致) |

## 対応する知識

- グループ [P5 README](../README.md)
- 関連: P5-a(.git)/ P5-c(.claude)= 同機構 / P5-e(bypass では保護パスも allow)
